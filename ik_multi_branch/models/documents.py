# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentFolder(models.Model):
    _inherit = 'documents.folder'
    
    branch_id = fields.Many2one('multi.branch', string='Branch')
 