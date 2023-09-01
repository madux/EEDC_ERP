from odoo import models, fields, api, _
from odoo.exceptions import ValidationError 


class MemoConfig(models.Model):
    _name = "memo.config"
    _description = "Memo setting"
    _rec_name = "memo_type"

    # name = fields.Char(string="Name")
    memo_type = fields.Selection(
        [
        ("Payment", "Payment"),
        ("loan", "Loan"),
        ("Internal", "Internal Memo"),
        ("material_request", "Material request"),
        ("procurement_request", "Procurement Request"),
        ("vehicle_request", "Vehicle request"),
        ("leave_request", "Leave request"),
        ("cash_advance", "Cash Advance"),
        ("soe", "Statement of Expense"),
        ], string="Memo Type",default="", required=True)
    
    approver_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_memo_config_rel',
        'hr_employee_memo_id',
        'config_memo_id',
        string="Employees for approvals",
        required=True
        )
    active = fields.Boolean(string="Active", default=True)

    @api.constrains('memo_type')
    def _check_duplicate_memo_type(self):
        memo = self.env['memo.config'].sudo()
        for rec in self:
            duplicate = memo.search([('memo_type', '=', rec.memo_type)], limit=2)
            if len([r for r in duplicate]) > 1:
                raise ValidationError("A memo type has already been configured for this record, kindly locate it and select the approvers")
           
