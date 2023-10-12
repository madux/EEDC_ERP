# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.misc import clean_context
import logging
import re
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")

class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    applicant_ids = fields.Many2many('hr.applicant', 
                                     'hr_applicants_survey_invite_rel',
                                     'hr_appllicant_id',
                                     'survey_invite_id',
                                     string='Applicants')
    
    def action_invite(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()
        Partner = self.env['res.partner']
        # compute partners and emails, try to find partners for given emails
        valid_partners = self.partner_ids
        langs = set(valid_partners.mapped('lang')) - {False}
        if len(langs) == 1:
            self = self.with_context(lang=langs.pop())
        valid_emails = []
        for email in emails_split.split(self.emails or ''):
            partner = False
            email_normalized = tools.email_normalize(email)
            if email_normalized:
                limit = None if self.survey_users_login_required else 1
                partner = Partner.search([('email_normalized', '=', email_normalized)], limit=limit)
            if partner:
                valid_partners |= partner
            else:
                email_formatted = tools.email_split_and_format(email)
                if email_formatted:
                    valid_emails.extend(email_formatted)

        if not valid_partners and not valid_emails and not self.applicant_ids:
            raise UserError(_("Please enter at least one valid recipient or applicants"))
        
        answers = self._prepare_answers(valid_partners, valid_emails, self.applicant_ids)
        for answer in answers:
            self._send_mail(answer)

        return {'type': 'ir.actions.act_window_close'}
    

    def _prepare_answers(self, partners, emails, applicant_ids=False):
        answers = self.env['survey.user_input']
        existing_answers = self.env['survey.user_input'].search([
            '&', ('survey_id', '=', self.survey_id.id),
            '|',
            ('partner_id', 'in', partners.ids),
            ('email', 'in', emails)
        ])
        partners_done = self.env['res.partner']
        emails_done = []
        if existing_answers:
            if self.existing_mode == 'resend':
                partners_done = existing_answers.mapped('partner_id')
                emails_done = existing_answers.mapped('email')

                # only add the last answer for each user of each type (partner_id & email)
                # to have only one mail sent per user
                for partner_done in partners_done:
                    answers |= next(existing_answer for existing_answer in
                        existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
                        if existing_answer.partner_id == partner_done)

                for email_done in emails_done:
                    answers |= next(existing_answer for existing_answer in
                        existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
                        if existing_answer.email == email_done)

        for new_partner in partners - partners_done:
            answers |= self.survey_id._create_answer(partner=new_partner, check_attempts=False, **self._get_answers_values())
        for new_email in [email for email in emails if email not in emails_done]:
            answers |= self.survey_id._create_answer(email=new_email, check_attempts=False, **self._get_answers_values())

        if applicant_ids:
            for applicant in applicant_ids:
                if applicant.email_from not in emails_done:
                    applicant_email = applicant.email_from
                    survey_input = self.survey_id._create_answer(email=applicant_email, check_attempts=False, **self._get_answers_values())
                    answers |= survey_input
                    applicant.survey_user_input_id = survey_input.id
            # for applicant_email in [email.email_from for email in self.applicant_ids if email not in emails_done]:
            #     answers |= self.survey_id._create_answer(email=applicant_email, check_attempts=False, **self._get_answers_values())
        return answers

    # def action_invite(self):
    #     self.ensure_one()
    #     if self.applicant_id:
    #         survey = self.survey_id.with_context(clean_context(self.env.context))

    #         if not self.applicant_id.response_id:
    #             self.applicant_id.write({
    #                 'response_id': survey._create_answer(partner=self.applicant_id.partner_id).id
    #             })

    #         partner = self.applicant_id.partner_id
    #         survey_link = survey._get_html_link(title=survey.title)
    #         partner_link = partner._get_html_link()
    #         content = _('The survey %(survey_link)s has been sent to %(partner_link)s', survey_link=survey_link, partner_link=partner_link)
    #         body = '<p>%s</p>' % content
    #         self.applicant_id.message_post(body=body)
    #     return super().action_invite()


# class SurveyUserInput(models.Model):
#     _inherit = "survey.user_input"

#     applicant_id = fields.One2many('hr.applicant', 'response_id', string='Applicant')

#     def _mark_done(self):
#         odoobot = self.env.ref('base.partner_root')
#         for user_input in self:
#             if user_input.applicant_id:
#                 body = _('The applicant "%s" has finished the survey.', user_input.applicant_id.partner_name)
#                 user_input.applicant_id.message_post(body=body, author_id=odoobot.id)
#         return super()._mark_done()

#     @api.model_create_multi
#     def create(self, values_list):
#         if 'default_applicant_id' in self.env.context:
#             self = self.with_context(default_applicant_id=False)
#         return super().create(values_list)
