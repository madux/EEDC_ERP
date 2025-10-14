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
        ('sent', 'Sent'),
        ('approve', 'Approve'),
        ('approve2', 'Approve 2'),
        ('done', 'Done'),
        ('refuse', 'Refuse'),
        ('custom', 'Select Custom Stage'),
    ], string='State/Stage Option', default='done', required=True)
    
    custom_stage_id = fields.Many2one(
        'memo.stage',
        string='Custom Stage',
        domain="[('memo_config_id', '=', memo_config_id)]"
    )
    
    @api.onchange('memo_config_id')
    def _onchange_memo_config_id(self):
        """Clear custom_stage_id when memo_config_id changes to ensure correct domain"""
        self.custom_stage_id = False
    
    def _get_stage_and_state(self):
        """
        Compute stage_id and state based on state_option.
        - If state_option is 'custom', use the selected custom_stage_id
        - If state_option is 'submit' or 'done', compute from memo_config stages
        - Otherwise, use custom_stage_id or the closest available stage
        Returns: (stage_id, state_string)
        """
        if not self.memo_config_id.stage_ids:
            raise ValidationError(
                f"Memo config '{self.memo_config_id.name}' has no stages configured"
            )
        
        stages = self.memo_config_id.stage_ids.sorted(key=lambda s: s.sequence)
        
        if self.state_option == 'custom':
            if not self.custom_stage_id:
                raise ValidationError(
                    "Please select a custom stage when 'Select Custom Stage' is chosen"
                )
            if self.custom_stage_id.memo_config_id.id != self.memo_config_id.id:
                raise ValidationError(
                    f"Selected stage '{self.custom_stage_id.name}' does not belong to "
                    f"memo config '{self.memo_config_id.name}'"
                )
            return self.custom_stage_id.id, self.custom_stage_id.name
        
        # Pre-computed stage mappings for standard options
        stage_mapping = {
            'submit': (stages[0].id if len(stages) > 0 else False, 'submit'),
            'sent': (stages[1].id if len(stages) > 1 else stages[0].id, 'Sent'),
            'approve': (stages[2].id if len(stages) > 2 else stages[-1].id, 'Approve'),
            'approve2': (stages[3].id if len(stages) > 3 else stages[-1].id, 'Approve2'),
            'done': (stages[-1].id, 'Done'),
            'refuse': (stages[-1].id, 'Refuse'),
        }
        
        stage_id, state_value = stage_mapping.get(
            self.state_option, 
            (stages[-1].id, 'Done')
        )
        
        return stage_id, state_value
    
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
            'description': first_row[3] if len(first_row) > 3 else '',
            'quantity': first_row[4] if len(first_row) > 4 else 1,
            'unit_price': first_row[5] if len(first_row) > 5 else 0,
        }
    
    def _process_payment_row(self, first_row):
        """Extract payment data from row - flexible mapping for now"""
        return {
            'code': str(first_row[0]).strip() if first_row[0] else '',
            'employee_number': self._normalize_emp_no(first_row[1]) if len(first_row) > 1 else '',
            'amount': first_row[2] if len(first_row) > 2 else 0,
            'request_date': self.compute_date(first_row[9]) if len(first_row) > 9 else None,
            'requester_name': str(first_row[3]).strip() if len(first_row) > 3 else '',
            'description': str(first_row[8]).strip() if len(first_row) > 8 else '',
            'quantity': 1,
            'unit_price': first_row[2] if len(first_row) > 2 else 0,
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
            
            if payment_number:
                existing_memo = self.env['memo.model'].sudo().search([
                    ('code', '=ilike', code)], limit=1)
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
                
                memo_id = self.env['memo.model'].sudo().create({
                    'code': code,
                    'migrated_legacy_id': payment_number,
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
                    row_data = self._process_payment_row(row)
                    vals = {
                        'memo_id': memo_id.id,
                        'memo_type': memo_id.memo_type.id,
                        'memo_type_key': memo_id.memo_type_key,
                        'description': row_data['description'] or row_data['requester_name'],
                        'quantity_available': row_data['quantity'],
                        'amount_total': row_data['unit_price'],
                    }
                    self.env['request.line'].sudo().create(vals)
                    line_count += 1
                
                _logger.info(f"Created payment {memo_id.code} with {line_count} lines")
                success_records.append(f"{memo_id.code} ({line_count} lines)")
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