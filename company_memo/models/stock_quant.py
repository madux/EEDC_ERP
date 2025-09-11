from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_is_zero, float_compare
    
    
class StockPicking(models.Model):
    _inherit = "stock.quant"
    _order = "id desc"
    
    def _get_branch_company_inventory_loss_location(self):
        user_branch, company_id = self.env.user.branch_id, self.company_id
        location = self.env['stock.location'].search([
            # ('branch_id', '=', user_branch.id),
            ('company_id', '=', company_id.id),
            ('usage', '=', 'inventory')
            ], limit=1)
        return location if location else False
        

    def _apply_inventory(self):
        move_vals = []
        if not self.user_has_groups('stock.group_stock_manager'):
            raise UserError(_('Only a stock manager or approver can validate an inventory adjustment.'))
        for quant in self:
            # checks the property_stock_inventory to ensure products is of type inventory loss 
            if quant.product_id.property_stock_inventory.usage != 'inventory':
                if not self._get_branch_company_inventory_loss_location():
                    raise ValidationError(f"{quant.product_id.name} does not have location with inventory loss type set on the property_stock_inventory")
                else:
                    quant.product_id.sudo().property_stock_inventory = self._get_branch_company_inventory_loss_location().id
            # Create and validate a move so that the quant matches its `inventory_quantity`.
            if float_compare(quant.inventory_diff_quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0:
                move_vals.append(
                    quant._get_inventory_move_values(quant.inventory_diff_quantity,
                                                     quant.product_id.with_company(quant.company_id).property_stock_inventory,
                                                     quant.location_id))
            else:
                move_vals.append(
                    quant._get_inventory_move_values(-quant.inventory_diff_quantity,
                                                     quant.location_id,
                                                     quant.product_id.with_company(quant.company_id).property_stock_inventory,
                                                     out=True))
        moves = self.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
        moves._action_done()
        self.location_id.write({'last_inventory_date': fields.Date.today()})
        date_by_location = {loc: loc._get_next_inventory_date() for loc in self.mapped('location_id')}
        for quant in self:
            quant.inventory_date = date_by_location[quant.location_id]
        self.write({'inventory_quantity': 0, 'user_id': False})
        self.write({'inventory_diff_quantity': 0})