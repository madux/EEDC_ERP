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
        # 'static/src/xml/helpdesk_memo_kanban_view.xml',
        'data/memo_type.xml',
        'data/memo_config.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "helpdesk_process/static/src/components/helpdesk_memo_dashboard.js",
            "helpdesk_process/static/src/components/helpdesk_memo_kanban_controller.js",
        ],
    },
}
