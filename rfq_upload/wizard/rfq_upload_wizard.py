# wizard/rfq_upload_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
import logging

_logger = logging.getLogger(__name__)

class RFQUploadWizard(models.TransientModel):
    _name = 'rfq.upload.wizard'
    _description = 'RFQ Upload Wizard'
    
    memo_id = fields.Many2one('memo.model', string="Memo", required=True, readonly=True)
    rfq_excel_file = fields.Binary(string="RFQ Excel File", required=False)
    rfq_excel_filename = fields.Char(string="Filename")
    
    validate_only = fields.Boolean(string="Validate Only", default=False, 
                                   help="Only validate the file without creating purchase orders")
    create_missing_products = fields.Boolean(string="Create Missing Products", default=True,
                                           help="Create new products if not found in system")
    create_missing_vendors = fields.Boolean(string="Create Missing Vendors", default=True,
                                          help="Create new vendors if not found in system")
    group_by_vendor = fields.Boolean(string="Group by Vendor", default=True,
                                   help="Create one PO per vendor")
    
    validation_result = fields.Text(string="Validation Result", readonly=True)
    processing_result = fields.Text(string="Processing Result", readonly=True)
    
    def action_download_template(self):
        """Download RFQ template with populated data from memo"""
        return self.memo_id.download_rfq_template()
    
    def action_validate_file(self):
        """Validate uploaded Excel file"""
        if not self.rfq_excel_file:
            raise ValidationError(_("Please upload a file first."))
                
        try:
            rfq_data = self._parse_excel_file()
            
            validation_errors = self._validate_rfq_data(rfq_data)
            
            if validation_errors:
                self.validation_result = "Validation Errors Found:\n\n" + "\n".join(validation_errors)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    # 'tag': 'rfq_upload.rfq_notify_and_refresh',
                    'params': {
                        'title': _('Validation Failed'),
                        'message': _('Please check validation results and correct the errors.'),
                        'sticky': False,
                        'type': 'warning'
                    }
                }
            else:
                self.validation_result = f"✓ File validation successful!\n\nFound {len(rfq_data)} valid RFQ lines."
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    # 'tag': 'rfq_upload.rfq_notify_and_refresh',
                    'params': {
                        'title': _('Validation Successful'),
                        'message': _('File is valid and ready for processing.'),
                        'sticky': False,
                        'type': 'success'
                    }
                }
                
        except Exception as e:
            self.validation_result = f"Error during validation: {str(e)}"
            raise ValidationError(_("Error validating file: %s") % str(e))
    
    def action_upload_rfq(self):
        """Process the uploaded RFQ file and create purchase orders"""
        if not self.rfq_excel_file:
            raise ValidationError(_("Please upload a file first."))
        
        
        try:
            rfq_data = self._parse_excel_file()
            
            if not self.validate_only:
                validation_errors = self._validate_rfq_data(rfq_data)
                if validation_errors:
                    raise ValidationError(_("Validation failed:\n%s") % "\n".join(validation_errors))
            
            if self.validate_only:
                self.processing_result = f"Validation completed successfully.\nFound {len(rfq_data)} valid RFQ lines.\nNo purchase orders created (validation only mode)."
                return self._show_success_message("File validated successfully!")
            else:
                options = {'create_vendors': self.create_missing_vendors, 'create_products' :self.create_missing_products}
                created_pos = self.memo_id.create_or_update_po_from_rfq(rfq_data, options)
                
                self.memo_id.write({
                    'rfq_excel_file': self.rfq_excel_file,
                    'rfq_excel_filename': self.rfq_excel_filename,
                    'rfq_uploaded': True,
                    'rfq_upload_date': fields.Datetime.now(),
                })
                
                result_message = f"RFQ processing completed successfully!\n\n"
                result_message += f"• Processed {len(rfq_data)} RFQ lines\n"
                result_message += f"• Created {len(created_pos)} Purchase Orders\n\n"
                
                if created_pos:
                    result_message += "Created Purchase Orders:\n"
                    for po in created_pos:
                        result_message += f"• {po.name} - {po.partner_id.name} (Total: {po.currency_id.symbol}{po.amount_total:.2f})\n"
                
                self.processing_result = result_message
                
                return self._show_success_message(f"Successfully created {len(created_pos)} Purchase Orders!")
                
        except Exception as e:
            self.processing_result = f"Error during processing: {str(e)}"
            _logger.error("RFQ processing error: %s", str(e))
            raise ValidationError(_("Error processing RFQ file: %s") % str(e))
    
    
    def _parse_excel_file(self):
        """Parse uploaded Excel/CSV file and return RFQ data"""
        try:
            file_data = base64.b64decode(self.rfq_excel_file)
            
            try:
                import pandas as pd
                
                if self.rfq_excel_filename and self.rfq_excel_filename.lower().endswith('.csv'):
                    df = pd.read_csv(io.BytesIO(file_data))
                else:
                    df = pd.read_excel(io.BytesIO(file_data))
                
                return df.to_dict('records')
                
            except ImportError:
                if self.rfq_excel_filename and self.rfq_excel_filename.lower().endswith('.csv'):
                    return self._parse_csv_fallback(file_data.decode('utf-8'))
                else:
                    raise ValidationError(_("Pandas is required for Excel file processing. Please install it or use CSV format."))
                    
        except Exception as e:
            raise ValidationError(_("Error reading file: %s. Please ensure the file is a valid Excel or CSV file.") % str(e))
    
    def _parse_csv_fallback(self, csv_content):
        """Parse CSV content without pandas"""
        import csv
        import io
        
        reader = csv.DictReader(io.StringIO(csv_content))
        return list(reader)
    
    def _validate_rfq_data(self, rfq_data):
        """Validate RFQ data and return list of errors"""
        errors = []
        required_columns = [
            'VENDOR CODE' ,'VENDOR NAME', 'PRODUCT NAME', 'QTY TO SUPPLY', 'PRICE PER QUANTITY'
        ]
        
        if not rfq_data:
            errors.append("No data found in uploaded file")
            return errors
        
        first_row = rfq_data[0]
        missing_columns = [col for col in required_columns if col not in first_row]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            return errors
        
        for idx, row in enumerate(rfq_data, 1):
            row_errors = []
            
            if not row.get('VENDOR CODE', ' ').strip():
                row_errors.append("Vendor code is required")
                
            if not row.get('VENDOR NAME', '').strip():
                row_errors.append("Vendor name is required")
            
            if not row.get('PRODUCT NAME', '').strip() and not row.get('PRODUCT CODE', '').strip():
                row_errors.append("Product name or product code is required")
            
            try:
                qty = float(row.get('QTY TO SUPPLY', 0))
                if qty <= 0:
                    row_errors.append("Quantity must be greater than 0")
            except (ValueError, TypeError):
                row_errors.append("Invalid quantity format")
            
            try:
                price = float(row.get('PRICE PER QUANTITY', 0))
                if price < 0:
                    row_errors.append("Price cannot be negative")
            except (ValueError, TypeError):
                row_errors.append("Invalid price format")
            
            vendor_email = row.get('VENDOR EMAIL', '').strip()
            if vendor_email and '@' not in vendor_email:
                row_errors.append("Invalid email format")
            
            if row_errors:
                errors.append(f"Row {idx}: {'; '.join(row_errors)}")
        
        return errors
    
    def _show_success_message(self, message):
        """Show success notification"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'sticky': False,
                'type': 'success'
            }
        }