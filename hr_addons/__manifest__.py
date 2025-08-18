{
    'name': 'HR Queries / Warnings Apps',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base', 'hr'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        'views/hr_employee_inherit.xml',
        'views/model_views.xml',
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
