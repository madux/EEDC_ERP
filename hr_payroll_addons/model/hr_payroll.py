from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date
import ast
import re

import logging

import json
_logger = logging.getLogger(__name__)

class HRPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    list_of_available_staff = fields.Text(string="Available staff")
    list_of_available_staff_with_details = fields.Text(string="Available staff details")
    error_details = fields.Text(string="Found Errors")
    reactivate_contract = fields.Boolean(
        string='Reactivate contract', 
        default=True,
        help="if checked, system will reactivate contract if employee is active and contract is false")
     

    def reset_payslip_x_dev_to_zero(self):
        """
        On payslip run:
        - Reset all salary-rule-related fields on each payslip
        - Recompute and accumulate totals from payslip lines
        """
        for run in self:
            for slip in run.slip_ids:
                slip.contract_id.x_dev = 0.00

    def get_staff_not_existing_in_payroll(self):
        """
            System checks list of employee staff ID provided
            system matches to check if the employees are existing, 
            if any does not exist - system flags it
            if any exist and reactivate is set to true, system sets
            the employee to Active and activate his current contract

            If no contract found, system sends signal and flags as warning
            if set to open all employee, it opens all affected employeee records else it displayss only errors
        """
        employeeObj = self.env['hr.employee'].sudo()
        if self.list_of_available_staff:
            '''TEST CASE 1: Passed 
            1. if data provided is list 
            2: if data provided is str
            3. if data provided is nonsense
            '''
            self.error_details = ''
            raw_input = (self.list_of_available_staff or "").strip()
            try:
                # Case 1: Python list format
                if raw_input.startswith('['):
                    parsed = ast.literal_eval(raw_input)
                    if not isinstance(parsed, list):
                        raise ValidationError("Invalid list format.")
                    list_of_available_staff = [str(x) for x in parsed]

                # Case 2: Excel / messy paste (BEST OPTION)
                else:
                    # Extract ONLY numbers (ignores "staff id", spaces, tabs, etc.)
                    list_of_available_staff = [str(x) for x in re.findall(r'\d+', raw_input)]

                if not list_of_available_staff:
                    raise ValidationError("No valid staff IDs found.")

            except Exception as e:
                raise ValidationError(f"Invalid format. Error: {str(e)}")

        else:
            '''TEST CASE 2: passed
            Dont provide any data
            '''
            raise ValidationError("""Please provide staff ids format below""")
           
        employees = list_of_available_staff
        affected_emp_ids = []
        not_existing_employee_error = ['The following errors occurred: ']
        if employees:
            for emp in employees:
                emp_id = employeeObj.search([('employee_number', '=', str(emp)), ('active','in', [True, False])],limit=1)
                if not emp_id:
                    '''TEST CASE 3: passed
                    Dont provide real employee staff number, check error details
                    '''
                    not_existing_employee_error.append(f"Employee with ID {emp} not existing")
                    affected_emp_ids.append(emp)
                    _logger.info(f'bloooom {emp}')
                else:
                    contracts = self.env['hr.contract'].search(
                                    [('employee_id', '=', emp_id.id)],
                                    order='date_start desc',
                                    limit=1
                                ) 
                    if self.reactivate_contract:
                        '''TEST CASE 4: passed 
                            1. deactivate real employee and both contract
                            2. create employee without contract at all, add the staff number to the list
                            '''
                        emp_id.active = True

                        if emp_id.contract_id:
                            emp_id.contract_id.active = True 
                        else:
                            
                            if not contracts:
                                affected_emp_ids.append(emp)
                                not_existing_employee_error.append(f"Employee with ID {emp} {emp_id.name} have no contract")
                                '''TEST CASE 5: passed
                                1. Find employee with contract
                                '''
                            else:
                                '''
                                    Reactivate the contract if employee record is active
                                ''' 
                                contracts.active = True
                    else:
                        '''TEST CASE 6: passed 
                        1. Provide real employee staff number
                        2. Set reactivate contract
                        3. Dont set reactivate contract: this should only show us
                        errors without any reactivation
                        '''
                        if emp_id.active == False:
                            not_existing_employee_error.append(f"Employee with ID {emp} {emp_id.name} was deactivated")
                            affected_emp_ids.append(emp)

                        if not emp_id.contract_id or not contracts:
                            affected_emp_ids.append(emp)
                            not_existing_employee_error.append(f"Employee with ID {emp} {emp_id.name} does not have contract")
                            '''TEST CASE 7: passed
                            1. Find employee with contract
                                '''

        msg_error = ',\n'.join(not_existing_employee_error)
        id_error = ','.join(affected_emp_ids)
        '''TEST CASE 8: pass  
        1. Check to ensure employee data is shown
        2. Check the error details message
        '''
        self.error_details = f'Find Below the affected staff IDS \n {id_error}\n' + msg_error
        return self.open_employee_record(affected_emp_ids)

    def open_employee_record(self, employee_numbers):

        employee_ids = self.env['hr.employee'].sudo().search([('employee_number', 'in', employee_numbers), ('active', 'in', [True, False])])
        for rec in self:
            form_view_ref = self.env.ref('hr.view_employee_form', False)
            tree_view_ref = self.env.ref('hr.view_employee_tree', False)
            return {
                'domain': [('id', 'in', employee_ids.ids)],
                'name': 'Employees',
                'res_model': 'hr.employee',
                'type': 'ir.actions.act_window',
                'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                'target': 'new',
                'context': {
                    'active_test': False   # 🔥 THIS IS THE KEY
                }
            }
    
    def compute_payslip_total(self):
        """
        On payslip run:
        - Reset all salary-rule-related fields on each payslip
        - Recompute and accumulate totals from payslip lines
        """
        for run in self:
            for slip in run.slip_ids:

                # 1️⃣ Collect all target fields from salary rules
                target_fields = set(
                    slip.line_ids
                    .mapped('salary_rule_id.compute_related_field')
                    .filtered(lambda f: f and f.name in slip._fields)
                    .mapped('name')
                )

                # 2️⃣ Reset fields to 0.0
                if target_fields:
                    slip.write({field: 0.0 for field in target_fields})

                # 3️⃣ Accumulate totals
                updates = {}

                for line in slip.line_ids:
                    field = line.salary_rule_id.compute_related_field
                    if not field or field.name not in slip._fields:
                        continue

                    updates[field.name] = updates.get(field.name, 0.0) + line.total

                # 4️⃣ Write totals
                if updates:
                    slip.write(updates)
    
class HRPayslip(models.Model):
    _inherit = "hr.salary.rule"
    
    def get_domain_fields(self):
        hr_payslip_fields = self.env['ir.model.fields'].sudo().search([('model_id.model', '=', 'hr.payslip')])
        return [('id', 'in', hr_payslip_fields.ids if hr_payslip_fields else [])]
    
    compute_related_field = fields.Many2one('ir.model.fields', string='Compute Related fields', 
                                            domain="[('name', 'ilike', 'x_compute')]",
                                            help="to be used to set which fields is related to it for computation")
    
    

class HRPayslip(models.Model):
    _inherit = "hr.payslip"
    
    x_compute_PRORATA = fields.Float(string='PRORATA', default=30, store=True,)
    # x_compute_type = fields.Float(string='Is Contract Dont use', default=False)
    x_compute_type = fields.Boolean(string='Contract', default=False)
    x_compute_ARREARS = fields.Float(string='ARREARS', default=0, store=True, ) 
    x_compute_surcharge = fields.Float(string='SURCHAGE', default=0,store=True,) 
    x_compute_shiftall = fields.Float(string='Shift Allowance', default=0,store=True,)
    x_compute_cashiersall = fields.Float(string='Cashiers Allowance', default=0,store=True,)
    x_compute_uniondue = fields.Float(string='NUEE', help="Union Due", default=0,store=True,)
    x_compute_overpay = fields.Float(string='Overpay', default=0,store=True,)
    x_compute_saladv = fields.Float(string='SALARY ADV', default=0,store=True)
    x_compute_thrift3 = fields.Float(string='Cooperative/ thrift', default=0,store=True)
    x_compute_HMO1 = fields.Float(string='HMP Pre Family', default=0,store=True)
    x_compute_HMO2 = fields.Float(string='HMP Pre Single', default=0,store=True)
    x_compute_HMO3 = fields.Float(string='HMO Std Family', default=0,store=True)
    x_compute_HMO4 = fields.Float(string='HMO Std Single', default=0,store=True)
    x_compute_volpfa = fields.Float(string='VOL Pension', default=0,store=True)
    x_compute_nhf_loan = fields.Float(string='NHF Loan', default=0,store=True)
    x_compute_nhf_fund = fields.Float(string='NHF (FUND)', default=0,store=True)
    x_compute_ssadue = fields.Float(string='SSAEAC', default=0,store=True)
    x_compute_cashadv = fields.Float(string='CHQ Cash advance', default=0,store=True)
    x_compute_cashadv2 = fields.Float(string='DIST CASH ADV', default=0,store=True)
    x_compute_houseloan = fields.Float(string='HOUSE LOAN DED', default=0,store=True)
    x_compute_dev = fields.Float(string='Compute Development Levy', default=0,store=True)
    x_compute_bank = fields.Char(string='Bank', related="contract_id.x_bank")
    x_compute_emp_type = fields.Char(string='Employee type', related="contract_id.x_emp_type")
    x_compute_accountno = fields.Char(string='Account No', related="contract_id.x_accountno")
    
    x_compute_pfa2 = fields.Selection([('False','None'),('STANBIC IBTC PENSION MANAGERS','STANBIC IBTC PENSION MANAGERS'),('OAK PENSIONS LIMITED','OAK PENSIONS LIMITED'),('FUG PENSIONS','FUG PENSIONS'),('CRUSADER STERLING PENSIONS','CRUSADER STERLING PENSIONS'),('GUARANTY TRUST PENSION MANAGERS LIMITED','GUARANTY TRUST PENSION MANAGERS LIMITED'),('FIDELITY','FIDELITY') ,('IGI PENSION FUND MANAGERS LTD','IGI PENSION FUND MANAGERS LTD'),('PAL PENSIONS','PAL PENSIONS'),('AXA MANSARD PENSIONS','AXA MANSARD PENSIONS'),('LEADWAY PENSION','LEADWAY PENSION'),('SIGMA PENSIONS LIMITED','SIGMA PENSIONS LIMITED'),('ARM PENSION MANAGERS','ARM PENSION MANAGERS') ,('AIICO','AIICO'),('FIRST GUARANTEE PENSION LIMITED','FIRST GUARANTEE PENSION LIMITED'),(' TANGERINE APT PENSIONS','TANGERINE APT PENSIONS'),('NLPC PFA LTD','NLPC PFA LTD'),('TRUST FUND PENSIONS PLC','TRUST FUND PENSIONS PLC'),('NORRENBERGER PENSIONS','NORRENBERGER PENSIONS') ,('FCMB PENSIONS','FCMB PENSIONS'),('NPF PENSIONS LIMITED','N.P.F. PENSIONS LIMITED'),('PREMIUM PENSION LIMITED','PREMIUM PENSION LIMITED'),('ACCESS PENSIONS LIMITED','ACCESS PENSIONS LIMITED')], 
                                 string='PFA')
    x_compute_pension_company = fields.Char(string='PENSION Company Amount')
    x_compute_banksortcode1 = fields.Char(string='Bank Sort code', related="contract_id.x_banksortcode1")
    x_compute_banksortcode2 = fields.Char(string='Bank Sort Code 2', help="sort code 2", related="contract_id.x_banksortcode2")
    x_compute_banksortcode = fields.Char(string='Bank Sort code 3', related="contract_id.x_banksortcode")
    x_compute_RSA_PIN = fields.Char(string='RSA PIN', related="contract_id.x_RSA_PIN")
    
    
    x_compute_transport_allowance = fields.Float(
        string='Transport Allowance',
        default=0.0,
        store=True
    )

    x_compute_rent_relief = fields.Float(
        string='Rent Relief',
        default=0.0,
        store=True
    )

    x_compute_hazard = fields.Float(
        string='Hazard',
        default=0.0,
        store=True
    )

    x_compute_meal = fields.Float(
        string='Meal',
        default=0.0,
        store=True
    )

    x_compute_utility = fields.Float(
        string='Utility',
        default=0.0,
        store=True
    )

    x_compute_house_allowance = fields.Float(
        string='House Allowance',
        default=0.0,
        store=True
    )

    x_compute_union_due_local = fields.Float(
        string='Union Due (Local)',
        default=0.0,
        store=True
    )

    x_compute_national_housing_fund = fields.Float(
        string='National Housing Fund',
        default=0.0,
        store=True
    )

    x_compute_pfa_employee_amount = fields.Float(
        string='PFA Employee Amount',
        default=0.0,
        store=True
    )

    x_compute_life_assurance_premium = fields.Float(
        string='Life Assurance Premium',
        default=0.0,
        store=True
    )

    x_compute_total_gross = fields.Float(
        string='Total Gross',
        default=0.0,
        store=True
    )

    x_compute_tax_compute_relief = fields.Float(
        string='Tax Relief',
        default=0.0,
        store=True
    )

    x_compute_tax_compute_income = fields.Float(
        string='Taxable Income',
        default=0.0,
        store=True
    )

    x_compute_tax_compute_paid = fields.Float(
        string='Tax Paid',
        default=0.0,
        store=True
    )

    x_compute_total_net = fields.Float(
        string='Total Net',
        default=0.0,
        store=True
    )

    x_compute_basic = fields.Float(
        string='Basic Salary',
        default=0.0,
        store=True
    )

    x_compute_house_loan = fields.Float(
        string='House Loan',
        default=0.0,
        stsore=True
    )
    
    def compute_payslip_total(self):
        """
        Reset all salary-rule-related fields to 0,
        then recompute and accumulate payslip line totals.
        """
        for rec in self:

            # 1️⃣ Collect all target fields from salary rules
            target_fields = set(
                rec.line_ids
                .mapped('salary_rule_id.compute_related_field')
                .filtered(lambda f: f and f.name in rec._fields)
                .mapped('name')
            )

            # 2️⃣ Reset fields to 0.0
            if target_fields:
                rec.write({field: 0.0 for field in target_fields})

            # 3️⃣ Accumulate totals
            updates = {}

            for line in rec.line_ids:
                line.x_compute_pfa2 = line.contract_id.x_pfa2
                field = line.salary_rule_id.compute_related_field
                if not field or field.name not in rec._fields:
                    continue

                updates[field.name] = updates.get(field.name, 0.0) + line.total

            # 4️⃣ Write computed totals
            if updates:
                rec.write(updates)
                
                
class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    # def _get_available_contracts_domain(self):
    #     return [('contract_ids.state', 'in', ('open', 'close')), ('company_id', '=', self.env.company.id)]
    def _get_available_contracts_domain(self):
        list_companies = [self.env.user.company_id.id] + self.env.user.company_ids.ids
        return [('contract_ids.state', 'in', ('open', 'close')), 
                ('company_id', 'in', list_companies)]
        
    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        #Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        
        '''REMOVED THE CODES OF WORK ENTRY BELOW BECAUSE
        IT IS NOT APPLICATION WITH EEDC '''
        # contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        # work_entries = self.env['hr.work.entry'].search([
        #     ('date_start', '<=', payslip_run.date_end),
        #     ('date_stop', '>=', payslip_run.date_start),
        #     ('employee_id', 'in', employees.ids),
        # ])
        
        # self._check_undefined_slots(work_entries, payslip_run)

        # if(self.structure_id.type_id.default_struct_id == self.structure_id):
        #     work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
        #     if work_entries._check_if_error():
        #         work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

        #         for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
        #             work_entries_by_contract[work_entry.contract_id] |= work_entry

        #         for contract, work_entries in work_entries_by_contract.items():
        #             conflicts = work_entries._to_intervals()
        #             time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
        #         return {
        #             'type': 'ir.actions.client',
        #             'tag': 'display_notification',
        #             'params': {
        #                 'title': _('Some work entries could not be validated.'),
        #                 'message': _('Time intervals to look for:%s', time_intervals_str),
        #                 'sticky': False,
        #             }
        #         }


        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return success_result

    