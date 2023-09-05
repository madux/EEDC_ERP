from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountMove(models.Model):
    _inherit = 'account.move'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    district_id = fields.Many2one('hr.district', string="District")
    origin = fields.Char(string="Source")
    
    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.memo_id:
            self.memo_id.state = "Done"
            if self.memo_id.memo_type == "soe":
                '''This is added to help send the soe reference to the related cash advance'''
                self.sudo().memo_id.cash_advance_reference.soe_advance_reference = self.memo_id.id
        return res
    

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    district_id = fields.Many2one('hr.district', string="District")
    
    def reverse_moves(self):
        res = super(AccountMoveReversal, self).post()
        for rec in self.move_ids:
            if rec.memo_id:
                rec.memo_id.state = "Approve" # waiting for payment and confirmation
        return res

     