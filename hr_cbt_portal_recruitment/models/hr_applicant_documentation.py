from odoo import models, fields, api, _


class HrApplicantDocuments(models.Model):
    _name = 'hr.applicant.documentation'

    document_type = fields.Many2one('documentation.type')
    document_file = fields.Binary(string='Document File', attachment=True)
    filename = fields.Char("Filename")
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')


class DocumentationType(models.Model):
    _name = 'documentation.type'

    name = fields.Char()