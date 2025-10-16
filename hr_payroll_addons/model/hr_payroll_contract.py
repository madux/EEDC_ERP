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
    
    employee_number = fields.Char(string="Staff ID")
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
    
    x_PRORATA = fields.Float(string='Prorata', default=30)
    x_type = fields.Float(string='Type', default=0)
    x_ARREARS = fields.Float(string='Arrears', default=0) 
    x_shiftall = fields.Float(string='Shiftall', default=0)
    x_cashiersall = fields.Float(string='All Cashiers', default=0)
    x_uniondue = fields.Float(string='Union Due', default=0)
    x_overpay = fields.Float(string='Overpay', default=0)
    x_saladv = fields.Float(string='Salary Advance', default=0)
    x_thrift3 = fields.Float(string='Thrift', default=0)
    x_HMO1 = fields.Float(string='HMO 1', default=0)
    x_HMO2 = fields.Float(string='HMO 2', default=0)
    x_HMO3 = fields.Float(string='HMO 3', default=0)
    x_HMO4 = fields.Float(string='HMO 4', default=0)
    x_volpfa = fields.Float(string='VOLPFA', default=0)
    x_nhf_loan = fields.Float(string='NHF Loan', default=0)
    x_ssadue = fields.Float(string='SSA DUE', default=0)
    x_cashadv = fields.Float(string='Cash advance 1', default=0)
    x_cashadv2 = fields.Float(string='Cash advance 2', default=0)
    x_houseloan = fields.Float(string='House loan', default=0)
    x_dev = fields.Float(string='House loan', default=0)
    

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
            
        
                    
    