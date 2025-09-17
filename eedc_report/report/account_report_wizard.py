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
        string='Report Name'
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
        string="Report Type", tracking=True,
        required=False, default="monthly_expenditure"
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
        string="Format", tracking=True,
        required=False, default="pdf"
    )
    
    branch_ids = fields.Many2many('multi.branch', string='District')
    company_id = fields.Many2one('res.company')
    moveline_ids = fields.Many2many('account.move.line', string='Dummy move lines')
    # budget_id = fields.Many2one('ng.account.budget.line', string='Budget')
    fiscal_year = fields.Date(string='Fiscal Year', default=fields.Date.today())
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_head_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"),
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital Expenditure"),
        ("Other", "Others"),
        ], default="Overhead", string="Account Type", 
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
        """
        Pre-populates the wizard with the user's default branches.
        This version is robust against a user not having a default branch_id set.
        """
        res = super().default_get(fields_list)
        user = self.env.user
        if 'branch_ids' in fields_list:
            branch_ids = user.branch_ids.ids
            if user.branch_id:
                branch_ids.append(user.branch_id.id)
            unique_branch_ids = list(set(branch_ids))
            res.update({'branch_ids': [(6, 0, unique_branch_ids)]})
        if 'company_id' in fields_list and user.company_id:
            res.update({'company_id': [(6, 0, user.company_id)]})
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

    def _build_base_domain(self, date_from, date_to, branch_id):
        """Builds a dynamic search domain based on wizard selections."""
        domain = [
            # ('move_id.branch_id', 'in', self.branch_ids.ids),
            ('move_id.branch_id', '=', branch_id),
            ('date', '>=', date_from), ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
        ]
        if self.company_id: domain.append(('move_id.company_id', '=', self.company_id.id))
        if self.journal_ids: domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.account_ids: domain.append(('account_id', 'in', self.account_ids.ids))
        if self.partner_id: domain.append(('partner_id', '=', self.partner_id.id))
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
        
        start_date, end_date, month_headers = self._get_date_range()
        
        is_quarterly = True if 'quarterly' in self.report_type else False
        
        all_branch_reports = []
        for branch in branches_to_process:
            report_lines = self._get_hierarchical_report_data(start_date, end_date, month_headers, branch, is_quarterly=is_quarterly)
            if report_lines:
                all_branch_reports.append({
                    'title': f'HEAD: {branch.code} - {branch.name}',
                    'report_lines': report_lines,
                })
        
        if not all_branch_reports:
            raise ValidationError("No data could be generated for the selected criteria.")
        
        budget_type_name = dict(self._fields['account_head_type'].selection).get(self.account_head_type, '')
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
    
    
    def _get_hierarchical_report_data(self, start_date, end_date, month_headers, branch, is_quarterly=False):
        year_start = end_date.replace(day=1, month=1)
        domain_end_date = end_date
        
        tags = self.env['economic.tag'].search([('account_head_type', '=', self.account_head_type)])
        all_accounts = tags.mapped('account_ids')
        if not all_accounts: return []

        base_domain = self._build_base_domain(year_start, domain_end_date, branch.id)
        base_domain.append(('account_id', 'in', all_accounts.ids))
        all_moves = self.env['account.move.line'].search(base_domain)

        # budget_domain = [('budget_type', '=', self.account_head_type), ('account_id', 'in', all_accounts.ids), ('branch_id', '=', branch.id)]
        # all_budget_lines = self.env['ng.account.budget.line'].search(budget_domain)
        
        sum_field = 'credit' if self.account_head_type == 'Revenue' else 'debit'

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
    
    def _get_consolidated_district_data(self, start_date, end_date, month_headers):
        """
        Generates consolidated data across all selected districts for the same period.
        Returns data in format: {tag/account: {district_code: amount, ...}}
        """
        branches_to_process = self.branch_ids or self.env['multi.branch'].search([])
        if not branches_to_process:
            raise ValidationError("No districts selected or configured for the current user.")
        
        # Get all relevant tags based on account_head_type
        tags = self.env['economic.tag'].search([('account_head_type', '=', self.account_head_type)])
        all_accounts = tags.mapped('account_ids')
        if not all_accounts:
            return [], []

        consolidated_data = {}
        district_headers = []
        
        # Build data for each district
        for branch in branches_to_process:
            district_headers.append(branch.code.upper())
            
            # Get base domain for this branch
            base_domain = self._build_base_domain(start_date, end_date, branch.id)
            base_domain.append(('account_id', 'in', all_accounts.ids))
            
            branch_moves = self.env['account.move.line'].search(base_domain)
            
            # Determine field to sum (debit vs credit)
            sum_field = 'credit' if self.account_head_type == 'Revenue' else 'debit'
            
            # Process by tags (economic codes)
            for tag in tags:
                tag_key = f"{tag.code}_{tag.name}"
                if tag_key not in consolidated_data:
                    consolidated_data[tag_key] = {
                        'code': tag.code,
                        'description': tag.name,
                        'level': 0,
                        'is_account': False,
                        'is_expandable': True,
                        'district_values': {},
                        'account_details': {},
                        'total_revenue': 0.0,
                        'total_expenditure': 0.0,
                    }
                
                # Get moves for this tag's accounts
                tag_moves = branch_moves.filtered(lambda m: m.account_id in tag.account_ids)
                
                # Calculate totals
                revenue_total = sum(tag_moves.mapped('credit'))
                expenditure_total = sum(tag_moves.mapped('debit'))
                
                # Store district values based on account_head_type
                if self.account_head_type == 'Revenue':
                    consolidated_data[tag_key]['district_values'][branch.code] = revenue_total
                    consolidated_data[tag_key]['total_revenue'] += revenue_total
                else:
                    consolidated_data[tag_key]['district_values'][branch.code] = expenditure_total
                    consolidated_data[tag_key]['total_expenditure'] += expenditure_total
                
                # Store account-level details for expansion (THIS IS THE KEY CHANGE)
                if branch.code not in consolidated_data[tag_key]['account_details']:
                    consolidated_data[tag_key]['account_details'][branch.code] = []
                
                for account in tag.account_ids:
                    account_moves = tag_moves.filtered(lambda m: m.account_id == account)
                    if account_moves:
                        account_revenue = sum(account_moves.mapped('credit'))
                        account_expenditure = sum(account_moves.mapped('debit'))
                        
                        # Only add accounts that have transactions
                        if account_revenue > 0 or account_expenditure > 0:
                            consolidated_data[tag_key]['account_details'][branch.code].append({
                                'code': account.code,
                                'name': account.name,
                                'revenue': account_revenue,
                                'expenditure': account_expenditure,
                                'level': 1,
                                'is_account': True,
                            })

        # Convert to list and calculate balances
        report_lines = []
        for key, data in consolidated_data.items():
            data['balance'] = data['total_revenue'] - data['total_expenditure']
            # Only include tags that have some activity
            if data['total_revenue'] > 0 or data['total_expenditure'] > 0:
                report_lines.append(data)
        
        # Sort by code
        report_lines.sort(key=lambda x: x.get('code', ''))
        
        return report_lines, district_headers
    
    def action_generate_consolidated_district_report(self):
        """Generate consolidated district report for browser display"""
        self.ensure_one()
        
        if self.report_type != 'consolidated_district':
            return self.action_generate_report()  # Fall back to existing logic
        
        start_date, end_date, month_headers = self._get_date_range()
        
        # Get consolidated data
        report_lines, district_headers = self._get_consolidated_district_data(start_date, end_date, month_headers)
        
        if not report_lines:
            raise ValidationError("No data could be generated for the selected criteria.")
        
        # Prepare data for template
        budget_type_name = dict(self._fields['account_head_type'].selection).get(self.account_head_type, '')
        period_string = self._get_period_string(start_date, end_date)
        
        # Get company name (will be extended to support multiple companies)
        company_name = self.company_id.name if self.company_id else self.env.company.name
        
        data = {
            'doc_model': self._name,
            'data': [{  # Wrap in data array like your existing reports
                'report_lines': report_lines,
                'district_headers': district_headers,
                'company_name': company_name,
                'subtitle': f"{budget_type_name.upper()} - {period_string.upper()}",
                'account_head_type': self.account_head_type,
            }],
            'start_date': start_date,
            'end_date': end_date,
        }
        
        # Use the existing report action pattern
        report_action = self.env.ref('eedc_report.action_consolidated_district_report')
        return report_action.report_action(self, data=data)
        
    def _get_period_string(self, start_date, end_date):
        """Helper to generate period string for report subtitle"""
        if start_date.year == end_date.year and start_date.month == end_date.month:
            return f"MONTHLY RETURNS {start_date.strftime('%B %Y')}"
        else:
            return f"CONSOLIDATED RETURNS {start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')}"

    

    def _get_capital_report_data(self, start_date, end_date, month_headers, branch, is_quarterly=False):
        
        domain = self._build_base_domain(start_date, end_date, branch)
        # domain.extend([
        #     ('ng_budget_line_id.budget_type', '=', self.account_head_type),
        #     ('display_type', '=', 'product'), 
        #     ('debit', '>', 0)
        #     ])
        
        all_invoice_lines = self.env['account.move.line'].search(domain)

        if not all_invoice_lines:
            _logger.warning(f"No invoice lines found for selected branches '{branch.name}'.")
            return []

        districts_data = []
        for line in all_invoice_lines:
            budget_line = line.ng_budget_line_id
            # approved_budget = budget_line.allocated_amount if budget_line else 0.0
            approved_budget = 0.0
            
            total_utilized = 0.0
            if budget_line:
                all_budget_moves = self.env['account.move.line'].search([
                    ('ng_budget_line_id', '=', budget_line.id),
                    ('move_id.state', '=', 'posted'),
                ])
                total_utilized = sum(all_budget_moves.mapped('debit'))

            monthly_values = {month: 0.0 for month in month_headers}
            if start_date <= line.date <= end_date:
                month_key = line.date.strftime('%b').upper()
                if month_key in monthly_values:
                    monthly_values[month_key] = line.debit

            line_data = {
                'description': line.name, 
                'code': line.account_id.code,
                'economic_code_and_desc': f'{line.account_id.code} - {line.account_id.name}',
                'approved_budget': approved_budget,
                'monthly_values': monthly_values
            }

            if is_quarterly:
                line_data.update({
                    'quarterly_total': total_utilized,
                    'balance': approved_budget - total_utilized,
                    'percentage_perf': (total_utilized / approved_budget) * 100 if approved_budget else 0.0,
                })
            else:
                previous_actual = total_utilized - line.debit
                line_data.update({
                    'previous_actual': previous_actual,
                    'total_exp_to_date': total_utilized,
                    'balance': approved_budget - total_utilized,
                })
            
            if start_date <= line.date <= end_date:
                capital_data.append(line_data)
            
        return sorted(capital_data, key=lambda x: x.get('code', ''))
    
    
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
            
            budget_type_name = dict(self._fields['account_head_type'].selection).get(self.account_head_type, '')
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
            is_capital = self.account_head_type == 'Capital'
            is_revenue = self.account_head_type == 'Revenue'

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
        
        report_name = f"{self.account_head_type}_{self.report_type}_{fields.Date.today()}.xls"
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
            'account_head_type': self.account_head_type,
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
        
        report_name = f"{self.account_head_type}_{self.report_type}_{fields.Date.today()}.xml"
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