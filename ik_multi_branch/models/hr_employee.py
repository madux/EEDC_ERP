# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    branch_id = fields.Many2one('multi.branch', string='Branch')
 