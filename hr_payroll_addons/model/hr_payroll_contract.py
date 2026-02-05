from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)

class HREmployee(models.Model):
    _inherit = "hr.employee"
    
    monthly_wage = fields.Float(string="Monthly Wage")
    annual_salary = fields.Float(string="Annual Salary")
    
    def create_employee_contract_action(self):
        rec_ids = self.env.context.get('active_ids', [])
        return {
              'name': 'Employee Contract',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.contract.wizard',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_employee_ids': rec_ids,
              },
        }
    
    
class HRContractWizard(models.Model):
    _name = "hr.contract.wizard"
    
    contract_start_date = fields.Date(string="Start date")
    contract_end_date = fields.Date(string="End date")
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Structure Type")
    monthly_wage = fields.Float(string="Monthly Wage")
    update_existing_contract = fields.Boolean(string="Update existing Contract")
    
    def auto_create_employee_contract(self):
        '''if monthly wage is selected, use the fixed monthly wage of use existing eployee monthly wage configured'''
        employees = self.employee_ids #.filtered(lambda mw: mw.monthly_wage > 0)
        if self.contract_start_date:
            for emp in employees:
                monthly_wage = self.monthly_wage if self.monthly_wage > 0 else emp.monthly_wage
                vals = {
                        'name': f"Contract for {emp.name}",
                        'employee_id': emp.id,
                        'date_start': self.contract_start_date,
                        'date_end': self.contract_end_date,
                        'structure_type_id': self.structure_type_id and self.structure_type_id.id or self.env.ref('hr_contract.structure_type_employee').id,
                        'department_id': emp.department_id.id,
                        'hr_responsible_id': self.env.uid,
                        'work_entry_source': 'calendar',
                        'wage_type': 'monthly',
                        'job_id': emp.job_id.id,
                        'wage': monthly_wage,
                        'monthly_yearly_costs': monthly_wage,
                        'final_yearly_costs': self.contract_end_date * 12,
                        'state': 'open',
                    }
                if not emp.contract_id:
                    contract_id = self.env['hr.contract'].create(vals)
                    emp.contract_id = contract_id.id
                else:
                    if self.update_existing_contract:
                        update_vals = {
                        'date_start': self.contract_start_date,
                        'date_end': self.contract_end_date,
                        'structure_type_id': self.structure_type_id and self.structure_type_id.id or self.env.ref('hr_contract.structure_type_employee').id,
                        'department_id': emp.department_id.id,
                        'hr_responsible_id': self.env.uid,
                        'wage_type': 'monthly',
                        'job_id': emp.job_id.id,
                        'wage': monthly_wage,
                        'monthly_yearly_costs': monthly_wage,
                        'final_yearly_costs': self.contract_end_date * 12,
                        'state': 'open',
                    }
                    emp.contract_id.write(update_vals)
        else:
            raise ValidationError(
                '''
                Please provide contract start date
                '''
            )

            
class HrContract(models.Model):
    _inherit = "hr.contract" 
    
    structure_id = fields.Many2one(
        'hr.payroll.structure', 
        required=False,
        store=True,
        string='Salary Structure 1')
    
    employee_number = fields.Char(string="Staff ID", store=True,)# related="employee_id.employee_number")
    rsa_number = fields.Char(string="RSA Number")
    prorata = fields.Char(string="Prorata")
    pension = fields.Char(string="PFA")
    sort_code = fields.Char(string="Sort code")
    bank = fields.Char(string="Bank")
    bank_account = fields.Char(string="Bank Account")
    hmo = fields.Char(string="HMO")
    nhf_loan = fields.Float(string="NHF LOAN")
    overpay = fields.Float(string="Overpay")
    salary_advance = fields.Float(string="Salary Advance")
    
    x_PRORATA = fields.Float(string='PRORATA', default=30)
    # x_type = fields.Float(string='Is Contract Dont use', default=False)
    x_type = fields.Boolean(string='Contract', default=False)
    x_ARREARS = fields.Float(string='SURCHARGE', default=0) 
    x_shiftall = fields.Float(string='Shift Allowance', default=0)
    x_cashiersall = fields.Float(string='Cashiers Allowance', default=0)
    x_uniondue = fields.Float(string='NUEE', help="Union Due", default=0)
    x_overpay = fields.Float(string='Overpay', default=0)
    x_saladv = fields.Float(string='SALARY ADV', default=0)
    x_thrift3 = fields.Float(string='Cooperative', default=0)
    x_HMO1 = fields.Float(string='HMP Pre Family', default=0)
    x_HMO2 = fields.Float(string='HMP Pre Single', default=0)
    x_HMO3 = fields.Float(string='HMO Std Family', default=0)
    x_HMO4 = fields.Float(string='HMO Std Single', default=0)
    x_volpfa = fields.Float(string='VOL Pension', default=0)
    x_nhf_loan = fields.Float(string='NHF Loan', default=0)
    x_ssadue = fields.Float(string='SSAEAC', default=0)
    x_cashadv = fields.Float(string='CHQ Cash advance', default=0)
    x_cashadv2 = fields.Float(string='DIST CASH ADV', default=0)
    x_houseloan = fields.Float(string='HOUSE LOAN DED', default=0)
    x_dev = fields.Float(string='Development Levy', default=0)
    x_bank = fields.Char(string='Bank')
    x_emp_type = fields.Char(string='Employee type')
    x_accountno = fields.Char(string='Account No')
    
    x_pfa2 = fields.Selection([('False','None'),('STANBIC IBTC PENSION MANAGERS','STANBIC IBTC PENSION MANAGERS'),('OAK PENSIONS LIMITED','OAK PENSIONS LIMITED'),('FUG PENSIONS','FUG PENSIONS'),('CRUSADER STERLING PENSIONS','CRUSADER STERLING PENSIONS'),('GUARANTY TRUST PENSION MANAGERS LIMITED','GUARANTY TRUST PENSION MANAGERS LIMITED'),('FIDELITY','FIDELITY') ,('IGI PENSION FUND MANAGERS LTD','IGI PENSION FUND MANAGERS LTD'),('PAL PENSIONS','PAL PENSIONS'),('AXA MANSARD PENSIONS','AXA MANSARD PENSIONS'),('LEADWAY PENSION','LEADWAY PENSION'),('SIGMA PENSIONS LIMITED','SIGMA PENSIONS LIMITED'),('ARM PENSION MANAGERS','ARM PENSION MANAGERS') ,('AIICO','AIICO'),('FIRST GUARANTEE PENSION LIMITED','FIRST GUARANTEE PENSION LIMITED'),(' TANGERINE APT PENSIONS','TANGERINE APT PENSIONS'),('NLPC PFA LTD','NLPC PFA LTD'),('TRUST FUND PENSIONS PLC','TRUST FUND PENSIONS PLC'),('NORRENBERGER PENSIONS','NORRENBERGER PENSIONS') ,('FCMB PENSIONS','FCMB PENSIONS'),('NPF PENSIONS LIMITED','N.P.F. PENSIONS LIMITED'),('PREMIUM PENSION LIMITED','PREMIUM PENSION LIMITED'),('ACCESS PENSIONS LIMITED','ACCESS PENSIONS LIMITED')], 
                                 string='PFA')
    x_banksortcode1 = fields.Char(string='Bank Sort code')
    x_banksortcode2 = fields.Char(string='Bank Sort Code 2', help="sort code 2")
    x_banksortcode = fields.Char(string='Bank Sort code 3')
    x_RSA_PIN = fields.Char(string='RSA PIN')
    x_district1 = fields.Char(string='District', default=0)
    x_district = fields.Char(string='District', default=0)  
    
    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            self.employee_number = self.employee_id.employee_number
            self.department_id = self.employee_id.department_id.id
            self.job_id = self.employee_id.job_id.id
            
    def action_run_contract(self):
        active_contract_ids = self.env['hr.contract'].search([('employee_id.active', '=', True)])
        for ct in active_contract_ids:
            ct.state = 'open'

    @api.model
    def create(self, vals_list):
        """Override create to support import validation and employee mapping."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        records = self.env[self._name]

        for vals in vals_list:
            staff_no = vals.get('employee_number')
            employee_id = vals.get('employee_id')
            _logger.info(f"vassss {vals} coooooooooo {vals_list}")

            # 🔹 Only run mapping if employee_number provided and no employee_id yet
            if staff_no:# and not employee_id:
                employee = self.env['hr.employee'].sudo().search([
                    ('employee_number', '=', staff_no)
                ], limit=1)

                if employee:
                    vals['employee_id'] = employee.id
                else:
                    # optional: auto-create employee
                    # employee = self.env['hr.employee'].sudo().create({
                    #     'name': vals.get('name') or f"Employee {staff_no}",
                    #     'employee_number': staff_no,
                    # })
                    # vals['employee_id'] = employee.id
                    pass 

            # 🔹 Avoid invalid search with False employee_id
            if vals.get('employee_id'):
                existing_contract = self.env['hr.contract'].sudo().search([
                    '|',('employee_id', '=', vals['employee_id']),
                    ('employee_id.employee_number', '=', vals.get('employee_number')),
                ], limit=1)
            else:
                existing_contract = False

            if existing_contract:
                # Update existing contract instead of creating
                existing_contract.sudo().write(vals)
                records |= existing_contract
            else:
                record = super(HrContract, self).create(vals)
                records |= record

        return records

    
    
class HRSalaryRule(models.Model):
    _inherit = "hr.salary.rule" 
    
    struct_id = fields.Many2one(
        'hr.payroll.structure', 
        required=True,
        string='Structure')
    
class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure" 
    
    clear_rule = fields.Boolean(
        required=False,
        default=False,
        string='Clear rule')
    
    auto_rule_id = fields.Many2one(
        'hr.salary.rule', 
        required=False,
        string='Auto Rule')
    
    structure_duplicate_ids = fields.Many2many(
        'hr.payroll.structure', 
        'hr_duplicate_structure_rels',
        'struct_id',
        'duplicate_struct_id',
        required=False,
        string='Structures')
    
    rule_duplicate_ids = fields.Many2many(
        'hr.salary.rule', 
        'hr_duplicate_salaray_rule_rels',
        'struct_id',
        'rule_id',
        required=False,
        string='Rules to Add')
    
    rule_ids = fields.Many2many(
        'hr.salary.rule', 
        'hr_salary_rule_rels',
        'struct_id',
        'rule_id',
        required=False,
        string='Rule')
    
    def action_add_missing_rule(self):
        if not self.rule_ids or not self.rule_duplicate_ids:
            raise ValidationError("Please select structure and rules to add to the structure")
        get_structure_ids = self.structure_duplicate_ids
        # if self.structure_duplicate_ids else self.env['hr.payroll.structure'].search([])
        for strucs in get_structure_ids:
            if self.clear_rule:
                strucs.rule_ids = False 
            strucs.rule_ids = [(4, r.id) for r in self.rule_duplicate_ids]
        self.structure_duplicate_ids = False
        self.rule_duplicate_ids = False
        
    def action_auto_generate_rule_structure(self):
        if not self.auto_rule_id:
            raise ValidationError("Please select the auto rule id")
        if self.auto_rule_id:
            structures = self.env['hr.payroll.structure'].search([])
            for str in structures:
                if str.mapped('rule_ids').filtered(
                    lambda sr: sr.id == self.auto_rule_id.id
                ):
                    self.structure_duplicate_ids = [(4, str.id)]
    
    # def action_duplicate_rule(self):
    #     # if not self.structure_duplicate_ids:
    #     #     raise ValidationError("Please select Structures to duplicate rules")
    #     get_structure_ids = self.structure_duplicate_ids if self.structure_duplicate_ids else self.env['hr.payroll.structure'].search([('id', '!=', self.id)])
    #     for strucs in get_structure_ids:
    #         if self.clear_rule:
    #             strucs.rule_ids = [(3, sr.id) for sr in strucs.rule_ids]
    #         for rule in self.rule_ids:
    #             new_rule = rule.copy()
    #             strucs.rule_ids = [(4, new_rule.id)]
    #     self.structure_duplicate_ids = False
        
    @api.model
    def create(self, vals):
        if vals['name']:
            rules = []
            name = vals['name'].strip()
            existing = self.env['hr.payroll.structure'].search([('name', '=', name)], limit=1)
            if existing:
                xml_rule = vals.get('rule_ids')
                rule_id = xml_rule[0][2][0] # [(<Command.SET: 6>, 0, [19487])]
                rules.append(rule_id)
                record = existing
            else:
                record = super(HrPayrollStructure, self).create(vals)
        _logger.info(f'Data generated for update {record.id} - {record.name}')
        for r in rules:
            record.write({"rule_ids": [(4, r)]})
        return record 