# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields
from odoo.exceptions import ValidationError

  
class CheckListWizard(models.TransientModel):
	_name = "checklist.setup.wizard"
	_order = "id asc"
	_description = "used to upload the required checklist"

	def get_default_document_types(self):
		documentation_types = self.env['documentation.type'].search([])
		return documentation_types.ids if documentation_types else False
	
	documentation_type_ids = fields.Many2many(
		'documentation.type',
		required=True,
		string="Documentation",
		default=lambda self: self.get_default_document_types()
	)
	applicant_ids = fields.Many2many(
		'hr.applicant',
		'applicant_checklist_rel',
		'hr_applicant', 
		'hr_checklist_id',
		string="Applicants",
	)

	def action_send_checklist(self):
		if self.applicant_ids and self.documentation_type_ids:
			for rec in self.mapped('applicant_ids'):
				# rec.write({
				# 			'applicant_documentation_checklist': [(3, re.id) for re in rec.applicant_documentation_checklist]
				# 			})
				# already_existing_data = rec.mapped('applicant_documentation_checklist').filtered(
				# 	lambda s: s.document_type.id in self.documentation_type_ids.ids and s.applicant_submitted_document_file == False
				# )
				'''Checks if the document type is already existing with data'''
				if rec.applicant_documentation_checklist:
					rec.write({
						'applicant_documentation_checklist': [(3, re.id) for re in rec.applicant_documentation_checklist]
						})
				rec.write({
					'applicant_documentation_checklist': [(0, 0, {
						'document_type': ch.id, 
						'document_file': ch.document_file.id,
						'applicant_id': rec.id,
						'is_compulsory': ch.is_compulsory,
						}) for ch in self.documentation_type_ids]
					})

				rec.send_checklist([rec.id])
		else:
			raise ValidationError("please ensure to select applicants and documents")
