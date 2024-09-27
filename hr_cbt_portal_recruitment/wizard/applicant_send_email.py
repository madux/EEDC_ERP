from odoo import models, fields, api, _
from odoo.exceptions import UserError
import psycopg2
import time
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

        max_retries = 5
        batch_size = 10
        delay = 1  # Initial delay in seconds

        for batch_start in range(0, len(self.applicant_ids), batch_size):
            batch_applicants = self.applicant_ids[batch_start:batch_start + batch_size]
            
            for applicant in batch_applicants:
                for attempt in range(max_retries):
                    try:
                        with self.env.cr.savepoint():
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
                        break  # If successful, break the retry loop
                    except psycopg2.errors.SerializationFailure as e:
                        if attempt + 1 == max_retries:
                            _logger.error(f"Failed to send email to applicant {applicant.id} after {max_retries} attempts: {str(e)}")
                            raise UserError(_("Failed to send email due to database concurrency issues. Please try again later."))
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    except Exception as e:
                        _logger.error(f"Unexpected error while sending email to applicant {applicant.id}: {str(e)}")
                        raise UserError(_("Failed to send email: %s") % str(e))

        return {'type': 'ir.actions.act_window_close'}