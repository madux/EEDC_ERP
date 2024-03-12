from odoo import models, fields, api, _


class HrApplicantDocuments(models.Model):
    _name = 'hr.applicant.documentation'

    document_type = fields.Many2one('documentation.type')
    document_file = fields.Many2one('ir.attachment', string='Document File')
    # filename = fields.Char("Filename")
    select = fields.Boolean("Confirmed", default=False)
    applicant_submitted_document_file = fields.Many2one('ir.attachment', string='Applicant Document', attachment=True)
    # applicant_filename = fields.Char("Applicant Filename")
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')


class DocumentationType(models.Model):
    _name = 'documentation.type'

    name = fields.Char()
    document_file = fields.Many2one('ir.attachment', string='Document File')