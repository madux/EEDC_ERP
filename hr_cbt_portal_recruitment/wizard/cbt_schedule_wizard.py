# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields

 
class CBTscheduleWizard(models.TransientModel):
    _name = "cbt.schedule.wizard"
    _order = "id asc"
    _description = "CBT Wizard Scheduler"
    _rec_name = "survey_id"

    cbt_template_config_id = fields.Many2one(
        'cbt.template.config',
        string="CBT Template",
        required=False,
    )
    survey_id = fields.Many2one(
        'survey.survey',
        string="Test Template",
        required=False,
    )
    email_invite_template = fields.Many2one(
        'mail.template',
        string="Invitation Mail Template",
        required=False,
    )
    applicant_ids = fields.Many2many(
        'hr.applicant',
        'application_cbt_schedult_rel',
        'hr_applicant', 
        'hr_cbt_schedule_id',
        string="Applicants",
    )

    def schedule_action(self):
        """takes all the applicants emails and shares test links to them"""
        return self.survey_id.action_send_survey(self.email_invite_template)
