# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
 

class AccountAsset(models.Model):
    _inherit = 'account.asset'
    _order = "id desc"
    
    previous_location_id = fields.Many2one('stock.location', string="Previous Asset Location")
    src_location_id = fields.Many2one('stock.location', string="Asset Location")
    previous_location = fields.Many2one('multi.branch', string="Previous Asset Location")
    source_location_id = fields.Many2one('multi.branch', string="Asset Location")
    asset_tracking_id = fields.Many2one('asset.tracking', string="Asset track id")
    date_of_transfer = fields.Date('Transfer Date')
    date_of_assignment = fields.Date('Assigned Date')
    date_received = fields.Date('Transfer Received')
    qty_received = fields.Float('Recieved Qty') 
    asset_history_ids = fields.One2many('asset.tracking', inverse_name='new_asset_id', string="History old", help="Used to get previous moves of asset transfers")
    asset_tracking_history_ids = fields.Many2many(
        'asset.tracking',
        'asset_tracking_rel', 
        'asset_tracking_id',
        'account_asset_id',
        string="Asset Transfer History", 
        help="Used to get previous moves of asset transfers")
           
    def button_confirm_move(self):
        selected_draft_moves = self.mapped('depreciation_move_ids').filtered(lambda a: a.select==True and a.state=='draft')
        if not selected_draft_moves:
            raise ValidationError("You must select an unposted entry") 
        else:
            for mv in selected_draft_moves:
                mv.action_post()
                mv.select = False
    
    def action_select_all(self):
        selected_draft_moves = self.mapped('depreciation_move_ids').filtered(lambda a: a.state=='draft')
        for mv in selected_draft_moves:
            if not mv.select:
                mv.select = True
            else:
                mv.select = False
                
    @api.constrains('name')
    def constraint_name(self):
        if self.name and not self.asset_tracking_id:
            asset_obj = self.env['account.asset'].search([('name', '=', self.name)], limit=2)
            if len(asset_obj) > 1:
                raise ValidationError("Asset Number already exist")