# wizard/rfq_upload_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RFQUploadWizard(models.TransientModel):
    _name = 'rfq.upload.wizard'
    _description = 'RFQ Upload Wizard'
    
    memo_id = fields.Many2one('memo.model', string="Memo", required=True)
    rfq_excel_file = fields.Binary(string="RFQ Excel File", required=True)
    rfq_excel_filename = fields.Char(string="Filename")
    
    def action_upload_rfq(self):
        """Process the uploaded RFQ file - basic version"""
        if not self.rfq_excel_file:
            raise ValidationError(_("Please upload a file first."))
        
        # Update memo with file data
        self.memo_id.write({
            'rfq_excel_file': self.rfq_excel_file,
            'rfq_excel_filename': self.rfq_excel_filename,
            'rfq_uploaded': True,
            'rfq_upload_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('RFQ file uploaded successfully. You can now process it manually.'),
                'sticky': False,
                'type': 'success'
            }
        }
    
    def action_download_template(self):
        """Download RFQ template"""
        return self.memo_id.download_rfq_template()