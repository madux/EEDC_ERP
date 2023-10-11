# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields


class CBTAnswerLine(models.Model):
    _name = "cbt.answer.line.option"
    _order = "id asc"
    _description = "CBT answer line"

    name = fields.Char("Description")
    is_answer = fields.Char("Sequence")
    code = fields.Char("Code")

class CBTQuestionLine(models.Model):
    _name = "cbt.question.line"
    _order = "id asc"
    _description = "CBT question line"

    sequence = fields.Char("Sequence")
    type = fields.Selection([
          ('radio', 'Radio'), 
          ('text', 'Text'), 
          ('check', 'Checkbox')], string="Type", default='radio')

    answer_line_ids = fields.One2many(
        'cbt.answer.line.option',
        'cbt_question_line_id',
        string="Answer line",
        required=True,
    )
    code = fields.Char("Code")
  
class CBTTemplateConfig(models.Model):
    _name = "cbt.template.config"
    _order = "id asc"
    _description = "CBT Template configuration"

    name = fields.Char("Template Name")
    active = fields.Boolean("Active")
    question_ids = fields.One2many(
        'cbt.question.line',
        'cbt_template_config_id',
        string="Question line",
        required=True,
    )

    def activate_button(self):
        pass 
