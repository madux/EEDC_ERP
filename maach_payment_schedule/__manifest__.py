# -*- coding: utf-8 -*-
{
    'name': "Maach Payment Schedule",

    'summary': """
        Maach Payment Schedule""",

    'description': """
        This module helps users schedule payment
    """,

    'author': "Maduka Sopulu.",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/payment_schedule.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
}
