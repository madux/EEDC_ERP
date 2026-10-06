from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
    
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = "id desc"
    _check_company_auto = False


    memo_id = fields.Many2one('memo.model', string='Request Reference')
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    is_inter_district_transfer = fields.Boolean("Is inter district transfer")
    
    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        # self.update_memo_status('Done')
        if self.sudo().memo_id and self.sudo().memo_id.code == self.origin:
            memo_id = self.sudo().memo_id
            # self.memo_id.is_request_completed = True # Done remove because it will set the process to done automatically 
            self.sudo().memo_id.update_final_state_and_approver()
            self.sudo().memo_id.update_status_badge()
            if memo_id.external_stock_picking_id and memo_id.external_stock_picking_id.state not in ['done']:
                external_stock_picking_id = memo_id.external_stock_picking_id
                external_stock_picking_id._action_done()
        return res

    def cross_check_to_ensure_delivery(self):
        '''used to cross check if delivery is done before recieving '''
        external_memo_picking_id = self.env['memo.model'].search([('external_stock_picking_id', '=', self.id)])
        if external_memo_picking_id and external_memo_picking_id.stock_picking_id.state != ['done']:
            raise ValidationError(f"The stock delivery reference {(external_memo_picking_id.stock_picking_id.name)} for this record has not been validated. \n Contact the delivery store officer to validate on his end before you recieve it")

    def button_validate(self):
        
        res = super(StockPicking, self).button_validate()
        # self.update_memo_status('Done')
        # for mv in self.move_ids_without_package:
        #     self.location_check_available_qty(mv.product_id,mv.location_id, mv.quantity_done)
        self.cross_check_to_ensure_delivery()
        if self.sudo().memo_id and self.sudo().memo_id.code == self.origin:
            memo_id = self.sudo().memo_id
            memo_id.is_request_completed = True # Dont remove because it will set the process to done automatically 
            self.sudo().memo_id.update_final_state_and_approver()
            self.sudo().memo_id.update_status_badge()

            # the receipt person should validate
            # if memo_id.external_stock_picking_id and memo_id.external_stock_picking_id.state not in ['done']:
            #     external_stock_picking_id = memo_id.external_stock_picking_id
            #     external_stock_picking_id.button_validate()
            memo_id.confirm_memo(memo_id.employee_id, f"Stock issuance for {memo_id.code} is now at stage {memo_id.stage_id.name}")
        return res
    
    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        self.state = "confirmed"
        # for mv in self.move_ids_without_package:
        #     self.location_check_available_qty(mv.product_id,mv.location_id, mv.quantity_done)
        return res 
    
    
    def location_check_available_qty(self, product_id, source_location_id, quantity_done):
        if source_location_id:
            qty = self.env['stock.quant'].sudo()._get_available_quantity(
                product_id, 
                source_location_id, 
                allow_negative=False)
            err_msg = [f"{product_id.name} Available Quantity is {qty} at Location {source_location_id.display_name} \n Below are the available locations with Quantities- \n"]
            if qty < quantity_done:
                available_product_locations = self.env['request.line'].sudo().get_available_locations_with_items(
                    self.company_id,
                    product_id,
                    )  
                if available_product_locations.get('data'):
                    for r in available_product_locations.get('data'):
                        err_msg.append(f"""Location: {r.get('Location')} - Quantity: {r.get('Quantity')} \n""")
                err_msg = "\n".join(err_msg)
                raise UserError(err_msg)
    

    # def update_memo_status(self, status):
    #     # not currently in use
    #     record = self.env['memo.model'].search([
    #         ('code', '=', self.origin)
    #         ], limit=1)
    #     if record:
    #         record.sudo().write({
    #             'state': status
    #             })
    

class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    def process(self):
        res = super(StockImmediateTransfer, self).process()
        for transfer in self.immediate_transfer_line_ids:
            transfer.picking_id.memo_id.is_request_completed = True
            transfer.sudo().picking_id.memo_id.update_status_badge()
            if transfer.picking_id.memo_id and transfer.picking_id.memo_id.external_stock_picking_id:
                external_stock_picking_id = transfer.picking_id.memo_id.external_stock_picking_id
                external_stock_picking_id.button_validate()
        return res

