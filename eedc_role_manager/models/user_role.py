from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class UserRole(models.Model):
    _name = 'user.role'
    _description = 'User Role'
    _order = 'name'

    name = fields.Char(string='Role Name', required=True, index=True)
    description = fields.Text(string='Description')
    
    group_ids = fields.Many2many(
        'res.groups', 
        'user_role_groups_rel', 
        'role_id', 
        'group_id',
        string='Security Groups',
        help="These are the Odoo security groups this role will grant to users."
    )
    
    company_ids = fields.Many2many(
        'res.company', 
        'user_role_company_rel', 
        'role_id', 
        'company_id',
        string='Allowed Companies',
        help="Users with this role will be approvers for memo stages in these companies only. Leave empty for all companies."
    )
    
    branch_ids = fields.Many2many(
        'multi.branch',
        'user_role_branch_rel',
        'role_id',
        'branch_id',
        string='Allowed Branches',
        help="Users with this role will be approvers for memo stages in these branches only. Leave empty for all branches."
    )
    
    is_request_approver = fields.Boolean(
        string='Is Request Approver?',
        help="Check this if this role designates the user as an approver in the memo request module."
    )
    
    user_ids = fields.Many2many(
        'res.users', 
        'user_role_users_rel', 
        'role_id', 
        'user_id',
        string='Users with this Role'
    )
    
    users_count = fields.Integer(
        compute='_compute_users_count',
        string="Users Count",
        store=True
    )
    limit_to_user_context = fields.Boolean(
        string='Limit to User Context',
        help="If checked, the user will only be assigned as an approver in their specific company and/or branch, ignoring the role's allowed companies/branches."
    )
    
    active = fields.Boolean(default=True)

    @api.depends('user_ids')
    def _compute_users_count(self):
        for role in self:
            role.users_count = len(role.user_ids)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Role name must be unique!')
    ]
    
    def action_view_users(self):
        """Smart button action to view users with this role."""
        self.ensure_one()
        return {
            'name': _('Users with the "%s" Role') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.user_ids.ids)],
            'context': {'create': False}
        }

    def write(self, vals):
        """When role definition changes, sync all users who have this role."""
        res = super().write(vals)
        
        if 'group_ids' in vals or 'company_ids' in vals:
            _logger.info("Role definition changed for %s. Syncing %d users.", 
                        self.mapped('name'), len(self.user_ids))
            self.user_ids._sync_permissions_from_roles()
        
        if any(field in vals for field in ['is_request_approver', 'company_ids', 'branch_ids', 'limit_to_user_context']):
            _logger.info("Role approval settings changed for %s. Syncing approvals for %d users.", 
                        self.mapped('name'), len(self.user_ids))
            self.user_ids._sync_approvals_from_roles()
            
        return res


class RoleGroupOwnership(models.Model):
    """
    This is an internal model to track which groups are granted by roles.
    It prevents accidentally removing a group that was manually added
    or is provided by another role.
    """
    _name = 'user.role.group.ownership'
    _description = 'User Role Group Ownership'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    group_id = fields.Many2one('res.groups', required=True, ondelete='cascade', index=True)
    role_ids = fields.Many2many('user.role')

    _sql_constraints = [
        ('user_group_uniq', 'unique (user_id, group_id)', 
         'A user can only have one ownership record per group.')
    ]


class RoleApprovalOwnership(models.Model):
    """
    Track which memo stage approvals are granted by roles.
    Similar to RoleGroupOwnership but for memo approvals.
    """
    _name = 'user.role.approval.ownership'
    _description = 'User Role Approval Ownership'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one('memo.stage', required=True, ondelete='cascade', index=True)
    role_ids = fields.Many2many('user.role', string='Granting Roles')

    _sql_constraints = [
        ('user_stage_uniq', 'unique (user_id, stage_id)', 
         'A user can only have one ownership record per memo stage.')
    ]