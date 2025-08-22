# models/purchase_order.py
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    rfq_source = fields.Selection([
        ('manual', 'Manual Creation'),
        ('excel_upload', 'Excel Upload'),
        ('system_generated', 'System Generated')
    ], string="RFQ Source", default='manual', readonly=True)
    
    @api.model
    def create(self, vals):
        """Override create to set RFQ source"""
        # If created through RFQ upload wizard, mark as excel_upload
        if self.env.context.get('rfq_excel_upload'):
            vals['rfq_source'] = 'excel_upload'
        elif vals.get('memo_id'):
            vals['rfq_source'] = 'system_generated'
        
        return super(PurchaseOrder, self).create(vals)