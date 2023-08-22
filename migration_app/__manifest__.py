##############################################################################
#    Copyright (C) 2021 MAACH SOFTWARE. All Rights Reserved
#    BItlect Extensions to Sms module


{
    'name': 'EEDC Migration Module',
    'version': '14.0.0',
    'author': "Maach media",
    'category': 'HR',
    'summary': '',
    'description': "",
    'depends': ['base'],
    "data": [
        'security/ir.model.access.csv',
        'wizard/import_employee_view.xml',
        
    ],
    "sequence": 3,
    'installable': True,
    'application': True,
}
