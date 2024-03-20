{
    'name': 'Plateau Addons',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base', 'account', 'account_accountant', 'currency_rate_live', 'company_memo', 'ik_multi_branch'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/view_import_chart_data.xml', 
        'views/company_memo_view.xml', 
        'views/account_view.xml', 
    ],
}
