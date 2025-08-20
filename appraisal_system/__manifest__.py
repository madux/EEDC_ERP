{
    "name": "Appraisal System",
    "version": "16.0.1",
    "author": "Michael Ndunwa",
    "category": "Human Resources",
    "summary": "Appraisal System for HR",
    "depends": ["base", "hr", "eedc_addons", "website", "company_memo"],
    "license": "LGPL-3",
    "description": "This module provides an appraisal system for employees working in the company.",
    # "icon": "appraisal/static/description/icon.png",
    "data": [
        # "security/ir.model.access.csv",
        # "views/website_menu.xml"
        "static/template/appraisal_system_template.xml",
        "static/template/appraisals_list_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "appraisal_system/static/src/js/appraisal_system.js",
            "appraisal_system/static/src/css/appraisal_system.css",
            "appraisal_system/static/src/css/appraisals_list.css",
            "appraisal_system/static/src/js/appraisals_data.js",
            "appraisal_system/static/src/js/appraisals_list.js",
        ]
    },
    "application": True,
    "installable": True,
}