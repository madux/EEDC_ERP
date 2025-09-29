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

_logger = logging.getLogger(__name__)


class ImportAccountData(models.TransientModel):
    _name = 'import.account.data'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename") 
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection(
        selection=[
            ("transaction", "Account transactions"),
            ("others", "Others"),
        ],
        string="Import Type", tracking=True,
        required=True, default = "transaction"
    )
    coa_prefix = fields.Selection(
        selection=[
            ("none", ""),
            ("01", "[01] HOLDCO"),
            ("02", "[02] MAINPOWER"),
            ("03", "[03] FIRSTPOWER"),
            ("04", "[04] TRANSPOWER"),
            ("05", "[05] EASTLAND"),
            ("06", "[06] NEWERA"),
        ],
        string="Company Chart of Account Prefix", tracking=True,
        required=True, default = ""
    )

    running_journal_id = fields.Many2one('account.journal', string="Running Journal", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True)
    default_account = fields.Many2one('account.account', string="Default account to be used to balance")
    
    def import_button(self):
        '''Used to import accounts debit and credit details from excel
        Excel format: See file in data/account_detail.xlsx
        or use the following header structure of excel
        Code [0]	Account Name [1]	DEBIT[2]	CREDIT[3]																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																																														
        '''
        if self.import_type == "transaction":
            return self.import_account_transaction()
        else:
            raise ValidationError("Not yet available")
        
    def import_account_transaction(self):
        if self.data_file:
            file_datas = base64.decodebytes(self.data_file)
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
        account_bank_statement_line = self.env['account.bank.statement.line'].sudo()
        if not self.running_journal_id:
            raise ValidationError('please select a running journal')
        else:
            if self.running_journal_id and self.running_journal_id.company_id.id != self.company_id.id:
                raise ValidationError(f"Running journal has company : {self.running_journal_id.company_id.name} different from the selected company {self.company_id.name}") 
        if self.coa_prefix == "none":
            raise ValidationError('please select a Company Chart of Account Prefix')
        
        if self.default_account and self.default_account.company_id.id != self.company_id.id:
                raise ValidationError(f"default account has company {self.default_account.company_id.name} different from the selected company {self.company_id.name}") 
        
        account_move = self.env['account.move'].sudo()
        date_of_payment = fields.Date.today() 
        # journal_row = row[4]
        # source_journal = self.env['account.journal'].search(['|',('code', '=', journal_row), ('name', '=', journal_row)], limit = 1)
        je_number =f"""{datetime.strftime(fields.Date.today(), "%m/%d/%Y")} Opening Balance"""
        inv = account_move.create({  
            'ref': je_number,
            'origin': je_number,
            'company_id': self.company_id.id,
            'invoice_date': date_of_payment or fields.Date.today(),
            'currency_id': self.company_id.currency_id.id,
            'date': fields.Date.today(),
            'journal_id': self.running_journal_id.id, #source_journal.id or 
            'move_type': 'entry',
        })
        total_debit = 0
        total_credit = 0
        for row in file_data:
            '''FORMAT ==> Code [0]	Account Name [1]	DEBIT[2]	CREDIT[3]'''
            if row[0]:
                acc_code = int(row[0]) if type(row[0]) in [int, float] else row[0]
                _logger.info(f'Account code is: {acc_code}')
                
                account_code = f"{self.coa_prefix}{acc_code}" # e.g 02100002
                narration = row[1]
                # debit = float(row[2]) if row[2] and int(row[2]) > -1 else False
                # credit = float(row[3]) if row[3] and int(row[3]) > -1 else False
                debit = float(row[2]) if row[2] else 0
                credit = float(row[3]) if row[3] else 0
                account_head_id = self.env['account.account'].search([('code', '=', account_code)], limit=1)
                _logger.info(f'WHAT ARE DEBIT AND CREDIT {debit} {credit}')
                
                if account_head_id:
                    if account_head_id.company_id.id != self.company_id.id:
                        _logger.info(f'Account code {account_head_id} does not related to {self.company_id.name}')
                        unsuccess_records.append(f'Account code {account_head_id} is not related to {self.company_id.name}')
                    else:
                        if debit or credit:
                            year, month, day = False, False, False
                            date_row = row[5]
                            if date_row:
                                if type(date_row) in [float, int]:
                                    date_of_payment = datetime(*xlrd.xldate_as_tuple(date_row, 0))
                                elif type(date_row) in str:
                                    dp = date_row.split('/')
                                    if dp:
                                        year = int(dp[2])
                                        month = int(dp[0])
                                        day = int(dp[1])
                                        date_of_payment = date(year, month, day)
                            movelines = {
                                'name': narration,
                                'account_id': account_head_id.id,
                                'credit': credit,
                                'debit': debit,
                                'balance_default_account_id': self.default_account.id, # default account to use to balance the leg
                                # 'credit_account_id': self.default_account.id, # account of the bank that will be on credit
                            }
                            
                            line = movelines
                            if line.get('credit'):# and line.get('credit') > 0:
                                moveline = [
                                    {
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('account_id'),
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': 0.0,
                                        'credit': line.get('credit'),
                                        'move_id': inv.id, 
                                        'company_id': self.company_id.id,
                                    },
                                    {
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('balance_default_account_id'),
                                        # 'account_id': self.running_journal_id.suspense_account_id.id,
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': line.get('credit'),
                                        'credit': 0.0,
                                        'move_id': inv.id,
                                        'company_id': self.company_id.id,
                                    }]
                                total_credit += line.get('credit')
                                # self.create_update_budget_line(line.get('debit_account_id'), inv.journal_id.id, inv.journal_id.branch_id, False, False, False, False, date_of_payment, budget_amount=False, amount_used=line.get('credit'))
                                
                            else:#lif line.get('debit') and line.get('debit') > 0:
                                moveline = [{
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('account_id'),
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': line.get('debit'),
                                        'credit': 0.0,
                                        'move_id': inv.id, 
                                        'company_id': self.company_id.id,
                                    }, 
                                            
                                    {
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('balance_default_account_id'),
                                        # 'account_id': self.running_journal_id.suspense_account_id.id,
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': 0.0,
                                        'credit': line.get('debit'),
                                        'move_id': inv.id,
                                        'company_id': self.company_id.id,
                                    }]
                                total_debit += line.get('debit')
                                
                                
                            inv.invoice_line_ids = [(0, 0, move) for move in moveline]
                            # inv.action_post()
                            _logger.info(f'Loading the created new move with id: {inv.id}')
                            count += 1
                            success_records.append(row)
                        else:
                            # unsuccess_records.append(f"{row} : Credit and debit must be equal or greater than 0:")
                            _logger.info(f'Credit and debit must be equal or greater than 0:')
                else:
                    unsuccess_records.append(f"No related account found with code {self.coa_prefix} {row[0]}  => {account_code} found ")
                    _logger.info(f'ACCOUNT HEAD/CODE NOT FOUND: {self.coa_prefix} {row[0]}  => {account_code}')
            else:
                _logger.info(f'Empty row skipped')
        # inv.invoice_line_ids = [(0, 0, {
        #     'name': f"Balance Entry line -  {inv.ref}",
        #     'ref': f"Balance Entry line - {inv.ref}",
        #     'account_id': line.get('balance_default_account_id'),
        #     'analytic_distribution': False, # analytic_distribution_id.id,
        #     'debit': total_debit,
        #     'credit': total_credit,
        #     'move_id': inv.id,
        #     'company_id': self.company_id.id,
        # })]
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        _logger.info(f'ANY ERRORS 1 {errors} ')
        if len(errors) > 1:
            _logger.info(f'ANY ERRORS {errors} ')
            message = '\n'.join(errors)
            # raise ValidationError(message)
            return self.env['hr.import_applicant.wizard'].confirm_notification(message)
        else:
            return True
    
    
