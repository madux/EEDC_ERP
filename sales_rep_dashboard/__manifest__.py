# -*- coding: utf-8 -*-
{
    "name": "Sales Rep Dashboard",
    "summary": "Beautiful KPI + charts dashboard for each salesperson",
    "version": "16.0.1.0.0",
    "category": "Sales",
    "author": "You",
    "license": "LGPL-3",
    "depends": ["base", "web", "sale", "website"],
    "data": [
        "views/dashboard_menu.xml",
        "views/dashboard_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "sales_rep_dashboard/static/lib/chartjs/chart.umd.js",
            "sales_rep_dashboard/static/lib/chartjs/chartjs-adapter-date-fns.bundle.js",
            "sales_rep_dashboard/static/src/scss/dashboard.scss",
            "sales_rep_dashboard/static/src/js/dashboard.js",
        ],
    },
    "installable": True,
    "application": False,
}
