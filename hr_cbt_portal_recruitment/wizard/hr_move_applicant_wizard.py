# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields
from odoo.exceptions import ValidationError

 
class HrApplicantMove(models.TransientModel):
    _name = "hr.applicant.move.wizard"
    _order = "id asc"
    _description = "used this feature to move applicants to the next stage"

    stage_id = fields.Many2one(
        'hr.recruitment.stage',
        required=True,
        string="Stage",
    )
    send_mail = fields.Boolean(
        string="Send Mail?",
    )
    applicant_ids = fields.Many2many(
        'hr.applicant',
        'applicant_move_rel',
        'hr_applicant', 
        'hr_move_schedule_id',
        string="Applicants",
    )
    email_invite_template = fields.Many2one(
        'mail.template',
        string="Mail Template",
        required=False,
    )

    def action_move_applicant(self):
        """moves applicants to selected stage"""
        if self.applicant_ids:
            for rec in self.mapped('applicant_ids'):#.filtered(lambda al: not al.stage_id.hired_stage):
                rec.write({
                    'stage_id': self.stage_id.id
                    })
            self.action_send_mail()
        else:
            raise ValidationError("please ensure to select applicants")

    def action_send_mail(self):
        email_list = self.mapped('applicant_ids').mapped('email_from')
        if email_list:
            self._send_mail(self.email_invite_template, email_list, self.env.user.company_id.email or self.env.user.email)
        else:
            raise ValidationError("Selected applicant(s) Email(s) not found")

    def _send_mail(self, template_id, email_items= None, email_from=None):
        '''Email_to = [lists of emails], Contexts = {Dictionary} '''
        email_to = ','.join([m for m in email_items if m])
        # ir_model_data = self.env['ir.model.data']
        # template_id = ir_model_data.get_object_reference('inseta_etqa', with_template_id)[1]         
        if template_id and email_to:
            template_id.write({'email_to': email_to})
            template_id.send_mail(self.id, True)
            # ctx = dict()
            # ctx.update({
            #     'default_model': 'inseta.learner.register',
            #     'default_res_id': self.id,
            #     'default_use_template': bool(template_id),
            #     'default_template_id': template_id,
            #     'default_composition_mode': 'comment',
            # })
            # template_rec = self.env['mail.template'].browse(template_id)
            # if email_to:
            #     template_rec.write({'email_to': email_to})
            # template_rec.with_context(ctx).send_mail(self.id, True)