from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date

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
            
            
class HRContract(models.Model):
    _inherit = "hr.contract" 
    
    employee_number = fields.Char(string="Staff ID", related="employee_id.employee_number")
    rsa_number = fields.Char(string="RSA Number")
    prorata = fields.Char(string="Prorata")
    pension = fields.Char(string="PFA")
    sort_code = fields.Char(string="Sort code")
    bank = fields.Char(string="Bank")
    bank_account = fields.Char(string="Bank Account")
    hmo = fields.Char(string="HMO")
    salary_advance = fields.Float(string="Salary Advance")
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
    x_bank = fields.Char(string='Bank Account')
    x_emp_type = fields.Char(string='Employee type')
    x_accountno = fields.Char(string='Account No')
    
    x_pfa2 = fields.Selection([('STANBIC IBTC PENSION MANAGERS','STANBIC IBTC PENSION MANAGERS'),('OAK PENSIONS LIMITED','OAK PENSIONS LIMITED'),('FUG PENSIONS','FUG PENSIONS'),('CRUSADER STERLING PENSIONS','CRUSADER STERLING PENSIONS'),('GUARANTY TRUST PENSION MANAGERS LIMITED','GUARANTY TRUST PENSION MANAGERS LIMITED'),('FIDELITY','FIDELITY') ,('IGI PENSION FUND MANAGERS LTD','IGI PENSION FUND MANAGERS LTD'),('PAL PENSIONS','PAL PENSIONS'),('AXA MANSARD PENSIONS','AXA MANSARD PENSIONS'),('LEADWAY PENSION','LEADWAY PENSION'),('SIGMA PENSIONS LIMITED','SIGMA PENSIONS LIMITED'),('ARM PENSION MANAGERS','ARM PENSION MANAGERS') ,('AIICO','AIICO'),('FIRST GUARANTEE PENSION LIMITED','FIRST GUARANTEE PENSION LIMITED'),(' TANGERINE APT PENSIONS','TANGERINE APT PENSIONS'),('NLPC PFA LTD','NLPC PFA LTD'),('TRUST FUND PENSIONS PLC','TRUST FUND PENSIONS PLC'),('NORRENBERGER PENSIONS','NORRENBERGER PENSIONS') ,('FCMB PENSIONS','FCMB PENSIONS'),('NPF PENSIONS LIMITED','N.P.F. PENSIONS LIMITED'),('PREMIUM PENSION LIMITED','PREMIUM PENSION LIMITED'),('ACCESS PENSIONS LIMITED','ACCESS PENSIONS LIMITED')], 
                                 string='PFA')
    x_banksortcode1 = fields.Char(string='Bank Sort code')
    x_banksortcode2 = fields.Char(string='Sort Code', help="sort code 2")
    x_banksortcode = fields.Char(string='Sort code')
    x_RSA_PIN = fields.Char(string='RSA PIN')
    x_district1 = fields.Char(string='District', default=0)
    x_district = fields.Char(string='District', default=0)  
    

class HRSalaryRule(models.Model):
    _inherit = "hr.salary.rule" 
    
    struct_id = fields.Many2one(
        'hr.payroll.structure', 
        required=False,
        string='Structure')
    
class HRPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure" 
    
    clear_rule = fields.Boolean(
        required=False,
        default=True,
        string='Clear rule')
    
    structure_duplicate_ids = fields.Many2many(
        'hr.payroll.structure', 
        'hr_duplicate_structure_rels',
        'struct_id',
        'duplicate_struct_id',
        required=False,
        string='Structures')
    
    def action_duplicate_rule(self):
        # if not self.structure_duplicate_ids:
        #     raise ValidationError("Please select Structures to duplicate rules")
        get_structure_ids = self.structure_duplicate_ids if self.structure_duplicate_ids else self.env['hr.payroll.structure'].search([('id', '!=', self.id)])
        for strucs in get_structure_ids:
            if self.clear_rule:
                strucs.rule_ids = [(3, sr.id) for sr in strucs.rule_ids]
            for rule in self.rule_ids:
                new_rule = rule.copy()
                strucs.rule_ids = [(4, new_rule.id)]
        self.structure_duplicate_ids = False
            
        
                    
    