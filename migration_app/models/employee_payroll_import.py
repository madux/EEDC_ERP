from odoo import fields, models ,api, _

class ProductCategory(models.Model):
    _inherit = "product.category"
    
    code = fields.Char("Code")
