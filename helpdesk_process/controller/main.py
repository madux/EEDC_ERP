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
 
EEDC_STATES = [
	'Anambra', 'anambra', 
	'Enugu', 'enugu', 
	'Abia', 'abia', 
	'Ebonyi', 'ebonyi', 
	'Imo', 'imo', 
	]
class MemoPortalRequestHelpdesk(http.Controller):
	@http.route(['/customer/ticket/submission'], type='http', methods=['POST'], website=True, auth="public", csrf=False)
	def memo_ticket_submission_process(self, **post):
		try:
			_logger.info(f'Creating Memo Portal Request data ...{post}')
			memo = request.env['memo.model'].sudo() 
			memo_config_obj = request.env['memo.config'].sudo().browse([int(post.get("helpdesk_memo_config_id"))])
			vals = {
				"name": post.get("title"),
				"customer_name": post.get("customer_name"),
				"customer_phone": post.get("customer_phone"),
				"customer_email": post.get("customer_email"),
				"customer_address1": post.get("customer_address1"),
				"customer_address2": post.get("customer_address2"),
				"complaint_description": post.get("complaint_description"),
				"meter_type": post.get("meter_type"),
				"customer_meter_no": post.get("customer_meter_no"),
				"memo_type_key": 'helpdesk',
				"stage_id": memo_config_obj.stage_ids[0].id,
				"helpdesk_memo_config_id": int(post.get("helpdesk_memo_config_id")) if post.get("helpdesk_memo_config_id") else False,
				"memo_setting_id": memo_config_obj.id,
				"district_id": int(post.get("district_id")) if post.get("district_id") else False,
				"customer_state_id": int(post.get("customer_state_id")) if post.get("customer_state_id") else False,
				"deadline_date": datetime.strptime(post.get("deadline_date",''), "%m/%d/%Y") if post.get("deadline_date") else False, 
				"request_date": fields.Date.today(),
			}
			_logger.info(f"Memo HELPDESK POST DATA {vals}")
			memo_id = memo.sudo().create(vals)
			memo_id.compute_config_stages_from_website(memo_config_obj)
			_logger.info(f"Memo GENERATED {memo_id}")
			if 'other_docs' in request.params:
				attached_files = request.httprequest.files.getlist('other_docs')
				for attachment in attached_files:
					file_name = attachment.filename
					datas = base64.b64encode(attachment.read())
					self.generate_attachment(memo_id.code, file_name, datas, memo_id.id)
			  
			request.session['memo_ticket_ref'] = memo_id.code
			_logger.info(f"mgbeke POST DATA {memo_id}")
			return json.dumps({'status': True, 'message': "Form Submitted!"})
		except Exception as e:
			# _logger.exception('Unexpected Error while generating ticket: %s' % e)
			return json.dumps({'status': False, 'message': 'Unexpected Error while generating ticket: %s' % e})
	
	@http.route(["/customerTicket"], type='http', auth='public', website=True, website_published=True)
	def memo_portal_helpdesk(self):
		vals = {
			"request_type_ids": request.env['memo.config'].sudo().search([('memo_key', '=', 'helpdesk')]),
			# "branch_ids": request.env['multi.branch'].sudo().search([]),
			"district_ids": request.env['hr.district'].sudo().search([]),
			"state_ids": request.env['res.country.state'].sudo().search([('country_id.name', 'in', ['Nigeria', 'nigeria']), ('name', 'in', EEDC_STATES)]),
			"request_date": datetime.strftime(fields.Date.today(), '%m/%d/%Y')
		}
		return request.render("helpdesk_process.memo_helpdesk_form_template", vals)

	@http.route(["/customer-ticket-success"], type='http', auth='public', website=True, website_published=True)
	def portal_memo_helpdesk_success(self):
		number = request.session.get('memo_ticket_ref')
		_logger.info(f'stored session code is {number}')
		vals = {
			"code": number
		}
		# request.session.clear()
		return request.render("helpdesk_process.memo_request_helpdesk_success_template", vals)

	def generate_attachment(self, name, title, datas, res_id, model='memo.model'):
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