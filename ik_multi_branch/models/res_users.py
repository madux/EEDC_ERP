from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.constrains('company_id', 'company_ids', 'active')
    def _check_company(self):
       
        for user in self.filtered(lambda u: u.active):
            if user.company_id and user.company_id not in user.company_ids:
                _logger.warning(
                    "Company mismatch for user %s: active company %s not in allowed companies %s. Auto-fixing...",
                    user.name,
                    user.company_id.name,
                    ', '.join(user.company_ids.mapped('name'))
                )
                
                # user.sudo().write({
                #     'company_ids': [(4, user.company_id.id)]
                # })
                
                user.sudo().write({
                    'company_ids': [(6, 0, [user.company_id.id])]
                })
                
                _logger.info(
                    "Fixed: User %s now has company %s in allowed companies",
                    user.name,
                    user.company_id.name
                )
                
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        """When user branch changes, sync with employee and update company."""
        for user in self:
            branch = user.branch_id
            if not branch:
                continue
            
            company = branch.company_id
            if not company:
                continue
            
            user.company_id = company
            
            user.company_ids = [(6, 0, [company.id])]
            
            user.branch_ids = [(6, 0, [branch.id])]
            
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                employee.branch_id = branch
                employee.company_id = company
                
                _logger.info(
                    "Synced user %s with employee: company=%s, branch=%s",
                    user.name, company.name, branch.name
                )