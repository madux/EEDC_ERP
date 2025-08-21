# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class InventoryFormController(http.Controller):

    @http.route(['/inventory-form'], type='http', auth="public", website=True)
    def inventory_form(self, **kwargs):
        # Dummy context (can be expanded later)
        context = {
            "dummy_customer": "Acme Ltd.",
            "dummy_operations": ["Delivery", "Internal transfer", "Receipt"],
        }
        return request.render("inventory_system.inventory_form_page", context)