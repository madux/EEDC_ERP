from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompanyMemo(models.Model):
    _inherit = "memo.model"

    company_id = fields.Many2one(
        'res.company', 
        default=lambda s: s.env.user.company_id.id,
        string='Company'
        )
    
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                default=lambda self: self.env.user.branch_id.id, required=False)
    
    
     