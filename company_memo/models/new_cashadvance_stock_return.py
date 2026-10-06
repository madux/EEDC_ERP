from odoo import api, fields, models, _
from odoo.exceptions import UserError 

class MemoReturnWizard(models.TransientModel):
    _name = 'memo.return.wizard'
    _description = 'Memo Return Unused Items'

    memo_id = fields.Many2one(
        'memo.model',
        string='Memo',
        required=True,
        readonly=True,
    )

    move_to_store = fields.Boolean(
        string='Move Items to Store',
        default=True,
    )

    company_id = fields.Many2one(
        related='memo_id.company_id',
        string='Company',
        readonly=True,
    )

    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Store',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
    )
    reason = fields.Text(
        string='Reason for Transfer',
        default="Reasons",
        required=True,
    )
    credit_note = fields.Binary(
            string='Attach Credit Note',
            required=True,
        )

    line_ids = fields.One2many(
        'memo.return.wizard.line',
        'wizard_id',
        string='Items to Return',
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Transfer',
        readonly=True,
    )
    branch_id = fields.Many2one(
            'multi.branch',
            related="memo_id.branch_id",
            string='Stock Transfer',
            readonly=True, store=True
        )

    @api.onchange('move_to_store')
    def _onchange_move_to_store(self):
        if not self.move_to_store:
            self.destination_location_id = False

    def action_confirm(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(
                _('There are no items available for return.')
            )

        if self.move_to_store and not self.destination_location_id:
            raise UserError(
                _('Please select the destination store.')
            )

        if not self.reason:
            raise UserError(
                _('Please provide a reason for the transfer.')
            )

        # If user does not want to move the items to store,
        # simply close the wizard.
        if not self.move_to_store:
            return {'type': 'ir.actions.act_window_close'}

        # ---------------------------------------------------------
        # SOURCE LOCATION
        # ---------------------------------------------------------
        #
        # Replace this with the actual location from your memo.
        #
        source_location = self.env['stock.location'].search([
            ('usage', '=', 'supplier'),
            ('company_id', '=', self.memo_id.company_id.id)], limit=1)

        if not source_location:
            raise UserError(
                _(f'No source/supplier location has been configured for {self.memo_id.company_id.name}.')
            )

        # ---------------------------------------------------------
        # FIND INTERNAL PICKING TYPE
        # ---------------------------------------------------------

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', 'in', [self.memo_id.company_id.id, self.env.company.id]),
        ], limit=1)

        if not picking_type:
            raise UserError(
                _(f'No receipt transfer operation type was found for {self.memo_id.company_id.name}')
            )

        
        # ---------------------------------------------------------
        # CREATE PICKING
        # ---------------------------------------------------------

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.memo_id.display_name,
        })

        # ---------------------------------------------------------
        # CREATE STOCK MOVES
        # ---------------------------------------------------------

        for line in self.line_ids:

            if line.return_qty <= 0:
                continue

            product = line.product_id

            move = self.env['stock.move'].create({
                'name': self.memo_id.display_name,
                'product_id': product.id,
                'product_uom_qty': line.return_qty,
                'product_uom': product.uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': self.destination_location_id.id,
                'company_id': self.memo_id.company_id.id or self.env.company.id,
            })

        if not picking.move_ids:
            raise UserError(
                _('No valid quantities were selected for return.')
            )

        # ---------------------------------------------------------
        # CONFIRM
        # ---------------------------------------------------------

        picking.action_confirm()

        # ---------------------------------------------------------
        # ASSIGN AVAILABLE STOCK
        # ---------------------------------------------------------

        picking.action_assign()

        # ---------------------------------------------------------
        # AUTO VALIDATE
        # ---------------------------------------------------------

        for move in picking.move_ids:
            for move_line in move.move_line_ids:
                move_line.qty_done = move.product_uom_qty

        picking.button_validate()

        # ---------------------------------------------------------
        # SAVE REFERENCE
        # ---------------------------------------------------------

        self.picking_id = picking.id

        # If your memo model has a field such as:
        #
        # stock_picking_id = fields.Many2one('stock.picking')
        #
        # you can link it here.
        #
        self.memo_id.stock_picking_id = picking.id
        self.memo_id.memo_cash_advance_procurement_status = False 
        self.memo_id.update_status_badge()

        # self.sudo().picking_id.action_print_store_receive_note()
        # return self.memo_id.generate_soe_entry_function(self.memo_id)
        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'stock.picking',
        #     'res_id': picking.id,
        #     'view_mode': 'form',
        #     'target': 'current',
        # }
        return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
    
    def view_store_picking(self):
        if not self.picking_id:
            raise UserError("No transfer has been generated")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_store_receive_note(self):
        self.ensure_one()
        if self.picking_id:
            return self.sudo().picking_id.action_print_store_receive_note()
        else:
            raise UserError("No transfer has been generated")


class MemoReturnWizardLine(models.TransientModel):
    _name = 'memo.return.wizard.line'
    _description = 'Memo Return Wizard Line'

    wizard_id = fields.Many2one(
        'memo.return.wizard',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
    )

    quantity_available = fields.Float(
        string='Quantity Available',
        readonly=True,
    )

    used_qty = fields.Float(
        string='Used Quantity',
        readonly=True,
    )

    return_qty = fields.Float(
        string='Return Quantity',
        readonly=False,
    )