from odoo import models, fields,_, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class MemoConfig(models.Model):
    _inherit = 'memo.config'
    
    def action_sync_approvers(self):
        """
        Synchronize all approvers for the selected memo configurations.
        This will trigger a full resync of all users who have roles mentioned
        in the approval_role_ids of the stages belonging to these configs.
        """
        config_ids = self.env.context.get('active_ids', [])
        configs = self.browse(config_ids)
        
        stages = self.env['memo.stage'].search([('memo_config_id', 'in', configs.ids)])
        
        roles = stages.mapped('approval_role_ids')
        
        if not roles:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No approval roles found in the selected configurations.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        users = roles.mapped('user_ids').filtered(lambda u: u.id != SUPERUSER_ID)
        
        if not users:
            _logger.info("action_sync_approvers: no users found with approval roles for configs %s", configs.mapped('name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No users assigned to the approval roles in these configurations.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        _logger.info("action_sync_approvers: syncing %d users for %d configs", len(users), len(configs))
        
        for user in users:
            try:
                user.sudo()._sync_approvals_from_roles()
                _logger.info("action_sync_approvers: synced user %s (id=%s)", user.login, user.id)
            except Exception:
                _logger.exception("action_sync_approvers: failed to sync user %s (id=%s)", user.login, user.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Approvers synchronized successfully for %d user(s).') % len(users),
                'type': 'success',
                'sticky': False,
            }
        }
    

class MemoStageInherit(models.Model):
    _inherit = 'memo.stage'

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