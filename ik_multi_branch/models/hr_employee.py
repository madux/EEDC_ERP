# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    branch_id = fields.Many2one('multi.branch', string='District')
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        for employee in self:
            branch = employee.branch_id
            user = employee.user_id
            if not branch or not user:
                continue

            company = branch.company_id
            if not company:
                raise ValidationError("Selected branch has no company assigned.")

            user.company_id = company
            
            user.company_ids = [(6, 0, [company.id])]
            
            if hasattr(user, 'branch_id'):
                user.branch_id = branch
            user.branch_ids = [(6, 0, [branch.id])]
            
            employee.company_id = company

            _logger.info(
                "Updated user %s to company %s and branch %s",
                user.name, company.name, branch.name
            )

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """When a user is assigned to the employee, sync their branch."""
        for employee in self:
            user = employee.user_id
            if not user:
                continue

            if len(user.branch_ids) == 1:
                employee.branch_id = user.branch_id.id