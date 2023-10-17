from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
# from odoo.addons.eha_website.controllers.controllers import EhaWebsite
import logging
import base64
import json
from datetime import date, datetime
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

class JobPortal(WebsiteSale):
    
    # @http.route()
    # def complete_recruitment(self, **post):
    #     """
    #     Returns:
    #         json: JSON reponse
    #     """
    #     _logger.info(f'Creating Applicants detailss ...{int(post.get("job_id"))}')
    #     job_id = post.get("job_id")
    #     email_from = post.get("email_from")
    #     job_id = job_id and int(job_id)
    #     job = request.env['hr.job'].sudo().search([('id', '=', job_id)])
    #     if not job.allow_to_appy_in_period(email_from):
    #         return request.render("eha_website_hr_recruitment.job_already_applied")
    #     else:
    #         return super().complete_recruitment(**post)
        

    # generate attachment
    def generate_attachment(self, name, title, datas, res_id, model='hr.applicant'):
        attachment = request.env['ir.attachment'].sudo()
        attachment_id = attachment.create({
            'name': f'{title} for {name}',
			'type': 'binary',
			'datas': datas,
			'res_name': name,
			'res_model': model,
			'res_id': res_id,
		})
        return attachment_id

    @http.route([
        '/complete/recruitment',
        '/complete/recruitment/<model("hr.applicant"):job_id>'
        ], type='http', auth="public", website=True)
    def complete_recruitment(self, **post):
        """
        Returns:
            json: JSON reponse
        """
        job_id = post.get("job_id")
        email_from = post.get("email_from")
        job_id = job_id and int(job_id)
        job = request.env['hr.job'].sudo().search([('id', '=', job_id)], limit=1)
        domain = [
            ('job_id', '=', job.id), 
            ('email_from', '=', email_from),
            ('create_date', '>=', job.datetime_publish),
            ('create_date', '<=', job.close_date)
            ('active', '=', True)
            ]
        applicants = self.env['hr.applicant'].sudo().search(domain)
        
        if date.today() > job.close_date:
            return request.render("hr_cbt_portal_recruitment.job_already_closed")
        
        elif applicants:
            """Checks if the period of submission falls between the publish and date"""
            return request.render("hr_cbt_portal_recruitment.recruitment_job_already_applied")
        else:
            _logger.info(f'Creating Applicants detailss ...{int(post.get("job_id"))}')
            applicant_name =  f'{post.get("partner_name")} {post.get("middle_name")} {post.get("last_name")}'
            vals = {
                "partner_name": applicant_name,
                "name": f'Application for {applicant_name}',
                "first_name": post.get('partner_name'),
                "last_name": post.get("last_name"),
                "middle_name": post.get("middle_name", ""),
                "job_id": int(post.get("job_id")) if post.get("job_id") else False,
                "email_from": post.get("email_from", ""),
                "partner_phone": post.get("partner_phone", ""),
                "description": post.get("description", ""),
                "current_salary": post.get("current_salary",""),
                "salary_proposed": post.get("current_salary",""),
                "salary_expected": post.get("salary_expection",""),
                "has_completed_nysc": 'Yes' if post.get("completed_nysc_yes") == 'on' else 'No',
                "know_anyone_at_eha": 'Yes' if post.get("personal_capacity_headings_yes") == 'on' else 'No',
                "degree_in_relevant_field": 'Yes' if post.get("level_qualification_header_yes") == 'on' else 'No',
                "reside_job_location": 'Yes' if post.get("reside_job_location_yes") == 'on' else 'No',
                "relocation_plans": 'Yes' if post.get("relocation_plans_yes") == 'on' else 'No',
                "resumption_period": post.get("periodselect",""),
                "reference_name": post.get("reference_name",""),
                "reference_title": post.get("reference_title",""),
                "reference_email": post.get("reference_email",""),
                "reference_phone": post.get("reference_phone",""),
                "specify_personal_personality": post.get("specify_personal_personality",""),
                "specifylevel_qualification": post.get("specifylevel_qualification",False),
                # attachment_ids
            }
            applicant = request.env['hr.applicant'].sudo().create(vals)
            _logger.info('Applicant record Successfully Registered!')

            _logger.info(f"POST DATA {vals}")
            if post.get("Resume"):
                # file_name = post.get("Resume").filename
                data = base64.b64encode(post.get("Resume").read())
                resume_attachment = self.generate_attachment(applicant_name, 'Resume', data, applicant.id)
                # vals.update({'attachment_ids': [(6, 0, [attachment.id])]})
            
            if 'other_docs' in request.params:
                attached_files = request.httprequest.files.getlist('other_docs')
                for attachment in attached_files:
                    file_name = attachment.filename
                    datas = base64.b64encode(attachment.read())
                    other_docs_attachment = self.generate_attachment(applicant_name, file_name, datas, applicant.id)
            
            # applicant = request.env['hr.applicant'].sudo().create(vals)
            # _logger.info('Applicant record Successfully Registered!')
            return http.request.render('website_hr_recruitment.thankyou')