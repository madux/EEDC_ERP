# models/purchase_order.py - Extend purchase order model

from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    rfq_source = fields.Selection([
        ('manual', 'Manual Creation'),
        ('excel_upload', 'Excel Upload'),
        ('system_generated', 'System Generated')
    ], string="RFQ Source", default='manual', readonly=True)
    
    # memo_state = fields.Char(related='memo_id.state', string="Memo State", readonly=True)
    
    @api.model
    def create(self, vals):
        """Override create to set RFQ source"""
        # If created through RFQ upload wizard, mark as excel_upload
        if self.env.context.get('rfq_excel_upload'):
            vals['rfq_source'] = 'excel_upload'
        elif vals.get('memo_id'):
            vals['rfq_source'] = 'system_generated'
        
        return super(PurchaseOrder, self).create(vals)


# Add method to memo model for the wizard action
class MemoModelExtended(models.Model):
    _inherit = 'memo.model'
    
    def action_upload_rfq_wizard(self):
        """Open RFQ upload wizard"""
        return {
            'name': 'Upload RFQ Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_memo_id': self.id,
                'rfq_excel_upload': True
            }
        }
    
    def action_download_rfq_template(self):
        """Download RFQ template - calls the existing method"""
        return self.download_rfq_template()
    
    @api.model
    def _create_or_update_po(self, vendor, line_data):
        """Override to set context for RFQ source"""
        # Set context to indicate this is from Excel upload
        return super(MemoModelExtended, self.with_context(rfq_excel_upload=True))._create_or_update_po(vendor, line_data)
    