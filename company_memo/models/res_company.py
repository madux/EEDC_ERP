from datetime import datetime
from dateutil.parser import parse
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class resCompany(models.Model):
    _inherit = 'res.company'

    user_signature = fields.Binary("Upload User Signature")
    account_default_debit_account_id = fields.Many2one(
        "account.account", 
        string="Default Account",
        )