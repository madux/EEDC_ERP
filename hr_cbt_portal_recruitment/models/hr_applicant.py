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
        "Test Started", 
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
    linkedin_account = fields.Char("Linkedin")
    specify_personal_personality = fields.Text("Provide Details")
    relationship_type = fields.Selection([
        ('father', 'Father'), 
        ('mother', 'Mother'),
        ('sister', 'Sister'),
        ('spouse', 'Spouse'),
        ('friend', 'Friend'),
        ('uncle', 'Uncle'),
        ('others', 'Others'),
        ], "Relationship Type")
    image_1920 = fields.Image(string="Image", max_width=1024, max_height=1024)
    degree_in_relevant_field = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="Degree in relevant field")
    specifylevel_qualification = fields.Text("Total years of Experience")
    knowledge_description = fields.Text("What is your Knowledge of this Role")
    presentlocation = fields.Char("Present Location")
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
    test_passed = fields.Boolean(string="Test Passed", related="survey_user_input_id.scoring_success")
    scoring_percentage = fields.Float(string="scoring Percentage", related="survey_user_input_id.scoring_percentage")
    scoring_total = fields.Float(string="Scoring Total", related="survey_user_input_id.scoring_total")
    nysc_certificate_link = fields.Char()
    has_professional_certification = fields.Selection([
        ('Yes', 'Yes'), ('No', 'No')], 
        string="Do you have any Professional Certification?",
        default="No")
    professional_certificate_link = fields.Char()
    gender = fields.Char()

    request_id = fields.Many2one('hr.job.recruitment.request', string="Recruitment Request", compute='_compute_request_id', store=True, index=True)

    @api.depends('job_id')
    def _compute_request_id(self):
        requests = self.env['hr.job.recruitment.request'].search([
            ('state', '=', 'recruiting'),
            ('job_id', 'in', self.job_id.ids)])
        for r in self:
            r.request_id = requests.filtered(lambda req: req.job_id == r.job_id)[:1] or False if r.job_id else False


    @api.depends("survey_user_input_id")
    def _compute_cbt_score(self):
        for rec in self:
            if rec.survey_user_input_id and rec.survey_user_input_id.scoring_success:
                rec.test_passed = True
            else:
                rec.test_passed = False 
            

                
