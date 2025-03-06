from odoo import models, fields


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    
    branch_ids = fields.Many2many(comodel_name='hr.district', string='Branch')
    public_pricelist = fields.Boolean(string='Public Pricelist')
