from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
 
 
class AccountMove(models.Model):
    _inherit = 'account.move'

    select = fields.Boolean(string="")
    
    def action_post(self):
        for record in self:
            record.auto_post = 'no'
        res = super().action_post()
        return res
        
    def button_view_asset_move(self):
        view_id = self.env.ref('account.view_move_form').id
        ret = {
            'name': "Asset Journal Entry Move",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.move',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
            }
        return ret