# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields

 
class CBTscheduleWizard(models.TransientModel):
    _name = "cbt.schedule.wizard"
    _order = "id asc"
    _description = "CBT Wizard Scheduler"

    name = fields.Char("Template Name")
    cbt_template_config_id = fields.Many2one(
        'cbt.template.config',
        string="CBT Template",
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
        """takes the cbt_template_config_id and randomly 
        generate question lines of the template for each applicants"""
        pass 
