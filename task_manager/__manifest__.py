{
    "name": "Task Manager",
    "summary": "A task management system module to boost productivity in the office and keep everyone accountable.",
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
        "views/website_admin_dashboard.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "task_manager/static/templates/task_manager_board_templates.xml",
            # JS + CSS
            "task_manager/static/src/js/tm_portal_board.js",
            "task_manager/static/src/scss/task_manager_board.scss",


            "task_manager/static/lib/chartjs/chart.umd.js",
            "task_manager/static/lib/chartjs/chartjs-adapter-date-fns.bundle.js",
            "task_manager/static/src/js/admin/tm_admin_api.js",
            "task_manager/static/src/js/admin/tm_admin_charts.js",
            "task_manager/static/src/js/admin/tm_admin_front.js",
            "task_manager/static/src/scss/tm_admin_dashboard.scss",

        ],
    },
    "application": True,
    "installable": True,
}