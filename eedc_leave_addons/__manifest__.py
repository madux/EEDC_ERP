{
    'name': 'LEAVE ADDONS Apps',
    'version': '16.0.1',
    'author': "Maduka Sopulu/Paul Ugwu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base','hr_holidays'],#, 'hr_payroll_addons'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [

        'views/hr_leave_allocation.xml',
        'security/ir.model.access.csv'
    ],
}
