{
    'name': 'Payroll Contract Addons',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['hr_contract_salary','hr_payroll','company_memo'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        'views/hr_payroll.xml',
        'views/hr_employee.xml',
        'views/hr_contract_wizard.xml',
        
    ],
}
