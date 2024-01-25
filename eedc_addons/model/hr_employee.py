from odoo import models, fields, api, _
import random
import logging
_logger = logging.getLogger(__name__)


class HREmployeePublic(models.Model):
    _inherit = "hr.employee.public"

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
    
    employee_transfer_history = fields.One2many( 
        'hr.employee.transfer.line', 
        'employee_id', 
        string='Transfer History'
        )
    
    # def open_employee_transfer_history():
    #     pass

    transfer_history_count = fields.Integer(string="Offers Count", compute="_compute_offer")

    def _compute_offer(self):
        # This solution is quite complex. It is likely that the trainee would have done a search in
        # a loop.
        data = self.env["hr.employee.transfer.line"].read_group(
            [],
            ["ids:array_agg(id)", "employee_id"],
            ["employee_id"],
        )
        mapped_count = {d["employee_id"][0]: d["employee_id_count"] for d in data}
        # mapped_ids = {d["employee_id"][0]: d["ids"] for d in data}
        for transfer_history in self:
            transfer_history.transfer_history_count = mapped_count.get(transfer_history.id, 0)
            # prop_type.offer_ids = mapped_ids.get(prop_type.id, [])
