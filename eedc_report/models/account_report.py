# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountReport(models.Model):
    """
    Extend account.report model to add branch and account type filter fields
    """
    _inherit = 'account.report'

    # Add branch filter field
    filter_multi_branch = fields.Boolean(
        string='Enable Branch Filter',
        help='Allow filtering by organizational branch',
        default=False,
    )

    # Add account type filter field
    filter_account_type = fields.Boolean(
        string='Enable Account Type Filter',
        help='Allow filtering by account type',
        default=False,
    )