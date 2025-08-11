from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class RequestLine(models.Model):
    _name = "request.line"
    _description = "Request line"

    # def _get_product_domain(self):
    #     products = [0]
    #     # if self.env.context.get('memo_type_key') == 'vehicle_request' or self.memo_type_key == "vehicle_request" :
    #     if self.memo_type_key == "vehicle_request" :
    #         # raise ValidationError(self.env.context.get('memo_type_key'))
    #         product_ids = self.env['product.product'].sudo().search([('is_vehicle_product', '=', True)])
    #         products = product_ids.ids if product_ids else products

    #     else:
    #         products = products
    #     return [('id', 'in', [1,4])]
    
    
    memo_id = fields.Many2one(
        "memo.model", 
        string="Memo ID"
        )
    request_line_id = fields.Integer(
        string="Request line ID",
        help="Will be used to get the actual cash advance line to retire",
        store=True,
        )
    fleet_id = fields.Many2one(
        "memo.fleet", 
        string="Fleet ID"
        )
    product_id = fields.Many2one(
        "product.product", 
        string="Product ID",
        # domain=lambda self: self._get_product_domain()
        )
    code = fields.Char(
        string="Product code", 
        related="product_id.default_code"
        )
    description = fields.Text(
        string="Description"
        )
    # district_id = fields.Many2one("hr.district", string="District ID")
    quantity_available = fields.Float(string="Qty Requested", default=0)
    amount_total = fields.Float(string="Unit Price")
    sub_total_amount = fields.Float(string="Subtotal", compute="compute_sub_total")
    retire_sub_total_amount = fields.Float(string="SubTotal", compute="compute_retire_sub_total")
    used_qty = fields.Float(string="Qty Used", default=1)
    used_amount = fields.Float(string="Amount Used (per unit)")
    note = fields.Char(string="Note")
    code = fields.Char(string="code")
    to_retire = fields.Boolean(string="To Retire", help="Used to select the ones to retire", default=False)
    retired = fields.Boolean(string="Retired", help="Used to select determined retired", default=False)
    state = fields.Char(string="State")
    source_location_id = fields.Many2one("stock.location", string="Source Location")
    dest_location_id = fields.Many2one("stock.location", string="Destination Location")
    total_balance_difference = fields.Float(
        string="Balance Diff", 
        compute="compute_balance_difference",
        help="Balance between total cash advance amount and To retired balance")
    
    @api.depends("sub_total_amount", "retire_sub_total_amount")
    def compute_balance_difference(self):
        for rec in self:
            rec.total_balance_difference = rec.sub_total_amount - rec.retire_sub_total_amount
            
    @api.depends("quantity_available", "amount_total")
    def compute_sub_total(self):
        for x in self:
            if (x.amount_total and x.quantity_available):
                x.sub_total_amount =  x.quantity_available * x.amount_total
            else:
                x.sub_total_amount = 0.00

    @api.depends("used_qty", "used_amount")
    def compute_retire_sub_total(self):
        for x in self:
            if (x.used_qty and x.used_amount):
                x.retire_sub_total_amount =  x.used_qty * x.used_amount
            else:
                x.retire_sub_total_amount = 0.00
    
    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            if self.memo_type_key == "vehicle_request" and not self.product_id.is_vehicle_product:
                raise ValidationError("Please ensure to select on vehicle items")
    
    @api.onchange('quantity_available')
    def onchange_quantity_available(self):
        if self.quantity_available:
            self.check_product_qty()
            
    distance_from = fields.Text(
        string="From",
        help="For vehicle request use"
        )
    distance_to = fields.Text(
        string="Destination",
        help="For vehicle request use"
        )
    driver_assigned = fields.Many2one(
        'hr.employee',
        string="Driver Assigned",
        help="For vehicle request use"
        )
    # memo_type = fields.Selection(
    #     [
    #     ("Payment", "Payment"), 
    #     ("loan", "Loan"), 
    #     ("Internal", "Internal Memo"),
    #     ("employee_update", "Employee Update Request"),
    #     ("material_request", "Material request"),
    #     ("procurement_request", "Procurement Request"),
    #     ("vehicle_request", "Vehicle request"),
    #     ("leave_request", "Leave request"),
    #     ("server_access", "Server Access Request"),
    #     ("cash_advance", "Cash Advance"),
    #     ("soe", "Statement of Expense"),
    #     ("recruitment_request", "Recruitment Request"),
    #     ], string="Memo Type")
    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=False
        )
    memo_type_key = fields.Char('Memo type key', readonly=True)#, related="memo_type.memo_key")
    
    def check_product_qty(self):
        if self.quantity_available and self.quantity_available > 0:
            if self.product_id and self.memo_type_key in ['material_request']:# and self.product_id.detailed_type in ['product']:
                # domain = ['|',('company_id', '=', self.env.user.company_id.id), 
                #           ('company_id', 'in', self.env.user.company_ids.ids)] 
                domain = [('company_id', '=', self.company_id.id), ('branch_id', '=', self.env.user.branch_id.id)] 
                # use the above domain because it will restrict products to warehouse company and branch 
                warehouse_location_id = self.env['stock.warehouse'].sudo().search(domain, limit=1)
                stock_location_id = warehouse_location_id.lot_stock_id
                total_availability = self.env['stock.quant'].sudo()._get_available_quantity(
                    self.product_id, stock_location_id, allow_negative=False) or 0.0
                product_qty = self.quantity_available 
                if product_qty > total_availability:
                    self.quantity_available = 0
                    raise UserError(f"""
                                    Request product quantity ({product_qty}) is lesser than the available unit ({total_availability}) in the inventory. 
                                    Contact system Admin to assign you to the warehouse of current company and current user branch where those products are located.""")

