{
    'name': 'Memo Helpdesk',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Memo helpdesk',
    'depends': ['base', 'hr', 'company_memo',],#, 'hr_payroll_addons'],
    'description': "ODOO Memo helpdesk: helps to management processes involved in helpesk",
    "data": [
        'security/ir.model.access.csv',
        'views/memo_view_helpdesk.xml',
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
