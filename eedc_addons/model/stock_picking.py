from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = "stock.location"
    
    wh_code = fields.Char(string="Warehouse code", size=5)
    
    @api.constrains('wh_code')
    def _check_wh_code(self):
        for record in self:
            whl = self.env['stock.location'].search([
                ('wh_code', '=', self.wh_code)
                ], limit=2)
            if whl and len([r.id for r in whl]) > 1: 
                raise UserError(f"{record.wh_code} is already exiting the system, kindly change")

# class StockPicking(models.Model):
#     _inherit = "stock.picking"

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
    
     