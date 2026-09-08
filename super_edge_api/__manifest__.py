{
    'name': 'SuperEdge Revenue API',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['account', 'ik_multi_branch'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        # 'views/account_payment.xml',
        # 'views/account_move.xml',
        'views/superedge_api.xml',
        'data/superedge_config.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'super_edge_api/static/css/style.css'
        ],
    },
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
