from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DocMgtConfig(models.Model):
    _name = "doc.mgt.config"
    _description = "Document Management Configuration Stored Data"
    
    memo_type_id = fields.Many2one("memo.type")
    
    
    # def get_res_id(self):
    #     if self.env['doc.mgt.config'].search_count([('id', '=', 1)]):
    #         return 1
    #     else:
    #         return False

    # @api.model
    # def create(self, vals):
    #     if self.search_count([]) > 0:
    #         raise ValidationError("Only one record of doc.mgt.config is allowed.")
    #     return super(DocMgtConfig, self).create(vals)
