from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


import logging

_logger = logging.getLogger(__name__)

class EconomicTag(models.Model):
    _name = "economic.tag"

    name = fields.Char(string="Name")
    code = fields.Char("Code", required=True)
    parent_tag_id = fields.Many2one('economic.tag', string='Parent')
    
    account_type = fields.Selection(
        [
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        default="expense",
        string="Account Type",
    )
    
    account_head_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"),
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital Expenditure"),
        ("Other", "Others"),
        ], string="Budget Type", 
    )
    active = fields.Boolean(string='Active', default=True)
    
    account_ids = fields.Many2many('account.account')
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Code must be unique.')
    ]

    @api.constrains('code')
    def _check_code_hierarchy(self):
        for rec in self:
            if rec.parent_tag_id:
                try:
                    if int(rec.code) < int(rec.parent_tag_id.code):
                        raise ValidationError('Code must be greater than the parent\'s code.')
                except ValueError:
                    raise ValidationError('Code and parent code must be numeric to compare hierarchy.')
