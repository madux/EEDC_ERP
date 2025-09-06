{
    'name': 'Multi Company - EEDC Apps',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': [
        'base', 'hr', 'company_memo', 'maach_payment_schedule',
        'ik_multi_branch', 'hr_pms', 'hr_payroll_addons', 
        'hr_cbt_portal_recruitment','helpdesk_process', 
        'failed_transformer_repair', 'eedc_addons', 'auditlog', 
        'portal_request'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'security/rule.xml',
        'data/res_company_data.xml',
        'data/multi_branch.xml',
        'data/stock_location.xml',
        'views/report_filters.xml',
        
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
