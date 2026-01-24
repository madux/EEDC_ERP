# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    account_asset_model = fields.Many2one(
        "account.asset", 
        string="Asset model",
        )
    sum_up_total = fields.Boolean(
        'Sum up total', 
        help="If set, procurement price_total = total tax inclusive",
        default=False
        )
    
    
    
    
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    account_asset_model = fields.Many2one(
        "account.asset", 
        string="Asset model",
        ) 
    part_number = fields.Char(
        string="Part number",
        ) 
    sum_up_total = fields.Boolean(
        'Sum up total', 
        help="If set, procurement price_total = total tax inclusive",
        related="categ_id.sum_up_total",
        default=False,
        store=True,
        readonly=True,
        )

    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    account_asset_model = fields.Many2one(
        "account.asset", 
        string="Asset model",
        ) 
    part_number = fields.Char(
        string="Part number",
        )
    
    sum_up_total = fields.Boolean(
        'Sum up total', 
        help="If set, procurement price_total = total tax inclusive",
        related="categ_id.sum_up_total",
        default=False,
        store=True,
        readonly=True,
        )