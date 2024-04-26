{
    'name': 'Maach Memo Dashboard',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base customizable dashboard for office memo',
    'depends': ['base', 'website', 'company_memo', 'portal', 'website_payment'],
    'description': "ODOO Base Extension to customize modules for portal users",
    "data": [
        # 'security/ir.model.access.csv',
        'static/templates/dashboard.xml',
        'security/ir.model.access.csv'
    ],
    # 'qweb': [
    #     'static/xml/partials.xml',
    # ],
    'assets': {
        'web.assets_frontend': [
        '/maach_dashboard/static/src/js/dashboard.js',
        '/maach_dashboard/static/src/js/soft-ui-dashobard.js',
        '/maach_dashboard/static/src/js/soft-ui-dashobard.js.map',
        '/maach_dashboard/static/src/js/soft-ui-dashobard.min.js',
        # '/maach_dashboard/static/src/js/core/bootstrap.min.js',
        '/maach_dashboard/static/src/js/plugins/perfect-scrollbar.min.js',
        '/maach_dashboard/static/src/js/plugins/smooth-scrollbar.min.js',
        '/maach_dashboard/static/src/js/plugins/chartjs.min.js',
        '/maach_dashboard/static/src/css/dashboard.css',
        '/maach_dashboard/views/dashboard_menu.xml',
        ],
        # 'web.assets_backend': [
        #         'maach_dashboard/static/src/components/**/*',
        # ], 
    },
}
