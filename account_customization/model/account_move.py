from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    
    def button_set_draft(self):
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['account.move'].browse([rec])
            record.button_draft()
    
    def button_set_cancel(self):
        rec_ids = self.env.context.get('active_ids', []) 
        for rec in rec_ids:
            record = self.env['account.move'].browse([rec])
            record.button_cancel()
    