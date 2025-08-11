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