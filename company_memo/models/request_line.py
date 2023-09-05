from odoo import models, fields, api, _


class RequestLine(models.Model):
    _name = "request.line"


    memo_id = fields.Many2one("memo.model", string="Memo ID")
    product_id = fields.Many2one("product.product", string="Product ID")
    code = fields.Char(string="Product code", related="product_id.default_code")
    description = fields.Char(string="Description")
    district_id = fields.Many2one("hr.district", string="District ID")
    quantity_available = fields.Float(string="Qty Requested")
    used_qty = fields.Float(string="Qty Used")
    amount_total = fields.Float(string="Unit Price")
    used_amount = fields.Float(string="Amount Used")
    note = fields.Char(string="Note")
    state = fields.Char(string="State")
    source_location_id = fields.Many2one("stock.location", string="Source Location")
    dest_location_id = fields.Many2one("stock.location", string="Destination Location")
    memo_type = fields.Selection(
        [
        ("Payment", "Payment"), 
        ("loan", "Loan"), 
        ("Internal", "Internal Memo"),
        ("material_request", "Material request"),
        ("procurement_request", "Procurement Request"),
        ("vehicle_request", "Vehicle request"),
        ("leave_request", "Leave request"),
        ("cash_advance", "Cash Advance"),
        ("soe", "Statement of Expense"),
        ], string="Memo Type")
    
    