{
    'name': 'Relatives Disclosure Form',
    'version': '16.0.1',
    'author': "Michael Ndunwa",
    'category': 'Human Resources',
    'summary': 'Relatives Disclosure Form for HR',
    'depends': ['base', 'hr', 'hr_recruitment', 'company_memo'],
    'license': 'LGPL-3',
    'description': "This module provides a form for employees to disclose relatives working in the company.",
    'icon': '/relatives_disclosure_form/static/description/icon.png',
    "data": [
        'views/relatives_disclosure_menu.xml',
        'views/relatives_disclosure_form_view.xml',
        'views/website_relatives_disclosure_form.xml'
    ],
    "assets": {
        'web.assets_frontend': [
            'relatives_disclosure_form/static/src/css/relatives_disclosure_form.css',
        ]
    },
    'application': True,
    'installable': True,
}