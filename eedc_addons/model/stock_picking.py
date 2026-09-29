from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class StockPicking(models.Model):
    _inherit = "stock.location"
    _order = "id desc"
    
    wh_code = fields.Char(string="code", size=10)

    
    @api.constrains('wh_code')
    def _check_wh_code(self):
        for record in self:
            whl = self.env['stock.location'].search([
                ('wh_code', '=', self.wh_code)
                ], limit=2)
            if whl and len([r.id for r in whl]) > 1: 
                raise UserError(f"{record.wh_code} is already exiting the system, kindly change")

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        default=lambda self: self._default_warehouse(),
    )

    @api.constrains('company_id')
    def _check_company_id(self):
        if self.company_id.id != self.branch_id.company_id.id:
            raise ValidationError("Company and branch company are not the same")

    # @api.constrains('warehouse_id')
    # def _check_warehouse_id(self):
    #     if self.warehouse_id.company_id.id != self.branch_id.company_id.id:
    #         raise ValidationError(f"Warehouse company {self.warehouse_id.company_id.id} and branch company {self.branch_id.company_id.id} are not the same")

    @api.model
    def _default_warehouse(self):
        return self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        # self.warehouse_id = warehouse.id
        self.company_id = warehouse.company_id.id

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.company_id = self.warehouse_id.company_id.id

class StockPicking(models.Model):
    _inherit = "stock.picking"
    _check_company_auto = False
    
    
    override_stock_lot = fields.Boolean("Dis-Allow Lot/Serial", default=True)
    store_note_reason = fields.Text(
        string='Reason',
        default ="This is basically to identify the store trnsfer processes"
    )
    
    # removed this implemenation since each product might come from 
    # different source location
    # @api.onchange('location_id', 'location_dest_id')
    @api.onchange('location_dest_id')
    def _onchange_locations(self):
        # moves = self.move_ids_without_package | self.move_ids
        for rec in self.move_ids_without_package:
            rec.sudo().write({
            # "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id
            })
            
    def action_print_store_receive_note(self):
        self.ensure_one()

        return self.env.ref(
            'eedc_addons.report_store_receive_note'
        ).report_action(self)

    def action_print_store_issue_note(self):
        self.ensure_one()

        return self.env.ref(
            'eedc_addons.report_store_issue_note'
        ).report_action(self)
    
    def reset_to_draft(self):
        for rec in self:
            if rec.state in ['cancel']:
                rec.state = 'draft'
                
    def _sanity_check(self, separate_pickings=True):
        """ Sanity check for `button_validate()`
            :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        pickings_without_moves = self.filtered(lambda p: not p.move_ids and not p.move_line_ids)
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        no_quantities_done_ids = set()
        no_reserved_quantities_ids = set()
        for picking in self:
            if all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel'))):
                no_quantities_done_ids.add(picking.id)
            if all(float_is_zero(move_line.reserved_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in picking.move_line_ids):
                no_reserved_quantities_ids.add(picking.id)
        pickings_without_quantities = self.filtered(lambda p: p.id in no_quantities_done_ids and p.id in no_reserved_quantities_ids)

        pickings_using_lots = self.filtered(lambda p: p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots)
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(no_quantities_done_ids, separate_pickings)
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                if not self.override_stock_lot:
                    raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _('\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                if not self.override_stock_lot: # newly added by @sopulu maduka to override product trnsfer lots
                    message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s. You can also go to the operation type and untick the use lot or create lot options') % (', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

#     def update_memo_status(self, status):
#         record = self.env['memo.model'].search([
#             ('code', '=', self.origin)
#             ], limit=1)
#         if record:
#             record.sudo().write({'state': status})
    
#     def _action_done(self):
#         res = super(StockPicking, self)._action_done()
#         self.update_memo_status('Done')
#         return res
    
#     def button_validate(self):
#         res = super(StockPicking, self).button_validate()
#         self.update_memo_status('Done')
#         return res


    
     