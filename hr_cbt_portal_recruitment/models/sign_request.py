# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _  

class SignRequest(models.Model):
    _inherit = "sign.request"

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Applicant'
        )
    dummy_share_link = fields.Char(
        string='Dummy Shared Link'
        )
    is_currently_sent = fields.Boolean(
        string='Currently sent', 
        help="Used to determine the current signature request to send"
        )
    
    
    