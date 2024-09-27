from odoo.addons.hr_recruitment.wizard.applicant_send_mail import ApplicantSendMail
import psycopg2
from odoo import _
from odoo.exceptions import UserError

class SendEmail(ApplicantSendMail):
    
    def action_send(self):
        self.ensure_one()

        without_emails = self.applicant_ids.filtered(lambda a: not a.email_from or (a.partner_id and not a.partner_id.email))
        if without_emails:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("The following applicants are missing an email address: %s.", ', '.join(without_emails.mapped(lambda a: a.partner_name or a.name))),
                }
            }

        retries = 3
        batch_size = 10

        for batch_start in range(0, len(self.applicant_ids), batch_size):
            batch_applicants = self.applicant_ids[batch_start:batch_start + batch_size]

            for applicant in batch_applicants:
                for attempt in range(retries):
                    try:
                        if not applicant.partner_id:
                            applicant.partner_id = self.env['res.partner'].create({
                                'is_company': False,
                                'type': 'private',
                                'name': applicant.partner_name,
                                'email': applicant.email_from,
                                'phone': applicant.partner_phone,
                                'mobile': applicant.partner_mobile,
                            })

                        applicant.message_post(
                            subject=self.subject,
                            body=self.body,
                            message_type='comment',
                            email_from=self.author_id.email,
                            email_layout_xmlid='mail.mail_notification_light',
                            partner_ids=applicant.partner_id.ids,
                        )
                        break
                    except psycopg2.errors.SerializationFailure:
                        self.env.cr.rollback()
                        if attempt + 1 == retries:
                            raise 
                    except Exception as e:
                        raise UserError(_("Failed to send email: %s") % str(e))