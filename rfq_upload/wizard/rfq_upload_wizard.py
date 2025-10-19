from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
import math
import logging
import pandas as pd

_logger = logging.getLogger(__name__)

class RFQUploadWizard(models.TransientModel):
    _name = 'rfq.upload.wizard'
    _description = 'RFQ Upload Wizard'
    
    memo_id = fields.Many2one('memo.model', string="Request", required=True, readonly=True)
    rfq_excel_file = fields.Binary(string="RFQ Excel File", required=False)
    rfq_excel_filename = fields.Char(string="Filename")
    
    sheet = fields.Char(string="Sheet Name", help="Enter the exact sheet name to import")
    sheet_list = fields.Text(string="Available Sheets", readonly=True)
    sheet_count = fields.Integer(default=0, help="Number of sheets in the file")
    
    create_missing_products = fields.Boolean(string="Create Missing Products", default=True,
                                           help="Create new products if not found in system")
    create_missing_vendors = fields.Boolean(string="Create Missing Vendors", default=True,
                                          help="Create new vendors if not found in system")
    group_by_vendor = fields.Boolean(string="Group by Vendor", default=True,
                                   help="Create one PO per vendor")
    
    validation_result = fields.Text(string="Validation Result", readonly=True, default="")
    processing_result = fields.Text(string="Processing Result", readonly=True, default="")
    
    
    @api.onchange('rfq_excel_file')
    def _onchange_rfq_excel_file(self):
        """Get sheet names when an Excel file is uploaded."""
        self.sheet = False
        self.sheet_count = 0
        self.sheet_list = ""
        self.validation_result = ""
        self.processing_result = ""

        is_excel = self.rfq_excel_filename and self.rfq_excel_filename.lower().endswith(('.xlsx', '.xls'))
        
        if self.rfq_excel_file and is_excel:
            try:
                decoded_data = base64.b64decode(self.rfq_excel_file)
                excel_file = pd.ExcelFile(io.BytesIO(decoded_data))
                sheet_names_list = excel_file.sheet_names
                self.sheet_count = len(sheet_names_list)
                
                if self.sheet_count > 0:
                    self.sheet = sheet_names_list[0]
                    self.sheet_list = "Available sheets: " + ", ".join(f'"{name}"' for name in sheet_names_list)
                    
            except Exception as e:
                _logger.error("Error reading Excel sheets: %s", str(e))
                self.sheet_count = 0
                self.sheet_list = f"Error reading file: {str(e)}"
    
    def action_download_template(self):
        """Download RFQ template with populated data from memo"""
        self.ensure_one()
        template_data = self._get_template_data()
        if not template_data.get('PRODUCT CODE'):
            raise ValidationError(_("There are no request items in this memo to generate a template for."))

        try:
            df = pd.DataFrame(template_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='RFQ_Template', index=False)
                worksheet = writer.sheets['RFQ_Template']
                for idx, col in enumerate(df):
                    max_len = max((df[col].astype(str).map(len).max(), len(str(df[col].name)))) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)

            excel_file = base64.b64encode(output.getvalue())
            filename = f'RFQ_Template_{self.memo_id.code or "New"}.xlsx'
            
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': excel_file,
                'res_model': 'memo.model',
                'res_id': self.memo_id.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("Error generating RFQ template: %s", str(e))
            raise ValidationError(_("Failed to generate template: %s") % str(e))
    
    def action_validate_file(self):
        """Validate uploaded Excel file"""
        if not self.rfq_excel_file:
            raise ValidationError(_("Please upload a file first."))
                
        try:
            rfq_data = self._parse_excel_file()
            validation_errors = self._validate_rfq_data(rfq_data)
            
            if validation_errors:
                msg = "✗ Validation Errors Found:\n\n" + "\n".join(validation_errors)
                self.validation_result = msg
                self.processing_result = ""
                self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                    'simple_notification',
                    {
                        'title': _('Validation Failed'),
                        'message': _('Please check validation results and correct the errors.'),
                        'sticky': False,
                        'type': 'danger'
                    }
                )
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                self.validation_result = f"✓ File validation successful!\n\nFound {len(rfq_data)} valid RFQ lines from sheet '{self.sheet or 'default'}'.\n\nFile is ready for processing."
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
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
            
            validation_errors = self._validate_rfq_data(rfq_data)
            if validation_errors:
                self.validation_result = "Validation Errors Found:\n\n" + "\n".join(validation_errors)
                raise ValidationError(_("Validation failed:\n%s") % "\n".join(validation_errors))
            
            options = {
                'create_vendors': self.create_missing_vendors, 
                'create_products': self.create_missing_products,
                'group_by_vendor': self.group_by_vendor,
            }
            created_pos = self.memo_id.create_or_update_po_from_rfq(rfq_data, options)
            
            self.memo_id.write({
                'rfq_excel_file': self.rfq_excel_file,
                'rfq_excel_filename': self.rfq_excel_filename,
                'rfq_uploaded': True,
                'rfq_upload_date': fields.Datetime.now(),
            })
            
            result_message = f"RFQ processing completed successfully!\n\n"
            result_message += f"• Sheet processed: '{self.sheet or 'default'}'\n"
            result_message += f"• Processed {len(rfq_data)} RFQ lines\n"
            result_message += f"• Created {len(created_pos)} Purchase Orders\n\n"
            
            if created_pos:
                result_message += "Created Purchase Orders:\n"
                for po in created_pos:
                    result_message += f"• {po.name} - {po.partner_id.name} (Total: {po.currency_id.symbol}{po.amount_total:.2f})\n"
            
            self.processing_result = result_message
            
            return self._show_success_message(f"Successfully created {len(created_pos)} Purchase Orders!")
            
            
            # self.env['bus.bus']._sendone(
            #     self.env.user.partner_id,
            #     'simple_notification',
            #     {
            #         'title': _('Processing Complete'),
            #         'message': f'Successfully created {len(created_pos)} Purchase Orders!',
            #         'sticky': False,
            #         'type': 'success'
            #     }
            # )
            
            # return {
            #     'type': 'ir.actions.act_window',
            #     'res_model': self._name,
            #     'res_id': self.id,
            #     'view_mode': 'form',
            #     'target': 'new',
            # }
                
        except Exception as e:
            self.processing_result = f"Error during processing: {str(e)}"
            _logger.error("RFQ processing error: %s", str(e))
            raise ValidationError(_("Error processing RFQ file: %s") % str(e))

    def _get_template_data(self):
        """Extracts product data from the memo's request lines to pre-populate the template."""
        template_data = {
            'VENDOR CODE': [], 'VENDOR NAME': [], 'VENDOR EMAIL': [], 'VENDOR PHONE': [],
            'VENDOR ADDRESS': [], 'PRODUCT CODE': [], 'PRODUCT NAME': [],
            'QUANTITY': [], 'UNIT PRICE': [],
        }
        
        if not self.memo_id.product_ids:
            return {}

        for line in self.memo_id.product_ids:
            for key in ['VENDOR CODE', 'VENDOR NAME', 'VENDOR EMAIL', 'VENDOR PHONE', 'VENDOR ADDRESS', 'UNIT PRICE']:
                template_data[key].append('')
            
            template_data['PRODUCT CODE'].append(line.product_id.default_code or '')
            template_data['PRODUCT NAME'].append(line.product_id.name or '')
            template_data['QUANTITY'].append(line.quantity_available or 1.0)
            
        return template_data
    
    def _parse_excel_file(self):
        """Parse uploaded Excel/CSV file and return RFQ data"""
        try:
            file_data = base64.b64decode(self.rfq_excel_file)
            
            if self.rfq_excel_filename and self.rfq_excel_filename.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(io.BytesIO(file_data))
                except Exception as e:
                    _logger.warning("Pandas CSV parsing failed, using fallback: %s", str(e))
                    return self._parse_csv_fallback(file_data.decode('utf-8'))
            else:
                sheet_name = self.sheet if self.sheet else 0
                try:
                    df = pd.read_excel(io.BytesIO(file_data), sheet_name=sheet_name)
                except ValueError as e:
                    if "Worksheet" in str(e) and "does not exist" in str(e):
                        excel_file = pd.ExcelFile(io.BytesIO(file_data))
                        available_sheets = ", ".join(f'"{name}"' for name in excel_file.sheet_names)
                        raise ValidationError(
                            _("Sheet '%s' not found in the Excel file.\n\nAvailable sheets: %s") % 
                            (sheet_name, available_sheets)
                        )
                    else:
                        raise ValidationError(_("Error reading Excel sheet: %s") % str(e))
            
            df = df.dropna(how='all')
            
            normalized_data = []
            for _, row in df.iterrows():
                normalized_row = self._normalize_row_data(row, df.columns.tolist())
                normalized_data.append(normalized_row)
            
            return normalized_data
                    
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(_("Error reading file: %s. Please ensure the file is a valid Excel or CSV file.") % str(e))
        
    def _normalize_row_data(self, row, columns):
        """Normalize row data using index fallback when column names not found"""
        expected_columns = [
            'VENDOR CODE', 'VENDOR NAME', 'VENDOR EMAIL', 'VENDOR PHONE', 
            'PRODUCT CODE', 'PRODUCT NAME', 'QUANTITY', 'UNIT PRICE'
        ]
        
        index_mapping = {
            0: 'VENDOR CODE',
            1: 'VENDOR NAME',
            2: 'VENDOR EMAIL',
            3: 'VENDOR PHONE',
            4: 'VENDOR ADDRESS',
            5: 'PRODUCT CODE',
            6: 'PRODUCT NAME',
            7: 'QUANTITY',
            8: 'UNIT PRICE'
        }
        
        normalized_row = {}
        
        column_map = {col.upper().strip(): col for col in columns}

        for col_key in expected_columns:
            actual_col = column_map.get(col_key, None)
            value = row.get(actual_col) if actual_col and hasattr(row, 'get') else None
            
            if value is not None and isinstance(value, float) and math.isnan(value):
                value = ""
            elif value is None:
                value = ""
                
            normalized_row[col_key] = str(value).strip()
        
        for idx, target_col in index_mapping.items():
            if idx < len(row) and not normalized_row.get(target_col):
                try:
                    value = row.iloc[idx]
                    if value is not None and not (isinstance(value, float) and math.isnan(value)):
                        normalized_row[target_col] = str(value).strip()
                except (IndexError, KeyError):
                    pass
        
        return normalized_row
    
    def _parse_csv_fallback(self, csv_content):
        """Parse CSV content without pandas - fallback method"""
        import csv
        import io
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            data = []
            columns = reader.fieldnames or []
            
            for row in reader:
                normalized_row = self._normalize_row_data(row, columns)
                data.append(normalized_row)
            
            return data
        except Exception as e:
            raise ValidationError(_("Error parsing CSV file: %s") % str(e))
    
    def _validate_rfq_data(self, rfq_data):
        """Validate RFQ data and return list of errors"""
        errors = []
        required_columns = [
            'VENDOR CODE', 'VENDOR NAME', 'PRODUCT NAME', 'QUANTITY', 'UNIT PRICE'
        ]
        
        if not rfq_data:
            errors.append(f"No data found in uploaded file (sheet: '{self.sheet or 'default'}')")
            return errors
        
        first_row = rfq_data[0]
        missing_columns = [col for col in required_columns if col not in first_row]
        if missing_columns:
            available_columns = list(first_row.keys())
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            errors.append(f"Available columns in sheet '{self.sheet or 'default'}': {', '.join(available_columns)}")
            return errors
        
        for idx, row in enumerate(rfq_data, 1):
            row_errors = []
            
            def get_cleaned_string(row, key):
                val = row.get(key)
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return ""
                return str(val).strip()
            
            vendor_code = get_cleaned_string(row, 'VENDOR CODE')
            vendor_name = get_cleaned_string(row, 'VENDOR NAME')
            product_name = get_cleaned_string(row, 'PRODUCT NAME')
            product_code = get_cleaned_string(row, 'PRODUCT CODE')
            
            if not vendor_code:
                row_errors.append("Vendor code is required")
                
            if not vendor_name:
                row_errors.append("Vendor name is required")
            
            if not product_name and not product_code.strip():
                row_errors.append("Product name or product code is required")
            
            try:
                qty_val = row.get('QUANTITY', 0)
                if qty_val is None or (isinstance(qty_val, float) and math.isnan(qty_val)):
                    row_errors.append("Quantity is required")
                else:
                    qty = float(qty_val)
                    if qty <= 0:
                        row_errors.append("Quantity must be greater than 0")
            except (ValueError, TypeError):
                row_errors.append("Invalid quantity format")
            
            try:
                price_val = row.get('UNIT PRICE')
                if price_val is None or (isinstance(price_val, float) and math.isnan(price_val)):
                    row_errors.append("Price is required and cannot be empty")
                else:
                    price = float(price_val)
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