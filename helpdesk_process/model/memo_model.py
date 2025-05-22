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
    state = fields.Selection([
        ('pending', 'Pending'),
        ('resolved', 'Resolved')
    ], string="Status", default='pending')
    memo_id = fields.Many2one(
        'memo.model', 
        string='Memo ID'
        )


class HelpdeskMemoModel(models.Model):
    _inherit = 'memo.model'
    
    helpdesk_memo_config_id = fields.Many2one(
        'memo.config', 
        string="Category", 
        )
    customer_partner_id = fields.Many2one('res.partner', string='Customer ID')
    customer_state_id = fields.Many2one('res.country.state', string='State')
    # customer_district_id = fields.Many2one('multi.branch', string='Customer District')
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
    complaint_duration = fields.Integer('Duration(Days)', compute="get_spent_duration_in_days")
    complaint_description = fields.Text('Complaints')
    deadline_date = fields.Date(
        string="Deadline date", 
        )
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
        'account.move', 
        'memo_invoice_helpdesk_rel',
        'memo_invoice_helpdesk_id',
        'invoice_memo_id',
        string='Invoice', 
        store=True,
        domain="[('type', 'in', ['in_invoice', 'in_receipt']), ('state', '!=', 'cancel')]"
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
                self.memo_type_key = 'helpdesk' # must be hardcorded to helpdesk 
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
    
    @api.depends('complaint_close_date')
    def get_spent_duration_in_days(self):
        for rec in self:
            if rec.complaint_start_date and rec.complaint_close_date:
                duration = rec.complaint_close_date - rec.complaint_start_date
                rec.complaint_duration = duration.days
            else:
                rec.complaint_duration = 0
    
    def confirm_memo_helpdesk(self):
        for complain in self:
            if not complain.complaint_resolution_ids.ids:
                raise ValidationError(
                    'Please add resolution lines'
                )
            complain.complaint_close_date = fields.Date.today()
            complain.confirm_memo(self.employee_id, "")
            
    def forward_memo(self):
        self.complaint_start_date = fields.Date.today()
        res = super(HelpdeskMemoModel, self).forward_memo()
        return res
    
    # def retrieve_dashboard(self):
    #     """
    #     Retrieve dashboard data for the helpdesk memo kanban view
    #     """
    #     self.ensure_one()
    #     result = {
    #         'total_tickets': 0,
    #         'resolved_tickets': 0,
    #         'pending_tickets': 0,
    #         'high_priority': 0,
    #         'urgent': 0,
    #         'avg_resolution_time': 0,
    #     }
        
    #     # Get all helpdesk memos
    #     memos = self.search([('memo_type_key', '=', 'helpdesk')])
        
    #     result['total_tickets'] = len(memos)
    #     result['resolved_tickets'] = sum(memos.mapped('resolved_count'))
    #     result['pending_tickets'] = sum(memos.mapped('pending_count'))
        
    #     # High priority and urgent counts (you'll need to add these fields if not present)
    #     # result['high_priority'] = len(memos.filtered(lambda m: m.priority == 'high'))
    #     # result['urgent'] = len(memos.filtered(lambda m: m.priority == 'urgent'))
        
    #     # Average resolution time in days
    #     closed_memos = memos.filtered(lambda m: m.complaint_close_date)
    #     if closed_memos:
    #         total_duration = sum(closed_memos.mapped('complaint_duration'))
    #         result['avg_resolution_time'] = total_duration / len(closed_memos)
        
    #     return result
    
    def retrieve_dashboard(self):
        """Return aggregated stats for all memos, or for the current user, etc."""
        total = self.search_count([("memo_type_key", "=", "helpdesk")])
        resolved = sum(self.search([("memo_type_key", "=", "helpdesk")]).mapped("resolved_count"))
        pending = sum(self.search([("memo_type_key", "=", "helpdesk")]).mapped("pending_count"))
        return {
            "total_tickets": total,
            "resolved_tickets": resolved,
            "pending_tickets": pending,
        }
        
            
   