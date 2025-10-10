from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import base64
import random
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
import base64
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class ImportDataWizard(models.TransientModel):
    _name = 'import.data.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection([
            ('new', 'Create New Record'),
            ('update', 'Update Record'),
        ],
        string='Import Type', required=True, index=True,
        copy=True, default='new', 
    )
    model_import = fields.Selection([
            ('cash_advance', 'Cash Advance'),
        ],
        string='Model to Type', required=True, index=True,
        copy=True, default='cash_advance', 
    )
    company_id = fields.Many2one("res.company","Company", required=True)
    branch_id = fields.Many2one("multi.branch","District", required=True)
    memo_config_id = fields.Many2one("memo.config","Memo Config to use", required=True)
    default_employee_id = fields.Many2one("hr.employee","Employee to use as default", required=True)
    clear_data = fields.Boolean("Clear data")
    
    def compute_date(self, date_str):
        appt_date = None
        if date_str:
            if type(date_str) in [int, float]:
                appt_date = datetime(*xlrd.xldate_as_tuple(date_str, 0)) 
            elif type(date_str) in [str]:
                if '-' in date_str:
                    # pref = str(date_str).strip()[0:7] # 12-Jul-
                    # suff = '20'+ date_str.strip()[-2:] # 2022
                    datesplit = date_str.split('-') # eg. 09, jul, 22
                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                    appt_date = f"{d}-{m}-20{y}"
                    appt_date = datetime.strptime(appt_date.strip(), '%d-%b-%Y') 
                elif '/' in date_str:
                    datesplit = date_str.split('/') # eg. 09, jul, 22
                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                    appt_date = f"{d}-{m}-20{y}"
                    appt_date = datetime.strptime(appt_date.strip(), '%d-%b-%Y') 
                else:
                    appt_date = datetime(*xlrd.xldate_as_tuple(float(date_str), 0)) #eg 4554545
        return appt_date
    
    def _normalize_emp_no(self, raw):
        if raw is None or raw == '':
            return ''
        if isinstance(raw, (int,)):
            return str(raw)
        if isinstance(raw, float):
            if raw.is_integer():
                return str(int(raw))
            s = str(raw)
            if s.endswith('.0'):
                return s[:-2]
            return s
        s = str(raw).strip()
        if s.endswith('.0') and re.match(r'^\d+\.0$', s):
            return s[:-2]
        return s
        
    def import_records_action(self):
        if self.data_file:
            if not self.memo_config_id.stage_ids:
                raise ValidationError(f"Memo config with ID {self.memo_config_id.id} {self.memo_config_id.name} does not have stages configured")
            # if self.property_stock_inventory.company_id.id != self.company_id.id:
            #     raise ValidationError("Adjustment Store location company must be same with selected company")
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        
        errors = ['The Following messages occurred']
        count = 0
        success_records = []
        unsuccess_records = []
        
        if self.model_import == "cash_advance":
            if self.import_type == "new":
                # Group line items by advance number
                advance_groups = {}
                for row in file_data:
                    advance_number = str(row[0]).strip() if row[0] else ''
                    if advance_number:
                        if advance_number not in advance_groups:
                            advance_groups[advance_number] = []
                        advance_groups[advance_number].append(row)
                
                _logger.info(f"Found {len(advance_groups)} unique advance numbers with {len(file_data)} total line items")
                
                # Process each advance number with all its line items
                for advance_number, rows in advance_groups.items():
                    try:
                        # Use first row for header information (all rows have same header data after preprocessing)
                        first_row = rows[0]
                        code = str(first_row[0]).strip() if first_row[0] else ''
                        subject = str(first_row[0]).strip() if first_row[0] else ''
                        employee_number = self._normalize_emp_no(first_row[1])
                        total_amount = first_row[2] if len(first_row) > 2 else 0
                        request_date = self.compute_date(first_row[10]) if len(first_row) > 10 else None
                        
                        # Check if advance already exists
                        existing_memo = self.env['memo.model'].sudo().search([
                            ('code', '=ilike', code)], limit=1)
                        
                        if existing_memo:
                            if self.clear_data:
                                existing_memo.unlink()
                            else:
                                _logger.info(f"Skipping existing memo {code} with {len(rows)} line items")
                                unsuccess_records.append(f"Skipped existing record: {code}")
                                count += 1
                                continue
                        
                        # Search for employee
                        employee = False
                        if employee_number:
                            employee = self.env['hr.employee'].sudo().search([
                                ('employee_number', '=', employee_number)
                            ], limit=1)
                            
                            if not employee:
                                _logger.warning(f"Employee not found with number: {employee_number}")
                        
                        # Determine which employee ID to use
                        if employee:
                            employee_id = employee.id
                            _logger.info(f"Using found employee: {employee.name} (ID: {employee.id})")
                        elif self.default_employee_id:
                            employee_id = self.default_employee_id.id
                            _logger.info(f"Using default employee: {self.default_employee_id.name}")
                        else:
                            employee_id = self.env.user.employee_id.id
                            _logger.info(f"Using current user's employee")
                        
                        _logger.info(f"Processing {advance_number} with {len(rows)} line items | Employee: {employee_number}")
                        
                        # Create the memo/cash advance record
                        memo_id = self.env['memo.model'].sudo().create({
                            'code': code,
                            'migrated_legacy_id': advance_number,
                            'requester_name': first_row[9] if len(first_row) > 9 else '',
                            'name': subject,
                            'employee_id': employee_id,
                            'state': "Done",
                            'stage_id': self.memo_config_id.stage_ids[-1].id,
                            'company_id': self.company_id.id,
                            'branch_id': self.branch_id.id,
                            'memo_setting_id': self.memo_config_id.id,
                            'memo_type': self.memo_config_id.memo_type.id,
                            'request_date': request_date if request_date else fields.Date.today(),
                            'memo_type_key': self.memo_config_id.memo_key,
                        })
                        
                        # Create ALL line items for this advance
                        line_items_created = 0
                        for row in rows:
                            vals = {
                                'memo_id': memo_id.id,
                                'memo_type': memo_id.memo_type.id,
                                'memo_type_key': memo_id.memo_type_key,
                                'description': row[3] if len(row) > 3 else (row[6] if len(row) > 6 else ''),
                                'quantity_available': row[4] if len(row) > 4 and row[4] else 1,
                                'amount_total': row[5] if len(row) > 5 else 0,
                            }
                            self.env['request.line'].sudo().create(vals)
                            line_items_created += 1
                        
                        _logger.info(f"Memo {memo_id.code} created with {line_items_created} line items")
                        success_records.append(f"{memo_id.code} ({line_items_created} lines)")
                        count += 1
                        
                    except Exception as e:
                        _logger.error(f"Error processing advance {advance_number}: {str(e)}")
                        unsuccess_records.append(f"Error processing {advance_number}: {str(e)}")
            
            elif self.import_type == "update":
                # Group line items by advance number
                advance_groups = {}
                for row in file_data:
                    advance_number = str(row[0]).strip() if row[0] else ''
                    if advance_number:
                        if advance_number not in advance_groups:
                            advance_groups[advance_number] = []
                        advance_groups[advance_number].append(row)
                
                _logger.info(f"Found {len(advance_groups)} unique advance numbers to update with {len(file_data)} total line items")
                
                # Process each advance number
                for advance_number, rows in advance_groups.items():
                    try:
                        first_row = rows[0]
                        code = str(first_row[0]).strip() if first_row[0] else ''
                        subject = str(first_row[0]).strip() if first_row[0] else ''
                        employee_number = self._normalize_emp_no(first_row[1])
                        request_date = self.compute_date(first_row[10]) if len(first_row) > 10 else None
                        
                        existing_memo = self.env['memo.model'].sudo().search([
                            ('code', '=ilike', code)], limit=1)
                        
                        if existing_memo:
                            # Search for employee
                            employee = False
                            if employee_number:
                                employee = self.env['hr.employee'].sudo().search([
                                    ('employee_number', '=', employee_number)
                                ], limit=1)
                            
                            # Determine employee ID
                            if employee:
                                employee_id = employee.id
                            elif self.default_employee_id:
                                employee_id = self.default_employee_id.id
                            else:
                                employee_id = self.env.user.employee_id.id
                            
                            _logger.info(f"Updating {advance_number} with {len(rows)} line items")
                            
                            # Update memo header
                            existing_memo.sudo().write({
                                'migrated_legacy_id': advance_number,
                                'requester_name': first_row[9] if len(first_row) > 9 else '',
                                'name': subject,
                                'employee_id': employee_id,
                                'request_date': request_date if request_date else fields.Date.today(),
                            })
                            
                            # Delete existing lines and replace with new ones
                            existing_lines = self.env['request.line'].sudo().search([
                                ('memo_id', '=', existing_memo.id)])
                            if existing_lines:
                                existing_lines.unlink()
                                _logger.info(f"Deleted {len(existing_lines)} old line items for {code}")
                            
                            # Create new line items
                            line_items_created = 0
                            for row in rows:
                                vals = {
                                    'memo_id': existing_memo.id,
                                    'memo_type': existing_memo.memo_type.id,
                                    'memo_type_key': existing_memo.memo_type_key,
                                    'description': row[3] if len(row) > 3 else (row[6] if len(row) > 6 else ''),
                                    'quantity_available': row[4] if len(row) > 4 and row[4] else 1,
                                    'amount_total': row[5] if len(row) > 5 else 0,
                                }
                                self.env['request.line'].sudo().create(vals)
                                line_items_created += 1
                            
                            _logger.info(f"Memo {existing_memo.code} updated with {line_items_created} line items")
                            success_records.append(f"{existing_memo.code} (updated, {line_items_created} lines)")
                            count += 1
                        else:
                            _logger.info(f"Record not found for update: {code}")
                            unsuccess_records.append(f"Record not found: {code}")
                            
                    except Exception as e:
                        _logger.error(f"Error updating advance {advance_number}: {str(e)}")
                        unsuccess_records.append(f"Error updating {advance_number}: {str(e)}")
            else:
                pass     
                
        errors.append('Successful Import(s): '+str(count)+' Advance(s) with line items')
        errors.append('Unsuccessful Import(s): '+str(len(unsuccess_records))+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message) 

    def confirm_notification(self,popup_message):
        view = self.env.ref('migration_app.hr_migration_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'hr.migration.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }