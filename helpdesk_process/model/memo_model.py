from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ComplaintResolution(models.Model):
    _name = 'complaint.resolution'
    
    name = fields.Char('Description')
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.uid
        )
    memo_id = fields.Many2one(
        'memo.model', 
        string='Memo ID'
        )
  
    
class HelpdeskMemoModel(models.Model):
    _inherit = 'memo.model'

    # attrs="{'required': [('memo_type_key', '=', 'helpdesk')]}"
    customer_partner_id = fields.Many2one('res.partner', string='Customer ID')
    customer_phone = fields.Char('Customer phone')
    customer_phone2 = fields.Char('Customer phone 2')
    customer_meter_no = fields.Char(string='Customer Account / Meter No')
    meter_type = fields.Selection([('postpaid', 'Postpaid'),
                                ('prepaid', 'Prepaid'),
                                ('direct source', 'Direct Source'),
                              ], string='Meter type', index=True,
                             copy=False,
                             readonly=False,
                             store=True, 
                             )
    customer_email = fields.Char('Customer Email')
    customer_address1 = fields.Char('Address 1')
    customer_address2 = fields.Char('Address 2')
    
    complaint_start_date = fields.Date('Start Date', default=fields.Date.today())
    complaint_close_date = fields.Date('Closed Date')
    complaint_duration = fields.Integer('Duration')
    complaint_description = fields.Text('Complaints')
    complaint_resolution_ids = fields.Many2many(
        'complaint.resolution',
        string='Resolution line'
        )
    
    def confirm_memo_helpdesk (self):
        for complain in self:
            if not complain.complaint_resolution_ids.ids:
                raise ValidationError(
                    'Please add resolution lines'
                ) 
   