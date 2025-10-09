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
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        if self.model_import == "cash_advance":
            if self.import_type == "new":
                for row in file_data:
                    migrated_number = str(row[0]).strip() if row[0] else ''
                    code = str(row[0]).strip() if row[0] else ''
                    subject = str(row[0]).strip() if row[0] else ''
                    employee_number = str(row[1]).strip() if row[1] else ''
                    total_amount = row[2]
                    request_date = self.compute_date(row[10]) 
                    if migrated_number:
                        existing_memo = self.env['memo.model'].sudo().search([
                            ('code', '=ilike', code)], limit=1) 
                        if existing_memo:
                            if self.clear_data:
                                existing_memo.unlink()
                            else:
                                _logger.info(f"Skipping existing memo {code}")
                                unsuccess_records.append(f"Skipped existing record: {code}")
                                count += 1
                                continue
                        employee = self.env['hr.employee'].sudo().search([('employee_number', '=', employee_number)], limit=1)
                        _logger.info(f"Processing {row[0]} - {migrated_number} ..EMPLOYEE: {employee_number}")
                        memo_id = self.env['memo.model'].sudo().create({
                            'code': code,
                            'migrated_legacy_id': migrated_number,
                            'requester_name': row[9],
                            'name': subject,
                            'employee_id': employee.id if employee else self.default_employee_id.id or self.env.user.employee_id.id,
                            'code': code,
                            'state': "Done",
                            'stage_id': self.memo_config_id.stage_ids[-1].id,
                            'company_id': self.company_id.id,
                            'branch_id': self.branch_id.id,
                            'memo_setting_id': self.memo_config_id.id,
                            'memo_type': self.memo_config_id.memo_type.id,
                            'request_date': request_date if request_date else fields.Date.today(),
                            'memo_type_key': self.memo_config_id.memo_key,
                        })
                        vals = {
                            'memo_id': memo_id.id,
                            'memo_type': memo_id.memo_type.id,
                            'memo_type_key': memo_id.memo_type_key,
                            'description': row[3] or row[6],
                            'quantity_available': row[4] or 1,
                            'amount_total':  row[5],
                        }
                        self.env['request.line'].sudo().create(vals)
                        _logger.info(f"Memo record created {memo_id.code}")
                        success_records.append(memo_id.code)
                    else:
                        unsuccess_records.append(f"Memo record created {migrated_number}")
                    count += 1
            elif self.import_type == "update":
                for row in file_data:
                    migrated_number = str(row[0]).strip() if row[0] else ''
                    code = str(row[0]).strip() if row[0] else ''
                    subject = str(row[0]).strip() if row[0] else ''
                    employee_number = str(row[1]).strip() if row[1] else ''
                    total_amount = row[2]
                    request_date = self.compute_date(row[10]) 
                    if migrated_number:
                        existing_memo = self.env['memo.model'].sudo().search([
                            ('code', '=ilike', code)], limit=1)
                        if existing_memo:
                            employee = self.env['hr.employee'].sudo().search([('employee_number', '=', employee_number)], limit=1)
                            _logger.info(f"Updating {row[0]} - {migrated_number} ..EMPLOYEE: {employee_number}")
                            existing_memo.sudo().write({
                                'migrated_legacy_id': migrated_number,
                                'requester_name': row[9],
                                'name': subject,
                                'employee_id': employee.id if employee else self.default_employee_id.id or self.env.user.employee_id.id,
                                'request_date': request_date if request_date else fields.Date.today(),
                            })
                            # Update or create request line
                            existing_line = self.env['request.line'].sudo().search([
                                ('memo_id', '=', existing_memo.id)], limit=1)
                            vals = {
                                'memo_id': existing_memo.id,
                                'memo_type': existing_memo.memo_type.id,
                                'memo_type_key': existing_memo.memo_type_key,
                                'description': row[3] or row[6],
                                'quantity_available': row[4] or 1,
                                'amount_total':  row[5],
                            }
                            if existing_line:
                                existing_line.sudo().write(vals)
                            else:
                                self.env['request.line'].sudo().create(vals)
                            _logger.info(f"Memo record updated {existing_memo.code}")
                            success_records.append(f"{existing_memo.code} (updated)")
                        else:
                            _logger.info(f"Record not found for update: {code}")
                            unsuccess_records.append(f"Record not found: {code}")
                    else:
                        unsuccess_records.append(f"Missing migrated number for row")
                    count += 1
            else:
                pass     
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
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