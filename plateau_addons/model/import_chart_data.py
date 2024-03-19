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


class ImportPLCharts(models.TransientModel):
    _name = 'pl.import.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)

    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Account Type", tracking=True,
        required=True,
    )
    journal_type = fields.Selection(
        selection=[
            ("purchase", "Purchase"),
            ("sale", "Sale"),
            ("bank", "Bank"),
            ("cash", "Cash"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Journal Type", tracking=True,
        required=True,
    )

    default_account = fields.Many2one('account.account', string="Default account")

    def create_chart_of_account(self, name, code):
        account_chart_obj = self.env['account.account']
        if name and code:
            account_existing = account_chart_obj.search([('code', '=', int(code))], limit = 1)
            account = account_chart_obj.create({
                        "name": name.strip().upper(),
                        "code": int(code),
                        "reconcile": True,
                        "account_type": self.account_type,
                    }) if not account_existing else account_existing
            return account
        else:
            return None

    def create_company(self, name, company_registry):
        if name and company_registry:
            company_obj = self.env['res.company']
            company = company_obj.search([('company_registry', '=', company_registry)], limit=1)
            if not company:
                company = self.env['res.company'].create({
                    'name': name,
                    'company_registry': company_registry,
                })
            return company
        else:
            return None
        
    # def create_journal(self, name, company_registry):
    #     if name and company_registry:
    #         company_obj = self.env['res.company']
    #         company = company_obj.search([('company_registry', '=', company_registry)], limit=1)
    #         if not company:
    #             company = self.env['res.company'].create({
    #                 'name': name,
    #                 'company_registry': company_registry,
    #             })
    #         return company
    #     else:
    #         return None

    def generate_analytic_plan(self, partner):
        analytic_account_plan = self.env['account.analytic.plan'].sudo()
        if partner:
            account_existing = analytic_account_plan.search([('code', '=', partner.vat)], limit = 1)
            account = analytic_account_plan.create({
                        "name": partner.name,
                        "code": partner.vat,
                        "default_applicability": 'optional',
                    }) if not account_existing else account_existing
            return account
        else:
            return None

    def create_contact(self, name, code):
        if name and code:
            partner = self.env['res.partner'].search([('vat', '=', code)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': name,
                    'vat': code,
                })
            return partner
        else:
            return None
        
    def create_branch(self, name, code):
        if name and code:
            branch = self.env['multi.branch'].search([('code', '=', code)], limit=1)
            if not branch:
                branch = self.env['multi.branch'].create({
                    'name': name,
                    'code': code,
                })
            return branch
        else:
            return None
        
    def create_analytic_account(self, name, partner, branch):
        analytic_account = self.env['account.analytic.account'].sudo()
        if partner:
            plan_id = self.generate_analytic_plan(partner)
            account_existing = analytic_account.search([('code', '=',partner.vat)], limit = 1)
            account = analytic_account.create({
                        "name": name, #partner.name.strip().title() +' - '+ partner.vat,
                        "partner_id": partner.id,
                        "branch_id": branch.id,
                        "company_id": self.env.user.company_id.id,
                        "plan_id": plan_id.id if plan_id else False,
                    }) if not account_existing else account_existing
            return account
        else:
            return None
        
    def create_journal(self, code, name, branch, account):
        if name and code:
            journal_obj =  self.env['account.journal']
            account_journal_existing = journal_obj.search([('code', '=',code)], limit = 1)
            journal = journal_obj.create({
                'name': name,
                'type': self.journal_type,
                'code': code,
                'branch_id': branch.id,
                'default_account_id': self.default_account.id
            }) if not account_journal_existing else account_journal_existing
            return journal
        else:
            return None

    def create_vendor_bill(self, company_id, account_id, analytic_account_id, **kwargs):
        journal_id = self.env['account.journal'].search(
        [('type', '=', 'purchase'),
            ('code', '=', 'BILL')
            ], limit=1)
        account_move = self.env['account.move'].sudo()
        partner_id = company_id.partner_id
        inv = account_move.create({  
            'ref': self.code,
            'origin': kwargs.get('code'),
            'partner_id': partner_id.id,
            'company_id': company_id.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            # Do not set default name to account move name, because it
            # is unique
            'name': f"{kwargs.get('code')}",
            'move_type': 'in_receipt',
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'journal_id': journal_id.id,
            'invoice_line_ids': [(0, 0, {
                    'name': kwargs.get('description'),
                    'ref': f"{kwargs.get('code')}",
                    'account_id': account_id.id,
                    'price_unit': f"{kwargs.get('amount')}",
                    'quantity': 1,
                    'discount': 0.0,
                    'code': kwargs.get('code'),
                    # 'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                    # 'product_id': pr.product_id.id if pr.product_id else None,
            })],
        })
        return inv
          
    def import_records_action(self):
        if self.data_file:
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
        for row in file_data:
            if row[0] and row[1] and row[5] and row[2]:
                account_id = self.create_chart_of_account(row[5], row[2])
                _logger.info(
                    f"Surviving thiws ganme {row} and {account_id.name}"
                )
                partner = self.create_contact(row[1].strip(), row[0])
                branch = self.create_branch(row[1].strip(), row[0])
                journal = self.create_journal(row[0], row[1], branch, account_id)
                account_id.update({
                    'allowed_journal_ids': [(4, journal.id)]
                })
                self.create_analytic_account(row[3], partner, branch)
                # kwargs = {'code': row[0], 'description': row[3]}
                # vendor_bill = self.create_vendor_bill(company_id, account_id, analytic_account_id, row, kwargs)
                _logger.info(f'data artifacts generated: {account_id.name}')
                count += 1
                success_records.append(row[0])
            else:
                unsuccess_records.append(row[0])
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            # return self.confirm_notification(message)

    def confirm_notification(self,popup_message):
        view = self.env.ref('plateau_addons.pl_import_wizard_form_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'pl.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }


class PLDialogModel(models.TransientModel):
    _name="pl.confirm.dialog"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)
