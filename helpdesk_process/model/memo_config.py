from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)



class HelpdeskMemoConfig(models.Model):
    _inherit = 'memo.config'
    
    task_count = fields.Integer(
        string='Total Tasks',
        compute="_compute_task_stats",
        help="Total of all tickets",
        store=True
    )
    resolved_count = fields.Integer(
        string='Resolved Tasks',
        compute="_compute_task_stats",
        help="All Completed tickets",
        store=True
    )
    pending_count = fields.Integer(
        string='Pending Tasks',
        compute="_compute_task_stats",
        help="All tickets in Sent (not moving)",
        store=True
    )
    unattended_count = fields.Integer(
        string='Unattended Tasks',
        compute="_compute_task_stats",
        help="All submit / refused tickets",
        store=True
    )

    @api.depends('memo_type')
    def _compute_task_stats(self):
        for memo in self:
            resolved_count, pending_count, unattended_count = 0, 0, 0
            '''this is all memo records that has the configuration of self'''
            resolutions = self.env['memo.model'].search([('helpdesk_memo_config_id', '=', memo.id)])
            memo.task_count = len(resolutions.ids)
            for rec in resolutions:
                if rec.state in ['Done', 'done']:
                    resolved_count += 1
                elif rec.state in ['Sent', 'Approve', 'Approve2']:
                    pending_count += 1
                else:
                    # tickets in refuse and draft / submitted
                    unattended_count += 1
                    
            memo.resolved_count = resolved_count
            memo.pending_count = pending_count
            memo.unattended_count = unattended_count
    
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
        
            
   