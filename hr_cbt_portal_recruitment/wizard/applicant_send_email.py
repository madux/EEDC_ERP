from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ApplicantSendMailInherit(models.TransientModel):
    _inherit = 'applicant.send.mail'

    def action_send(self):
        self.ensure_one()
        without_emails = self.applicant_ids.filtered(lambda a: not a.email_from or (a.partner_id and not a.partner_id.email))
        if without_emails:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The following applicants are missing an email address: %s.") % ', '.join(without_emails.mapped(lambda a: a.partner_name or a.name)),
                }
            }

        for applicant in self.applicant_ids:
            if not applicant.partner_id:
                applicant.partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile,
                })
            
            mail_values = {
                'email_from': self.author_id.email,
                'author_id': self.author_id.id,
                'model': 'hr.applicant',
                'res_id': applicant.id,
                'subject': self.subject,
                'body_html': self.body,
                'auto_delete': True,
                'email_to': applicant.partner_id.email or applicant.email_from,
            }
            
            self.env['mail.mail'].sudo().create(mail_values)

        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'type': 'notification', 'message': _("Emails have been queued for sending."), 'sticky': False}
        }