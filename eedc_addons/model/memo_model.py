from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

class MemoModel(models.Model):
    _inherit = 'memo.model'

    employee_transfer_line_ids = fields.One2many( 
        'hr.employee.transfer.line', 
        'memo_id', 
        string='Employee Transfer Lines'
        )
    district_id = fields.Many2one("hr.district", string="District ID")
    
    def finalize_employee_transfer(self):
        body_msg = f"""Dear {self.employee_id.name}, 
        <br/>I wish to notify you that a {type} with description, '{self.name}',\
        from {self.employee_id.department_id.name or self.user_ids.name} \
        department have been Confirmed by {self.env.user.name}.<br/>\
        Respective authority should take note. \
        <br/>Kindly {self.get_url(self.id)} <br/>\
        Yours Faithfully<br/>{self.env.user.name}"""
        self.update_final_state_and_approver()
        self.mail_sending_direct(body_msg)
        self.state = 'Done'

    def generate_employee_transfer(self):
        """Check if the user is enlisted as the approver for memo type"""
        view_id = self.env.ref('eedc_addons.view_hr_employee_transfer_form').id
        employee_ids = [rec.employee_id.id for rec in self.employee_transfer_line_ids]
        ret = {
            'name': "Employee transfer request",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.employee.transfer',
            # 'res_id': rr_id.id,
            'type': 'ir.actions.act_window',
            # 'domain': [],
            'context': {
                'default_memo_id': self.id,
                'default_employee_ids': [(6, 0, employee_ids)],
                'default_employee_transfer_lines': [(4, line.id) for line in self.employee_transfer_line_ids]
            },
            'target': 'new'
            }
        return ret 


class Requestline(models.Model):
    _inherit = 'request.line'

    district_id = fields.Many2one("hr.district", string="District ID")


class AccountAccount(models.Model):
    _inherit = 'account.account'

    district_id = fields.Many2one('hr.district', string="District")

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    district_id = fields.Many2one('hr.district', string="District")