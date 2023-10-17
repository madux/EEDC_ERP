# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields, api, _


class Applicant(models.Model):
    _inherit = "hr.applicant"
    _order = "id asc"
    _rec_name = "partner_name"

    @api.onchange(
        'first_name','middle_name', 'last_name'
        )
    def onchange_of_applicants_name(self):
        fn, mm, ln = "", "", ""
        if self.first_name:
            fn = self.first_name
        if self.middle_name:
            mm = self.middle_name
        if self.last_name:
            ln = self.last_name
        self.partner_name = f'{fn} {mm} {ln}'

    cbt_scheduled_date = fields.Date("CBT Scheduled Date ")
    shared_url = fields.Char("Shared Url", 
                             help="""Used to store the url of the applicant for 
                             cbt: /applicantId/Link i.e /5/213r423wqsffbjmdfcefbgrfvcdfsbgnfbvdvbrgfnhadhfgjr1234""")
    applicant_question_line_ids = fields.One2many(
        'cbt.question.line',
        'hr_applicant_id',
        string="Question line",
        required=False,
    )
    cbt_template_config_id = fields.Many2one(
        'cbt.template.config',
        string="CBT Template",
        required=False,
    )
    survey_user_input_id = fields.Many2one(
        'survey.user_input',
        string="Survey Test",
        required=False,
    )
    test_started = fields.Boolean(
        "Test Start", 
        readonly=True, 
        help="used to check if application test has been set")
    cbt_start_date = fields.Datetime("CBT Start Date")
    cbt_end_date = fields.Datetime("CBT End Date ")
    duration = fields.Integer("Duration")

    current_salary = fields.Float("Current Salary ", group_operator="avg", help="Current Salary")
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    last_name = fields.Char("Last Name")
    has_completed_nysc = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Completed NYSC",default="No")
    know_anyone_at_eedc = fields.Selection([
        ('Yes', 'Yes'), ('No', 'No')],
        string="Know anyone at EEDC?",
        default=False)
    specify_personal_personality = fields.Text("Provide Details")
    degree_in_relevant_field = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Degree in relevant field")
    specifylevel_qualification = fields.Text("Total years of Experience")
    reside_job_location = fields.Selection([('Yes', 'Yes'), ('No', 'No')], 
                                           string="Reside within Job location",
                                           default=False
                                           )
    relocation_plans = fields.Selection(
        [('Yes', 'Yes'), ('No', 'No')], string="Relocation Plans")
    resumption_period = fields.Char("Resumption period, if successful")
    reference_name = fields.Char("Reference name")
    reference_title = fields.Char("Reference Title")
    reference_email = fields.Char("Reference email")
    reference_phone = fields.Char("Reference Phone")
