# -*- coding: utf-8 -*-
import base64
import json
import logging
from multiprocessing.spawn import prepare
import urllib.parse
from odoo import http, fields
from odoo.exceptions import ValidationError
from odoo.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

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
			"leave_type_ids": request.env["hr.leave.type"].sudo().search([]),
		}
		return request.render("portal_request.portal_request_template", vals)
	 
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
			[
				('employee_number', '=', staff_num),
				('active', '=', True),
				('user_id', '=', user.id)], limit=1) 
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
			
	@http.route(['/get/leave-allocation/<int:leave_type>/<staff_num>/'], type='json', website=True, auth="user", csrf=False)
	def get_leave_allocation(self,leave_type,staff_num):
		"""Check staff Identification No.
		Args:
			staff_num (str): The Id No to be validated
		Returns:
			dict: Response
		"""
		_logger.info('Checking Staff ID No ...')
		user = request.env.user
		if staff_num:
			employee = request.env['hr.employee'].sudo().search(
			[('employee_number', '=', staff_num), ('active', '=', True)], limit=1) 
			if employee:
				# get leave artifacts
				leave_allocation = request.env['hr.leave.allocation'].sudo()
				leave_allocation_id = leave_allocation.search([
					('holiday_status_id', '=', leave_type),
					('employee_id.employee_number', '=', staff_num)
					], limit=1)
				if leave_allocation_id:
					return {
						"status": True,
						"data": {
							'number_of_days_display': leave_allocation_id.number_of_days_display,
						},
						"message": "", 
					}
				else:
					return {
					"status": False,
					"data": {
						'number_of_days_display': "",
					},
					"message": "No allocation set up for the employee. Contact Admin", 
					}
			else:
				return {
					"status": False,
					"data": {
						'number_of_days_display': "",
					},
					"message": "Employee with staff ID provided does not exist. Contact Admin", 
					}
		return {
				"status": False,
				"data": {
					'number_of_days_display': "",
				},
				"message": "Please select staff ID. Contact Admin", 
				}
	@http.route(['/check-overlapping-leave'], type='json', website=True, auth="user", csrf=False)
	def check_overlapping_leave(self, **post):
		staff_num = post.get('data').get('staff_num')
		start_date = post.get('data').get('start_date')
		end_date = post.get('data').get('end_date')
		_logger.info(f'posted to check overlapping leave ...{staff_num}, {start_date}, {end_date}')

		employee_id = request.env['hr.employee'].sudo().search([
			('employee_number', '=', staff_num)
			], limit=1)
		if not any([staff_num, start_date, end_date]):
			return {
					"status": False,
					"message": "Please ensure you provide staff number , leave start date and leave end date", 
					}
		else:
			_logger.info('All fields captured')

		if employee_id: 
			st = datetime.strptime(start_date, "%m/%d/%Y")
			ed = datetime.strptime(end_date, "%m/%d/%Y")
			# all_employees = self.employee_id | self.employee_ids
			hr_request = request.env['hr.leave'].sudo().search(
				[
				('request_date_from', '<=', st),
				('request_date_to', '>=', ed),
				('employee_id', '=', employee_id.id),
				# ('state', 'not in', ['draft', 'Refuse']),
				], 
				limit=1) 
			if hr_request:
				msg = """You can not set two time off that overlap on the same day for the same employee. Existing time off:"""
				return {
					"status": False,
					"message": msg, 
					} 
			else:
				_logger.info('No date inbetween')
				return {
					"status": True,
					"message": "", 
					}
		else:
			msg = """No Employee record found"""
			return {
				"status": False,
				"message": msg, 
				}
		
	@http.route(['/check-cash-retirement'], type='json', website=True, auth="user", csrf=False)
	def check_cash_retirement(self, **post):
		user = request.env.user 
		request_type = post.get('request_type')
		staff_num = post.get('staff_num')
		memo_obj = request.env['memo.model'].sudo()
		if staff_num:
			domain = [
				('employee_id.employee_number', '=', staff_num),
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
				('memo_type', '=', 'cash_advance'),
				('soe_advance_reference', '=', False),
				('state', '=', 'Done') 
			]
			cash_advance_not_retired = memo_obj.search(domain, limit=1)
			_logger.info(f"This is cash advance check staff_num: {staff_num}")
			if cash_advance_not_retired:
				_logger.info(f"Cash advance not retired: {cash_advance_not_retired}")
				return {
					"status": False,
					"message": f"You cannot request for another cash advance without retiring an existing one" 
				}
			else:
				_logger.info(f"Cash advance is retired")
				return {
					"status": True,
					"message": "" 
				}
				
		else:
			return {
				"status": False,
				"message": "Staff Number required" 
			}

	@http.route(['/check_order'], type='json', website=True, auth="user", csrf=False)
	def check_order(self, **post):
		staff_num = post.get('staff_num')
		existing_order = post.get('existing_order')
		request_type = post.get('request_type')
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
			domain = [
				('employee_id.employee_number', '=', staff_num),
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
				('code', '=ilike', existing_order) 
			]
			if request_type == "soe":
				'''this should only return the request cash advance that has
				  been approved and taken out from the account side
				'''
				domain += [('state', 'in', ['Done']), ('memo_type', 'in', ['cash_advance'])]
			else:
				domain += [('state', 'in', ['submit'])]
			memo_request = request.env['memo.model'].sudo().search(domain, limit=1) 
			if memo_request: 
				return {
					"status": True,
					"data": {
						'name': memo_request.employee_id.name,
						'phone': memo_request.employee_id.work_phone or memo_request.employee_id.mobile_phone,
						'state': 'Draft' if memo_request.state == 'submit' else 'Waiting For Payment / Confirmation' if memo_request.state == 'Approve' else 'Approved' if memo_request.state == 'Approve2' else 'Done' if memo_request.state == 'Done' else 'Refused',
						'work_email': memo_request.employee_id.work_email,
						'subject': memo_request.name,
						'description': memo_request.description or "",
						'amount': sum([
							rec.amount_total or rec.product_id.list_price for rec in memo_request.product_ids]) \
								if memo_request.product_ids else memo_request.amountfig,
						'district_id': memo_request.employee_id.ps_district_id.id,
						'request_date': memo_request.date.strftime("%m/%d/%Y") if memo_request.date else "",
						'product_ids': [
							{'id': q.product_id.id, 
							'name': q.product_id.name if q.product_id else q.description, 
							'qty': q.quantity_available,
							# building lines for cash advance and soe
							'used_qty': q.used_qty,
							'amount_total': q.amount_total,
							'used_amount': q.used_amount,
							'description': q.description or "",
							'code': q.code,
							} 
							for q in memo_request.mapped('product_ids').filtered(lambda x: not x.retired)
						]
					},
					"message": "", 
					}
			else:
				message = "Sorry !!! ReF does not exist or You cannot do an SOE because the request Cash Advance has not been approved" \
				if request_type == "soe" else "Order ID with staff ID does not exist / has been submitted already. Contact Admin"
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
					"message": message 
					}
			
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
	

	@http.route(['/my/request-state'], type='json', website=True, auth="user", csrf=False)
	def check_qty(self,  *args, **kwargs):
		type = kwargs.get('type') 
		id = kwargs.get('id') 
		"""Check quantity.
		Args:
			type (type): either set to draft or set to Sent
			id: id of the record
		Returns:
			dict: Response
		"""
		_logger.info(f'Sending request of .... {type} with id {id}')
		if id and type:
			record = request.env['memo.model'].sudo().search(
			[
				('active', '=', True),
				('id', '=', int(id))
			], 
			limit=1) 
			if record:
				return {
					"status": True,
					"message": f"Succeessfully updated", 
					}
			else:
				return {
					"status": False,
					"message": "There is no record found to update status", 
					}
		else:
			return {
				"status": False,
				"message": "No record found to update", 
				}
				 
		
	@http.route(['/check-quantity'], type='json', website=True, auth="user", csrf=False)
	def check_qty(self,  *args, **kwargs):
		# params = kwargs.get('params')
		product_id = kwargs.get('product_id')
		qty = kwargs.get('qty') 
		district = kwargs.get('district') 
		request_type = kwargs.get('request_type') 

		"""Check quantity.
		Args:
			product_id (id): The Id No to be validated
			qty (qty): qty
		Returns:
			dict: Response
		"""
		_logger.info(f'Checking product for {product_id} District {district} check_ qty No ...{qty}')
		if product_id:
			product = request.env['product.product'].sudo().search(
			[
				('active', '=', True),
				('id', '=', int(product_id))
			], 
			limit=1) 
			if product:
				domain = [
					('company_id', '=', request.env.user.company_id.id) 
				]
				# if district:
				# 	district_id = request.env['hr.district'].browse([int(district)])
				# 	if district_id:
				# 		domain = [
				# 			('branch_id', '=', district_id.branch_id.id) 
				# 		]
				warehouse_location_id = request.env['stock.warehouse'].search(domain, limit=1)
				stock_location_id = warehouse_location_id.lot_stock_id
				# should_bypass_reservation : False
				if request_type in ['material_request']:
					total_availability = request.env['stock.quant'].sudo()._get_available_quantity(product, stock_location_id, allow_negative=False) or 0.0
					product_qty = float(qty) if qty else 0
					if product_qty > total_availability:
						return {
							"status": False,
							"message": f"Selected product quantity ({product_qty}) is higher than the Available Quantity. Available quantity is {total_availability}", 
							}
					else:
						return {
							"status": True,
							"message": "", 
							}
				else:
					return {
						"status": True,
						"message": "", 
						}
			else:
				return {
					"status": True,
					"message": "The product does not exist on the inventory", 
					}
		else:
			return {
				"status": True,
				"message": "Please ensure you select a product line", 
				}

	# total_availability = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id) if move.product_id else 0.0

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
			district = request.env['hr.district'].sudo().search([
				('id', '=', post.get("selectDistrict"))
				], limit=1)
			if district:
				district_id = district.id 
			else:
				district_id = memo_id.district_id.id
		_logger.info(f'WHAT IS DISTRICT ==> {district_id}')
		leave_start_date = datetime.strptime(post.get("leave_start_datex",''), "%m/%d/%Y") if post.get("leave_start_datex") else fields.Date.today()
		leave_end_date = datetime.strptime(post.get("leave_end_datex",''), "%m/%d/%Y") \
			if post.get("leave_start_datex") else leave_start_date + relativedelta(days=1)
		
		if post.get("selectRequestOption") == "soe":
			cash_advance_id = request.env['memo.model'].sudo().search([
			('code', '=', existing_order)], limit=1)
		else:
			cash_advance_id = False
		vals = {
			"employee_id": employee_id.id,
			"memo_type": "Payment" if post.get("selectRequestOption") == "payment_request" else post.get("selectRequestOption") if post.get("selectRequestOption") else "Internal",
			"email": post.get("email_from"),
			"phone": post.get("phone_number"),
			"name": post.get("subject"),
			"description": post.get("description"),
			"amountfig": post.get("amount_fig"),
			"date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(), #format_to_odoo_date(post.get("request_date",'')),
			"leave_type_id": post.get("leave_type_id", ""),
			"leave_start_date": leave_start_date,
			"leave_end_date": leave_end_date,
			"district_id": district_id,
			# or district_id or int(post.get("selectDistrict")) if post.get("selectDistrict") else 1, #int(post.get("selectDistrict")) if post.get("selectDistrict") else memo_id.district_id.id if memo_id else False,
			"approver_id": employee_id.parent_id.id, 
			"state": "Sent",
			"direct_employee_id": employee_id.parent_id.id, 
			"cash_advance_reference": cash_advance_id.id if cash_advance_id else False,
			"res_users": [
				(4, employee_id.parent_id.user_id.id), 
				(4, request.env.user.id)],
			"users_followers": [
				(4, employee_id.parent_id.id), 
				(4, employee_id.id)],
		}
		_logger.info(f"POST DATA {vals}")
		_logger.info(f"""Accreditation ggeenn geen===>  {json.loads(post.get('productItems'))}""")
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
		memo_id.forward_memos(
				memo_id.direct_employee_id or employee_id.parent_id.id, 
				post.get("description", "")
				)
		request.session['memo_ref'] = memo_id.code
		_logger.info('Successfully Registered!')
		return json.dumps({'status': True, 'message': "Form Submitted!"})
	
	def generate_request_line(self, product_items, memo_id):
		memo_id.sudo().write({'product_ids': False})
		counter = 1
		for rec in product_items:
			desc = rec.get('description', '')
			_logger.info(f"REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec}")
			product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
			if product_id:
				request.env['request.line'].sudo().create({
					'memo_id': memo_id.id,
					'product_id': product_id.id, #int(rec.get('product_id')) if rec.get('product_id') else False,
					'quantity_available': float(rec.get('qty')) if rec.get('qty') else 0,
            		'description': BeautifulSoup(desc, features="lxml").get_text(),
					'used_qty': rec.get('used_qty'),
					'amount_total': rec.get('amount_total'),
					'used_amount': rec.get('used_amount'),
					'note': rec.get('note'),
					'code': rec.get('code') if rec.get('code') else f"{memo_id.code} - {counter}",
					'to_retire': rec.get('line_checked'),
				})
			counter += 1

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
	
	def get_request_info(self, request):
		"""
		Returns context data extracted from :param:`request`.

		Heavily based on flask integration for Sentry: https://git.io/vP4i9.
		"""
		urlparts = urllib.parse.urlsplit(request.url)
		query_string = urlparts.query
		_logger.info(f"URL PARTS = {urlparts} QUERY STRING IS {query_string}")

	@http.route(['/my/requests', '/my/requests/<string:type>', '/my/requests/param/<string:search_param>', '/my/requests/page/<string:page>'], type='http', auth="user", website=True)
	def my_requests(self, type=False, page=False, search_param=False):
		"""This route is used to call the requesters or user records for display
		page: the pagination index: prev or next
		type: material_request
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
						if type in ['Internal', 'procurement_request','server_access' 'vehicle_request', 'material_request'] \
							else ['Internal', 'server_access', 'procurement_request', 'vehicle_request', 'material_request', 'leave_request', 'soe', 'cash_advance', 'payment_request', 'Loan']
		request_id = request.env['memo.model'].sudo()
		domain = [
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
			]
		domain += [
			('memo_type', 'in', memo_type),
		]
		if search_param:
			# if request.httprequest:
			requests = request.httprequest 
			# url_obj = self.get_request_info()
			# self.get_request_info(requests)
			domain += [
				'|', ('name', 'ilike', search_param),
				('code', 'ilike', search_param),
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
	
	@http.route('/my/request/update/<int:id>/<string:status>', type='http', auth="user", website=True)
	def update_my_request_status(self, id, status):
		user = request.env.user
		request_id = request.env['memo.model'].sudo()
		domain = [
				('employee_id.user_id', '=', user.id),
				('id', '=', id),
				('state', '=', "Sent"),
			]
		requests = request_id.search(domain, limit=1)
		requests.write({'state': status})
		return request.redirect('/my/request/view/%s' %(requests.id))

 