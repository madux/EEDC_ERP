from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = "stock.location"
    _order = "id desc"
    
    wh_code = fields.Char(string="code", size=5) 
    
    # @api.constrains('wh_code')
    # def _check_wh_code(self):
    #     for record in self:
    #         whl = self.env['stock.location'].search([
    #             ('wh_code', '=', self.wh_code)
    #             ], limit=2)
    #         if whl and len([r.id for r in whl]) > 1: 
    #             raise UserError(f"{record.wh_code} is already exiting the system, kindly change")

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    @api.onchange('location_id', 'location_dest_id')
    def _onchange_locations(self):
        # (self.move_ids | self.move_ids_without_package).update({
        #     "location_id": self.location_id,
        #     "location_dest_id": self.location_dest_id
        # })
        moves = self.move_ids_without_package | self.move_ids
        for rec in self.move_ids_without_package:
            rec.sudo().write({
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id
            })
            
    # @api.onchange('location_id', 'location_dest_id')
    # def _onchange_locations(self):
    #     (self.move_ids | self.move_ids_without_package).update({
    #         "location_id": self.location_id,
    #         "location_dest_id": self.location_dest_id
    #     })
    #     if any(line.reserved_qty or line.qty_done for line in self.move_ids.move_line_ids):
    #         return {'warning': {
    #                 'title': 'Locations to update',
    #                 'message': _("You might want to update the locations of this transfer's operations")
    #             }
    #         }
    
    def reset_to_draft(self):
        for rec in self:
            if rec.state in ['cancel']:
                rec.state = 'draft'

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
    
     