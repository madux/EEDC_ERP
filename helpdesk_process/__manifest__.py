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
        'views/memo_view_helpdesk_kaban.xml',
        # 'views/helpdesk_memo_dashboard.xml',
        'data/memo_type.xml',
        'data/memo_config.xml',
        'static/templates/memo_helpdesk_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
        '/helpdesk_process/static/src/js/memo_helpdesk_ticket.js',
    ]},
}
