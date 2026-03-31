# -*- coding: utf-8 -*-
{
    'name': 'Finance Portal',
    'version': '16.0.1.0.0',
    'summary': 'Expense & Payment Portal — Supplier/Customer Payments, Dashboard',
    'category': 'Accounting',
    'depends': ['account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
