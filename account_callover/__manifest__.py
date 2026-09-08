{
    'name': 'Account Callover',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'MAACH SOFTWARE',
    'summary': 'Monthly callover (pivot) report of Journal Item debit amounts by Account and Branch',
    'description': """
Account Callover
=================
Adds a SQL-based reporting model (account.callover) that pivots
account.move.line debit values (where memo_id is set) into monthly
columns (Jan..Dec) plus a Total, grouped by account_id and branch_id
(from the related move's branch_id, multi.branch).

Because the underlying model is a PostgreSQL SQL VIEW, the figures are
always computed live/dynamically whenever the list is opened or
refreshed - there is no stored/cached data to get out of sync.
""",
    'depends': ['account', 'ik_multi_branch'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_callover_views.xml',
        # 'views/res_users_bulk_import_views.xml',
        'views/res_users.xml',
        # 'security/account_callover_security.xml',
        'report/report_account_callover_pdf.xml',
        'report/report_account_callover_actions.xml'
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'account_callover/static/src/js/account_callover_list_view.js',
    #         'account_callover/static/src/xml/account_callover_list_view.xml',
    #         'account_callover/static/src/scss/account_callover.scss',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
    'application': False,
}
