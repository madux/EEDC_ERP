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
        'helpdesk.memo.model', 
        string='Memo ID'
        )
  
    
class HelpdeskMemoModel(models.Model):
    _name = 'helpdesk.memo.model'
    _inherit = ['memo.model']

    memo_type = fields.Many2one(
        'memo.type', 
        string="Request type", 
        default=lambda self: self.env.ref('helpdesk_process.mtype_helpdesk').id
        )
    
    helpdesk_memo_config_id = fields.Many2one(
        'memo.config', 
        string="Category", 
        )
    customer_partner_id = fields.Many2one('res.partner', string='Customer ID')
    customer_name = fields.Char('Customer Name')
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
    complaint_resolution_ids = fields.One2many(
        'complaint.resolution',
        'memo_id',
        string='Resolution line'
        )
    
    user_owned_cash_advance_ids = fields.Many2many(
        'memo.model', 
        'user_owned_cash_helpdesk_advance_rel',
        'user_owned_cash_helpdesk_advance_id',
        'memo_id', string="User owned cash helpdesk advances", store=False)
    
    approver_ids = fields.Many2many(
        'hr.employee',
        'memo_model_helpdesk_employee_rel',
        'memo_id',
        'hr_employee_id',
        string='Approvers'
        )
    
    invoice_ids = fields.Many2many(
        'hr.employee',
        'memo_model_helpdesk_employee_rel',
        'memo_id',
        'hr_employee_id',
        string='Approvers'
        )
    partner_ids = fields.Many2many(
        'res.partner', 
        'memo_res_helpdesk_partner_rel',
        'memo_res_partner_id',
        'memo_partner_id',
        string='Reciepients', 
        )
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'memo_ir_attachment_helpdesk_rel',
        'memo_ir_attachment_id',
        'ir_attachment_memo_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', 'memo.model')]"
        )
    memo_sub_stage_ids = fields.Many2many(
        'memo.sub.stage', 
        'memo_sub_stage_helpdesk_rel',
        'memo_sub_stage_id',
        'memo_id',
        string='Sub Stages', 
        store=True,
        )
    
    @api.onchange('helpdesk_memo_config_id')
    def get_helpdesk_memo_config_id_stage_id(self):
        """ Gives default stage_id """
        if self.helpdesk_memo_config_id:
            if self.helpdesk_memo_config_id.stage_ids:
                memo_setting_stage = self.helpdesk_memo_config_id.stage_ids[0]
                self.stage_id = memo_setting_stage.id if memo_setting_stage else False
                self.memo_setting_id = self.helpdesk_memo_config_id.id
                self.memo_type_key = self.memo_type.memo_key 
                self.requested_department_id = self.employee_id.department_id.id
                self.users_followers = [
                            (4, self.employee_id.administrative_supervisor_id.id),
                            ] 
            else:
                self.memo_type = False
                self.stage_id = False
                self.memo_setting_id = False
                self.memo_type_key = False
                self.requested_department_id = False
                msg = f"No stage configured for the select configuration. Please contact administrator"
                return {'warning': {
                            'title': "Validation",
                            'message':msg,
                        }
                }
        else:
            self.stage_id = False
    
    def confirm_memo_helpdesk (self):
        for complain in self:
            if not complain.complaint_resolution_ids.ids:
                raise ValidationError(
                    'Please add resolution lines'
                ) 
   