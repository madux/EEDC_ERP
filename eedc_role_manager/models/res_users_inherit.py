from odoo import models, fields, api, _, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    role_ids = fields.Many2many(
        'user.role', 
        'user_role_users_rel', 
        'user_id', 
        'role_id',
        string='Roles',
        copy=False
    )
    
    branch_ids = fields.Many2many(
        'multi.branch',
        'user_branch_rel',
        'user_id',
        'branch_id',
        string='Branches',
        help="User's assigned branches for approval context"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to sync roles after user creation."""
        users = super().create(vals_list)
        users_with_roles = users.filtered('role_ids')
        if users_with_roles:
            users_with_roles._sync_permissions_from_roles()
            users_with_roles._sync_approvals_from_roles()
        return users

    def write(self, vals):
        """Override write to sync roles and approvals when relevant fields change."""
        users_to_resync_approvals = self.env['res.users']
        if any(field in vals for field in ['role_ids', 'branch_ids']):
            users_to_resync_approvals = self
            
        res = super().write(vals)
        
        if 'role_ids' in vals:
            self._sync_permissions_from_roles()
            
        if users_to_resync_approvals:
            users_to_resync_approvals._sync_approvals_from_roles()
            
        return res

    def _sync_permissions_from_roles(self):
        """
        This is the core synchronization method for groups and companies.
        It ensures that a user's groups and companies match exactly what their assigned roles dictate.
        This method is unchanged from the original implementation to preserve functionality.
        """
        ownership_model = self.env['user.role.group.ownership']
        
        users_to_sync = self.filtered(lambda u: u.id != SUPERUSER_ID)
        _logger.info("Super user ID: {SUPERUSER_ID}......")
        for user in users_to_sync:
            desired_groups = user.role_ids.mapped('group_ids')
            
            current_ownerships = ownership_model.search([('user_id', '=', user.id)])
            groups_managed_by_roles = current_ownerships.mapped('group_id')
            
            groups_to_add = desired_groups - user.groups_id
            if groups_to_add:
                user.write({'groups_id': [(4, group.id) for group in groups_to_add]})

            groups_to_remove = groups_managed_by_roles - desired_groups
            if groups_to_remove:
                user.write({'groups_id': [(3, group.id) for group in groups_to_remove]})

            current_ownerships.filtered(lambda own: own.group_id not in desired_groups).unlink()
            
            for group in desired_groups:
                ownership = ownership_model.search([('user_id', '=', user.id), ('group_id', '=', group.id)])
                roles_granting_group = user.role_ids.filtered(lambda r: group in r.group_ids)
                if ownership:
                    ownership.write({'role_ids': [(6, 0, roles_granting_group.ids)]})
                else:
                    ownership_model.create({
                        'user_id': user.id,
                        'group_id': group.id,
                        'role_ids': [(6, 0, roles_granting_group.ids)]
                    })

            desired_companies = user.role_ids.mapped('company_ids')
            if desired_companies:
                # companies_to_set = desired_companies | user.company_id
                user.company_ids = [(6, 0, desired_companies.ids)]
                if user.company_id not in desired_companies:
                    user.company_id = desired_companies[0].id
                    
        return True

    
    def _sync_approvals_from_roles(self):
        """
        Synchronize memo.stage approver lists based on user's roles, companies and branches.
        """
        MemoStage = self.env['memo.stage']
        ownership_model = self.env['user.role.approval.ownership']

        for user in self.filtered(lambda u: u.employee_id):
            employee = user.employee_id
            approval_roles = user.role_ids.filtered('is_request_approver')

            stages_user_should_approve = self.env['memo.stage']
            if approval_roles:
                potential_stages = MemoStage.search([('approval_role_ids', 'in', approval_roles.ids)])
                for stage in potential_stages:
                    stage_config = stage.memo_config_id
                    stage_company = stage_config.company_id
                    stage_branch = stage_config.branch_id

                    matching_roles = approval_roles & stage.approval_role_ids
                    if not matching_roles:
                        continue

                    should_approve = False
                    for role in matching_roles:
                        # Company check
                        role_allows_company = True
                        if stage_company and role.company_ids:
                            if stage_company not in role.company_ids:
                                role_allows_company = False

                        role_allows_branch = True
                        if stage_branch:
                            if role.branch_ids:
                                if stage_branch not in role.branch_ids:
                                    role_allows_branch = False
                            else:
                                if not user.branch_ids or stage_branch not in user.branch_ids:
                                    role_allows_branch = False
                        else:
                            if role.branch_ids and user.branch_ids and not (role.branch_ids & user.branch_ids):
                                role_allows_branch = False
                            if role.branch_ids and not user.branch_ids:
                                role_allows_branch = False

                        if role_allows_company and role_allows_branch:
                            should_approve = True
                            break

                    if should_approve:
                        stages_user_should_approve |= stage

            current_ownerships = ownership_model.search([
                ('user_id', '=', user.id),
                ('employee_id', '=', employee.id)
            ])
            current_stages = current_ownerships.mapped('stage_id')

            stages_to_add = stages_user_should_approve - current_stages
            stages_to_remove = current_stages - stages_user_should_approve

            for stage in stages_to_add:
                if employee not in stage.approver_ids:
                    stage.write({'approver_ids': [(4, employee.id)]})

                existing = ownership_model.search([
                    ('user_id', '=', user.id),
                    ('employee_id', '=', employee.id),
                    ('stage_id', '=', stage.id)
                ], limit=1)
                if not existing:
                    granting_roles = approval_roles.filtered(lambda r: r in stage.approval_role_ids)
                    ownership_model.create({
                        'user_id': user.id,
                        'employee_id': employee.id,
                        'stage_id': stage.id,
                        'role_ids': [(6, 0, granting_roles.ids)]
                    })

            for stage in stages_to_remove:
                if employee in stage.approver_ids:
                    stage.write({'approver_ids': [(3, employee.id)]})
            if stages_to_remove:
                ownership_model.search([
                    ('user_id', '=', user.id),
                    ('employee_id', '=', employee.id),
                    ('stage_id', 'in', stages_to_remove.ids)
                ]).unlink()

            remaining_ownerships = ownership_model.search([
                ('user_id', '=', user.id),
                ('employee_id', '=', employee.id),
                ('stage_id', 'in', stages_user_should_approve.ids)
            ])
            for ownership in remaining_ownerships:
                granting_roles = approval_roles.filtered(lambda r: r in ownership.stage_id.approval_role_ids)
                ownership.write({'role_ids': [(6, 0, granting_roles.ids)]})

        return True

    def action_sync_roles_manually(self):
        """Manual action to trigger role and approval sync - useful for testing/troubleshooting."""
        self._sync_permissions_from_roles()
        self._sync_approvals_from_roles()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Role and approval synchronization completed successfully.',
                'type': 'success',
                'sticky': False,
            }
        }