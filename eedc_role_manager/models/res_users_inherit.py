from odoo import models, fields, api

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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to sync roles after user creation."""
        users = super().create(vals_list)
        users_with_roles = users.filtered('role_ids')
        if users_with_roles:
            users_with_roles._sync_permissions_from_roles()
        return users

    def write(self, vals):
        """Override write to sync roles if role_ids are changed."""
        res = super().write(vals)
        if 'role_ids' in vals:
            self._sync_permissions_from_roles()
        return res

    def _sync_permissions_from_roles(self):
        """
        This is the core synchronization method. It ensures that a user's
        groups and companies match exactly what their assigned roles dictate.
        """
        ownership_model = self.env['user.role.group.ownership']
        
        for user in self:
            desired_groups = user.role_ids.mapped('group_ids')
            desired_companies = user.role_ids.mapped('company_ids')
            
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

            if desired_companies:
                user.company_ids = [(6, 0, desired_companies.ids)]
                if user.company_id not in desired_companies:
                    user.company_id = desired_companies[0].id
                    
        return True
    
    def action_sync_roles_manually(self):
        """Manual action to trigger role sync - useful for testing/troubleshooting."""
        self._sync_permissions_from_roles()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Role synchronization completed successfully.',
                'type': 'success',
                'sticky': False,
            }
        }