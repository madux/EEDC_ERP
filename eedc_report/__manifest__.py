{
    'name': 'EEDC Report',
    'version': '17.0',
    'author': "Maduka Sopulu/ Paul Ugwu",
    'description': "EEDC Report module",
    'category': 'ERP',
    'summary': 'Module for report',
    'depends': [
        'base', 'account', 'ik_multi_branch', 'account_reports'],
    "data": [
        'security/ir.model.access.csv',
        'report/report_dynamic_account_template.xml',
        'report/account_report_wizard_view.xml', 
        'report/account_report_template.xml',
        'views/account_views.xml',
        # 'data/general_ledger_report_enhanced.xml',
        # 'views/general_ledger_templates.xml',
        'wizard/account_import.xml',
        'data/economic_tag.xml',
    ],
}
