# -*- coding: utf-8 -*-
{
    'name': 'Office Memo Application',
    'version': '14.0',
    'author': 'Maach Services',
    'description': """An Odoo Memo application use to send memo / information accross individuals: 
    It can also be used to send requests.""",
    'summary': 'Memo application for Companies etc ',
    'category': 'Base',
    # 'live_test_url': "https://www.youtube.com/watch?v=KEjxieAoGeA&feature=youtu.be",

    'depends': ['base', 'account', 'purchase', 'stock', 'mail', 'hr', 'contacts', 'hr_holidays', 'hr_recruitment', 'documents'], #, 'account_payment_invoice_online_payment_patch'],
    'data': [
        'security/security_group.xml', 
        'sequence/sequence.xml',
        'views/company_memo_view.xml',
        'views/res_users.xml',
        'views/memo_forward_view.xml',
        'views/memo_config_view.xml',
        'views/account_account_view.xml',
        'views/account_move.xml',
        'views/document_view.xml',
        'views/document_kanban_view.xml',
        'wizard/return_memo_wizard_view.xml',
        'reports/report_memo.xml',
        'views/assets.xml',
        'security/ir.model.access.csv',
        'data/memo_stage.xml',
        'data/memo_type.xml',
        'data/ir_cron.xml' 
    ],
    'assets': {'web.assets_backend': [
        '/company_memo/static/src/js/error_message.js',
        # '/company_memo/static/src/js/hide_function.js',
    ]},
    # 'qweb': [
    #     'static/src/xml/base.xml',
    # ],
    'price': 135.00,
    'sequence': 1,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
}
