{
    "name": "Task Manager",
    "summary": "Website task board for employees (Staff-ID login) + simple back-office",
    "version": "16.0.1.0.2",
    "author": "Michael Ndunwa",
    "license": "LGPL-3",
    "website": "",
    "category": "Productivity",
    "depends": ["base", "web", "website", "hr", "portal"],
    "icon": "task_manager/static/description/icon.png",
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/cron.xml",
        "views/backend_views.xml",
        "views/website_pages.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "task_manager/static/templates/task_manager_board_templates.xml",
            # JS + CSS
            "task_manager/static/src/js/tm_portal_board.js",
            "task_manager/static/src/scss/task_manager_board.scss",
        ],
    },
    "application": True,
    "installable": True,
}