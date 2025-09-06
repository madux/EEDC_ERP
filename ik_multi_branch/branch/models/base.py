# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import ValidationError, UserError, AccessError
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'
    branch_ids = fields.Many2many('multi.branch', string='Allowed branches')

    @api.model
    def _get_default_branch(self):
        return self.env.user.branch_id
    
    @api.constrains('groups_id')
    def _check_one_user_type(self):
        """We check that no users are both portal and users (same with public).
           This could typically happen because of implied groups.
        """
        user_types_category = self.env.ref('base.module_category_user_type', raise_if_not_found=False)
        user_types_groups = self.env['res.groups'].search(
            [('category_id', '=', user_types_category.id)]) if user_types_category else False
        if user_types_groups:  # needed at install
            if self._has_multiple_groups(user_types_groups.ids):
                # if self.has_group('base.group_portal'):
                #     pass
                # else:
                raise ValidationError(_('The user cannot have more than one user types.'))
                
    
    def _has_multiple_groups(self, group_ids):
        """Find users that are members of >1 of the provided groups.
        If found, remove them from those groups and add them to portal.
        Returns True if at least one user was reassigned.
        """
        if not group_ids:
            return False

        # Normalize group_ids to ints/tuple for SQL
        group_ids = [int(g) for g in group_ids]
        args = [tuple(group_ids)]
        if len(self.ids) == 1:
            where_clause = "AND r.uid = %s"
            args.append(self.id)
        else:
            where_clause = ""

        # Find users that belong to more than one of the supplied groups
        query = """
            SELECT r.uid
            FROM res_groups_users_rel r
            WHERE r.gid IN %s """ + where_clause + """
            GROUP BY r.uid
            HAVING COUNT(DISTINCT r.gid) > 1
        """
        self.env.cr.execute(query, args)
        users = [row[0] for row in self.env.cr.fetchall()]

        if not users:
            return False

        # Use ORM to modify groups (keeps cache and access rules correct)
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        if not portal_group:
            # If portal group can't be found, bail out (or raise if you prefer)
            return False

        # Build write commands:
        # (3, gid) => remove that group; (4, portal_group.id) => add portal group
        ops = [(3, int(g)) for g in group_ids] + [(4, portal_group.id)]

        # Use sudo() if this code may run as a user without the right to change groups
        self.env['res.users'].browse(users).sudo().write({'groups_id': ops})

        return False
    
    # def write(self, vals):
    #     if 'groups_id' in vals and self.has_group('base.group_portal'):
    #         import traceback
    #         _logger.warning(f"Portal user groups being modified: {self.name}")
    #         _logger.warning(f"New groups: {vals['groups_id']}")
    #         _logger.warning(f"Traceback: {traceback.format_stack()}")
    #     return super(ResUsers, self).write(vals)
    
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    
    def write(self, values):
        if 'parent_id' in values:
            manager = self.env['hr.employee'].browse(values['parent_id']).user_id
            if manager:
                to_change = self.filtered(lambda e: e.leave_manager_id == e.parent_id.user_id or not e.leave_manager_id)
                to_change.write({'leave_manager_id': values.get('leave_manager_id', manager.id)})

        old_managers = self.env['res.users']
        if 'leave_manager_id' in values:
            old_managers = self.mapped('leave_manager_id')
            if values['leave_manager_id']:
                leave_manager = self.env['res.users'].browse(values['leave_manager_id'])
                old_managers -= leave_manager
                approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
                if approver_group and not leave_manager.has_group('hr_holidays.group_hr_holidays_responsible'):
                    pass
                    # raise ValidationError("Changing Leave manager!!")
                    # leave_manager.sudo().write({'groups_id': [(4, approver_group.id)]})

        res = super(HrEmployeeBase, self).write(values)
        # remove users from the Responsible group if they are no longer leave managers
        # old_managers.sudo()._clean_leave_responsible_users()

        if 'parent_id' in values or 'department_id' in values:
            today_date = fields.Datetime.now()
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].sudo().search(['|', ('state', 'in', ['draft', 'confirm']), ('date_from', '>', today_date), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        return res

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _branch_default_get(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one('multi.branch', string='Branch', default=_branch_default_get)


class IrRule(models.Model):
    _inherit = 'ir.rule'
    branch_ids = fields.Many2many('multi.branch', string='Allowed branches')
     
    def _make_access_error(self, operation, records):
        _logger.info('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, records.ids[:6], self._uid, records._name)

        model = records._name
        description = self.env['ir.model']._get(model).name or model
        msg_heads = {
            # Messages are declared in extenso so they are properly exported in translation terms
            'read':   _("Due to security restrictions, you are not allowed to access '%(document_kind)s' (%(document_model)s) records.", document_kind=description, document_model=model),
            'write':  _("Due to security restrictions, you are not allowed to modify '%(document_kind)s' (%(document_model)s) records.", document_kind=description, document_model=model),
            'create': _("Due to security restrictions, you are not allowed to create '%(document_kind)s' (%(document_model)s) records.", document_kind=description, document_model=model),
            'unlink': _("Due to security restrictions, you are not allowed to delete '%(document_kind)s' (%(document_model)s) records.", document_kind=description, document_model=model)
        }
        operation_error = msg_heads[operation]
        resolution_info = _("Contact your administrator to request access if necessary.")

        # if not self.env.user.has_group('base.group_no_one') or not self.env.user.has_group('base.group_user'):
        #     return AccessError(f"{operation_error}\n\n{resolution_info}")

        # This extended AccessError is only displayed in debug mode.
        # Note that by default, public and portal users do not have
        # the group "base.group_no_one", even if debug mode is enabled,
        # so it is relatively safe here to include the list of rules and record names.
        rules = self._get_failing(records, mode=operation).sudo()

        records_sudo = records[:6].sudo()
        company_related = any('company_id' in (r.domain_force or '') for r in rules)

        def get_record_description(rec):
            # If the user has access to the company of the record, add this
            # information in the description to help them to change company
            if company_related and 'company_id' in rec and rec.company_id in self.env.user.company_ids:
                return f'{rec.display_name} (id={rec.id}, company={rec.company_id.display_name})'
            return f'{rec.display_name} (id={rec.id})'

        records_description = ', '.join(get_record_description(rec) for rec in records_sudo)
        failing_records = _("Records: %s", records_description)

        user_description = f'{self.env.user.name} (id={self.env.user.id})'
        failing_user = _("User: %s", user_description)

        rules_description = '\n'.join(f'- {rule.name}' for rule in rules)
        failing_rules = _("This restriction is due to the following rules:\n%s", rules_description)
        if company_related:
            failing_rules += "\n\n" + _('Note: this might be a multi-company issue.')

        # clean up the cache of records prefetched with display_name above
        records_sudo.invalidate_recordset()

        msg = f"{operation_error}\n\n{failing_records}\n{failing_user}\n\n{failing_rules}\n\n{resolution_info}"
        return AccessError(msg)