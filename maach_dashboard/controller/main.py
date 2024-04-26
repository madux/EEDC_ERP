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


class OfficeDashboard(http.Controller):
	
	@http.route([
		"/office-dashboard", 
		"/office-dashboard/<string:search_request>", 
		"/office-dashboard/<string:memo_type_param>",
		"/office-dashboard/<string:search_request>/<string:memo_type_param>"
		], type='http', auth='user', website=True, website_published=True)
	def office_dashboard(self, memo_type_param=False, search_request=False):
		user = request.env.user
		domain = ['|','|','|','|', ('employee_id.user_id', '=', user.id),
				('users_followers.user_id','=', user.id),
				('employee_id.administrative_supervisor_id.user_id.id','=', user.id),
				('memo_setting_id.approver_ids.user_id.id','=', user.id),
				('stage_id.approver_ids.user_id.id','=', user.id),
			]
		if search_request:
			domain += [
				'|', ('code', '=ilike', search_request),
			 	('name', 'ilike', search_request),
			]
		if memo_type_param:
			domain += [('memo_type.name', '=', memo_type_param)]

		# memos = request.env["memo.model"].sudo().search(domain)
		today_date = fields.Date.today()
		past_seven_days = today_date + relativedelta(days=-7) # 
		past_one_month = today_date + relativedelta(months=-30) # 
		past_seven_days = datetime.strptime(past_seven_days.strftime('%Y%m%d'), '%Y%m%d')
		current_datetime = datetime.strptime(today_date.strftime('%Y%m%d'), '%Y%m%d')
		past_week_domain = domain + [
			('date', '>=', past_seven_days),
			('date', '<=', current_datetime),
			]
		past_one_month_domain = domain + [
			('date', '>=', past_one_month),
			('date', '<=', current_datetime),
			('state', 'in', ['Done', 'Approve2','Approve'])
			]
		
		ongoing_domain = domain + [
			('state', 'not in', ['Done', 'Approve2','Approve']),
			# ('to_create_document', '=', True)
			]
		
		expected_document_domain = domain + [
			('state', 'not in', ['Done', 'Approve2','Approve']),
			('to_create_document', '=', True)
			]
		count_past_week_memo = request.env["memo.model"].sudo().search_count(past_week_domain) 
		count_ongoing_memo = request.env["memo.model"].sudo().search_count(ongoing_domain) 
		expected_document_upload = request.env["memo.model"].sudo().search_count(expected_document_domain) 
		completed_memo_past_one_month = request.env["memo.model"].sudo().search(past_one_month_domain) 
		y_axis_data = self.get_xy_data(memo_type_param)[0]
		vals = {
			"memo_ids": completed_memo_past_one_month,
			"count_past_week_memo": count_past_week_memo,
			"count_today_memo": count_ongoing_memo,
			"get_documents_to_upload": expected_document_upload,
			"memo_completed_past_one_month": len(completed_memo_past_one_month),
			"memo_types": request.env['memo.type'].search([('allow_for_publish', '=', True), ('active', '=', True)]),
			"request_item": {
				'new_request':  len([
					m.id for m in request.env['memo.model'].search([('state', 'in', ['submit'])])
					]),
				'expect_document_request': self.get_expected_document()[0],
				'department_expected_to_submit': self.get_expected_document()[1],
				
				},
			"max_progress": max(y_axis_data) if y_axis_data else 0,
			"y_data_chart": json.dumps({'data': y_axis_data or '[]'}),
			"x_data_chart": json.dumps({'data': self.get_xy_data(memo_type_param)[1] or '[]'})
		}
		return request.render("maach_dashboard.maach_dashboard_template_id", vals)
	
	def get_expected_document(self):
		total_expectation, departments = 0, []
		document_folders = request.env['documents.folder'].search([])
		for doc in document_folders:
			start = doc.submission_minimum_range
			end = doc.submission_maximum_range
			today =  fields.Date.today()
			min_date = doc.next_reoccurance_date + relativedelta(days=-start)
			maximum_date = doc.next_reoccurance_date + relativedelta(days=end)
			if today >= min_date and today <= maximum_date:
				total_expectation += 1
				departments += [dep.name for dep in doc.department_ids]
		return total_expectation, list(set(departments))
	
	def get_xy_data(self, memo_type_param="document_request"):
		'''Test for document charts
        1. configure document folder with occurrence and min and max range set to 2 . ie two days
        2. Create a new memo of type document request,
        3. Approve the memo, 
        4. Reset the next occurrence and try again
        '''
		hr_department = request.env['hr.department'].sudo()
		department_total_progress = []
		departments = []
		if memo_type_param == "document_request":
			document_folders = request.env['documents.folder'].search([])
			total_document_folders = len(document_folders) # 5
			document_ratio = 100 / total_document_folders # == 20
			# document_ratio = float_round(document_ratio, precision_rounding=2)
			for document in document_folders:
				"""Get all the departments in documents folder"""
				departments += [dep.id for dep in document.department_ids]
			for department in list(set(departments)): # set to remove duplicates
				department_submission = 0 
				for doc in document_folders:
					'''get the min date of submission before reoccurence and that after reoccurence date'''
					min_date = doc.next_reoccurance_date + relativedelta(days=-doc.submission_minimum_range)
					maximum_date = doc.next_reoccurance_date + relativedelta(days=doc.submission_maximum_range)
					docu_ids = doc.mapped('document_ids')
					if docu_ids:
						submitted_documents_document = docu_ids.filtered(
							lambda su: su.submitted_date >= min_date and su.submitted_date <= maximum_date and su.memo_id.dept_ids.id == hr_department.browse(department).id if su.submitted_date else False
						) # check if the submitted document is within the min date and maximum date and count it as +1
						if submitted_documents_document:
							department_submission += len(submitted_documents_document)
				dept_document_ratio = int(department_submission * document_ratio) # total to display 4 * 20 == 80
				department_total_progress.append(dept_document_ratio)
		return department_total_progress, [hr_department.browse(dp).name for dp in list(set(departments))]

	@http.route(["/memo-records"], type='http', auth='user', website=True, website_published=True)
	def open_related_record_view(self):
		url = "/web#action=487&model=memo.model&view_type=list&cids=1&menu_id=333"
		return request.redirect(url)