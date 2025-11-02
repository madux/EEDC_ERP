##############################################################################
#    Copyright (C) 2021 MAACH SOFTWARE. All Rights Reserved
#    BItlect Extensions to Sms module


{
    'name': 'EEDC Migration Module',
    'version': '14.0.0',
    'author': "Sopulu/Paul",
    'category': 'HR',
    'summary': '',
    'description': "",
    'depends': ['base', 'hr', 'stock', 'ik_multi_branch', 'multi_company', 'eedc_addons'],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/import_employee_view.xml',
        'wizard/import_product_wizard.xml',
        'wizard/import_data.xml',
        
    ],
    "sequence": 3,
    'installable': True,
    'application': True,
}
