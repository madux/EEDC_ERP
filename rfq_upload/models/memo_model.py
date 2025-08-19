# models/memo_model.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MemoModel(models.Model):
    _inherit = 'memo.model'
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    # Add RFQ fields to existing memo model
    rfq_excel_file = fields.Binary(string="RFQ Excel File", help="Upload Excel file with RFQ data")
    rfq_excel_filename = fields.Char(string="RFQ Filename")
    rfq_uploaded = fields.Boolean(string="RFQ Uploaded", default=False)
    rfq_upload_date = fields.Datetime(string="RFQ Upload Date")
    
    def download_rfq_template(self):
        """Generate and return RFQ Excel template - simplified version"""
        try:
            import base64
            import io
            
            # Try to import pandas, if not available, create simple CSV
            try:
                import pandas as pd
                has_pandas = True
            except ImportError:
                has_pandas = False
            
            if has_pandas:
                # Create template data
                template_data = {
                    'VENDOR CODE': ['V001', 'V002'],
                    'VENDOR NAME': ['Sample Vendor 1', 'Sample Vendor 2'],
                    'VENDOR EMAIL': ['vendor1@example.com', 'vendor2@example.com'],
                    'VENDOR PHONE': ['+1234567890', '+0987654321'],
                    'VENDOR ADDRESS': ['123 Main St, City', '456 Oak Ave, Town'],
                    'PRODUCT CODE': ['P001', 'P002'],
                    'PRODUCT NAME': ['Sample Product 1', 'Sample Product 2'],
                    'QTY TO SUPPLY': [10, 5],
                    'PRICE PER QUANTITY': [100.00, 250.00],
                }
                
                # Create DataFrame and Excel file
                df = pd.DataFrame(template_data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='RFQ_Template', index=False)
                
                excel_file = base64.b64encode(output.getvalue())
                output.close()
                filename = 'RFQ_Template.xlsx'
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                # Fallback: Create simple CSV file
                csv_content = "VENDOR CODE,VENDOR NAME,VENDOR EMAIL,VENDOR PHONE,VENDOR ADDRESS,PRODUCT CODE,PRODUCT NAME,QTY TO SUPPLY,PRICE PER QUANTITY\n"
                csv_content += "V001,Sample Vendor 1,vendor1@example.com,+1234567890,123 Main St City,P001,Sample Product 1,10,100.00\n"
                csv_content += "V002,Sample Vendor 2,vendor2@example.com,+0987654321,456 Oak Ave Town,P002,Sample Product 2,5,250.00\n"
                
                excel_file = base64.b64encode(csv_content.encode('utf-8'))
                filename = 'RFQ_Template.csv'
                mimetype = 'text/csv'
            
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': excel_file,
                'res_model': 'memo.model',
                'res_id': self.id if hasattr(self, 'id') and self.id else False,
                'mimetype': mimetype
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % attachment.id,
                'target': 'self',
            }
            
        except Exception as e:
            raise ValidationError(_("Error generating template: %s") % str(e))
    
    def action_upload_rfq_wizard(self):
        """Open RFQ upload wizard"""
        return {
            'name': _('Upload RFQ Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_memo_id': self.id,
            }
        }