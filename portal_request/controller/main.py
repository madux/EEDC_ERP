# -*- coding: utf-8 -*-
import base64
import json
import logging
from multiprocessing.spawn import prepare
import time
import random
import ast

import requests 
from odoo import http, fields
from odoo.exceptions import ValidationError
from odoo.http import request
from datetime import date, datetime


_logger = logging.getLogger(__name__)


def format_to_odoo_date(date_str: str) -> str:
	"""Formats date format mm/dd/yyyy eg.07/01/1988 to %Y-%m-%d
		OR  date format yyyy/mm/dd to  %Y-%m-%d
	Args:
		date (str): date string to be formated

	Returns:
		str: The formated date
	"""
	if not date_str:
		return

	data = date_str.split('/')
	if len(data) > 2 and len(data[0]) ==2: #format mm/dd/yyyy
		try:
			mm, dd, yy = int(data[0]), int(data[1]), data[2]
			if mm > 12: #eg 21/04/2021" then reformat to 04/21/2021"
				dd, mm = mm, dd
			if mm > 12 or dd > 31 or len(yy) != 4:
				return
			return f"{yy}-{mm}-{dd}"
		except Exception:
			return
	
class PortalRequest(http.Controller):
	
	@http.route(["/portal-request"], type='http', auth='user', website=True, website_published=True)
	def portal_request(self):
		"""Request portal for employee / portal users
		"""
		vals = {
			# "product_ids": request.env["product.product"].sudo().search([
			# 	('detailed_type', 'in', ['consu', 'product'])
			# 	]),
			"district_ids": request.env["hr.district"].sudo().search([]),
		}
		return request.render("portal_request.portal_request_template", vals)
	
	@http.route(["/portal-success"], type='http', auth='user', website=True, website_published=True)
	def portal_success(self):
		"""Request portal for employee / portal users
		"""
		memo_number = request.session.get('memo_ref')
		vals = {
			"memo_id": memo_number
		}
		# request.session.clear()
		return request.render("portal_request.portal_request_success_template", vals)

	@http.route(['/portal-request-product'], type='http', website=True, auth="user", csrf=False)
	def get_portal_product(self, **post):
		productItems = json.loads(post.get('productItems'))
		request_type_option = post.get('request_type')
		_logger.info(f'productitemmms {productItems}')
		domain = [
			('detailed_type', 'in', ['consu', 'product']), ('id', 'not in', [int(i) for i in productItems])
			]
		if request_type_option and request_type_option == "vehicle_request":
			domain = [('is_vehicle_product', '=', True), ('detailed_type', 'in', ['service']), ('id', 'not in', [int(i) for i in productItems])]
		products = request.env["product.product"].sudo().search(domain)
		return json.dumps({
			"results": [{"id": item.id,"text": f'{item.name} {item.id}', 'qty': item.qty_available} for item in products],
			"pagination": {
				"more": True,
			}
		})
	
	@http.route(['/check_staffid/<staff_num>'], type='json', website=True, auth="user", csrf=False)
	def check_staff_num(self, staff_num):
		"""Check staff Identification No.
		Args:
			staff_num (str): The Id No to be validated
		Returns:
			dict: Response
		"""
		_logger.info('Checking Staff ID No ...')
		user = request.env.user
		# ('user_id', '=', user.id)
		if staff_num:
			employee = request.env['hr.employee'].sudo().search(
			[('employee_number', '=', staff_num),('active', '=', True)], limit=1) 
			if employee:
				return {
					"status": True,
					"data": {
						'name': employee.name,
						'phone': employee.work_phone or employee.mobile_phone,
						'work_email': employee.work_email,
					},
					"message": "", 
					}
			else:
				return {
					"status": False,
					"data": {
						'name': "",
						'phone': "",
						'work_email': "",
					},
					"message": "Employee with staff ID provided does not exist. Contact Admin", 
					}
			
	@http.route(['/check_order'], type='json', website=True, auth="user", csrf=False)
	def check_order(self, **post):
		staff_num = post.get('staff_num')
		existing_order = post.get('existing_order')
		# staff_num, existing_order
		"""Check existing order No.
		Args:
			existing_order (str): The Id No to be validated
			staff num (str): staff num of the employee 
		Returns:
			dict: Response
		"""
		_logger.info('Checking check_order No ...')
		user = request.env.user 
		if staff_num:
			memo_request = request.env['memo.model'].sudo().search(
			[
				('employee_id.employee_number', '=', staff_num),
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
				('code', '=ilike', existing_order)
			], 
			limit=1) 
			if memo_request: 
				return {
					"status": True,
					"data": {
						'name': memo_request.employee_id.name,
						'phone': memo_request.employee_id.work_phone or memo_request.employee_id.mobile_phone,
						'state': 'Draft' if memo_request.state == 'submit' else 'Waiting For Payment / Confirmation' if memo_request.state == 'Approve' else 'Approved' if memo_request.state == 'Approve2' else 'Done' if memo_request.state == 'Done' else 'Refused',
						'work_email': memo_request.employee_id.work_email,
						'subject': memo_request.name,
						'description': memo_request.description,
						'amount': memo_request.amountfig,
						'district_id': memo_request.employee_id.ps_district_id.id,
						'request_date': memo_request.date.strftime("%m/%d/%Y") if memo_request.date else "",
						'product_ids': [
							{'id': q.product_id.id, 
							'name': q.product_id.name if q.product_id else q.description, 
							'qty': q.quantity_available
							} 
							for q in memo_request.product_ids
						]
					},
					"message": "", 
					}
			else:
				return {
					"status": False,
					"data": {
						'name': "",
						'phone': "",
						'work_email': "",
						'subject': "",
						'description': "",
						'district_id': "",
						'request_date': "",
						'product_ids': "",
					},
					"message": "Existing order ID with staff ID does not exist. Contact Admin", 
					}
		

		# portal_request data_process form post
	@http.route(['/portal_data_process'], type='http', methods=['POST'],  website=True, auth="user", csrf=False)
	def portal_data_process(self, **post):
		"""
		Returns:
			json: JSON reponse
		"""
		_logger.info(f'Creating Portal Request data ...{post}')
		employee_id = request.env['hr.employee'].sudo().search([
			('user_id', '=', request.env.uid), 
			('employee_number', '=', post.get('staff_id'))], limit=1)
		if not employee_id:
			_logger.info(f'Employee not found')
			return json.dumps({'status': False, 'message': "No employee record found for staff id provided"})
		existing_request  = post.get("selectTypeRequest")
		existing_order = post.get("existing_order")
		memo_id = False
		if existing_request == "existing":
			_logger.info(f'existing found')
			memo_id = request.env['memo.model'].sudo().search([
			('employee_id', '=', employee_id.id), 
			('code', '=', existing_order)], limit=1)
			if not memo_id:
				_logger.info(f'memo not found')
				return json.dumps({'status': False, 'message': "No existing request found for the employee"})
		district_id =False 
		if post.get("selectDistrict"):
			district = request.env['hr.district'].sudo().browse([int(post.get("selectDistrict"))])
			if district:
				district_id = district.id 
			else:
				district_id = memo_id.district_id.id
		
		vals = {
			"employee_id": employee_id.id,
			"memo_type": "Payment" if post.get("selectRequestOption") == "payment_request" else post.get("selectRequestOption") if post.get("selectRequestOption") else "Internal",
			"email": post.get("email_from"),
			"phone": post.get("phone_number"),
			"name": post.get("subject"),
			"description": post.get("description"),
			"amountfig": post.get("amount_fig"),
			"date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(), #format_to_odoo_date(post.get("request_date",'')),
			"leave_start_date": datetime.strptime(post.get("leave_start_date",''), "%m/%d/%Y") if post.get("leave_start_date") else fields.Date.today(),
			# format_to_odoo_date(post.get("leave_start_date",'')),
			"leave_end_date": datetime.strptime(post.get("leave_end_date",''), "%m/%d/%Y") if post.get("leave_start_date") else fields.Date.today(),
			# format_to_odoo_date(post.get("leave_end_date",'')),
			"district_id": district_id, #int(post.get("selectDistrict")) if post.get("selectDistrict") else memo_id.district_id.id if memo_id else False,
			}
		_logger.info(f"POST DATA {vals}")
		_logger.info(f"""Accreditation ggeenn ===>  {json.loads(post.get('productItems'))}""")
		productItems = []
		productItems = json.loads(post.get('productItems'))
		memo_obj = request.env['memo.model']
		if not memo_id:
			_logger.info("Memo id creating")
			memo_id = memo_obj.sudo().create(vals)
		else:
			_logger.info("Memo id updating")
			memo_id.sudo().write(vals)
		if productItems:
			_logger.info(f'PRODUCT IDS IS HERE {productItems}')
			self.generate_request_line(productItems, memo_id) # LA
		# memo_id.action_submit_button()
		request.session['memo_ref'] = memo_id.code
		_logger.info('Successfully Registered!')
		return json.dumps({'status': True, 'message': "Form Submitted!"})
	
	def generate_request_line(self, product_items, memo_id):
		memo_id.sudo().write({'product_ids': False})
		for rec in product_items:
			_logger.info(f"PRODUCT IDS=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec.get('product_id')}")
			product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
			if product_id:
				request.env['request.line'].sudo().create({
					'memo_id': memo_id.id,
					'product_id': int(rec.get('product_id')) if rec.get('product_id') else False,
					'quantity_available': float(rec.get('qty')) if rec.get('qty') else 0,
					'description': f"Request: {product_id.description or product_id.name}",
				})

	def get_pagination(self, page):
		sessions = request.session  
		session_start_limit = sessions.get('start')
		session_end_limit = sessions.get('end')
		if page == "next":
			s = session_end_limit 
			e = session_end_limit + 10
		elif page == 'prev': 
			# e.g start 20 , end 30
			s = session_start_limit - 10
			e = session_end_limit - 10
			# sessions['start'] = s 
			# sessions['end'] = e
		else:
			s = 0 
			e = 10
		return s, e

	@http.route(['/my/requests', '/my/requests/<string:type>', '/my/requests/page/<string:page>'], type='http', auth="user", website=True)
	def my_requests(self, type=False, page=False):
		"""This route is used to call the requesters or user records for display
		page: the pagination index: prev or next
		"""
		user = request.env.user
		sessions = request.session
		if not page: 
			sessions['start'] = 0 
			sessions['end'] = 10
		
		memo_type = ['payment_request', 'Loan'] if type in ['payment_request', 'Loan'] \
			else ['soe', 'cash_advance'] if type in ['soe', 'cash_advance'] \
				else ['leave_request'] if type in ['leave_request'] \
					else ['Internal', 'procurement_request', 'vehicle_request', 'material_request'] \
						if type in ['Internal', 'procurement_request', 'vehicle_request', 'material_request'] \
							else ['Internal', 'procurement_request', 'vehicle_request', 'material_request', 'leave_request', 'soe', 'cash_advance', 'payment_request', 'Loan']
		request_id = request.env['memo.model'].sudo()
		domain = [
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
			]
		domain += [
			('memo_type', 'in', memo_type),
		]
		start, end = self.get_pagination(page)# if page else False, False
		_logger.info(f"Session storage is {sessions.get('start')} {sessions.get('end')}")
		requests = request_id.search(domain)
		if requests:
			requests = requests[start:end]# if page else request_id.search(domain)
			sessions['start'] = start
			sessions['end'] = end 
		else:
			requests = False
		values = {'requests': requests}
		return request.render("portal_request.my_portal_request", values)
	
	@http.route('/my/request/view/<int:id>', type='http', auth="user", website=True)
	def my_single_request(self, id):
		"""This route is used to call the requesters or user record for display"""
		user = request.env.user
		request_id = request.env['memo.model'].sudo()
		domain = [
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
				('id', '=', id),
			]
		requests = request_id.search(domain, limit=1)
		values = {'req': requests}
		return request.render("portal_request.request_form_template", values)
	
	@http.route('/my/request/cancel/<int:id>', type='http', auth="user", website=True)
	def cancel_my_request(self, id):
		user = request.env.user
		request_id = request.env['memo.model'].sudo()
		domain = [
				('employee_id.user_id', '=', user.id),
				('id', '=', id),
			]
		requests = request_id.search(domain, limit=1)
		requests.write({'state': 'submit'})
		return request.redirect('/my/request/view/%s' %(requests.id))


	# def generate_request_line(self, elective_dicts):
	# 	pass
	# 	"""
	# 		# elective_dicts ==> [{'3': ['12', '11', '14']}]
	# 		# register_obj ==> assessor or moderator or provider obj
	# 	"""
	# 	_logger.info(f"Raw items = = , {elective_dicts}")
	# 	convert_elective_dicts = json.loads(elective_dicts)
	# 	_logger.info(f"Converted elective_dicts = = >, {convert_elective_dicts}")
	# 	if convert_elective_dicts:
	# 		for rec in convert_elective_dicts: # [{'3': [3, 45, 667]}]
	# 			for qual, elective_unit in rec.items(): # {'3': [3, 45, 667]}
	# 				if qual and elective_unit:
	# 					qualification_elective_lists = []
	# 					for units in elective_unit:
	# 						vals = {
	# 						'qualification_id': int(qual),
	# 						'qualification_unit_standard_id': int(units)
	# 							}
	# 						# if regtype=="assessor":
	# 						# 	vals.update({
	# 						# 		'assessor_register_id': register_obj.id
	# 						# 	})
	# 						# elif regtype=="moderator":
	# 						# 	vals.update({
	# 						# 		'moderator_register_id': register_obj.id
	# 						# 	})
	# 						if regtype=="provider":
	# 							vals.update({
	# 								'provider_register_id': register_obj.id
	# 							})
	# 						qualification_elective_lists.append(vals)
	# 					unit_standards = self.generate_compulsory_qualification_units(qual)
	# 					if unit_standards:
	# 						for un in unit_standards:
	# 							# building compulsory unit standard
	# 							vals = {
	# 							'qualification_id': int(qual),
	# 							'qualification_unit_standard_id': un,
	# 							}
	# 							# if regtype=="assessor":
	# 							# 	vals.update({
	# 							# 		'assessor_register_id': register_obj.id
	# 							# 	})
	# 							# elif regtype=="moderator":
	# 							# 	vals.update({
	# 							# 		'moderator_register_id': register_obj.id
	# 							# 	})
	# 							if regtype=="provider":
	# 								vals.update({
	# 									'provider_register_id': register_obj.id
	# 								})
	# 							qualification_elective_lists.append(vals)
	# 							# if regtype=="assessor":
	# 							# 		register_obj.assessor_qualification_ids = [(0, 0, {
	# 							# 		'assessor_register_id': register_obj.id,
	# 							# 		'qualification_id': int(qual),
	# 							# 		'assessor_qualification_unit_standards':  [(0, 0, val) for val in qualification_elective_lists],
	# 							# 	})]
	# 							# elif regtype=="moderator":
	# 							# 	register_obj.moderator_qualification_ids = [(0, 0, {
	# 							# 		'moderator_register_id': register_obj.id,
	# 							# 		'qualification_id': int(qual),
	# 							# 		'moderator_qualification_unit_standards':  [(0, 0, val) for val in qualification_elective_lists],
	# 							# 	})]

	# 					if regtype=="provider":
	# 							register_obj.provider_qualification_ids = [(0, 0, {
	# 							'accreditation_id': register_obj.id,
	# 							'qualification_id': int(qual),
	# 							'provider_qualification_unit_standards':  [(0, 0, val) for val in qualification_elective_lists],
	# 						})]