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
        'views/menu_inheritance.xml',
        'views/hr_job_views.xml',
        'views/hr_applicant_view.xml',
        'views/career.xml',
        'static/src/xml/website_hr_recruitment_templates.xml',
        'views/hr_employee.xml',
        'wizard/cbt_schedule_wizard_view.xml',
        'wizard/survey_invite_inherit.xml',
        'wizard/hr_move_applicant.xml',
        'wizard/import_applicant_view.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/preloader.xml',
    ],
    'assets': {
        'web.assets_frontend': [
        '/hr_cbt_portal_recruitment/static/src/js/recruitment_apply_form.js',
    ]},
    'qweb': [
        # 'static/src/xml/custom_template.xml',
        # 'static/src/xml/website_hr_recruitment_templates.xml'
    ]
}
