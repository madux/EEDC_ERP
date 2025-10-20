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
            

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        for line in self:
            account_type = line.account_id.account_type
            if line.move_id.is_sale_document(include_receipts=True):
                if (line.display_type == 'payment_term') ^ (account_type == 'asset_receivable'):
                    pass 
                    # raise UserError(_("Any journal item on a receivable account must have a due date and vice versa."))
            if line.move_id.is_purchase_document(include_receipts=True):
                if (line.display_type == 'payment_term') ^ (account_type == 'liability_payable'):
                    pass 
                    # raise UserError(_("Any journal item on a payable account must have a due date and vice versa."))
    