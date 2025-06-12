{
    "name": "Relatives Disclosure Form",
    "version": "16.0.1",
    "author": "Michael Ndunwa",
    "category": "Human Resources",
    "summary": "Relatives Disclosure Form for HR",
    "depends": ["base", "hr", "eedc_addons", "website"],
    "license": "LGPL-3",
    "description": "This module provides a form for employees to disclose relatives working in the company.",
    "icon": "relatives_disclosure_form/static/description/icon.png",
    "data": [
        "security/ir.model.access.csv",
        "views/relatives_disclosure_form_view.xml",
        "views/relatives_disclosure_kanban_view.xml",
        "views/relatives_disclosure_menu.xml",
        # "static/templates/relatives_disclosure_form_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/relatives_disclosure_form/static/src/js/relatives_disclosure_form.js",
            "relatives_disclosure_form/static/src/css/relatives_disclosure_form.css",
        ]
    },
    "application": True,
    "installable": True,
}
