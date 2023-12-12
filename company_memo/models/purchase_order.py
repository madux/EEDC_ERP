from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Memo Reference')
    
    def update_memo_status(self, status):
        if self.memo_id:
            self.memo_id.state = status
        else: 
            if self.origin:
                memo = self.env['memo.model'].browse([
                    ('code', '=', self.origin)
                    ])
                if memo:
                    memo.state = status
    
    def button_confirm(self):
        # is request completed is used to determine if the entire process is done
        if self.memo_id:
            self.memo_id.is_request_completed = True
            self.sudo().memo_id.update_final_state_and_approver()
        res = super(PurchaseOrder, self).button_confirm()
        return res
    
    ## dont cancel the memo because it might affect memo record
    # def button_cancel(self):
    #     res = super(PurchaseOrder, self).button_cancel()
    #     # self.update_memo_status('Done') 
    #     return res