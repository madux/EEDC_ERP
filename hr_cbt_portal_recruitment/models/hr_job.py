# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
 
class HrJob(models.Model):
    _inherit = 'hr.job'
 
    request_id = fields.Many2one('hr.job.recruitment.request', string="Recruitment Request", store=True)
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