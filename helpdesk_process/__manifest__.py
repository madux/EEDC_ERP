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
        'security/helpdesk_groups.xml',
        'views/memo_view_helpdesk.xml',
        'views/memo_view_helpdesk_kaban.xml',
        'data/memo_type.xml',
        'data/memo_config.xml',
        'static/templates/memo_helpdesk_template.xml',
        'static/templates/memo_helpdesk_customer_status.xml',
        'security/ir_rule.xml',
    ],
    "assets": {
        'web.assets_frontend': [
            '/helpdesk_process/static/src/js/memo_helpdesk_ticket.js',
            '/helpdesk_process/static/src/js/memo_helpdesk_status.js',
            'helpdesk_process/static/src/css/customerInfo.css'
        ],
        "web.assets_backend": [
            "helpdesk_process/static/src/components/helpdesk_memo_dashboard.js",
            "helpdesk_process/static/src/components/helpdesk_memo_kanban_controller.js",
            # "helpdesk_process/static/src/css/customerInfo.css"
        ],
        "web.assets_qweb": [
            # "helpdesk_process/views/helpdesk_memo_kanban_view.xml",
            "helpdesk_process/views/helpdesk_memo_model_dashboard_view.xml",
            "helpdesk_process/static/src/components/helpdesk_memo_kanban_view.xml",
            "helpdesk_process/views/helpdesk_memo_kanban_view.xml"
        ],
    },
}
