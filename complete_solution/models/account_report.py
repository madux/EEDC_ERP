# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_multi_branch = fields.Boolean(string='Branch Filter', default=False)
    filter_account_type = fields.Boolean(string='Account Type Filter', default=False)
