# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class AppraisalSystemController(http.Controller):
    @http.route(['/appraisal-system', '/appraisal-system/'], type='http', auth='public', website=True, sitemap=True)
    def page(self, **kwargs):
        return request.render('appraisal_system.appraisal_system_page', {})
    
    @http.route(['/appraisals', '/appraisals/'], type='http', auth='public', website=True, sitemap=True)
    def appraisals(self, **kwargs):
        return request.render('appraisal_system.appraisals_list_page', {})