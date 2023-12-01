# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
# from odoo.tools import mute_logger
# from odoo.tools.translate import html_translate
 
class HrJob(models.Model):
    _inherit = 'hr.job'
 
    datetime_publish = fields.Date("Date Published")
    close_date = fields.Date("Closing Date")

    @api.onchange('website_published')
    def onchange_website_published(self):
        today = fields.Date.today()
        for rec in self:
            if rec.website_published:
                rec.datetime_publish = today
                rec.close_date = today + relativedelta(days=10)

    # @api.onchange('datetime_publish')
    # def onchange_datetime_publish(self):
    #     today = fields.Date.today()
    #     for rec in self:
    #         if rec.datetime_publish:
    #             rec.close_date = self.datetime_publish + relativedelta(day=5)

    @api.onchange('close_date')
    def ensure_close_date_is_greater(self):
        if self.close_date:
            if self.close_date and not self.datetime_publish:
                self.close_date = False
                return {
                    'warning': {
                        'title': "Validation",
                        'message': "Please Ensure to add Publish Date",
                    }
                }

            if self.close_date < self.datetime_publish:
                self.close_date = False
                return {
                    'warning': {
                        'title': "Validation",
                        'message': "End date cannot be lesser than Publish Date",
                    }
                }
            

    job_section_descriptions = fields.Many2many('description.sections')

    # @api.model
    # @mute_logger('odoo.addons.base.models.ir_qweb')
    # def _get_default_website_description(self):
    #     sections = self.env['description.sections'].sudo().search([])

    #     template = self.env['ir.qweb']._render(
    #         "website_hr_recruitment.default_website_description",
    #         {'job_section_descriptions': sections},
    #         raise_if_not_found=False
    #     )

    #     return template
    
    # website_description = fields.Html(
    #     'Website description', translate=html_translate,
    #     default=_get_default_website_description, prefetch=True,
    #     sanitize_overridable=True,
    #     sanitize_attributes=False, sanitize_form=False)


    class hrJobDescriptionSection(models.Model):
        _name = 'description.sections'

        title = fields.Char()
        job_descriptions = fields.One2many('job.descriptions', 'section_description')

    class hrJobDescriptions(models.Model):
        _name = 'job.descriptions'

        description = fields.Char()
        section_description = fields.Many2one('description.sections')

