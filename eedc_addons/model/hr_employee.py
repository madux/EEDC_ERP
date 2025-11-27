from odoo import models, fields, api, _
import random
from difflib import SequenceMatcher
import logging
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# class HRDistrict(models.Model):
#     _name = "hr.district"
#     _description = "HR district Addons"

#     name = fields.Char(
#         string="Name", 
#         required=True
#         )
#     state_id = fields.Many2one(
#         'res.country.state',
#         string="Country", 
#         required=False
#         )
#     branch_id = fields.Many2one(
#         'multi.branch',
#         string="Branch", 
#         required=False
#         )


# class HREmployeePublic(models.Model):
#     _inherit = "hr.employee.public"
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    
    first_name = fields.Char(string="First name", required=True, copy=False)
    middle_name = fields.Char(string="Middle name", copy=False)
    last_name = fields.Char("Surname", required=True, copy=False)
    house_address = fields.Char(string='House Address', groups="base.group_user")
    age = fields.Char(string='Age', groups="base.group_user")
    local_government = fields.Many2one('res.lga', string='LGA')
    state_id = fields.Many2one('res.country.state', string='State')
    state_of_origin = fields.Char(string='State of Origin')
    lga = fields.Char(string='Local Goovernment') 
    rank_id = fields.Many2one('hr.rank', string='Rank')
    is_external_staff = fields.Boolean(string='Is External')
    external_company_id = fields.Many2one('res.partner', string='External Company')
    next_of_kin_ids = fields.Many2many('res.partner', 'nok_partner_public_rel', 'nok_partner_public_id', string='Next of Kin(s)')

    spouse_name = fields.Char(string='Spouse Name')
    spouse_telephone = fields.Char(string='Spouse Telephone')
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    manager = fields.Boolean(string="Is a Manager")


class HREmployee(models.Model):
    _inherit = "hr.employee"

    # name = fields.Char(string="Name", compute='_compute_full_name', store=True, required=False)
    first_name = fields.Char(string="First name", required=True, copy=False)
    middle_name = fields.Char(string="Middle name", copy=False)
    last_name = fields.Char("Surname", required=True, copy=False)
    house_address = fields.Char(string='House Address', groups="base.group_user")
    age = fields.Char(string='Age')
    local_government = fields.Many2one('res.lga', string='LGA')
    state_id = fields.Many2one('res.country.state', string='State')
    state_of_origin = fields.Char(string='State of Origin')
    lga = fields.Char(string='Local Goovernment') 
    rank_id = fields.Many2one('hr.rank', string='Rank')
    is_external_staff = fields.Boolean(string='Is External')
    external_company_id = fields.Many2one('res.partner', string='External Company')
    next_of_kin_ids = fields.Many2many('res.partner', 'nok_partner_rel', 'nok_partner_id', string='Next of Kin(s)')

    spouse_name = fields.Char(string='Spouse Name')
    spouse_telephone = fields.Char(string='Spouse Telephone')
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    manager = fields.Boolean(string="Is a Manager")
    query_number = fields.Integer(string="Query", copy=False, compute="compute_number_queries") 
    warning_number = fields.Integer(string="Warning", copy=False, compute="compute_number_warning") 
    
    def transfer_employee_action(self):
        rec_ids = self.env.context.get('active_ids', [])
        employee = self.env['hr.employee']
        # emp_transfer = self.env['hr.employee.transfer'].sudo()
        # emp_transfer_id = emp_transfer.create({
        #     'employee_ids': [(6, 0, [rec for rec in rec_ids])],
        #     'employee_transfer_lines': [(0, 0, {
        #               'employee_id': employee.browse([emp]).id,
        #               'current_dept_id': employee.browse([emp]).department_id.id,
        #           }) for emp in rec_ids],

        # })
        # view_id = self.env.ref('eedc_addons.view_hr_employee_transfer_form').id
        # ret = {
        #     'name': "Employee Transfer",
        #     'view_mode': 'form',
        #     'view_id': view_id,
        #     'view_type': 'form',
        #     'res_model': 'hr.employee.transfer',
        #     'res_id': emp_transfer_id.id,
        #     'type': 'ir.actions.act_window',
        #     'domain': [],
        #     'target': 'new'
        #     }
        # return ret
    
        return {
              'name': 'Employee Transfer',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.transfer',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_employee_ids': rec_ids,
                  'default_employee_transfer_lines': [(0, 0, {
                      'employee_id': employee.browse([emp]).id, 
                      'current_dept_id': employee.browse([emp]).department_id.id,
                  }) for emp in rec_ids]
              },
        }
    

    def stats_transfer_employee_lines(self):
        return {
            'name': _('Employee Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.transfer.line',
            'views': [[self.env.ref('eedc_addons.hr_employee_transfer_line_view_tree').id, 'tree']],
            'domain': [('employee_id', 'in', self.ids)],
        }
    
    # def stats_transfer_employee_lines(self):
    #     return {
    #           'name': 'Employee Transfer', 
    #         # 'views': [[self.env.ref('hr_holidays.hr_leave_employee_view_dashboard').id, 'tree']],
    #         #   "view_id": self.env.ref('eedc_addons.view_hr_employee_transfer_form'),
    #           'res_model': 'hr.employee.transfer',
    #           'type': 'ir.actions.act_window',
    #         #   'target': 'current',
    #           'domain': [], #[('employee_id', 'in', self.ids)],
    #           }, 
    
    
    employee_transfer_history = fields.One2many( 
        'hr.employee.transfer.line', 
        'employee_id', 
        string='Transfer History'
        )
    
    
    def action_update_memo_model_employee(self):
        """
        Update memo.model records to reference the correct current employee.
        Supports multi-record update via window action (active_ids).
        """
        MemoModel = self.env['memo.model']

        rec_ids = self.env.context.get('active_ids', [])
        employees = self.browse(rec_ids)

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for employee in employees:
            if not employee.user_id:
                _logger.info(f"Employee {employee.name} has no linked user, skipping")
                skipped_count += 1
                continue

            user = employee.user_id

            # All memos created by that user
            memo_records = MemoModel.sudo().search([('create_uid', '=', user.id)])

            if not memo_records:
                _logger.info(f"No memo records found for user {user.login} (employee: {employee.name})")
                continue

            _logger.info(f"Found {len(memo_records)} memo records for user {user.login}")

            for memo in memo_records:
                try:
                    # If already correct, skip
                    if memo.employee_id and memo.employee_id.id == employee.id:
                        skipped_count += 1
                        continue

                    if memo.employee_id:
                        old_employee = memo.employee_id

                        similarity = self._calculate_name_similarity(
                            old_employee.name or '',
                            employee.name or ''
                        )

                        _logger.info(
                            f"Memo {memo.id}: Old '{old_employee.name}' vs New '{employee.name}' "
                            f"- Similarity: {similarity:.2%}"
                        )

                        # Only update if similarity >= 60%
                        if similarity >= 0.60:
                            memo.sudo().write({'employee_id': employee.id})
                            _logger.info(f"Updated memo {memo.id}: {old_employee.name} -> {employee.name}")
                            updated_count += 1
                        else:
                            _logger.warning(
                                f"Skipped memo {memo.id}: Name mismatch "
                                f"(similarity {similarity:.2%}). Old='{old_employee.name}', New='{employee.name}'"
                            )
                            skipped_count += 1
                    else:
                        # No employee assigned → assign directly
                        memo.sudo().write({'employee_id': employee.id})
                        _logger.info(f"Assigned employee to memo {memo.id}: {employee.name}")
                        updated_count += 1

                except Exception as e:
                    _logger.exception(f"Error updating memo {memo.id}: {str(e)}")
                    error_count += 1

        # ---- FINAL RESPONSE ----
        message_parts = []
        if updated_count:
            message_parts.append(f"{updated_count} memo(s) updated")
        if skipped_count:
            message_parts.append(f"{skipped_count} memo(s) skipped")
        if error_count:
            message_parts.append(f"{error_count} error(s) occurred")

        message = ", ".join(message_parts) if message_parts else "No changes made"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Memo Employee Update Complete',
                'message': message,
                'type': 'success' if not error_count else 'warning',
                'sticky': True,
            }
        }


    def _calculate_name_similarity(self, name1, name2):
        """
        Uses SequenceMatcher to get similarity between two names.
        """
        name1_norm = ' '.join(name1.lower().split())
        name2_norm = ' '.join(name2.lower().split())
        return SequenceMatcher(None, name1_norm, name2_norm).ratio()
    
    # @api.onchange('first_name', 'middle_name', 'last_name')
    # def onchange_update_full_name(self):
    #     self.name = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))
    #     # self.name = " ".join([name for name in [self.first_name, self.middle_name, self.last_name] if name])

    @api.onchange(
        'first_name','middle_name', 'last_name'
        )
    def onchange_of_applicants_name(self):
        fn, mm, ln = "", "", ""
        if self.first_name:
            fn = self.first_name
        if self.middle_name:
            mm = self.middle_name
        if self.last_name:
            ln = self.last_name
        self.name = f'{fn} {mm} {ln}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                name = " ".join(filter(None, [vals.get('first_name', ''), vals.get('middle_name', ''), vals.get('last_name', '')]))
                vals['name'] = name
        return super().create(vals_list)
    
    # @api.depends('first_name', 'middle_name', 'last_name')
    # def _compute_full_name(self):
    #     for record in self:
    #         current_fullname = record.name
    #         if record.first_name:
    #             non_empty_names = filter(None, [record.first_name, record.middle_name, record.last_name])
    #             full_name = " ".join(non_empty_names)
    #             record.name = full_name
    #         else:
    #             self.name = current_fullname

    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        employee_ids = []
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            if operator == 'ilike' and not (name or '').strip():
                domain = []
            else:
                domain = ['|', ('name', '=', name), ('employee_number', '=', name)]
            employee_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        if not employee_ids:
            employee_ids = self._search(expression.AND([['|',('name', operator, name), ('employee_number', operator, name)], args]), limit=limit, access_rights_uid=name_get_uid)
        return employee_ids
    


    
