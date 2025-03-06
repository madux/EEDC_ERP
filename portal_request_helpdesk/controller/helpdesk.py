# -*- coding: utf-8 -*-
import base64
import json
import logging
import random
from multiprocessing.spawn import prepare
import urllib.parse
from odoo import http, fields
from odoo.exceptions import ValidationError
from odoo.tools import consteq, plaintext2html
from odoo.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
import odoo
import odoo.addons.web.controllers.home as main
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url, is_user_internal
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)
 
class PortalRequestHelpdesk(http.Controller):
    
    # portal_request data_process form post
	@http.route(['/ticket/submission'], type='http', methods=['POST'], website=True, auth="public", csrf=False)
	def ticket_submission_process(self, **post):
		"""
		Returns:
			json: JSON reponse
		"""
		try:
			_logger.info(f'Creating Portal Request data ...{post}')
			helpdesk = request.env['helpdesk.ticket'].sudo()   
			vals = {
				"name": post.get("title"),
				"partner_name": post.get("client_name"),
				"partner_phone": post.get("phone_number"),
				"partner_email": post.get("email_from"),
				"description": post.get("description"),
				"ticket_type_id": int(post.get("ticket_type_id")) if post.get("ticket_type_id") else False,
				"team_id": int(post.get("request_type_id")) if post.get("request_type_id") else False,
				"deadline_date": datetime.strptime(post.get("deadline_date",''), "%m/%d/%Y") if post.get("deadline_date") else False, 
				"request_date": fields.Date.today(),
			}
			_logger.info(f"HELPDESK POST DATA {vals}")
			helpdesk_id = helpdesk.sudo().create(vals)
			 
			## generating attachment
			if 'other_docs' in request.params:
				attached_files = request.httprequest.files.getlist('other_docs')
				for attachment in attached_files:
					file_name = attachment.filename
					datas = base64.b64encode(attachment.read())
					self.generate_attachment(helpdesk_id.ticket_ref, file_name, datas, helpdesk_id.id)
			  
			request.session['ticket_ref'] = helpdesk_id.code
			_logger.info(f"mgbeke POST DATA {helpdesk_id}")
   
			return json.dumps({'status': True, 'message': "Form Submitted!"})
		except Exception as e:
			# _logger.exception('Unexpected Error while generating ticket: %s' % e)
			return json.dumps({'status': False, 'message': 'Unexpected Error while generating ticket: %s' % e})
	
	@http.route(["/portal-helpdesk"], type='http', auth='public', website=True, website_published=True)
	def portal_helpdesk(self):
		vals = {
			"request_type_ids": request.env['helpdesk.team'].sudo().search([('is_published', '=', True)]),
			"ticket_type_ids": request.env['helpdesk.ticket.type'].sudo().search([]),
			"request_date": datetime.strftime(fields.Date.today(), '%m/%d/%Y')
		}
		return request.render("portal_request_helpdesk.portal_helpdesk_form_template", vals)

	@http.route(["/portal-helpdesk-success"], type='http', auth='public', website=True, website_published=True)
	def portal_helpdesk_success(self):
		number = request.session.get('ticket_ref')
		_logger.info(f'stored session code is {number}')
		vals = {
			"code": number
		}
		# request.session.clear()
		return request.render("portal_request_helpdesk.portal_request_helpdesk_success_template", vals)

	def generate_attachment(self, name, title, datas, res_id, model='helpdesk.ticket'):
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