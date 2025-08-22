{
    'name': 'Memo RFQ Upload',
    'version': '16.0.1',
    'author': "Maduka Sopulu / Paul Ugwu",
    'category': 'ERP',
    'summary': 'Odoo Module to upload RFQ',
    'depends': [
        'base', 'purchase', 'stock', 'company_memo'],
    'description': "ODOO Base Extension to customize base modules ",
    'external_dependencies': {
        'python': ['pandas', 'openpyxl']
    },
    "data": [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/memo_view.xml',
        'wizard/rfq_upload_wizard.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'rfq_upload/static/src/js/rfq_actions.js',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
}
