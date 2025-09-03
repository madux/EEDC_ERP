from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# class ResourceEmployeeLeave(models.AbstractModel):
#     _inherit = "resource.employee.leave.reliever"
#     _description = "Resource Employee leave Reliever"
    
#     administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    
    
    
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")
    legacy_id = fields.Integer(string="legacy_id")
    external_id = fields.Char(string="External ID")
    leave_reliever_memo_stage_ids = fields.Char(string="Memo stages reliever is assigned")
    maximum_cash_advance_limit = fields.Integer(
        string="Maximum Limit Cash Advance", 
        default=5
        )
    leave_reliever = fields.Many2one(
        'hr.employee', 
        string="Leave Reliever",  
        )
    
    def reset_leave_reliever(self):
        stage_obj = self.env['memo.stage'].sudo()
        for rec in self:
            if not rec.leave_reliever :
                raise ValidationError("No relieve found to update")
            if rec.leave_reliever_memo_stage_ids:
                slms = eval(rec.leave_reliever_memo_stage_ids)
                for st in slms:
                    st_id = stage_obj.browse([st])
                    st_id.update({
                        'approver_ids': [(3, rec.leave_reliever.id), (4,rec.id)]
                    })
    
    
    
    # company_id = fields.Many2one(
    #     'res.company',
    #     string="Company",
    #     default=lambda self: self.env.user.company_id.id,
    #     compute="compute_related_user_company"
    # )
    
    # @api.depends('user_id')
    # def compute_related_user_company(self):
    #     for rec in self:
    #         current_company = rec.company_id if rec.company_id else False 
    #         if rec.user_id:
    #             rec.company_id = rec.user_id.company_id.id
    #         else:
    #             rec.company_id = current_company.id