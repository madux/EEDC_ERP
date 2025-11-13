from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
import logging 
from bs4 import BeautifulSoup
import io
import xlwt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

_logger = logging.getLogger(__name__)


class AccountDynamicReport(models.Model):
    _name = "account.dynamic.report"

    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals'
        )
    
    account_ids = fields.Many2many(
        'account.account',
        string='Accounts',
        default=lambda self: [(6, 0, [])]
        )
    name = fields.Char(
        string='Report Name',
        default="Financial Report"
        )
    account_analytics_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts'
        )
    report_type = fields.Selection(
        selection=[
            ("all", "All Statement"),
            ("monthly_expenditure", "Monthly Expenditures"),
            ("first_quarterly", "First Quarterly Expenditures"),
            ("second_quarterly", "Second Quarterly Expenditures"),
            ("third_quarterly", "Third Quarterly Expenditures"),
            ("fourth_quarterly", "Fourth Quarterly Expenditures"),
            ("consolidated_district", "Consolidated District Report"),
            ("cf", "CashFlow Statement"),
            ("bank", "Trial Balance"),
            ("cash", "General Ledger"),
        ],
        string="Report Type",
        required=False, default="consolidated_district"
    )
    format = fields.Selection(
        selection=[
            ("pdf", "PDF"),
            ("html", "System Viewer"),
            ("xml", "XML"),
            ("xls", "Excel"),
            ("tab", "Tableau"),
            ("powerBi", "Power BI"),
            ("dashboard", "Dashboard"),
        ],
        string="Format",
        required=False, default="html"
    )
    
    company_id = fields.Many2one('res.company')
    company_ids = fields.Many2many('res.company', string='Companies') #, domain=lambda self: [('id', 'in', self.env.companies.ids)]
    branch_ids = fields.Many2many('multi.branch', string='District') #, domain=lambda self: [('company_id', 'in', self.company_ids)]
    moveline_ids = fields.Many2many('account.move.line', string='Dummy move lines')
    # budget_id = fields.Many2one('ng.account.budget.line', string='Budget')
    fiscal_year = fields.Date(string='Fiscal Year', default=fields.Date.today())
    date_from = fields.Date(string='Date from', default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string='Date to', default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_type = fields.Selection(
        [
            ("all", "All Account Type"),
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
        default="expense",
        string="Account Type",
    )
    account_head_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"),
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital Expenditure"),
        ("Other", "Others"),
        ], default="Overhead", string="Account Head", 
    )
    excel_file = fields.Binary('Download Excel file', readonly=True)
    filename = fields.Char('Excel File')
    xml_file = fields.Binary('Download XML Report', readonly=True)
    xml_filename = fields.Char('XML Filename', default="report.xml")
    def search_domain(self):
        user_branch_ids = self.env.user.branch_ids.ids + [self.env.user.branch_id.id]
        search_domain = [('move_id.state', 'in', ['posted']), ('branch_id', 'in', user_branch_ids), ('account_id.account_head_type', '!=', False)]
        if self.journal_ids:
            search_domain.append(('move_id.journal_id.id', 'in', [j.id for j in self.journal_ids]))
        if self.branch_ids:
            search_domain.append(('move_id.branch_id.id', 'in', [j.id for j in self.branch_ids]))
        if self.account_ids:
            search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))
        if self.account_head_type:
            search_domain.append(('account_id.account_head_type', '=', self.account_head_type))
        if self.date_from and self.date_to:
            search_domain.extend([('date', '>=', self.date_from),('date', '<=', self.date_to)])
        return search_domain
    
    def get_budget(self, tag, branch_ids):
        budget_line = self.env['ng.account.budget.line'].sudo()
        budget_line_ids = budget_line.search([
            ('budget_type', '=', tag.account_head_type),
            ('branch_id.id', 'in', branch_ids)])
        return budget_line_ids
        
    def print_reports(self):
        search_domain = self.search_domain()
        account_tags = self.env['account.account.tag']
        report_obj = {}
        user_branch_ids = self.branch_ids.ids if self.branch_ids else self.env.user.branch_ids.ids + [self.env.user.branch_id.id]
        
        for tag in account_tags.sudo().search([]):
            """Search all the account tags and get there account balances"""
            period_filter = True if self.date_from and self.date_to else False
            tag_balance = tag.get_monthly_moves_and_balance(search_domain, period_filter)
            previous_month_balance = tag_balance[0] 
            current_month_balance = tag_balance[1]
            tag_budget_ids = self.get_budget(tag, user_branch_ids)
            budget_balance = [rec.budget_balance for rec in tag_budget_ids]
            current_balance = previous_month_balance + current_month_balance
            report_obj[f'{tag.id}'] = {
                'id': tag.id, 
                'name': tag.name, 
                'previous_month_expenses': previous_month_balance, 
                'current_month_expenses': current_month_balance, 
                'current_balance': current_balance, 
                'tag_budget_balance': sum(budget_balance), 
                }
            # if tag.parent_id:
            #     parentid= tag.parent_id
            #     report_obj.update({f'{tag.parent_id.id}': report_obj})
        _logger.info(f"MONTHLY REPORT {report_obj}")
        

    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user

        if 'branch_ids' in fields_list:
            branch_ids = user.branch_ids.ids or []
            if user.branch_id:
                branch_ids = list(set(branch_ids + [user.branch_id.id]))
            res.update({'branch_ids': [(6, 0, branch_ids)]})

        if 'company_ids' in fields_list:
            comp_ids = user.company_ids.ids or ([user.company_id.id] if user.company_id else [])
            res.update({'company_ids': [(6, 0, comp_ids)]})

        if 'company_id' in fields_list and user.company_id:
            res.update({'company_id': user.company_id.id})

        return res
    
    
    def _get_budget(self):
        return self.env['ng.account.budget'].search([
            ('branch_id','in', self.branch_ids.ids),
            ('budget_type','=', self.account_head_type),
        ], limit=1)
        
    
    def _get_date_range(self):
        start_date, end_date = self.date_from, self.date_to
        
        is_quarterly = 'quarterly' in self.report_type
        if is_quarterly or not (start_date and end_date):
            if not self.fiscal_year:
                raise ValidationError("You must provide a Fiscal Year to generate this report.")
            
            year = self.fiscal_year.year
            
            if self.report_type == 'first_quarterly':
                start_date = datetime(year, 1, 1).date()
                end_date = datetime(year, 3, 31).date()
            elif self.report_type == 'second_quarterly':
                start_date = datetime(year, 4, 1).date()
                end_date = datetime(year, 6, 30).date()
            elif self.report_type == 'third_quarterly':
                start_date = datetime(year, 7, 1).date()
                end_date = datetime(year, 9, 30).date()
            elif self.report_type == 'fourth_quarterly':
                start_date = datetime(year, 10, 1).date()
                end_date = datetime(year, 12, 31).date()
            else:
                start_date = self.fiscal_year.replace(day=1)
                end_date = start_date + relativedelta(months=1, days=-1)
                
        if start_date and end_date:
            if end_date > start_date + relativedelta(years=1):
                end_date = start_date + relativedelta(years=1, days=-1)
                _logger.warning(f"Report date range exceeded one year. It has been automatically capped to {end_date}.")
        
        month_headers = []
        current_date = start_date
        while current_date <= end_date:
            month_headers.append(current_date.strftime('%b').upper())
            current_date += relativedelta(months=1)
            
        return start_date, end_date, list(dict.fromkeys(month_headers))

    def _build_base_domain(self, date_from, date_to, branch_id, company_id):
        """Builds a dynamic search domain based on wizard selections."""
        domain = [
            ('date', '>=', date_from), 
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
        ]
        
        if company_id: 
            domain.append(('move_id.company_id', '=', company_id))
        
        if branch_id:
            domain.extend([
                '|', '|',
                ('move_id.branch_id', '=', branch_id),
                ('journal_id.branch_id', '=', branch_id),
                ('branch_id', '=', branch_id)
            ])
        
        if self.journal_ids: 
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.account_ids: 
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.partner_id: 
            domain.append(('partner_id', '=', self.partner_id.id))
        
        return domain

        
    
    def action_generate_report(self):
        self.ensure_one()
        
        if self.report_type == 'consolidated_district':
            return self.action_generate_consolidated_district_report()
    
        if self.format in ['pdf', 'html']:
            return self.action_print_report()
        elif self.format == 'xls':
            return self.action_export_as_excel()
        elif self.format == 'xml':
            return self.action_export_as_xml()
        
    
    def action_print_report(self):
        self.ensure_one()
        branches_to_process = self.branch_ids or self.env['multi.branch'].search([])
        if not branches_to_process:
            raise ValidationError("No district selected or configured for the current user.")
        
        company = self.company_id
        
        start_date, end_date, month_headers = self._get_date_range()
        
        is_quarterly = True if 'quarterly' in self.report_type else False
        
        all_branch_reports = []
        for branch in branches_to_process:
            report_lines = self._get_hierarchical_report_data(start_date, end_date, month_headers, branch, company, is_quarterly=is_quarterly)
            if report_lines:
                all_branch_reports.append({
                    'title': f'HEAD: {branch.code} - {branch.name}',
                    'report_lines': report_lines,
                })
        
        if not all_branch_reports:
            raise ValidationError("No data could be generated for the selected criteria.")
        
        budget_type_name = dict(self._fields['account_type'].selection).get(self.account_type, '')
        period_string = ""
        if not is_quarterly:
            period_string = (
                f"MONTHLY RETURNS {start_date.strftime('%B %Y')}"
                if start_date.year == end_date.year and start_date.month == end_date.month
                else f"MONTHLY RETURNS {start_date.strftime('%B %Y')} - "
                    f"{end_date.strftime('%B %Y')}"
            )
        else:
            q_map = {'first': 'Q1', 'second': 'Q2', 'third': 'Q3', 'fourth': 'Q4'}
            q_name = next((v for k, v in q_map.items() if k in self.report_type), "QX")
            period_string = f"{dict(self._fields['report_type'].selection).get(self.report_type, '')} ({q_name}) {end_date.year}"

        data = {
            'doc_model': self._name, 'data': all_branch_reports,
            'month_headers': month_headers, 'fiscal_year': end_date.strftime('%Y'),
            'subtitle': f"{budget_type_name.upper()} - {period_string.upper()}",
            'quarterly_total_header': f"{month_headers[0] if month_headers else ''} - {month_headers[-1] if month_headers else ''} {end_date.year}" if is_quarterly else ""
        }
        
        
        action_ref = 'eedc_report.action_report_expenditure_quarterly' if is_quarterly else 'eedc_report.action_report_expenditure_monthly'
        report_action = self.env.ref(action_ref)
        report_obj = self.env['ir.actions.report'].sudo().browse([report_action.id])
        if self.format == 'html':
            report_obj.sudo().update({'report_type': 'qweb-html'})
        else:
            report_obj.sudo().update({'report_type': 'qweb-pdf'})
        
        return report_action.report_action(self, data=data)
    
    
    def _get_hierarchical_report_data(self, start_date, end_date, month_headers, branch, company, is_quarterly=False):
        year_start = end_date.replace(day=1, month=1)
        domain_end_date = end_date
        
        # tags = self.env['economic.tag'].search([('account_type', '=', self.account_type)]) if self.account_head_type != 'all' else self.env['economic.tag'].search([])
        if self.account_type != 'all':
            tags = self.env['economic.tag'].search([('account_type', '=', self.account_type)])
        else:
            tags = self.env['economic.tag'].search([])
            
        all_accounts = tags.mapped('account_ids')
        if not all_accounts: return []

        base_domain = self._build_base_domain(year_start, domain_end_date, branch.id, company_id=False)
        """args : company_id=False, this will not add company in the domain builder"""
        if self.company_ids:
            base_domain.append(('company_id', 'in', self.company_ids.ids))
        
        base_domain.append(('account_id', 'in', all_accounts.ids))
        all_moves = self.env['account.move.line'].search(base_domain)

        # budget_domain = [('budget_type', '=', self.account_head_type), ('account_id', 'in', all_accounts.ids), ('branch_id', '=', branch.id)]
        # all_budget_lines = self.env['ng.account.budget.line'].search(budget_domain)
        REVENUE_TYPES = ['income', 'income_other']
        
        sum_field = 'credit' if self.account_type in REVENUE_TYPES else 'debit'

        account_data = {}
        for acc in all_accounts:
            moves_for_acc = all_moves.filtered(lambda m: m.account_id == acc)
            # budget_for_acc = all_budget_lines.filtered(lambda b: b.account_id == acc)
            
            monthly_values = {month: 0.0 for month in month_headers}
            for move in moves_for_acc.filtered(lambda m: start_date <= m.date <= end_date):
                month_key = move.date.strftime('%b').upper()
                if month_key in monthly_values:
                    monthly_values[month_key] += getattr(move, sum_field, 0.0)

            account_data[acc.code] = {
                # 'approved_budget': sum(budget_for_acc.mapped('allocated_amount')),
                'approved_budget': 0.0,
                'monthly_values': monthly_values,
                'previous_actual': sum(m.debit for m in moves_for_acc if m.date < start_date),
                'total_actual_to_date': sum(m.debit for m in moves_for_acc),
            }

        report_lines = {}
        for tag in tags:
            approved = sum(account_data.get(acc.code, {}).get('approved_budget', 0) for acc in tag.account_ids)
            previous = sum(account_data.get(acc.code, {}).get('previous_actual', 0) for acc in tag.account_ids)
            total_exp = sum(account_data.get(acc.code, {}).get('total_actual_to_date', 0) for acc in tag.account_ids)
            
            monthly_vals = {month: 0.0 for month in month_headers}
            for acc in tag.account_ids:
                for month in month_headers:
                    monthly_vals[month] += account_data.get(acc.code, {}).get('monthly_values', {}).get(month, 0)
            
            line_data = { 'code': tag.code, 'name': tag.name, 'level': 0, 'is_acc': 'no',
                           'approved_budget': approved, 
                           'monthly_values': monthly_vals }
            
            if is_quarterly:
                line_data.update({
                    'quarterly_total': total_exp,
                    'balance': approved - total_exp,
                    'percentage_perf': (total_exp / approved) * 100 if approved else 0.0,
                })
            else:
                line_data.update({
                    'previous_actual': previous,
                    'total_exp_to_date': previous + sum(monthly_vals.values()),
                    'balance': approved - (previous + sum(monthly_vals.values())),
                })
            report_lines[tag.code] = line_data

        for tag in tags.sorted(key=lambda t: t.id, reverse=True):
            if tag.parent_tag_id and tag.parent_tag_id.code in report_lines and tag.code in report_lines:
                p, c = report_lines[tag.parent_tag_id.code], report_lines[tag.code]
                p['approved_budget'] += c['approved_budget']
                p['balance'] += c['balance']
                if is_quarterly:
                    p['quarterly_total'] += c['quarterly_total']
                    p['percentage_perf'] = (p['quarterly_total'] / p['approved_budget']) * 100 if p['approved_budget'] else 0.0
                else:
                    p['previous_actual'] += c['previous_actual']
                    p['total_exp_to_date'] += c['total_exp_to_date']
                for month in month_headers:
                    p['monthly_values'][month] += c['monthly_values'].get(month, 0.0)

        final_report_data = []
        def build_recursive(tag, level):
            if tag.code in report_lines:
                line_data = report_lines[tag.code]
                line_data['level'] = level
                final_report_data.append(line_data)
                for acc in tag.account_ids.sorted(key=lambda a: a.code or ''):
                    data = account_data.get(acc.code, {})
                    approved = data.get('approved_budget', 0.0)
                    total_exp = data.get('total_actual_to_date', 0.0)
                    if approved or total_exp:
                        acc_line = {'code': acc.code, 'name': acc.name, 'level': level + 1, 'is_acc': 'yes',
                                    'approved_budget': approved, 'monthly_values': data.get('monthly_values', {})}
                        if is_quarterly:
                            acc_line.update({
                                'quarterly_total': total_exp, 'balance': approved - total_exp,
                                'percentage_perf': (total_exp / approved) * 100 if approved else 0.0,
                            })
                        else:
                            previous = data.get('previous_actual', 0.0)
                            acc_line.update({
                                'previous_actual': previous,
                                'total_exp_to_date': previous + sum(data.get('monthly_values', {}).values()),
                                'balance': approved - (previous + sum(data.get('monthly_values', {}).values())),
                            })
                        final_report_data.append(acc_line)
                for child in tags.filtered(lambda t: t.parent_tag_id == tag).sorted(key=lambda c: c.code):
                    build_recursive(child, level + 1)
        for tag in tags.filtered(lambda t: not t.parent_tag_id).sorted(key=lambda t: t.code):
            build_recursive(tag, 0)
        return final_report_data
    
    
    
    def _get_consolidated_district_data(self, start_date, end_date, month_headers, company):
        """
        Generates consolidated data across all selected districts for the same period.
        Shows individual accounts instead of tags, with expandable move lines.
        Includes "Unassigned District" column for entries without branch assignment.
        Returns: (report_lines, district_headers, district_codes)
        """
        self.ensure_one()
        _logger.info(f"=== Starting _get_consolidated_district_data for company: {company.name} (ID: {company.id}) ===")
        _logger.info(f"Date range: {start_date} to {end_date}")
        
        include_unassigned = not self.branch_ids # True if not branch ids
        _logger.info(f"Include Unassigned District: {include_unassigned} (branch_ids set: {bool(self.branch_ids)})")
        
        # branches_to_process = self.branch_ids or self.env['multi.branch'].search([('company_id','=', company.id)])
        branches_to_process = self.branch_ids or self.env['multi.branch'].search([('company_id','in', self.company_ids.ids)])
        # False or [12, 34, 65]
        _logger.info(f"Branches to process: {len(branches_to_process)} - {[b.name for b in branches_to_process]}")
        
        if not branches_to_process and not include_unassigned: # [12, 34, 65]
            _logger.warning(f"No branches found for company {company.name}")
            return [], [], [], []

        if self.account_ids:
            all_accounts = self.account_ids
            _logger.info(f"Using {len(all_accounts)} manually selected accounts")
        else:
            if self.account_type != 'all':
                all_accounts = self.env['account.account'].search([
                    ('company_id', '=', company.id), 
                    ('account_type', '=', self.account_type)
                ])
            else:
                all_accounts = self.env['account.account'].search([
                    ('company_id', '=', company.id), 
                ])
            _logger.info(f"Found {len(all_accounts)} accounts with type '{self.account_type}' for company {company.name}")

        if not all_accounts:
            _logger.warning(f"No accounts found for company {company.name} with type {self.account_type}")
            return [], [], [], []
        
        _logger.info(f"Processing accounts: {[(a.code, a.name) for a in all_accounts[:5]]}...")

        consolidated_data = {}
        district_headers = []
        district_codes = []

        for branch in branches_to_process:
            _logger.info(f"\n--- Processing branch: {branch.name} (ID: {branch.id}) ---")
            district_headers.append(branch.name.upper())
            district_codes.append(branch.code.upper())

            base_domain = self._build_base_domain(start_date, end_date, branch.id, company.id)
            base_domain.append(('account_id', 'in', all_accounts.ids))
            
            _logger.info(f"Search domain: {base_domain}")

            branch_moves = self.env['account.move.line'].search(base_domain)
            _logger.info(f"Found {len(branch_moves)} move lines for branch {branch.name}")
            
            if branch_moves:
                _logger.info(f"Sample move lines: {[(m.account_id.code, m.date, m.debit, m.credit) for m in branch_moves[:3]]}")

            self._process_branch_moves(branch_moves, branch, all_accounts, consolidated_data)

        if include_unassigned:
            _logger.info(f"\n--- Processing UNASSIGNED entries (no branch) ---")
            
            unassigned_code = 'UNASSIGNED'
            unassigned_name = 'UNASSIGNED DISTRICT'
            district_headers.append(unassigned_name)
            district_codes.append(unassigned_code)
            
            unassigned_domain = [
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('move_id.state', '=', 'posted'),
                ('move_id.company_id', '=', company.id),
                ('account_id', 'in', all_accounts.ids),
                '&', '&',
                ('branch_id', '=', False),
                ('move_id.branch_id', '=', False),
                ('journal_id.branch_id', '=', False),
            ]
            
            _logger.info(f"Unassigned domain: {unassigned_domain}")
            unassigned_moves = self.env['account.move.line'].search(unassigned_domain)
            _logger.info(f"Found {len(unassigned_moves)} UNASSIGNED move lines")
            
            if unassigned_moves:
                # Create a pseudo-branch object for unassigned entries
                UnassignedBranch = type('UnassignedBranch', (), {
                    'code': unassigned_code,
                    'name': unassigned_name,
                    'id': 0
                })()
                
                self._process_branch_moves(unassigned_moves, UnassignedBranch, all_accounts, consolidated_data)

        report_lines = []
        for key, data in consolidated_data.items():
            data['balance'] = data.get('total_revenue', 0.0) - data.get('total_expenditure', 0.0)
            if data.get('total_revenue', 0.0) > 0 or data.get('total_expenditure', 0.0) > 0:
                report_lines.append(data)

        report_lines.sort(key=lambda x: x.get('code', ''))
        
        _logger.info(f"=== Summary for {company.name}: {len(report_lines)} accounts with data ===")
        if report_lines:
            _logger.info(f"First account: {report_lines[0].get('code')} - Rev: {report_lines[0].get('total_revenue')}, Exp: {report_lines[0].get('total_expenditure')}")
        else:
            _logger.warning("NO REPORT LINES GENERATED - Check if account_head_type matches your data!")

        return report_lines, district_headers, district_codes, company.id


    def _process_branch_moves(self, branch_moves, branch, all_accounts, consolidated_data):
        """
        Helper method to process move lines for a branch (or unassigned entries)
        and update consolidated_data dictionary
        """
        for account in all_accounts:
            account_key = f"{account.code}_{account.name}"
            if account_key not in consolidated_data:
                consolidated_data[account_key] = {
                    'code': account.code,
                    'description': account.name,
                    'level': 0,
                    'is_account': True,
                    'is_expandable': True,
                    'district_values': {},
                    'move_details': {},
                    'total_revenue': 0.0,
                    'total_expenditure': 0.0,
                }

            account_moves = branch_moves.filtered(lambda m: m.account_id == account)

            if account_moves:
                revenue_total = sum(account_moves.mapped('credit'))
                expenditure_total = sum(account_moves.mapped('debit'))

                REVENUE_TYPES = ['income', 'income_other']
                
                if account.account_type in REVENUE_TYPES:
                    consolidated_data[account_key]['district_values'][branch.code] = revenue_total
                    consolidated_data[account_key]['total_revenue'] += revenue_total
                else:  # expense, asset_*, liability_*, equity_*
                    consolidated_data[account_key]['district_values'][branch.code] = expenditure_total
                    consolidated_data[account_key]['total_expenditure'] += expenditure_total

                if branch.code not in consolidated_data[account_key]['move_details']:
                    consolidated_data[account_key]['move_details'][branch.code] = []

                for move_line in account_moves:
                    move_data = {
                        'id': move_line.id,
                        'date': move_line.date.strftime('%Y-%m-%d') if move_line.date else '',
                        'reference': move_line.move_id.name or move_line.name,
                        'description': move_line.name or (move_line.move_id.ref if hasattr(move_line.move_id, 'ref') else '') or 'No Description',
                        'partner': move_line.partner_id.name if move_line.partner_id else '',
                        'debit': move_line.debit,
                        'credit': move_line.credit,
                        'balance': (move_line.credit or 0.0) - (move_line.debit or 0.0),
                        'level': 1,
                        'is_account': False,
                        'is_move_line': True,
                    }
                    consolidated_data[account_key]['move_details'][branch.code].append(move_data)

                consolidated_data[account_key]['move_details'][branch.code].sort(
                    key=lambda x: x.get('date', ''), reverse=True
                )

    
    def action_generate_consolidated_district_report(self):
        """Generate consolidated district report for browser display - now supports multiple companies"""
        self.ensure_one()
        
        _logger.info("="*80)
        _logger.info("ACTION: action_generate_consolidated_district_report called")
        _logger.info(f"Report Type: {self.report_type}")
        _logger.info(f"Account Type: {self.account_type}")
        _logger.info(f"Date Range: {self.date_from} to {self.date_to}")
        _logger.info(f"Format: {self.format}")
        _logger.info(f"Selected Companies: {[c.name for c in self.company_ids]}")
        _logger.info(f"Selected Branches: {[b.name for b in self.branch_ids]}")
        _logger.info(f"Wizard ID: {self.id}")
        _logger.info("="*80)
        
        if self.report_type != 'consolidated_district':
            _logger.info("Wrong report type, delegating to action_generate_report()")
            return self.action_generate_report()
        
        companies_to_process = self.company_ids or self.env['res.company'].search([])
        _logger.info(f"Companies to process: {[c.name for c in companies_to_process]}")
        
        if not companies_to_process:
            raise ValidationError("No companies selected or available.")
        
        if self.format == 'html':
            report_url = f'/report/html/eedc_report.consolidated_district_report_template/{self.id}'
            _logger.info(f"Redirecting to custom route: {report_url}")
            
            return {
                'type': 'ir.actions.act_url',
                'url': report_url,
                'target': 'new',
            }
        
        else:
            start_date, end_date, month_headers = self._get_date_range()
            all_company_reports = []
            company_ids_list = []
            
            for company in companies_to_process:
                _logger.info(f"\n{'='*60}")
                _logger.info(f"Processing company: {company.name}")
                _logger.info(f"{'='*60}")
                
                report_lines, district_headers, district_codes, company_id = \
                    self._get_consolidated_district_data(start_date, end_date, month_headers, company)
                
                _logger.info(f"Result for {company.name}: {len(report_lines)} report lines")
                
                if report_lines:
                    budget_type_name = dict(self._fields['account_type'].selection).get(self.account_type, '')
                    period_string = self._get_period_string(start_date, end_date)
                    
                    report_data = {
                        'report_lines': report_lines,
                        'district_headers': district_headers,
                        'district_codes': district_codes,
                        'company_name': company.name,
                        'subtitle': f"{budget_type_name.upper()} - {period_string.upper()}",
                        'account_type': self.account_type,
                        'res_company': company,
                    }
                    all_company_reports.append(report_data)
                    company_ids_list.append(company_id)
                    _logger.info(f"✓ Added report for {company.name}")
                else:
                    _logger.warning(f"✗ No data for {company.name} - SKIPPING")
            
            if not all_company_reports:
                raise ValidationError("No data could be generated for the selected criteria.")
            
            data = {
                'doc_model': self._name,
                'company_reports': all_company_reports,
                'wizard_id': self.id,
                'current_date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else '',
                'current_date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else '',
                'account_types': self._fields['account_type'].selection,
                'current_account_type': self.account_type,
                'current_company_ids': company_ids_list,
                'current_company_ids_json': json.dumps(company_ids_list),
            }
            
            report_action = self.env.ref('eedc_report.action_consolidated_district_report_pdf')
            return report_action.report_action(self, data=data)


    def _generate_report_data(self):
        """Generate fresh report data from current wizard state"""
        self.ensure_one()
        
        companies_to_process = self.company_ids or self.env['res.company'].search([])
        start_date, end_date, month_headers = self._get_date_range()
        
        all_company_reports = []
        
        for company in companies_to_process:
            report_lines, district_headers, district_codes, company_id = \
                self._get_consolidated_district_data(start_date, end_date, month_headers, company)
            
            if report_lines:
                budget_type_name = dict(self._fields['account_type'].selection).get(self.account_type, '')
                period_string = self._get_period_string(start_date, end_date)
                
                all_company_reports.append({
                    'report_lines': report_lines,
                    'district_headers': district_headers,
                    'district_codes': district_codes,
                    'company_name': company.name,
                    'subtitle': f"{budget_type_name.upper()} - {period_string.upper()}",
                    'account_type': self.account_type,
                    'res_company': company,
                })
        
        return all_company_reports

    
    @api.model
    def update_report_params(self, wizard_id, **kwargs):
        """Update report parameters - with enhanced error handling"""
        try:
            wid = int(wizard_id)
        except (ValueError, TypeError) as e:
            _logger.error(f"Invalid wizard id: {wizard_id} - {str(e)}")
            return {'error': 'Invalid wizard id'}

        wizard = self.sudo().browse(wid)
        if not wizard.exists():
            _logger.error(f"Wizard not found: {wid}")
            return {'error': 'Wizard not found'}

        update_vals = {}
        
        # Date validation
        if 'date_from' in kwargs and kwargs.get('date_from'):
            try:
                date_from = kwargs.get('date_from')
                if isinstance(date_from, str):
                    date_from = fields.Date.from_string(date_from)
                update_vals['date_from'] = date_from
            except Exception as e:
                _logger.error(f"Invalid date_from: {kwargs.get('date_from')} - {str(e)}")
                return {'error': f'Invalid date_from format: {str(e)}'}
        
        if 'date_to' in kwargs and kwargs.get('date_to'):
            try:
                date_to = kwargs.get('date_to')
                if isinstance(date_to, str):
                    date_to = fields.Date.from_string(date_to)
                update_vals['date_to'] = date_to
            except Exception as e:
                _logger.error(f"Invalid date_to: {kwargs.get('date_to')} - {str(e)}")
                return {'error': f'Invalid date_to format: {str(e)}'}
        
        if 'account_type' in kwargs and kwargs.get('account_type'):
            account_type = kwargs.get('account_type')
            # Validate account_type against selection field
            valid_types = [t[0] for t in self._fields['account_type'].selection]
            if account_type in valid_types:
                update_vals['account_type'] = account_type
            else:
                _logger.error(f"Invalid account_type: {account_type}")
                return {'error': f'Invalid account_type: {account_type}'}
        
        if 'company_ids' in kwargs:
            company_ids = kwargs.get('company_ids')
            if company_ids is None:
                company_ids = []
            
            # Validate company IDs exist
            if company_ids:
                valid_companies = self.env['res.company'].sudo().browse(company_ids).exists()
                if len(valid_companies) != len(company_ids):
                    _logger.warning(f"Some company IDs don't exist: {company_ids}")
            
            update_vals['company_ids'] = [(6, 0, company_ids)]

        if update_vals:
            try:
                wizard.sudo().write(update_vals)
                _logger.info(f"Successfully updated wizard {wid} with: {update_vals}")
            except Exception as e:
                _logger.error(f"Failed to update wizard {wid}: {str(e)}", exc_info=True)
                return {'error': f'Failed to update parameters: {str(e)}'}
        
        return {'success': True, 'updated_fields': list(update_vals.keys())}
    
        
    def _get_period_string(self, start_date, end_date):
        """Helper to generate period string for report subtitle"""
        if start_date.year == end_date.year and start_date.month == end_date.month:
            return f"MONTHLY RETURNS {start_date.strftime('%B %Y')}"
        else:
            return f"CONSOLIDATED RETURNS {start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}"
    
    
    def get_account_and_journal_budget(self, account_id, fiscal_year=False):
        domain = [('account_id', '=', account_id.id)]
        if not fiscal_year:
            fiscal_year = fields.Date.today() 
        else:
            fiscal_year = fiscal_year
        domain += [('budget_allocation_date', '>=', fiscal_year), ('allocation_date', '<=', fiscal_year)]
        related_budgets = self.env['ng.account.budget.line'].search(domain)
        utilized_budget, budget_amount, variance = 0, 0, 0
        for rec in related_budgets:
            utilized_budget += rec.utilized_amount
            budget_amount += rec.allocated_amount
            variance += rec.budget_balance
        return budget_amount, abs(utilized_budget), abs(variance)
     
    
    # def action_export_as_excel(self, data):
    #     data = data.get('data')
    #     if data:
    #         headers = [
    #             'S/N', 
    #             'Economic Code', 
    #             'Details/Narration', 
    #             'Actual (NGN)', 
    #             f"Budget {data[0].get('account_obj').get('fiscal_year')}", 
    #             'Utilization(NGN)', 
    #             'Variance (NGN)', 
    #             'Remark'
    #             ]
    #         style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
    #                 num_format_str='#,##0.00')
    #         wb = xlwt.Workbook()
    #         ws = wb.add_sheet(self.name, cell_overwrite_ok=True)
    #         colh = 0
    #         ws.write(0, 6, 'RECORDS GENERATED: %s - On %s' %(self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d')), style0)
    #         for head in headers:
    #             ws.write(1, colh, head)
    #             colh += 1
    #         rowh = 2
    #         for dt in data:
    #             dynamic_column = 0
    #             ws.write(rowh, dynamic_column, '')
    #             ws.write(rowh, dynamic_column + 1, dt.get('account_obj').get('account_name'))
    #             ws.write(rowh, dynamic_column + 2, "-")
    #             ws.write(rowh, dynamic_column + 3,  '{0:,}'.format(float(dt.get('account_obj').get('actual_amount'))))
    #             ws.write(rowh, dynamic_column + 4, '{0:,}'.format(float(dt.get('account_obj').get('budget_amount'))))
    #             ws.write(rowh, dynamic_column + 5, '{0:,}'.format(float(dt.get('account_obj').get('budget_utilized'))))
    #             ws.write(rowh, dynamic_column + 6, '{0:,}'.format(float(dt.get('account_obj').get('budget_balance'))))
    #             ws.write(rowh, dynamic_column + 7, '-')
    #             account_move_line = dt.get('account_obj').get('account_move_line')
                
    #             rowh += 1
    #             # dynamic_column += 1
    #             for count, ml in enumerate(account_move_line, 1):
    #                 ws.write(rowh, dynamic_column, count)
    #                 ws.write(rowh, dynamic_column + 1, '')
    #                 ws.write(rowh, dynamic_column + 2, ml.get('move_description'))
    #                 ws.write(rowh, dynamic_column + 3,  '{0:,}'.format(float(ml.get('move_balance') or 0)))
    #                 ws.write(rowh, dynamic_column + 4, '{0:,}'.format(float(ml.get('account_and_journal_budget') or 0)))
    #                 ws.write(rowh, dynamic_column + 5, '{0:,}'.format(float(ml.get('account_and_journal_budget_utilization') or 0)))
    #                 ws.write(rowh, dynamic_column + 6, '{0:,}'.format(float(ml.get('account_and_journal_budget_variance') or 0)))
    #                 ws.write(rowh, dynamic_column + 7, '-')
    #                 rowh += 1
    #         rowh += 1 # added extra row to give space for each account lines
    #         fp = io.BytesIO()
    #         wb.save(fp)
            
    #         # buffered = io.BytesIO()
    #         # img.save(buffered, format="PNG")
    #         # img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
    #         filename = "{} ON {}.xls".format(
    #             self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d'), style0)
    #         # self.excel_file = base64.encodestring(fp.getvalue())
    #         self.excel_file = base64.b64encode(fp.getvalue())
            
    #         # attachementObj = self.attachment_render(self.name, base64.encodestring(fp.getvalue()), 'application/vnd.ms-excel')
    #         # self.send_mail([attachementObj])
    #         self.filename = filename
    #         attachment = self.attachment_render(self.name, base64.b64encode(fp.getvalue()), 'application/vnd.ms-excel')
    #         fp.close()
    #         _logger.info(f"THISSS IS LINK {'/web/content/%s/%s?download=true' % (attachment.id, attachment.name)}"),
    #         return {
    #             'type': 'ir.actions.act_url',
    #             'name': 'REPORT',
    #             'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
    #         }
    #         # return { 
    #         #         'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
    #         #         'type': 'ir.actions.act_url',
    #         #         'url': '/web/content/?model=account.dynamic.report&download=true&field=excel_file&id={}&filename={}'.format(self.id, self.filename),
    #         #         'target': 'new',
    #         #         'nodestroy': True,
    #         # }
    #     else:
    #         raise ValidationError('No data found to generate excel report')
    def _get_monthly_report_data(self, start_date, end_date, month_headers, branch):
        """ Prepares data for a monthly report. """
        # start_date, end_date, month_headers = self._get_date_range()

        report_map = {
            'Overhead': '_get_hierarchical_report_data',
            'Personnel': '_get_hierarchical_report_data',
            'Expenditure': '_get_hierarchical_report_data',
            'Revenue': '_get_hierarchical_report_data',
            'Capital': '_get_capital_report_data',
        }
        method_name = report_map.get(self.account_head_type, '_get_hierarchical_report_data')
        # if not method_name:
        #     raise ValidationError(f"Report not implemented for budget type: {self.account_head_type}")

        report_data_method = getattr(self, method_name)
        report_data = report_data_method(start_date, end_date, month_headers, branch, is_quarterly=False)

        return report_data

    def _get_quarterly_report_data(self, start_date, end_date, month_headers, branch):
        report_map = {
            'Capital': '_get_capital_report_data',
            'Personnel': '_get_capital_report_data',
            'Expenditure': '_get_capital_report_data',
            }
        method_name = report_map.get(self.account_head_type, '_get_hierarchical_report_data')
        report_data_method = getattr(self, method_name)
        return report_data_method(start_date, end_date, month_headers, branch, is_quarterly=True)
    
    def action_export_as_excel(self):
        self.ensure_one()
        if not xlwt:
            raise ValidationError("The 'xlwt' Python library is not installed. Please install it with 'pip install xlwt'.")

        branches_to_process = self.branch_ids or self.env.user.branch_id
        if not branches_to_process:
            raise ValidationError("No district selected or configured for the current user.")

        start_date, end_date, month_headers = self._get_date_range()
        is_quarterly = 'quarterly' in self.report_type
        report_data_method = self._get_quarterly_report_data if is_quarterly else self._get_monthly_report_data
        
        all_branch_reports = []
        for branch in branches_to_process:
            report_lines = report_data_method(start_date, end_date, month_headers, branch)
            if report_lines:
                all_branch_reports.append({
                    'title': f'HEAD: {branch.code} - {branch.name}',
                    'report_lines': report_lines,
                })
        
        if not all_branch_reports:
            raise ValidationError("No data could be generated for the selected criteria.")
        
        workbook = xlwt.Workbook(encoding='utf-8')
        
        title_style = xlwt.easyxf('font: bold on, height 280; align: horiz left')
        subtitle_style = xlwt.easyxf('font: bold on, height 240; align: horiz left')
        header_style = xlwt.easyxf('font: bold on; align: horiz center; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25;')
        normal_style = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin;')
        bold_style = xlwt.easyxf('font: bold on; borders: left thin, right thin, top thin, bottom thin;')
        currency_style = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin;', num_format_str='#,##0.00')
        currency_bold_style = xlwt.easyxf('font: bold on; borders: left thin, right thin, top thin, bottom thin;', num_format_str='#,##0.00')
        percent_style = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin;', num_format_str='0.00%')
        percent_bold_style = xlwt.easyxf('font: bold on; borders: left thin, right thin, top thin, bottom thin;', num_format_str='0.00%')

        for report in all_branch_reports:
            sheet_name = report['title'].split('-')[0].strip()[:31] # Max 31 chars for sheet name
            sheet = workbook.add_sheet(sheet_name, cell_overwrite_ok=True)
            
            budget_type_name = dict(self._fields['account_type'].selection).get(self.account_type, '')
            q_map = {'first': 'Q1', 'second': 'Q2', 'third': 'Q3', 'fourth': 'Q4'}
            q_name = next((v for k, v in q_map.items() if k in self.report_type), "QX")
            report_name_text = dict(self._fields['report_type'].selection).get(self.report_type, '')
            month_dates = sorted(list({start_date, end_date})) 
            month_str_list = [d.strftime('%B %Y') for d in month_dates]
            period_string = f"""{report_name_text} ({q_name}) {end_date.year}" if is_quarterly else f"MONTHLY RETURNS {" - ".join(month_str_list)}"""
            subtitle = f"{budget_type_name.upper()} - {period_string.upper()}"
            
            sheet.write_merge(0, 0, 0, 8, report['title'], title_style)
            sheet.write_merge(1, 1, 0, 8, subtitle, subtitle_style)
            
            headers = []
            is_capital = self.account_type == 'Capital'
            is_revenue = self.account_type == 'Revenue'

            headers.append(('CODE' if is_revenue or not is_capital else 'DESCRIPTION', 3000))
            headers.append(('ECONOMIC' if is_revenue or not is_capital else 'CODE', 10000 if not is_capital else 3000))
            headers.append(('APPROVED BUDGET', 5000))

            if not is_quarterly:
                total_header = "TOTAL ACTUAL REVENUE TO DATE" if is_revenue else "TOTAL ACTUAL EXP. TO DATE"
                month_header = f"REVENUE FOR THE MONTH OF {month_headers[0]}" if is_revenue else f"EXP. FOR THE MONTH OF {month_headers[0]}"
                headers.extend([('PREVIOUS ACTUAL', 5000), (month_header, 6000), (total_header, 6000)])
            else:
                for month in month_headers:
                    headers.append((month, 4000))
                quarterly_total_header = f"{month_headers[0]}-{month_headers[-1]} {end_date.year}"
                headers.extend([(quarterly_total_header, 5000), ('% PERF TO DATE', 3000)])
            
            headers.append(('BALANCE', 5000))

            for col_num, (header_text, width) in enumerate(headers):
                sheet.write(3, col_num, header_text, header_style)
                sheet.col(col_num).width = width

            row_num = 4
            for line in report['report_lines']:
                style = bold_style if line.get('is_acc') == 'yes' else normal_style
                curr_style = currency_bold_style if line.get('is_acc') == 'yes' else currency_style
                perc_style = percent_bold_style if line.get('is_acc') == 'yes' else percent_style
                
                indent = '    ' * line.get('level', 0) if not is_capital else ''
                
                col_num = 0
                sheet.write(row_num, col_num, line.get('code', ''), style); col_num += 1
                sheet.write(row_num, col_num, indent + line.get('name', line.get('description', '')), style); col_num += 1
                sheet.write(row_num, col_num, line.get('approved_budget', 0.0), curr_style); col_num += 1
                
                if not is_quarterly:
                    sheet.write(row_num, col_num, line.get('previous_actual', 0.0), curr_style); col_num += 1
                    for month in month_headers:
                        sheet.write(row_num, col_num, line.get('monthly_values', {}).get(month, 0.0), curr_style); col_num += 1
                    sheet.write(row_num, col_num, line.get('total_exp_to_date', 0.0), curr_style); col_num += 1
                else:
                    for month in month_headers:
                        sheet.write(row_num, col_num, line.get('monthly_values', {}).get(month, 0.0), curr_style); col_num += 1
                    sheet.write(row_num, col_num, line.get('quarterly_total', 0.0), curr_style); col_num += 1
                    sheet.write(row_num, col_num, line.get('percentage_perf', 0.0) / 100, perc_style); col_num += 1
                    
                sheet.write(row_num, col_num, line.get('balance', 0.0), curr_style); col_num += 1
                row_num += 1

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        
        report_name = f"{self.account_type}_{self.report_type}_{fields.Date.today()}.xls"
        self.filename = report_name
        self.excel_file = base64.encodebytes(fp.read())
        fp.close()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=excel_file&filename={self.filename}&download=true',
            'target': 'self',
        }
    
    def action_export_as_xml(self):
        self.ensure_one()
        
        branches_to_process = self.branch_ids or self.env.user.branch_id
        if not branches_to_process:
            raise ValidationError("No district selected or configured for the current user.")

        start_date, end_date, month_headers = self._get_date_range()
        is_quarterly = 'quarterly' in self.report_type
        report_data_method = self._get_quarterly_report_data if is_quarterly else self._get_monthly_report_data
        
        all_branch_reports = []
        for branch in branches_to_process:
            report_lines = report_data_method(start_date, end_date, month_headers, branch)
            if report_lines:
                all_branch_reports.append({
                    'title': f'HEAD: {branch.code} - {branch.name}',
                    'district_code': branch.code,
                    'report_lines': report_lines,
                })
        
        if not all_branch_reports:
            raise ValidationError("No data could be generated for any of the selected criteria.")

        root = ET.Element('FinancialReport', attrib={
            'generated_on': fields.Date.today().isoformat(),
            'report_type': self.report_type,
            'account_type': self.account_type,
        })

        for report_data in all_branch_reports:
            report_element = ET.SubElement(root, 'Report', attrib={
                'district_name': report_data['title'].split(' - ')[-1],
                'district_code': report_data.get('district_code', '')
            })
            
            lines_element = ET.SubElement(report_element, 'ReportLines')
            
            def build_xml_hierarchy(lines, parent_node):
                level_parents = {-1: parent_node}
                for line in lines:
                    level = line.get('level', 0)
                    parent = level_parents[level - 1]
                    
                    line_node = ET.SubElement(parent, 'Line', attrib={'is_account': line.get('is_acc', 'no')})
                    
                    ET.SubElement(line_node, 'Code').text = str(line.get('code', ''))
                    ET.SubElement(line_node, 'Description').text = line.get('name', line.get('description', ''))
                    ET.SubElement(line_node, 'ApprovedBudget').text = str(line.get('approved_budget', 0.0))
                    
                    if not is_quarterly:
                        ET.SubElement(line_node, 'PreviousActual').text = str(line.get('previous_actual', 0.0))
                        ET.SubElement(line_node, 'TotalToDate').text = str(line.get('total_exp_to_date', 0.0))
                    else:
                        ET.SubElement(line_node, 'QuarterlyTotal').text = str(line.get('quarterly_total', 0.0))
                        ET.SubElement(line_node, 'PerformancePercentage').text = str(line.get('percentage_perf', 0.0))
                        
                    ET.SubElement(line_node, 'Balance').text = str(line.get('balance', 0.0))
                    
                    monthly_node = ET.SubElement(line_node, 'MonthlyValues')
                    for month in month_headers:
                        ET.SubElement(monthly_node, month).text = str(line.get('monthly_values', {}).get(month, 0.0))
                        
                    level_parents[level] = line_node

            build_xml_hierarchy(report_data['report_lines'], lines_element)

        xml_string = ET.tostring(root, 'utf-8')
        pretty_xml_string = minidom.parseString(xml_string).toprettyxml(indent="  ")

        fp = io.BytesIO(pretty_xml_string.encode('utf-8'))
        
        report_name = f"{self.account_type}_{self.report_type}_{fields.Date.today()}.xml"
        self.xml_filename = report_name
        self.xml_file = base64.encodebytes(fp.read())
        fp.close()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=xml_file&filename={self.xml_filename}&download=true',
            'target': 'self',
        }
    
    def attachment_render(self, attachment_name, report_binary, mimetype):
        attachmentObj = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': report_binary,
            'store_fname': attachment_name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': mimetype
        })
        return attachmentObj