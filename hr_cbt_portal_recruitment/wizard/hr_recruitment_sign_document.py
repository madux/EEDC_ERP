# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command


class HrRecruitmentSignDocumentWizard(models.TransientModel):
    _inherit = 'hr.recruitment.sign.document.wizard'
    _description = 'Sign document in recruitment'

     
    applicant_ids = fields.Many2many(
        'hr.applicant',
        string="Applicants"
        )
    
     
    def validate_signature(self):
        self.ensure_one()

        sign_request = self.env['sign.request']
        if not self.check_access_rights('create', raise_exception=False):
            sign_request = sign_request.sudo()

        sign_values = []
        sign_templates_applicant_ids = self.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 1)
        sign_templates_both_ids = self.sign_template_ids - sign_templates_applicant_ids

        for sign_template_id in sign_templates_applicant_ids:
            sign_values.append((
                sign_template_id,
                [{
                    'role_id': self.applicant_role_id.id,
                    'partner_id': self.partner_id.id
                }]
            ))
        for sign_template_id in sign_templates_both_ids:
            second_role = sign_template_id.sign_item_ids.responsible_id - self.applicant_role_id
            sign_values.append((
                sign_template_id,
                [{
                    'role_id': self.applicant_role_id.id,
                    'partner_id': self.partner_id.id
                }, {
                    'role_id': second_role.id,
                    'partner_id': self.responsible_id.partner_id.id
                }]
            ))

        sign_requests = self.sudo().env['sign.request'].create([{
            'template_id': sign_request_values[0].id,
            'request_item_ids': [Command.create({
                'partner_id': signer['partner_id'],
                'role_id': signer['role_id'],
            }) for signer in sign_request_values[1]],
            'reference': _('Signature Request - %s', sign_request_values[0].name),
            'subject': self.subject,
            'message': self.message,
            'attachment_ids': [(4, attachment.copy().id) for attachment in self.attachment_ids], # Attachments may not be bound to multiple sign requests
        } for sign_request_values in sign_values])
        sign_requests.message_subscribe(partner_ids=self.cc_partner_ids.ids)

        if not self.check_access_rights('write', raise_exception=False):
            sign_requests = sign_requests.sudo()

        for sign_request in sign_requests:
            sign_request.toggle_favorited()

        if self.responsible_id and sign_templates_both_ids:
            signatories_text = _('%s and %s are the signatories.', self.partner_id.display_name, self.responsible_id.display_name)
        else:
            signatories_text = _('Only %s has to sign.', self.partner_id.display_name)
        record_to_post = self.applicant_id
        record_to_post.message_post_with_view(
            'hr_recruitment_sign.message_signature_request',
            values={
                'user_name': self.env.user.display_name,
                'document_names': self.sign_template_ids.mapped('name'),
                'signatories_text': signatories_text
            }
        )

        if len(sign_requests) == 1 and self.env.user.id == self.responsible_id.id:
            return sign_requests.go_to_document()
        return True
