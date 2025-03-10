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