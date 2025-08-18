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
    