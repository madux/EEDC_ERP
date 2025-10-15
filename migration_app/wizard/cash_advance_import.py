from odoo import fields, models, api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import base64
import random
import logging
import re
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
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
            ('payment', 'Payment'),
        ],
        string='Model to Import', required=True, index=True,
        copy=True, default='cash_advance', 
    )
    company_id = fields.Many2one("res.company", "Company", required=True)
    branch_id = fields.Many2one("multi.branch", "District", required=True)
    memo_config_id = fields.Many2one("memo.config", "Memo Config to use", required=True)
    default_employee_id = fields.Many2one("hr.employee", "Employee to use as default", required=True)
    clear_data = fields.Boolean("Clear data")
    
    state_option = fields.Selection([
        ('submit', 'Draft'),
        ('Sent', 'Sent'),
        ('Approve', 'Approve'),
        ('Approve2', 'Approve 2'),
        ('Done', 'Done'),
        ('Refuse', 'Refuse'),
    ], string='State Option', default='Done', required=True)
    
    stage_id = fields.Many2one(
        'memo.stage',
        string='Stage',
        domain="[('memo_config_id', '=', memo_config_id)]"
    )
    
    @api.onchange('memo_config_id')
    def _onchange_memo_config_id(self):
        """Clear stage_id when memo_config_id changes to ensure correct domain"""
        self.stage_id = False
    
    def _get_stage_and_state(self):
        """
        Compute stage_id and state based on state_option and selected stage.
        """
        if not self.memo_config_id or not self.memo_config_id.stage_ids:
            raise ValidationError(
                f"Memo config '{getattr(self.memo_config_id, 'name', '')}' has no stages configured"
            )

        stages = self.memo_config_id.stage_ids.sorted(key=lambda s: s.sequence)
        opt = self.state_option

        if opt in ['submit', 'Submit']:
            return (stages[0].id if len(stages) > 0 else False, 'submit')

        if opt in ['Done', 'done']:
            return (stages[-1].id if len(stages) > 0 else False, 'Done')

        if not self.stage_id:
            raise ValidationError(
                f"Please select a stage for state '{self.state_option}'"
            )
        if self.stage_id.memo_config_id.id != self.memo_config_id.id:
            raise ValidationError(
                f"Selected stage '{self.stage_id.name}' does not belong to "
                f"memo config '{self.memo_config_id.name}'"
            )

        return (self.stage_id.id, opt)
    
    def compute_date(self, date_str):
        """Convert various date formats to datetime object"""
        appt_date = None
        if date_str:
            if type(date_str) in [int, float]:
                appt_date = datetime(*xlrd.xldate_as_tuple(date_str, 0)) 
            elif type(date_str) in [str]:
                if '-' in date_str:
                    datesplit = date_str.split('-')
                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                    appt_date = f"{d}-{m}-20{y}"
                    appt_date = datetime.strptime(appt_date.strip(), '%d-%b-%Y') 
                elif '/' in date_str:
                    datesplit = date_str.split('/')
                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                    appt_date = f"{d}-{m}-20{y}"
                    appt_date = datetime.strptime(appt_date.strip(), '%d-%b-%Y') 
                else:
                    appt_date = datetime(*xlrd.xldate_as_tuple(float(date_str), 0))
        return appt_date
    
    def _normalize_emp_no(self, raw):
        """Normalize employee number to string format"""
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
    
    def _process_cash_advance_row(self, first_row):
        """Extract cash advance data from row"""
        return {
            'code': str(first_row[0]).strip() if first_row[0] else '',
            'employee_number': self._normalize_emp_no(first_row[1]),
            'amount': first_row[2],
            'request_date': self.compute_date(first_row[10]) if len(first_row) > 10 else None,
            'requester_name': first_row[9] if len(first_row) > 9 else '',
            # 'description': first_row[3] if len(first_row) > 3 else '',
            'description': first_row[3] or first_row[6],
            'quantity': first_row[4] if len(first_row) > 4 else 1,
            'unit_price': first_row[5] if len(first_row) > 5 else 0,
        }
    
    def _process_payment_row(self, first_row):
        """Extract payment data from row"""
        
        def safe_float(val, default=0.0):
            try:
                if val is None or val == '':
                    return default
                if isinstance(val, str) and val.upper() == 'FALSE':
                    return default
                return float(val)
            except (ValueError, TypeError):
                _logger.warning(f"Could not convert '{val}' to float, using {default}")
                return default
        
        def extract_product_code(display_name):
            """Extract code from format like '[ST-609-0072] Product Name'"""
            if not display_name:
                return None
            display_name_str = str(display_name).strip()
            match = re.match(r'\[([^\]]+)\]', display_name_str)
            if match:
                return match.group(1)
            return None
        
        product_display_name = str(first_row[15]).strip() if len(first_row) > 15 else ''
        product_code = extract_product_code(product_display_name)
        
        approver_employee_number = self._normalize_emp_no(first_row[16]) if len(first_row) > 16 else ''
        
        return {
            'code': str(first_row[0]).strip() if first_row[0] else '',
            'employee_number': self._normalize_emp_no(first_row[2]) if len(first_row) > 2 else '',
            'amount': safe_float(first_row[9]) if len(first_row) > 9 else 0.0,
            'request_date': self.compute_date(first_row[18]) if len(first_row) > 18 else None,
            'requester_name': str(first_row[3]).strip() if len(first_row) > 3 else '',
            'description': str(first_row[11]).strip() if len(first_row) > 11 and first_row[11] else str(first_row[10]).strip() if len(first_row) > 10 else '',
            'quantity': safe_float(first_row[12], 1.0) if len(first_row) > 12 else 1.0,
            'unit_price': safe_float(first_row[13]) if len(first_row) > 13 else 0.0,
            'display_name': str(first_row[1]).strip() if len(first_row) > 1 else '',
            'work_location': str(first_row[4]).strip() if len(first_row) > 4 else '',
            'product_code': product_code,
            'product_display_name': product_display_name,
            'approver_employee_number': approver_employee_number,
        }
        
    def import_records_action(self):
        if self.data_file:
            if not self.memo_config_id.stage_ids:
                raise ValidationError(
                    f"Memo config '{self.memo_config_id.name}' does not have stages configured"
                )
            
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        
        stage_id, state_value = self._get_stage_and_state()
        
        errors = ['The Following messages occurred']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        
        if self.model_import == "cash_advance":
            success_records, unsuccess_records, count = self._import_cash_advance(
                file_data, stage_id, state_value, success_records, unsuccess_records
            )
            
        elif self.model_import == "payment":
            success_records, unsuccess_records, count = self._import_payment(
                file_data, stage_id, state_value, success_records, unsuccess_records
            )
        
        errors.append(f'Successful Import(s): {count} Record(s)')
        if success_records:
            errors.append(f'  Records: {success_records}')
        
        errors.append(f'Unsuccessful Import(s): {len(unsuccess_records)} Record(s)')
        if unsuccess_records:
            errors.append(f'  Records: {unsuccess_records}')
        
        if len(errors) > 2:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def _import_cash_advance(self, file_data, stage_id, state_value, success_records, unsuccess_records):
        """Handle cash advance import logic"""
        advance_groups = {}
        for row in file_data:
            migrated_number = str(row[0]).strip() if row[0] else ''
            if migrated_number:
                if migrated_number not in advance_groups:
                    advance_groups[migrated_number] = []
                advance_groups[migrated_number].append(row)
        
        _logger.info(f"Found {len(advance_groups)} unique advance numbers")
        count = 0
        
        for migrated_number, rows in advance_groups.items():
            first_row = rows[0]
            row_data = self._process_cash_advance_row(first_row)
            code = row_data['code']
            employee_number = row_data['employee_number']
            request_date = row_data['request_date']
            
            if migrated_number:
                existing_memo = self.env['memo.model'].sudo().search([
                    ('code', '=ilike', code)], limit=1)
                
                if self.import_type == 'new':
                    if existing_memo:
                        if self.clear_data:
                            existing_memo.unlink()
                            _logger.info(f"Deleted existing memo {code}")
                        else:
                            _logger.info(f"Skipping existing memo {code}")
                            unsuccess_records.append(f"Skipped existing record: {code}")
                            count += 1
                            continue
                    
                    employee = self.env['hr.employee'].sudo().search([
                        ('employee_number', '=', employee_number)], limit=1)
                    _logger.info(f"Processing {code} - Employee: {employee_number}")
                    
                    memo_id = self.env['memo.model'].sudo().create({
                        'code': code,
                        'migrated_legacy_id': migrated_number,
                        'requester_name': row_data['requester_name'],
                        'name': row_data['code'],
                        'employee_id': employee.id if employee else self.default_employee_id.id,
                        'state': state_value,
                        'stage_id': stage_id,
                        'company_id': self.company_id.id,
                        'branch_id': self.branch_id.id,
                        'memo_setting_id': self.memo_config_id.id,
                        'memo_type': self.memo_config_id.memo_type.id,
                        'request_date': request_date if request_date else fields.Date.today(),
                        'memo_type_key': self.memo_config_id.memo_key,
                    })
                    
                    line_count = 0
                    for row in rows:
                        row_data = self._process_cash_advance_row(row)
                        vals = {
                            'memo_id': memo_id.id,
                            'memo_type': memo_id.memo_type.id,
                            'memo_type_key': memo_id.memo_type_key,
                            'description': row_data['description'] or row_data['code'],
                            'quantity_available': row_data['quantity'] or 1,
                            'amount_total': row_data['unit_price'],
                        }
                        self.env['request.line'].sudo().create(vals)
                        line_count += 1
                    
                    _logger.info(f"Created memo {memo_id.code} with {line_count} lines")
                    success_records.append(f"{memo_id.code} ({line_count} lines)")
                    
                elif self.import_type == 'update':
                    if existing_memo:
                        employee = self.env['hr.employee'].sudo().search([
                            ('employee_number', '=', employee_number)], limit=1)
                        _logger.info(f"Updating {code} - Employee: {employee_number}")
                        
                        existing_memo.sudo().write({
                            'migrated_legacy_id': migrated_number,
                            'requester_name': row_data['requester_name'],
                            'name': row_data['code'],
                            'employee_id': employee.id if employee else self.default_employee_id.id,
                            'request_date': request_date if request_date else fields.Date.today(),
                        })
                        
                        # Delete existing lines
                        existing_lines = self.env['request.line'].sudo().search([
                            ('memo_id', '=', existing_memo.id)])
                        if existing_lines:
                            existing_lines.unlink()
                        
                        line_count = 0
                        for row in rows:
                            row_data = self._process_cash_advance_row(row)
                            vals = {
                                'memo_id': existing_memo.id,
                                'memo_type': existing_memo.memo_type.id,
                                'memo_type_key': existing_memo.memo_type_key,
                                'description': row_data['description'] or row_data['code'],
                                'quantity_available': row_data['quantity'] or 1,
                                'amount_total': row_data['unit_price'],
                            }
                            self.env['request.line'].sudo().create(vals)
                            line_count += 1
                        
                        _logger.info(f"Updated memo {existing_memo.code} with {line_count} lines")
                        success_records.append(f"{existing_memo.code} (updated, {line_count} lines)")
                    else:
                        _logger.info(f"Record not found for update: {code}")
                        unsuccess_records.append(f"Record not found: {code}")
            else:
                unsuccess_records.append(f"Skipped - no migrated number")
            count += 1
        
        return success_records, unsuccess_records, count

    def _import_payment(self, file_data, stage_id, state_value, success_records, unsuccess_records):
        """Handle payment import logic"""
        payment_groups = {}
        for row in file_data:
            payment_number = str(row[0]).strip() if row[0] else ''
            if payment_number:
                if payment_number not in payment_groups:
                    payment_groups[payment_number] = []
                payment_groups[payment_number].append(row)
        
        _logger.info(f"Found {len(payment_groups)} unique payment numbers")
        count = 0
        
        for payment_number, rows in payment_groups.items():
            first_row = rows[0]
            row_data = self._process_payment_row(first_row)
            code = row_data['code']
            employee_number = row_data['employee_number']
            request_date = row_data['request_date']
            approver_employee_number = row_data['approver_employee_number']
            
            if payment_number:
                existing_memo = self.env['memo.model'].sudo().search([
                    ('code', '=ilike', code)], limit=1)
                
                # Find approver user for users_followers
                approver_user = None
                if approver_employee_number:
                    approver_employee = self.env['hr.employee'].sudo().search([
                        ('employee_number', '=', approver_employee_number)], limit=1)
                    if approver_employee and approver_employee.user_id:
                        approver_user = approver_employee.user_id
                        _logger.info(f"Found approver user: {approver_user.name}")
                
                if self.import_type == 'new':
                    if existing_memo:
                        if self.clear_data:
                            existing_memo.unlink()
                            _logger.info(f"Deleted existing payment {code}")
                        else:
                            _logger.info(f"Skipping existing payment {code}")
                            unsuccess_records.append(f"Skipped existing payment: {code}")
                            count += 1
                            continue
                    
                    employee = self.env['hr.employee'].sudo().search([
                        ('employee_number', '=', employee_number)], limit=1) if employee_number else None
                    _logger.info(f"Processing payment {code} - Employee: {employee_number}")
                    
                    memo_vals = {
                        'code': code,
                        'migrated_legacy_id': payment_number,
                        'requester_name': row_data['requester_name'],
                        'name': row_data['display_name'] or row_data['code'],
                        'employee_id': employee.id if employee else self.default_employee_id.id,
                        'state': state_value,
                        'stage_id': stage_id,
                        'company_id': self.company_id.id,
                        'branch_id': self.branch_id.id,
                        'memo_setting_id': self.memo_config_id.id,
                        'memo_type': self.memo_config_id.memo_type.id,
                        'request_date': request_date if request_date else fields.Date.today(),
                        'memo_type_key': self.memo_config_id.memo_key,
                    }
                    
                    if approver_user:
                        memo_vals['users_followers'] = [(4, approver_user.id)]
                    
                    memo_id = self.env['memo.model'].sudo().create(memo_vals)
                    
                    line_count = 0
                    for row in rows:
                        row_data = self._process_payment_row(row)
                        
                        product_id = False
                        if row_data['product_code']:
                            product = self.env['product.product'].sudo().search([
                                '|',
                                ('default_code', '=ilike', row_data['product_code']),
                                ('name', '=ilike', row_data['product_code'])
                            ], limit=1)
                            
                            if product:
                                product_id = product.id
                                _logger.info(f"Found product: {product.name} for code {row_data['product_code']}")
                            else:
                                _logger.warning(f"Product not found for code: {row_data['product_code']}")
                        
                        vals = {
                            'memo_id': memo_id.id,
                            'memo_type': memo_id.memo_type.id,
                            'memo_type_key': memo_id.memo_type_key,
                            'description': row_data['description'] or row_data['display_name'],
                            'quantity_available': row_data['quantity'],
                            'amount_total': row_data['unit_price'],
                        }
                        
                        if product_id:
                            vals['product_id'] = product_id
                        
                        self.env['request.line'].sudo().create(vals)
                        line_count += 1
                    
                    _logger.info(f"Created payment {memo_id.code} with {line_count} lines")
                    success_records.append(f"{memo_id.code} ({line_count} lines)")
                    
                elif self.import_type == 'update':
                    if existing_memo:
                        employee = self.env['hr.employee'].sudo().search([
                            ('employee_number', '=', employee_number)], limit=1) if employee_number else None
                        _logger.info(f"Updating payment {code} - Employee: {employee_number}")
                        
                        update_vals = {
                            'migrated_legacy_id': payment_number,
                            'requester_name': row_data['requester_name'],
                            'name': row_data['display_name'] or row_data['code'],
                            'employee_id': employee.id if employee else self.default_employee_id.id,
                            'request_date': request_date if request_date else fields.Date.today(),
                        }
                        
                        if approver_user:
                            update_vals['users_followers'] = [(5, 0, 0), (4, approver_user.id)]
                        
                        existing_memo.sudo().write(update_vals)
                        
                        existing_lines = self.env['request.line'].sudo().search([
                            ('memo_id', '=', existing_memo.id)])
                        if existing_lines:
                            existing_lines.unlink()
                        
                        line_count = 0
                        for row in rows:
                            row_data = self._process_payment_row(row)
                            
                            product_id = False
                            if row_data['product_code']:
                                product = self.env['product.product'].sudo().search([
                                    '|',
                                    ('default_code', '=ilike', row_data['product_code']),
                                    ('name', '=ilike', row_data['product_code'])
                                ], limit=1)
                                
                                if product:
                                    product_id = product.id
                                    _logger.info(f"Found product: {product.name} for code {row_data['product_code']}")
                            
                            vals = {
                                'memo_id': existing_memo.id,
                                'memo_type': existing_memo.memo_type.id,
                                'memo_type_key': existing_memo.memo_type_key,
                                'description': row_data['description'] or row_data['display_name'],
                                'quantity_available': row_data['quantity'],
                                'amount_total': row_data['unit_price'],
                            }
                            
                            if product_id:
                                vals['product_id'] = product_id
                            
                            self.env['request.line'].sudo().create(vals)
                            line_count += 1
                        
                        _logger.info(f"Updated payment {existing_memo.code} with {line_count} lines")
                        success_records.append(f"{existing_memo.code} (updated, {line_count} lines)")
                    else:
                        _logger.info(f"Record not found for update: {code}")
                        unsuccess_records.append(f"Record not found: {code}")
            else:
                unsuccess_records.append(f"Skipped payment - no reference number")
            count += 1
        
        return success_records, unsuccess_records, count

    def confirm_notification(self, popup_message):
        """Show confirmation dialog with import results"""
        view = self.env.ref('migration_app.hr_migration_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
            'name': 'Import Results',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'hr.migration.confirm.dialog',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }