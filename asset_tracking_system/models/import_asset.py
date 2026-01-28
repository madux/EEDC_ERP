
from odoo import fields, models ,api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
import base64

_logger = logging.getLogger(__name__)


class ImportAssetWizard(models.TransientModel):
    _name = 'import.asset.wizard'

    data_file = fields.Binary(string="Upload File (.xls)", required=True)
    filename = fields.Char("Filename")
    update_existing_asset = fields.Boolean("Update Existing Non running Asset")
    
    index = fields.Integer("Sheet Index", default=0) # e.g 0, 1, 2
    company_id = fields.Many2one(comodel="res.company", string="Company", required=True, default=lambda self: self.env.user.company_id.id)
    location_id = fields.Many2one(comodel="multi.branch", string="Location", required=True, default=lambda self: self.env.user.branch_id.id)
    asset_model = fields.Many2one(comodel="account.asset", string="Asset model", required=True)
    
    def get_asset_model(self, asset_model_obj):
        return dict(
            method = asset_model_obj.method,
            method_number = asset_model_obj.method_number,
            method_period = asset_model_obj.method_period,
            prorata_computation_type = asset_model_obj.prorata_computation_type,
            account_asset_id = asset_model_obj.account_asset_id, # cost or fixed asset account
            account_depreciation_id = asset_model_obj.account_depreciation_id,
            account_depreciation_expense_id = asset_model_obj.account_depreciation_expense_id,
            journal_id = asset_model_obj.journal_id,
        )
        
    def create_asset(self, **kwargs):
        # create account asset using asset model and values of our excel template
        asset_model = self.get_asset_model(self.asset_model)
        model_id = self.asset_model.id,
        location_id = self.location_id.id,
        
        method = asset_model.method
        prorata_computation_type = asset_model.get('prorata_computation_type'),
        account_asset_id = asset_model.get('account_asset_id'),
        account_depreciation_id = asset_model.get('account_depreciation_id'),
        account_depreciation_expense_id = asset_model.get('account_depreciation_expense_id'),
        journal_id = asset_model.get('journal_id'),
        method_period = asset_model.get('method_period'),
        
        method_number = kwargs.get('method_number'),
        name = kwargs.get('name'),
        original_value = kwargs.get('original_value')
        prorata_date = kwargs.get('prorata_date')
        product_desc = kwargs.get('product_desc')
        qty_received= kwargs.get('qty_received')
        serial_number = kwargs.get('serial_number')
        asset_code = kwargs.get('asset_code')
        origin_ref = kwargs.get('origin_ref')
        
        self.env['account.asset'].sudo().create({
            'method': method,
            'method_number': method_number,
            'method_period': method_period,
            'prorata_computation_type': prorata_computation_type,
            'account_asset_id': account_asset_id,
            'account_depreciation_id': account_depreciation_id,
            'account_depreciation_expense_id': account_depreciation_expense_id,
            'journal_id': journal_id,
            'name': name,
            'model_id': model_id,
            'location_id': location_id,
            'original_value': original_value,
            'prorata_date': prorata_date,
            'product_desc': product_desc,
            'qty_received': qty_received,
            'serial_number': serial_number,
            'asset_code': asset_code,
            'origin_ref': origin_ref,
        })
        
    def _clean_numeric_value(self, value):
        """Clean and convert various formats to float"""
        if not value:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
            
            value = value.replace(',', '').replace(' ', '')
            
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def import_records_action(self):
        if self.data_file: 
            # CHECKS IF THE USER HAS LOADED EXCEL FILE
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
        
        def find_existing_asset(asset_code, serial_number=None):
            asset_id = False
            if asset_code:
                code = str(int(asset_code)) if type(asset_code) in [float, int] else asset_code 
                serial_number = str(int(serial_number)) if type(serial_number) in [float, int] else serial_number 
                account_asset = self.env['account.asset'].sudo().search([
                    ('asset_code', '=', code),
                    ('company_id', '=', self.company_id.id), 
                    '|', ('serial_number', '=', serial_number), 
                    ], limit = 1)
                if account_asset:
                    asset_id = account_asset.id
                else:
                    asset_id = False 
            return asset_id
        
        for row in file_data:
            # try:
            sequence = row[0]
            prorata_date = datetime.strptime(row[1], '%d/%m/%Y')
            origin_ref = row[2]
            asset_code = row[3]
            serial_number = row[4]
            product_desc = row[6]
            name = row[6]
            location_id = self.location_id.id
            qty_received = row[8]
            original_value = self._clean_numeric_value(row[9])
            method_number = row[10] # life cycle
            
            found_asset_id = find_existing_asset(asset_code, serial_number)
            if found_asset_id:
                code = asset_code or serial_number
                if self.update_existing_asset and found_asset_id.state == 'draft': 
                    found_asset_id.update({
                        'name': name,
                        'prorata_date': prorata_date,
                        'origin_ref': name,
                        'asset_code': asset_code,
                        'product_desc': product_desc,
                        'serial_number': serial_number,
                        'location_id': location_id,
                        'qty_received': qty_received,
                        'original_value': original_value,
                        'method_number': method_number,
                        
                        'method': self.asset_model.method,
                        'method_period': self.asset_model.method_period,
                        'prorata_computation_type': self.asset_model.prorata_computation_type,
                        'account_asset_id': self.asset_model.account_asset_id.id,
                        'account_depreciation_id': self.asset_model.account_depreciation_id.id,
                        'account_depreciation_expense_id': self.asset_model.account_depreciation_expense_id.id,
                        'journal_id': self.asset_model.journal_id.id,
                        'model_id': self.asset_model.id,
                    })
                else:
                    unsuccess_records.append(f'Asset with {str(code)} Already exists')
            else:
                self.create_asset(
                    sequence=sequence,
                    prorata_date=prorata_date,
                    origin_ref=origin_ref,
                    name=name,
                    asset_code=asset_code,
                    serial_number=serial_number,
                    product_desc=product_desc,
                    location_id=location_id,
                    qty_received=qty_received,
                    original_value=original_value,
                    method_number=method_number,
                ) 
                success_records.append(asset_code)
            count += 1
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
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

