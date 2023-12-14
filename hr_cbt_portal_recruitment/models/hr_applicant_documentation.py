from odoo import models, fields, api, _


class HrApplicantDocuments(models.Model):
    _name = 'hr.applicant.documentation'

    # document_type = fields.Selection([
    #     ('degree_cert', 'Degree Certificate'),
    #     ('nysc_cert', 'NYSC Certificate'),
    #     ('high_school_cert', 'High School Certificate'),
    #     ('birth_cert', 'Birth Certificate'),
    # ], string='Document Type', required=True)
    document_type = fields.Many2one('documentation.type')
    document_file = fields.Binary(string='Document File', attachment=True)
    filename = fields.Char("Filename")
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')


class DocumentationType(models.Model):
    _name = 'documentation.type'

    name = fields.Char()