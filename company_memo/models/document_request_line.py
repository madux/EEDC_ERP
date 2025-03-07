from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DocumentRequestLine(models.Model):
    _name = "document.request.line"
    _description = "Document Request line"

    memo_document_request_id = fields.Many2one(
        "memo.model", 
        string="Request from"
    )
    request_from_document_folder = fields.Many2one(
        "documents.folder", 
        string="Request from"
    )
    request_to_document_folder = fields.Many2one(
        "documents.folder", 
        string="Request document to"
        # domain="[('id', '=', self.dummy_request_from_document_folder_ids)]"
    )
    dummy_request_from_document_folder_ids = fields.Many2many(
        "document.folder",
        string="Dummy Request from IDs"
        )
    
    @api.onchange('request_from_document_folder')
    def suitable_document_ids(self):
        if self.request_from_document_folder:
            user_branch = self.env.user.branch_id.id
            user_branch_ids = self.env.user.branch_ids.ids
            branches = user_branch_ids + [user_branch]
            document_folders = self.env['document.folder'].search([('branch_id', 'in', branches)])
            document_folders = []
            for r in document_folders:
                if r.id != self.request_from_document_folder.id:
                    document_folders.append(r.id)
            self.dummy_request_from_document_folder_ids = [(6, 0, document_folders)]
    
