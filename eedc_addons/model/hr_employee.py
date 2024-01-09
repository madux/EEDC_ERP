from odoo import models, fields, api, _
import random
import logging
_logger = logging.getLogger(__name__)


# class HREmployee(models.Model):
#     _inherit = "hr.employee"

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    house_address = fields.Char(string='House Address', groups="hr.group_hr_user")
    age = fields.Char(string='Age', groups="hr.group_hr_user")
    local_government = fields.Many2one('res.lga', string='LGA', groups="hr.group_hr_user")
    state_id = fields.Many2one('res.country.state', string='State', groups="hr.group_hr_user")
    state_of_origin = fields.Char(string='State of Origin', groups="hr.group_hr_user")
    lga = fields.Char(string='Local Government', groups="hr.group_hr_user") 
    rank_id = fields.Many2one('hr.rank', string='Rank', groups="hr.group_hr_user")
    is_external_staff = fields.Boolean(string='Is External', groups="hr.group_hr_user")
    external_company_id = fields.Many2one('res.partner', string='External Company', groups="hr.group_hr_user")
    next_of_kin_ids = fields.Many2many('res.partner', 'nok_partner_rel', 'nok_partner_id', string='Next of Kin(s)', groups="hr.group_hr_user")

    spouse_name = fields.Char(string='Spouse Name', groups="hr.group_hr_user")
    spouse_telephone = fields.Char(string='Spouse Telephone', groups="hr.group_hr_user")
    father_name = fields.Char(string="Father's Name", groups="hr.group_hr_user")
    father_phone = fields.Char(string="Father's Phone", groups="hr.group_hr_user")
    mother_name = fields.Char(string="Mother's Name", groups="hr.group_hr_user")
    mother_phone = fields.Char(string="Mother's Phone", groups="hr.group_hr_user")
    manager = fields.Boolean(string="Is a Manager", groups="hr.group_hr_user")
