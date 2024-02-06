from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountMoveMemo(models.Model):
    _inherit = 'account.move'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")
    origin = fields.Char(string="Source")
    payment_journal_id = fields.Many2one('account.journal', string="Payment Journal", required=False)

    def action_post(self):
        if self.memo_id:
            if self.memo_id.memo_type.memo_key == "soe":
                '''This is added to help send the soe reference to the related cash advance'''
                self.sudo().memo_id.cash_advance_reference.soe_advance_reference = self.memo_id.id
            self.memo_id.is_request_completed = True
            # self.memo_id.state = "Done"
        return super(AccountMoveMemo, self).action_post()
    
class AccountMove(models.Model):
    _inherit = 'account.move.line'

    code = fields.Char(string="Code")
    

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).post()
        for rec in self.move_ids:
            if rec.memo_id:
                rec.memo_id.state = "Approve" # waiting for payment and confirmation
        return res

     