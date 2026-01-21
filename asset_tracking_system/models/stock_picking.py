from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    
    request_line_id = fields.Many2one('request.line', string='Request line id',)
    
class StockMove(models.Model):
    _inherit = "stock.move"
    
    request_line_id = fields.Many2one('request.line', string='Request line id',)
    
    
class StockPicking(models.Model):
    _inherit = "stock.picking"

    memo_id = fields.Many2one('memo.model', string='Memo Reference')
    
    bl_awb_number = fields.Char(string="BL/AWB No.", copy=True)
    truck_company_name = fields.Many2one('res.partner', string='Truck company Name')
    truck_reg = fields.Char(string='Truck registration No.')
    truck_type = fields.Char(string='Truck Type')
    truck_driver = fields.Many2one('res.partner', string='Driver details')
    truck_driver_phone = fields.Char(string='Driver Phone')
    
    # def _action_done(self):
    #     res = super(StockPicking, self)._action_done() 
    #     return res

    def button_validate(self):
        # if self.origin and self.env['sale.order'].search([('name', '=', self.origin), ('is_crusher_order', '=', True)], limit=1):
        #     if not all(self.actual_shipment_date, self.truck_driver_name, self.truck_reg, self.truck_driver_phone, self.truck_company_name):
        #         raise ValidationError(f"Fields such as [Driver name,Driver phone, truck registration number, company, actual shipment date] must be provided. Check the Drivers / Truck Information tab")
        self.update_issued_qty(self.move_ids_without_package)
        self.update_asset_register()
        res = super(StockPicking, self).button_validate()
        '''Validate issued quantity''' 
        return res
    
    def update_issued_qty(self, stock_move_lines):
        for mv in stock_move_lines: #self.move_line_ids:
            if mv.request_line_id:
                issued_qty = mv.quantity_done
                mv.request_line_id.issue_qty = mv.request_line_id.issue_qty + issued_qty
                mv.request_line_id.qty_to_issue = 0

    def update_asset_register(self):
        memo_id = False 
        if hasattr(self.env['stock.picking'], 'memo_id'):
            if self.memo_id:
                memo_id = self.memo_id
                _logger.info(f"Generate this assets MEEEMAO DO {memo_id}")
            else:
                memo_id = self.purchase_line_id and self.purchase_line_id[0] or self.env['purchase.order'].search([
                ('name', '=', self.origin)
                ], limit=1)
                memo_id = memo_id and memo_id.memo_id
                _logger.info(f"FOUND MEMOO Generate this assets {memo_id}")
            if memo_id.po_ids:
                assets = memo_id.generate_asset(po_ids=memo_id.po_ids, generate_all=False, store_number=self.name, memo_id = memo_id.id)
                _logger.info(f"Generate this assets xxxxxx {[rec for rec in assets]}")
        else:
            po_id = self.purchase_line_id and self.purchase_line_id[0]
            if po_id:
                self.generate_asset(po_ids= po_id, generate_all=False, store_number=self.name, memo_id = False)
            # else:
            #     raise ValidationError("There is no PO to generate asset for")
     
    def generate_asset(self, po_ids=False, generate_all = False, **kwargs):
        '''generate_all = True => generates the total number of asset quantites, else it generates it as one single parent asset, asset people will now run the asset'''
        assets = []
        asset_obj = self.env['account.asset']
        # asset_line = self.mapped('asset_ids')
        # if asset_line:
        #     pass 
            # raise UserError('Asset(s) has already being created')
        po_ids = po_ids
        for rec in po_ids:
            for po in rec.order_line:
                if po.product_id: 
                    asset_model = po.product_id.account_asset_model or po.product_id.categ_id.account_asset_model
                    '''CHECK AND CREATE ASSET BASED ON THE NUMBER OF QUANTITY'''
                    if asset_model:
                        '''the product is linked to asset model, so it will generate asset'''
                        item_number = 101
                        code = f'Batch-{self.name}'
                        no_of_items_to_generate = range(0, int(po.qty_received)) if generate_all else range(0, 1) 
                        for ass in no_of_items_to_generate:
                            asset_code = f"{code}-{item_number + 1}"
                            taxes = 0
                            # if po.product_id.categ_id.sum_up_total:
                            #     taxes = sum([r.amount for r in po.added_tax_ids])
                            #     for at in po.added_tax_ids:
                            #         taxes += at.amount
                            #     tax = abs(taxes / 100) * po.price_unit
                            #     total_tax = tax + po.price_unit if abs(taxes) > 0 else po.price_tax
                            # else:
                            total_tax = po.price_unit + po.price_tax / po.product_qty
                            _logger.info(f"Generate 1.0 this assets {ass} {[rec for rec in assets]}")
                            asset = asset_obj.create({
                                'product_id': po.product_id.id,
                                'product_desc': po.product_id.name or po.product_id.description,
                                # 'memo_id': kwargs.get('memo_id'),                                
                                'source_location_id': self.env.user.branch_id.id,                                
                                'branch_id': self.env.user.branch_id.id,                                
                                'date_of_commission': self.date_of_commission,
                                'model_id': asset_model.id,
                                'account_asset_id': asset_model.account_asset_id.id,
                                'account_depreciation_id': asset_model.account_depreciation_id.id,
                                'account_depreciation_expense_id': asset_model.account_depreciation_expense_id.id,
                                'modify_action': self.modify_action,
                                'asset_code': asset_code, # f'''{self.code} {self.id} {asset_count}''',
                                'original_value': total_tax,
                                'purchase_value_without_tax': po.price_unit,
                                'inventory_number': kwargs.get('store_number'),
                                'responsible_bu': self.env.user.branch_id.id,
                                'method_number': asset_model.method_number,
                                'method_period': asset_model.method_period,
                                'method': asset_model.method,
                                'prorata_computation_type': asset_model.prorata_computation_type,
                                'parent_number': "", # make it empty since this is the parent asset #asset_model.name,
                                'fleet_number': asset_model.fleet_number,
                                'qty_received': po.product_qty,
                                'is_asset_from_procurement': True,
                                'purchase_order': po.order_id.id,
                                'prorata_date': po.order_id.date_order,
                            })
                            assets.append(asset.id)
                            _logger.info(f"Generate 1 this assets {asset} {[rec for rec in assets]}")
                        else:
                            _logger.info(f"Product did not generate asset because it does not have asset model in its category")
        if hasattr(self.env['stock.picking'], 'memo_id'):
            self.memo_id.asset_ids = [(4, ass) for ass in assets]
        # return assets       

# class StockImmediateTransfer(models.TransientModel):
#     _inherit = 'stock.immediate.transfer'
#     _description = 'Immediate Transfer'

#     def process(self):
#         res = super(StockImmediateTransfer, self).process()
#         for transfer in self.immediate_transfer_line_ids:
#             transfer.picking_id.memo_id.is_request_completed = True
#         return res

