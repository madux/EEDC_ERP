from odoo import models, fields
from odoo.exceptions import ValidationError

class MemoStageInherit(models.Model):
    _inherit = 'memo.stage'

    # Add the new field to the existing memo.stage model
    approval_role_ids = fields.Many2many(
        "user.role",
        string="Approval Roles",
        help="Users having any of these roles can approve this stage."
    )
    
    

class MemoSubStageLineInherit(models.Model):
    _inherit = 'memo.sub.stage'

    def responsible_approver_right(self):
        user = self.env.user

        direct_employee_approvers = self.approver_ids | \
                                    self.sub_stage_id.approver_ids | \
                                    self.sub_stage_id.memo_config_id.approver_ids
        
        allowed_user_ids = set(direct_employee_approvers.mapped('user_id.id'))

        required_roles = self.sub_stage_id.approval_role_ids
        
        if required_roles:
            role_based_users = self.env['res.users'].search([('role_ids', 'in', required_roles.ids)])
            allowed_user_ids.update(role_based_users.ids)

        if user.id not in allowed_user_ids:
            raise ValidationError("You do not have the required role or are not a designated approver for this stage.")
        
        return True