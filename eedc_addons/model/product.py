from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class productProduct(models.Model):
    _inherit = "product.product"
    
    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, compute_child
        '''
        Warehouse = self.env['stock.warehouse']
        Location = self.env['stock.location']

        def _search_ids(model, values):
            ids = set()
            domain = []
            for item in values:
                if isinstance(item, int):
                    ids.add(item)
                else:
                    domain = expression.OR([[(self.env[model]._rec_name, 'ilike', item)], domain])
            if domain:
                ids |= set(self.env[model].search(domain).ids)
            return ids

        # We may receive a location or warehouse from the context, either by explicit
        # python code or by the use of dummy fields in the search view.
        # Normalize them into a list.
        location = self.env.context.get('location')
        if location and not isinstance(location, list):
            location = [location]
        warehouse = self.env.context.get('warehouse')
        branch_location_ids = Location.search([('branch_id', '=', self.env.user.branch_id.id), ('usage', '=', 'internal')])
        if warehouse and not isinstance(warehouse, list):
            warehouse = [warehouse]
            
        # filter by location and/or warehouse
        if warehouse:
            w_ids = set(Warehouse.browse(_search_ids('stock.warehouse', warehouse)).mapped('view_location_id').ids)
            winternal_ids = set(Warehouse.browse(_search_ids('stock.warehouse', warehouse)).mapped('lot_stock_id').ids)
            
            if location:
                l_ids = _search_ids('stock.location', location)
                location_ids = w_ids & l_ids & winternal_ids
            else:
                location_ids = w_ids | winternal_ids
        else:
            if location:
                location_ids = _search_ids('stock.location', location)
            else:
                location_ids = set(Warehouse.search([]).mapped('view_location_id').ids)
                internal_location_ids = set(Warehouse.search([]).mapped('lot_stock_id').ids)
                location_ids = location_ids | internal_location_ids
                
        ## Added current branch locations to also be displayed on the qty_available for product
        if branch_location_ids:
            location_ids = location_ids | set(branch_location_ids.ids)
        return self._get_domain_locations_new(location_ids)
    
    