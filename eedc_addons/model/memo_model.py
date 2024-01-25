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