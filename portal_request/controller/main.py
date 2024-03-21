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
# Shared parameters for all login/signup flows
SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()

def get_url(id):
	base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
	base_url += "/my/request/view/%s" % (id)
	return "<a href={}> </b>Click<a/>. ".format(base_url)

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
		
# class Home(main.Home):
	# @http.route('/', type='http', auth="none")
	# def index(self, s_action=None, db=None, **kw):
	# 	# if request.db and request.session.uid and not is_user_internal(request.session.uid):
	# 	# 	# return request.redirect_query('/web/login_successful', query=request.params)
	# 	# 	return request.redirect('/')
	# 	# return request.redirect_query('/web', query=request.params)
	# 	# return request.redirect('/my/requests')
	# 	return request.redirect('/')
		
	# @http.route('/web/login', type='http', auth="none")
	# def web_login(self, redirect=None, **kw):
	# 	ensure_db()
	# 	request.params['login_success'] = False
	# 	if request.httprequest.method == 'GET' and redirect and request.session.uid:
	# 		return request.redirect(redirect)
	# 		# return request.redirect('/')
		


	# 	# simulate hybrid auth=user/auth=public, despite using auth=none to be able
	# 	# to redirect users when no db is selected - cfr ensure_db()
	# 	if request.env.uid is None:
	# 		if request.session.uid is None:
	# 			# no user -> auth=public with specific website public user
	# 			request.env["ir.http"]._auth_method_public()
	# 		else:
	# 			# auth=user
	# 			request.update_env(user=request.session.uid)

	# 	values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
	# 	try:
	# 		values['databases'] = http.db_list()
	# 	except odoo.exceptions.AccessDenied:
	# 		values['databases'] = None

	# 	if request.httprequest.method == 'POST':
	# 		try:
	# 			uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
	# 			request.params['login_success'] = True
	# 			# return request.redirect(self._login_redirect(uid, redirect=redirect))
	# 			return request.redirect('/')
	# 		except odoo.exceptions.AccessDenied as e:
	# 			if e.args == odoo.exceptions.AccessDenied().args:
	# 				values['error'] = _("Wrong login/password")
	# 			else:
	# 				values['error'] = e.args[0]
	# 	else:
	# 		if 'error' in request.params and request.params.get('error') == 'access':
	# 			values['error'] = _('Only employees can access this database. Please contact the administrator.')

	# 	if 'login' not in values and request.session.get('auth_login'):
	# 		values['login'] = request.session.get('auth_login')

	# 	if not odoo.tools.config['list_db']:
	# 		values['disable_database_manager'] = True

	# 	response = request.render('web.login', values)
	# 	response.headers['X-Frame-Options'] = 'SAMEORIGIN'
	# 	response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
	# 	return response
	
class PortalRequest(http.Controller):
	
	@http.route(["/portal-request"], type='http', auth='user', website=True, website_published=True)
	def portal_request(self):
		"""Request portal for employee / portal users
		"""
		memo_config_memo_type_ids = [mt.memo_type.id for mt in request.env["memo.config"].sudo().search([])]
		vals = {
			# "district_ids": request.env["hr.district"].sudo().search([]),
			"leave_type_ids": request.env["hr.leave.type"].sudo().search([]),
			"memo_key_ids": request.env["memo.type"].sudo().search([
				('id', 'in', memo_config_memo_type_ids), ('allow_for_publish', '=', True)
				]),
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
				if employee.department_id:
					
					return {
						"status": True,
						"data": {
							'name': employee.name or "",
							'phone': employee.work_phone or employee.mobile_phone or "",
							'work_email': employee.work_email or "",
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
						"message": "Employee is not linked to any department. Contact Admin", 
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
			
	@http.route(
			['/get/leave-allocation/<int:leave_type>/<staff_num>/'], 
			type='json', website=True, auth="user", csrf=False)
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
		
	@http.route(['/check-configured-stage'], type='json', website=True, auth="user", csrf=False)
	def check_configured_leave(self, **post):
		staff_num = post.get('staff_num')
		request_option = post.get('request_option')
		_logger.info(f'posted to check configured stage ...{staff_num}, {request_option}')
		employee_id = request.env['hr.employee'].sudo().search([
			('employee_number', '=', staff_num)
			], limit=1)
		if not any([staff_num, request_option]):
			return {
					"status": False,
					"message": "Please ensure you provide staff number, request option", 
					}
		else:
			_logger.info('All fields captured')

		if employee_id and employee_id.department_id:
			# check if user is from external company, restrict them from using internal applications 
			memo_setting_id = request.env['memo.config'].sudo().search([
				('memo_type.memo_key', '=', request_option),
				('department_id', '=', employee_id.department_id.id)
				], limit=1) 
			if not memo_setting_id or not memo_setting_id.stage_ids:
				msg = """
				Please contact system admin to properly 
				configure a request type for your department"""
				return {
					"status": False,
					"message": msg, 
					} 
			else:
				_logger.info('Found memo setting for thee')
				if employee_id.is_external_staff and not employee_id.external_company_id.id in memo_setting_id.mapped('allowed_for_company_ids').ids:
				# .filtered(
				# 	lambda partner: partner.id !=  employee_id.external_company_id.id): 
					_logger.info('Employee not an external user')

					return {
						"status": False,
						"message": '''
						Sorry! You are not allowed to
						use this option for now''' 
						}
				else:
					_logger.info('Employee is internal allowed user')
					return {
						"status": True,
						"message": "", 
						}
		else:
			msg = """
			No Employee record found or employee department 
			not properly configured. Contact system Admin"""
			return {
				"status": False,
				"message": msg, 
				}
		
	@http.route(['/check-cash-retirement'], type='json', website=True, auth="user", csrf=False)
	def check_cash_retirement(self, **post):
		_logger.info(f"Cash advance posting: {post}")
		user = request.env.user 
		request_type = post.get('request_type')
		staff_num = post.get('staff_num')
		memo_obj = request.env['memo.model'].sudo()
		if staff_num:
			domain = [
				('employee_id.employee_number', '=', staff_num),
				('active', '=', True),
				('employee_id.user_id', '=', user.id),
				('memo_type.memo_key', '=', 'cash_advance'),
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
				domain += [('state', 'in', ['Done']), ('memo_type.memo_key', 'in', ['cash_advance'])]
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
						# 'district_id': memo_request.employee_id.ps_district_id.id,
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
						# 'district_id': "",
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

	@http.route(['/portal-request-employee'], type='http', website=True, auth="user", csrf=False)
	def get_portal_employee(self, **post):
		request_type_option = post.get('request_type')
		if request_type_option:
			if request_type_option == "employee":
				employeeItems = json.loads(post.get('employeeItems'))
				_logger.info(f'Employeeitemmms {employeeItems}')
				domain = [('active', '=', True), ('id', 'not in', [int(i) for i in employeeItems])]
				employees = request.env["hr.employee"].sudo().search(domain)
				return json.dumps({
					"results": [{"id": item.id,"text": f'{item.name} - {item.employee_number}'} for item in employees],
					"pagination": {
						"more": True,
					}
				})	
			elif request_type_option == "department":
				domain = [('active', '=', True)]
				departments = request.env["hr.department"].sudo().search(domain)
				return json.dumps({
					"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
					"pagination": {
						"more": True,
					}
				})
			elif request_type_option == "role":
				domain = [('active', '=', True)]
				departments = request.env["hr.job"].sudo().search(domain)
				return json.dumps({
					"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
					"pagination": {
						"more": True,
					}
				})
			elif request_type_option == "district":
				domain = []
				departments = request.env["hr.district"].sudo().search(domain)
				return json.dumps({
					"results": [{"id": item.id,"text": f'{item.name}'} for item in departments],
					"pagination": {
						"more": True,
					}
				})
			else:	
				return json.dumps({
					"results": [{"id": '',"text": '',}],
					"pagination": {
						"more": True,
					}
				})	
		else:
			return json.dumps({
				"results": [{"id": '',"text": ''}],
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
				# ('detailed_type', '=', 'product'),
				('id', '=', int(product_id))
			], 
			limit=1) 
			if product:
				domain = [
					('company_id', '=', request.env.user.company_id.id) 
				] 
				warehouse_location_id = request.env['stock.warehouse'].search(domain, limit=1)
				stock_location_id = warehouse_location_id.lot_stock_id
				# should_bypass_reservation : False
				if request_type in ['material_request'] and product.detailed_type in ['product']:
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

	# total_availability = request.env['stock.quant']._get_available_quantity(move.product_id, move.location_id) if move.product_id else 0.0
	
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
		
		leave_start_date = datetime.strptime(post.get("leave_start_datex",''), "%m/%d/%Y") if post.get("leave_start_datex") else fields.Date.today()
		leave_end_date = datetime.strptime(post.get("leave_end_datex",''), "%m/%d/%Y") \
			if post.get("leave_start_datex") else leave_start_date + relativedelta(days=1)
		if post.get("selectRequestOption") == "soe":
			cash_advance_id = request.env['memo.model'].sudo().search([
			('code', '=', existing_order)], limit=1)
		else:
			cash_advance_id = False
		systemRequirementOptions = [
			'Application change : True' if post.get("applicationChange") == "on" else '',
			'Enhancement : True' if post.get("enhancement") == "on" else '',
			'Datapatch : True' if post.get("datapatch") == "on" else '',
			'Database Change : True' if post.get("databaseChange") == "on" else '',
			'OS Change : True' if post.get("osChange") == "on" else '',
			'Ids on OS and DB : True' if post.get("ids_on_os_and_db") == "on" else '',
			'Version Upgrade : True' if post.get("versionUpgrade") == "on" else '',
			'Hardware Option : True' if post.get("hardwareOption") == "on" else '',
			'Other Changes : ' + post.get("other_system_details", "") if post.get("other_system_details") else '', 
			'Justification reason : ' + post.get("justification_reason", "") if post.get("justification_reason") else '', 
			'Start date : ' + post.get("request_date",'') if post.get("request_date") else '', 
			'End date : ' + post.get("request_end_date",'') if post.get("request_end_date") else '', 
			]
		description_body = f"""
		<b>Description: </b> {post.get("description", "")}<br/>
		<b>Requirements: </b> {'<br/>'.join([r for r in systemRequirementOptions if r ])}
		"""
		vals = {
			"employee_id": employee_id.id,
			"memo_type": request.env['memo.type'].search([('memo_key', '=', post.get("selectRequestOption"))], limit=1).id,
			# "Payment" if post.get("selectRequestOption") == "payment_request" else post.get("selectRequestOption"),
			"email": post.get("email_from"),
			"phone": post.get("phone_number"),
			"name": post.get("subject", ''),
			"amountfig": post.get("amount_fig", 0),
			"date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(), #format_to_odoo_date(post.get("request_date",'')),
			"leave_type_id": post.get("leave_type_id", ""),
			"leave_start_date": leave_start_date,
			"leave_end_date": leave_end_date,
			# "district_id": district_id,
			"applicationChange": True if post.get("applicationChange") == "on" else False,
			"enhancement": True if post.get("enhancement") == "on" else False,
			"datapatch": True if post.get("datapatch") == "on" else False,
			"databaseChange": True if post.get("databaseChange") == "on" else False,
			"osChange": True if post.get("osChange") == "on" else False,
			"ids_on_os_and_db": True if post.get("ids_on_os_and_db") == "on" else False,
			"versionUpgrade": True if post.get("versionUpgrade") == "on" else False,
			"hardwareOption": True if post.get("hardwareOption") == "on" else False,
			"otherChangeOption": True if post.get("otherChangeOption") == "on" else False,
			"other_system_details": post.get("other_system_details"),
			"justification_reason": post.get("justification_reason"),
			"state": "Sent",
			"cash_advance_reference": cash_advance_id.id if cash_advance_id else False,
			"description": description_body, 
			"request_date": datetime.strptime(post.get("request_date",''), "%m/%d/%Y") if post.get("request_date") else fields.Date.today(),
			"request_end_date": datetime.strptime(post.get("request_end_date",''), "%m/%d/%Y") if post.get("request_end_date") else False

		}
		_logger.info(f"POST DATA {vals}")
		_logger.info(f"""Accreditation ggeenn geen===>  {json.loads(post.get('DataItems'))}""")
		DataItems = []
		DataItems = json.loads(post.get('DataItems'))
		memo_obj = request.env['memo.model']
		if not memo_id:
			_logger.info("Memo id creating")
			memo_id = memo_obj.sudo().create(vals)
		else:
			_logger.info("Memo id updating")
			memo_id.sudo().write(vals)
		if DataItems:
			_logger.info(f'DATA ITEMS IDS IS HERE {DataItems}')
			if post.get("selectRequestOption") != "employee_update":
				self.generate_request_line(DataItems, memo_id)
		
			elif post.get("selectRequestOption") == "employee_update":
				self.generate_employee_transfer_line(DataItems, memo_id)
		
		## generating attachment
		if 'other_docs' in request.params:
			attached_files = request.httprequest.files.getlist('other_docs')
			for attachment in attached_files:
				file_name = attachment.filename
				datas = base64.b64encode(attachment.read())
				other_docs_attachment = self.generate_attachment(memo_id.code, file_name, datas, memo_id.id)
		####
		# memo_id.action_submit_button()
		stage_id = memo_id.get_initial_stage(
			memo_id.memo_type.memo_key, 
			memo_id.employee_id.department_id.id or memo_id.dept_ids.id
			)
		_logger.info(f'''initial stage come be {stage_id} ''')
		approver_ids, next_stage_id = memo_id.get_next_stage_artifact(stage_id, True)
		stage_obj = request.env['memo.stage'].search([('id', '=', next_stage_id)])
		approver_ids = stage_obj.approver_ids.ids if stage_obj.approver_ids else [employee_id.parent_id.id]
		follower_ids = [(4, r) for r in approver_ids]
		user_ids = [(4, request.env.user.id)]
		if employee_id.administrative_supervisor_id:
			follower_ids.append((4, employee_id.administrative_supervisor_id.id))
		if employee_id.parent_id:
			follower_ids.append((4, employee_id.parent_id.id))
		memo_id.sudo().update({
			'stage_id': next_stage_id, 
			'approver_id': random.choice(approver_ids),
			'approver_ids': [(4, r) for r in approver_ids],
			"direct_employee_id": random.choice(approver_ids),
			'users_followers': follower_ids,
			'res_users': user_ids,
			'memo_setting_id': stage_obj.memo_config_id.id,
			'memo_type_key': memo_id.memo_type.memo_key,
		})
		_logger.info(f'''
			   Successfully Registered! with memo id Approver = {approver_ids} \
				stage {next_stage_id} {memo_id} {memo_id.stage_id} {memo_id.stage_id.memo_config_id} \
					or {stage_obj} {stage_obj.memo_config_id} {memo_id.memo_setting_id}''')
		 
		memo_id.confirm_memo(
				memo_id.direct_employee_id or employee_id.parent_id.id, 
				post.get("description", ""),
				from_website=True
				)
		request.session['memo_ref'] = memo_id.code
		return json.dumps({'status': True, 'message': "Form Submitted!"})
	
	def generate_request_line(self, DataItems, memo_id):
		memo_id.sudo().write({'product_ids': False})
		counter = 1
		for rec in DataItems:
			desc = rec.get('description', '')
			_logger.info(f"REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec}")
			product_id = request.env['product.product'].sudo().browse([int(rec.get('product_id'))])
			if product_id:
				request.env['request.line'].sudo().create({
					'memo_id': memo_id.id,
					'memo_type': memo_id.memo_type.id,
					'memo_type_key': memo_id.memo_type.memo_key,
					'product_id': product_id.id, 
					#int(rec.get('product_id')) if rec.get('product_id') else False,
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

	def generate_employee_transfer_line(self, DataItems, memo_id):
		counter = 1
		for rec in DataItems:
			_logger.info(f"REQUESTS INCLUDES=====> MEMO IS {memo_id} -ID {memo_id.id} ---{rec}")
			transfer_line = request.env['hr.employee.transfer.line'].sudo()
			employee = request.env['hr.employee'].sudo()
			department = request.env['hr.department'].sudo()
			role = request.env['hr.job'].sudo()
			district = request.env['hr.district'].sudo()
			employee_id = employee.browse([int(rec.get('employee_id'))]) if rec.get('employee_id') else False
			transfer_dept_id = department.browse([int(rec.get('transfer_dept'))]) if rec.get('transfer_dept') else False
			role_id = role.browse([int(rec.get('new_role'))]) if rec.get('new_role') else False
			# district_id = district.browse([int(rec.get('new_district'))]) if rec.get('new_district') else False

			if employee_id and transfer_dept_id and role_id:#and district_id:
				transfer_line.create({
					'memo_id': memo_id.id,
					'employee_id': employee_id.id, 
					'transfer_dept': transfer_dept_id.id,
					'current_dept_id': employee_id.department_id.id,
					'new_role': role_id.id,
					# 'new_district': district_id.id, 
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
		
		all_memo_type_keys = [rec.memo_key for rec in request.env['memo.type'].search([])]
		
		memo_type = ['payment_request', 'Loan'] if type in ['payment_request', 'Loan'] \
			else ['soe', 'cash_advance'] if type in ['soe', 'cash_advance'] \
				else ['leave_request'] if type in ['leave_request'] \
					else ['employee_update'] if type in ['employee_update'] \
						else ['Internal', 'procurement_request', 'vehicle_request', 'material_request'] \
							if type in ['Internal', 'procurement_request','server_access' 'vehicle_request', 'material_request'] \
								else all_memo_type_keys
		request_id = request.env['memo.model'].sudo()
		domain = [
				('active', '=', True),
				'|','|','|','|',('employee_id.user_id', '=', user.id),
				('users_followers.user_id','=', user.id),
				('employee_id.administrative_supervisor_id.user_id.id','=', user.id),
				('memo_setting_id.approver_ids.user_id.id','=', user.id),
				('stage_id.approver_ids.user_id.id','=', user.id),
			]
		domain += [
			('memo_type.memo_key', 'in', memo_type),
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
	
	@http.route('/my/request/view/<string:id>', type='http', auth="user", website=True)
	def my_single_request(self, id):
		id = int(id) if id else 0
		"""This route is used to call the requesters or user record for display"""
		user = request.env.user
		request_id = request.env['memo.model'].sudo()
		attachment = request.env['ir.attachment'].sudo()
		domain = [
				('active', '=', True),
				# ('employee_id.user_id', '=', user.id),
				('id', '=', int(id)),
				'|','|','|','|',('employee_id.user_id', '=', user.id),
				('users_followers.user_id','=', user.id),
				('employee_id.administrative_supervisor_id.user_id.id','=', user.id),
				('memo_setting_id.approver_ids.user_id.id','=', user.id),
				('stage_id.approver_ids.user_id.id','=', user.id),
			]
		requests = request_id.search(domain, limit=1)
		memo_attachment_ids = attachment.search([
			('res_model', '=', 'memo.model'),
			('res_id', '=', requests.id)
			])
		values = {
			'req': requests,
			# 'req': requests,
			'current_user': user.id,
			'record_attachment_ids': memo_attachment_ids,
			}
		return request.render("portal_request.request_form_template", values) 
	
	@http.route('/my/request/update', type='json', auth="user", website=True)
	def update_my_request(self, **post):
		_logger.info(f"updating the request ...{post.get('memo_id')}")
		user = request.env.user
		request_id = request.env['memo.model'].sudo()
		domain = [
			# ('employee_id.user_id', '=', user.id),
			('id', '=', post.get('memo_id')),
			# ('state', 'in', ['Refuse']),
		]
		request_record = request_id.search(domain, limit=1)
		stage_id = False
		status = post.get('status', '')
		if request_record:
			if status == "cancel":
				stage_id = request.env.ref('company_memo.memo_cancel_stage').id
				body_msg = f"""
					Dear Sir / Madam, <br/>
					I wish to notify you that a memo with description \n <br/>\
					has been cancel by {request.env.user.name} <br/>\
					Kindly {get_url(request_record.id)}"""
				request_record.mail_sending_direct(body_msg)
				request_record.write({
					'state': 'Refuse', 
					'stage_id': stage_id,
					})
				return {
					"status": True, 
					"message": "Record updated successfully", 
					}
			elif status == "Sent":
				stage_id = request_record.sudo().memo_setting_id.stage_ids[0].id if \
					request_record.sudo().memo_setting_id.stage_ids else \
						request.env.ref('company_memo.memo_cancel_stage').id
				request_record.sudo().write({'state': 'Sent', 'stage_id': stage_id})
				return {
					"status": True, 
					"message": "Record updated successfully", 
					}
			elif status in ["Resend"]:
				# useds this to determine the stages configured on the system
				# if the length of stages is just 1, try the first condition else,
				# set the stage to the next stage after draft.
				if not request.env.user.id == request_record.employee_id.user_id.id:
					return {
						"status": False, 
						"message": "Only initiator can resend this request", 
						}
				
				memoStage_ids = request_record.sudo().memo_setting_id.stage_ids.ids 
				if memoStage_ids:
					stage_id = memoStage_ids[0] if len(memoStage_ids) < 1 else memoStage_ids[1]
					request_record.write({'state': 'Sent', 'stage_id': stage_id})
					return {
						"status": True, 
						"message": "Record updated successfully", 
						}
				else:
					return {
					"status": False, 
					"message": "No stage configured or found for this request. Contact admin", 
					}
			elif status in ["Approve"]:
				if not (request_record.supervisor_comment or request_record.manager_comment):
					return {
						"status": False, 
						"message": "Please Ensure to provide manager's or supervisor's comment", 
						}
			
				is_approved_stage = request_record.sudo().memo_setting_id.mapped('stage_ids').\
					filtered(lambda appr: appr.is_approved_stage == True) 
				if is_approved_stage:
					stage_id = is_approved_stage[0] 
					# is_approved_stage = request_record.sudo().memo_setting_id.mapped('stage_ids').\
					# filtered(lambda appr: appr.approver_id.user_id.id == request.env.user.id)
					current_stage_approvers = request_record.sudo().stage_id.approver_ids
					if request.env.user.id in [r.user_id.id for r in current_stage_approvers]:
						request_record.sudo().update_final_state_and_approver()
						request_record.sudo().write({
							'res_users': [(4, request.env.user.id)]
							})
					else:
						return {
						"status": True,
						"message": "You are not allowed to approve this document", 
						}
						# request_record.write({'state': 'Sent', 'stage_id': stage_id})
					body_msg = f"""
					Dear Sir / Madam <br/>\
					I wish to notify you that a memo with description \n <br/>\
					has been approved for validation by {request.env.user.name} <br/>\
					Kindly {get_url(request_record.id)}"""
					request_record.mail_sending_direct(body_msg)
					return {
						"status": True,
						"message": "Record updated successfully", 
						}
				else:
					return {
					"status": False, 
					"message": "No stage configured as approved stage. Contact admin", 
					}
			else:
				return {
						"status": False, 
						"message": "Request must have a status", 
						}
		else:
			return {
					"status": False, 
					"message": "No matching record found", 
					}
		# return request.redirect(f'/my/request/view/{str(id)}')# %(requests.id))
	
	@http.route('/update/data', type='json', auth="user", website=True)
	def update_my_request_status(self, **post):
		request_id = request.env['memo.model'].sudo()
		domain = [
			('id', '=', int(post.get('memo_id'))),
		]
		request_record = request_id.search(domain, limit=1)
		_logger.info(f"retriving memo update {request_record}...")
		if request_record:
			# TODO some kind of repeatation was done here. COnsider rewriting
			supervisor_message = request_record.supervisor_comment or ""
			manager_message = request_record.manager_comment or ""
			message, body = "", ""
			status = post.get('status', '')
			_logger.info(f"retriving memo update {post.get('supervisor_comment')}...")
			if post.get('supervisor_comment', ''):
				body = plaintext2html(post.get('supervisor_comment'))
				value = {
					'is_supervisor_commented': True,
					'state': 'Refuse' if status == 'Refuse' else request_record.state,
					'stage_id': request.env.ref("company_memo.memo_refuse_stage").id if status == 'Refuse' else request_record.stage_id.id,
					}
				
				if request_record.employee_id.administrative_supervisor_id:
					message = supervisor_message +"\n"+ "By: " + request.env.user.name + ':'+ body
					value.update({
						'supervisor_comment': message
						})
				else:
					message = manager_message +"\n"+ "By: " + request.env.user.name + ':'+ body
					value.update({
						'manager_comment': message
						})
				request_record.write(value)
				body_msg = f"""
					Dear Sir / Madam, <br/>
					I wish to notify you that a memo with the reference #{request_record.code} \n <br/>\
					has been commented by the supervisor / manager. <br/>\
					Kindly {get_url(request_record.id)}"""
				request_record.mail_sending_direct(body_msg) 
				request_record.message_post(body=body)
				return {
						"status": True,
						"message": "Comment successfully Updated",
						}
			# elif post.get('manager_comment'):
			# 	body = plaintext2html(post.get('manager_comment'))
			# 	message = manager_message +"\n"+ "By: " + request.env.user.name +':'+ body
			# 	request_record.write({
			# 		'manager_comment': message,
			# 		'state': 'Refuse' if status == 'Refuse' else request_record.state,
			# 		'stage_id': request.env.ref("company_memo.memo_refuse_stage").id if status == 'Refuse' else request_record.stage_id.id,
			# 		})
			# 	body_msg = f"""
			# 		Dear Sir / Madam, <br/>
			# 		I wish to notify you that a memo with description \n <br/>\
			# 		has been commented by the Manager. <br/>\
			# 		Kindly {get_url(request_record.id)}"""
			# 	request_record.message_post(body=body)
			# 	return {
			# 			"status": True,
			# 			"message": "Comment successfully Updated",
			# 			}
			else:
				_logger.info(f"xxxxxx not updated")
				return {
					"status": False, 
					"message": "Please Provide a write up in the comment section", 
				}
		else:
			return {
				"status": False, 
				"message": "No matching memo record found. Contact Admin", 
			}
