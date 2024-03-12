{
    'name': 'Plateau Addons',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base', 'account', 'account_accountant', 'currency_rate_live'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        'views/view_import_chart_data.xml', 
    ],
}
