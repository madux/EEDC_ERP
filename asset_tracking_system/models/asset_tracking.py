# # -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from calendar import monthrange
import calendar


class AssetTracking(models.Model):
    _name = 'asset.tracking'
    _description = 'Asset Tracking'
    _rec_name = "asset_code"
    _inherit = ['mail.thread']
    _order = "id desc"

    name = fields.Char(string='Ref', tracking=True, default='New')
    asset_code = fields.Char(string='Asset Number', readonly=False, copy=False)
    category = fields.Selection([
        ('it', 'IT Equipment'),
        ('vehicle', 'Vehicle'),
        ('furniture', 'Furniture'),
        ('other', 'Other')
    ], string='Category', required=False)
    active = fields.Boolean('Active', default=True)
    serial_number = fields.Char('Serial Number')
    transfer_expense = fields.Boolean('Transfer Depreciation Expense to BU', default=True)
    date_of_commission = fields.Date('Purchase Date')
    date_of_transfer = fields.Date('Transfer Date')
    date_received = fields.Date('Transfer Received')
    date_of_assignment = fields.Date('Assigned Date')
    purchase_date = fields.Date('Purchase Date')
    purchase_value = fields.Float('Purchase Value')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    asset_id = fields.Many2one('account.asset', string='Asset ID', required=False)
    old_asset_id = fields.Many2one('account.asset', string='Old Asset ID')
    new_asset_id = fields.Many2one('account.asset', string='New Asset ID')
    src_location_id = fields.Many2one('stock.location', string="Asset Location")
    previous_location_id = fields.Many2one('stock.location', string="Old Previous location")
    previous_location = fields.Many2one('multi.branch', string="Previous Asset Location")
    source_location_id = fields.Many2one('multi.branch', string="Destination Asset Location")
    asset_history_ids = fields.One2many('account.asset', inverse_name='asset_tracking_id', string="Asset History", help="Used to get previous moves of asset transfers")
    value_factor = fields.Float(
        string='Value Factor (%)',
        help="Multiplier to apply when an asset moves to this location (e.g. 1.1 = increase by 10%)"
    )
    new_book_value = fields.Float(
        string='New Value',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('transfer', 'Awaiting Receipt'),
        ('received', 'Asset received'),
        ('maintenance', 'Under Maintenance'),
        ('disposed', 'Disposed')
    ], default='draft', tracking=True)
     
    note = fields.Text('Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.tracking') or 'New'
        return super().create(vals)
    
    @api.onchange('assigned_to')
    def onchange_assignedTo(self):
        if self.assigned_to:
            allowed_branches = self.assigned_to.check_allowed_user_branches([self.source_location_id.id])
            if not allowed_branches:
                self.assigned_to = False 
                raise ValidationError(f"Assigned User does not belong to {self.source_location_id.name}")
               
    @api.onchange('asset_code')
    def onchange_asset_code(self):
        if self.asset_code:
            not_found = True
            account_asset_id = self.env['account.asset'].search(
                ['|', ('asset_code', '=', self.asset_code),
                 ('name', '=', self.asset_code),
                 ('state', 'in', ['open', 'paused', 'draft']),
                  ('active', '=', True)
                 ], limit=1)
            if account_asset_id:
                self.asset_id = account_asset_id.id
                self.previous_location = account_asset_id.branch_id.id
                self.branch_id = account_asset_id.branch_id.id
                # self.serial_number = account_asset_id.serial_number
                self.date_of_commission = account_asset_id.acquisition_date or account_asset_id.date_of_commission
                not_found = False
            else:
                self.asset_id = False
                self.asset_code = ''
                if not_found:
                    raise ValidationError(f'No running asset with code {self.asset_code} found on the system')      
    
     
    @api.onchange('source_location_id')
    def onchange_source_location_id(self):
        for rec in self:
            if rec.source_location_id:
                if rec.transfer_expense and rec.source_location_id.id == rec.branch_id.id: 
                    rec.source_location_id = False
                    raise ValidationError("Business unit and source location cannot be the same")
    
    # @api.onchange('transfer_expense')
    # def onchange_transfer_expense(self):
    #     for rec in self:
    #         if rec.transfer_expense == True and rec.state == "draft":
    #             rec.source_location_id = False
   
    def transfer_asset(self):
        self.asset_id.sudo().update({
            'awaiting_transfer_location': self.source_location_id.name,
            'transfer_status': 'Transfered & Awaiting Receipt',
        })
        self.sudo().update({
            'date_of_transfer': fields.Date.today(),
            'state': 'transfer',
            'previous_location': self.asset_id.branch_id.id,
        })
        
        #TODO Send notification
    def receive_and_calculate(self):
        if not self.env.user.check_allowed_user_branches([self.source_location_id.id]):
            raise ValidationError(f"You are not allowed to receive this asset: If you are sure, contact system admin to add {self.source_location_id.name} to your allowed branch")
        
        if not self.asset_id:
            ValidationError('Please enter valid asset id')
        
        for asset in self:
            # validations
            if not asset.source_location_id.account_asset_id:
                raise ValidationError(f"Location branch: {asset.source_location_id.name} must have default expense accounts set up")
            if not asset.source_location_id.account_depreciation_id:
                raise ValidationError(f"Location branch: {asset.source_location_id.name} must have depreciation accounts set up")
            if not asset.source_location_id.account_depreciation_expense_id:
                raise ValidationError(f"Location branch: {asset.source_location_id.name} must have depreciation expense accounts set up")
                
            if asset.transfer_expense:
                # ensure no duplicate asset create by checking if it already exists and not running 
                if asset.new_asset_id and asset.new_asset_id.state not in ['draft', 'cancel']:
                    raise ValidationError("Asset is already generated and running")
                else:
                    asset.new_asset_id.unlink()
                
                '''If user wants to transfer asset artificats and entries to another business unit'''
                asset.new_asset_id = asset.asset_id.id
                asset.asset_id.sudo().update({
                    'date_of_assignment': fields.Date.today(),
                    'date_received': fields.Date.today(),
                    'branch_id': asset.source_location_id.id,
                    'source_location_id': asset.source_location_id.id,
                    'previous_location': asset.asset_id.branch_id.id, 
                    'to_transfer_expense': True,
                    'asset_tracking_history_ids':  [(4, asset.id)]
                })
            else:
                # if source location and current location must be the same
                asset.new_asset_id = asset.asset_id.id
                asset.asset_id.sudo().update({
                    'date_received': fields.Date.today(),
                    'branch_id': asset.source_location_id.id,
                    'source_location_id': asset.source_location_id.id,
                    'previous_location': asset.asset_id.branch_id.id,
                    'to_transfer_expense': False,
                    'asset_tracking_history_ids': [(4, asset.id)]
                    
                })
            asset.state = 'received'
            asset.date_received = fields.Date.today()
            asset.previous_location = asset.branch_id.id
            asset.assigned_to = self.env.user.id if not asset.assigned_to else asset.assigned_to.id
            return self.action_generate_asset(asset.asset_id)
          
    def action_generate_asset(self, asset):
        tree_view_id = self.env.ref('account_asset.view_account_asset_tree').id
        form_view_id = self.env.ref('account_asset.view_account_asset_form').id 
        ret = {
            'name': "Asset",
            'view_mode': 'form',
            'view_id': form_view_id,
            'view_type': 'form',
            # 'views': [
            #     (tree_view_id, 'tree'), 
            #     (form_view_id, 'form')],
            'res_model': 'account.asset',
            'res_id': asset.id,
            ## 'domain': [('id', 'in', asset.id)],
            'type': 'ir.actions.act_window', 
            'target': 'new',
            }
        return ret
    
    def action_view_asset_history(self):
        tree_view_id = self.env.ref('account_asset.view_account_asset_tree').id
        form_view_id = self.env.ref('account_asset.view_account_asset_form').id 
        tracking_assets = self.env['account.asset'].search([
            ('asset_tracking_id', '=', self.id),
            ('active', 'in', [True, False, 1, 0])])
        asset_ids = tracking_assets.ids if tracking_assets else []
        ret = {
            'name': "Asset",
            'view_mode': 'tree',
            'view_id': form_view_id,
            'view_type': 'tree,form',
            'views': [
                (tree_view_id, 'tree'), 
                (form_view_id, 'form')],
            'res_model': 'account.asset',
            # 'res_id': asset.id,
            'domain': [('id', 'in', asset_ids), ('active', 'in', [True, False, 1, 0])],
            'type': 'ir.actions.act_window', 
            'target': 'current',
        }
        return ret  

    #Server action 
    def get_filtered_received_record(self):
        view_id_form = self.env.ref('asset_tracking_system.view_asset_tracking_form')
        view_id_tree = self.env.ref('asset_tracking_system.view_asset_tracking_tree')
        user = self.env.user
        # allowed_internal_users = user.check_allowed_user_branches([self.source_location_id.id])
        allowed_internal_users = user.get_user_allowed_branches()
        record_ids = []
        # if allowed_internal_users:
            # raise ValidationError('true') 
        asset_to_receive = self.sudo().search([('state', '=', 'transfer'), ('source_location_id', 'in', allowed_internal_users)])
        if asset_to_receive:
            record_ids = asset_to_receive.ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asset to be received',
            'limit': 80,
            'res_model': 'asset.tracking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(view_id_tree.id, 'tree'), (view_id_form.id,'form')],
            'target': 'current',
            'domain': [('id', 'in', record_ids)]
        }
     