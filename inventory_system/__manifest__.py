# -*- coding: utf-8 -*-
{
    "name": "Inventory System",
    "version": "16.0.1.0.0",
    "author": "Michael Ndunwa",
    # "category": "",
    "summary": "An Inventory System",
    "depends": ["base", "web", "website"],
    "description": "This module is an inventory system module.",
    "icon": "inventory_system/static/description/icon.png",
    "data": [
        "static/templates/inventory_form.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "inventory_system/static/src/css/inventory_form.css",
            "inventory_system/static/src/js/inventory_form.js",
        ],
    },
    "license": "LGPL-3",
}