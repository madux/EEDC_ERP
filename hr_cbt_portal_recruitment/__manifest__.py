# -*- coding: utf-8 -*-
{
    'name': "HR CBT Recruitment ",

    'summary': """
        Extend the default hr recruitment module from Odoo with EEDC specific requirements""",

    'description': """
        Extend the default hr recruitment module from Odoo with EEDC specific requirements
    """,

    'author': "EEDC Ltd.",
    'license': 'LGPL-3',
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [
        'base',
        'hr_recruitment',
        'hr_recruitment_survey',
        'website_hr_recruitment',
    ],

    'data': [
        # 'views/hr_job_views.xml',
        'views/hr_applicant_view.xml',
        'wizard/cbt_schedule_wizard_view.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        # 'views/preloader.xml',
        # 'views/templates.xml',
    ],
}
