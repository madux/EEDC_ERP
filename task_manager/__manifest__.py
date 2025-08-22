# -*- coding: utf-8 -*-
{
    "name": "Task Manager",
    "summary": "Website task board for employees (Staff-ID login) + simple back-office",
    "version": "16.0.1.0.0",
    "author": "Michael Ndunwa",
    "license": "LGPL-3",
    "website": "",
    "category": "Productivity",
    "depends": ["base", "web", "website", "hr"],
    "icon": "task_manager/static/description/icon.png",
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/backend_views.xml",
        "views/website_pages.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # QWeb templates (you prefer /static/templates/ so we include that path)
            "task_manager/static/templates/task_manager_board_templates.xml",
            # JS + CSS
            "task_manager/static/src/js/task_manager_login.js",
            "task_manager/static/src/js/task_manager_board.js",
            "task_manager/static/src/scss/task_manager_board.scss",
        ],
    },
    "application": True,
}