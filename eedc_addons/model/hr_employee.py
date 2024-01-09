from odoo import models, fields, api, _
import random
import logging
_logger = logging.getLogger(__name__)


# class HREmployee(models.Model):
#     _inherit = "hr.employee"

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    

    house_address = fields.Char(string='House Address')
    age = fields.Char(string='Age')
    local_government = fields.Many2one('res.lga', string='LGA')
    state_id = fields.Many2one('res.country.state', string='State')
    state_of_origin = fields.Char(string='State of Origin')
    lga = fields.Char(string='Local Government') 
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
