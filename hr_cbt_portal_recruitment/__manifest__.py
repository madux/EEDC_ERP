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
        'eedc_addons',
        'hr_recruitment_sign',
    ],

    'data': [
        'views/menu_inheritance.xml',
        'views/hr_job_views.xml',
        'views/hr_applicant_view.xml',
        'views/career.xml',
        'static/src/xml/website_hr_recruitment_templates.xml',
        'static/src/xml/hr_documentation_request.xml',
        'views/hr_employee.xml',
        'views/hr_recruitment_request.xml',
        'views/hr_recruitment_stage_inherit.xml',
        'views/hr_documentation_view.xml',
        # 'views/company_memo_inherit.xml',
        'wizard/cbt_schedule_wizard_view.xml',
        'wizard/survey_invite_inherit.xml',
        'wizard/hr_move_applicant.xml',
        'wizard/applicant_checklist_wizard.xml',
        'wizard/import_applicant_view.xml',
        'wizard/hr_recruitment_sign_view.xml',
        'wizard/score_sheet_export.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/preloader.xml',
        'data/documentation_data.xml'

    ],
    'assets': {
        'web.assets_frontend': [
        '/hr_cbt_portal_recruitment/static/src/js/recruitment_apply_form.js',
        '/hr_cbt_portal_recruitment/static/src/js/documentation_request.js',
    ]},
    'qweb': [
        # 'static/src/xml/custom_template.xml',
        # 'static/src/xml/website_hr_recruitment_templates.xml'
    ]
}
