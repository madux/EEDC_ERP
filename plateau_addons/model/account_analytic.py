from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class accountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    code = fields.Char(string='Code')
    
     