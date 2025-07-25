from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    maximum_cash_advance_limit = fields.Integer(
        string="Maximum Limit Cash Advance", 
        default=5
        )
    
    # company_id = fields.Many2one(
    #     'res.company',
    #     string="Company",
    #     default=lambda self: self.env.user.company_id.id,
    #     compute="compute_related_user_company"
    # )
    
    # @api.depends('user_id')
    # def compute_related_user_company(self):
    #     for rec in self:
    #         current_company = rec.company_id if rec.company_id else False 
    #         if rec.user_id:
    #             rec.company_id = rec.user_id.company_id.id
    #         else:
    #             rec.company_id = current_company.id