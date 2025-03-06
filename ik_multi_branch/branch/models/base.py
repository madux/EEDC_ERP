# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'
    branch_ids = fields.Many2many('hr.district', string='Allowed branches')

    @api.model
    def _get_default_branch(self):
        return self.env.user.branch_id

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _branch_default_get(self):
        return self.env.user.branch_id

    branch_id = fields.Many2one('hr.district', string='Branch', default=_branch_default_get)
