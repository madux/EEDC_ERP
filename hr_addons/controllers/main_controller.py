import base64
import csv
import io
import datetime
from odoo import http, fields
from odoo.http import request
from odoo.modules.module import get_resource_path

class DashboardPagesController(http.Controller):

    @http.route('/attendance-employee', type='http', auth='user')
    def show_attendance_employee_list(self, **kw):
        """Display memo list view"""
        file_path = get_resource_path(
            'hr_addons',
            'static/html',
            'hr_dashboard.html'
        )
        
        if not file_path:
            return "HTML file not found."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html')]
        )
    # -------------------------------------------------------------
    # GENERIC HELPER FOR FILTERS & DOMAIN
    # -------------------------------------------------------------
    def _build_domain(self, search_val, filters):
        domain = [('active', '=', True)] if 'active' in request.env['hr.employee']._fields else []
        if search_val:
            domain.append('|')
            domain.append(('name', 'ilike', search_val))
            domain.append(('employee_number', 'ilike', search_val))
        
        for k, v in filters.items():
            if v:
                domain.append((k, '=', v))
        return domain

    # -------------------------------------------------------------
    # 1. EMPLOYEES (hr.employee)
    # -------------------------------------------------------------
    @http.route('/api/dashboard/employees', type='json', auth='user', methods=['POST'], csrf=False)
    def get_employees(self, page=1, limit=40, search='', filters=None, **kwargs):
        filters = filters or {}
        domain = [('active', '=', True)]
        
        if search:
            domain += ['|', ('name', 'ilike', search), ('employee_number', 'ilike', search)]
        if filters.get('department_id'):
            domain.append(('department_id', '=', int(filters['department_id'])))
        if filters.get('company_id'):
            domain.append(('company_id', '=', int(filters['company_id'])))

        Employee = request.env['hr.employee'].sudo()
        total_count = Employee.search_count(domain)
        offset = (page - 1) * limit
        employees = Employee.search(domain, offset=offset, limit=limit, order='id desc')

        records = []
        for emp in employees:
            records.append({
                'id': emp.id,
                'name': emp.name,
                'employee_code': emp.employee_number or emp.barcode or f"EMP-{emp.id}",
                'work_email': emp.work_email or 'N/A',
                'work_phone': emp.work_phone or 'N/A',
                'job_title': emp.job_title or 'N/A',
                'department': emp.department_id.name or 'Unassigned',
                'department_id': emp.department_id.id or False,
                'company': emp.company_id.name or 'Unassigned',
                'company_id': emp.company_id.id or False,
                'avatar_url': f'/web/image/hr.employee/{emp.id}/avatar_128',
            })

        # Dropdown Filter Options
        departments = request.env['hr.department'].sudo().search_read([], ['id', 'name'])
        companies = request.env['res.company'].sudo().search_read([], ['id', 'name'])

        return {
            'records': records,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit if total_count else 1,
            'filter_options': {
                'departments': departments,
                'companies': companies
            }
        }

    # -------------------------------------------------------------
    # 2. ATTENDANCE LOGS (hr.attendance)
    # -------------------------------------------------------------
    @http.route('/api/dashboard/attendance', type='json', auth='user', methods=['POST'], csrf=False)
    def get_attendance(self, page=1, limit=40, search='', filters=None, **kwargs):
        filters = filters or {}
        domain = []
        
        if search:
            domain += ['|', ('employee_id.name', 'ilike', search), ('employee_id.employee_number', 'ilike', search)]
        if filters.get('department_id'):
            domain.append(('employee_id.department_id', '=', int(filters['department_id'])))
        if filters.get('date'):
            domain += [('check_in', '>=', f"{filters['date']} 00:00:00"), ('check_in', '<=', f"{filters['date']} 23:59:59")]

        Attendance = request.env['hr.attendance'].sudo()
        total_count = Attendance.search_count(domain)
        offset = (page - 1) * limit
        attendances = Attendance.search(domain, offset=offset, limit=limit, order='check_in desc')

        records = []
        for att in attendances:
            emp = att.employee_id
            check_in_dt = fields.Datetime.context_timestamp(request.env.user, att.check_in) if att.check_in else None
            check_out_dt = fields.Datetime.context_timestamp(request.env.user, att.check_out) if att.check_out else None

            records.append({
                'id': att.id,
                'employee_id': emp.id,
                'employee_name': emp.name,
                'employee_code': emp.employee_number or emp.barcode or f"EMP-{emp.id}",
                'department': emp.department_id.name or 'Unassigned',
                'date': check_in_dt.strftime('%d %b %Y') if check_in_dt else '--',
                'check_in': check_in_dt.strftime('%I:%M %p') if check_in_dt else '-- : --',
                'check_out': check_out_dt.strftime('%I:%M %p') if check_out_dt else '-- : --',
                'worked_hours': round(att.worked_hours, 2) if att.worked_hours else 0.0,
                'avatar_url': f'/web/image/hr.employee/{emp.id}/avatar_128',
            })

        departments = request.env['hr.department'].sudo().search_read([], ['id', 'name'])

        return {
            'records': records,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit if total_count else 1,
            'filter_options': {'departments': departments}
        }

    # -------------------------------------------------------------
    # 3. LEAVE REQUESTS (hr.leave)
    # -------------------------------------------------------------
    @http.route('/api/dashboard/leaves', type='json', auth='user', methods=['POST'], csrf=False)
    def get_leaves(self, page=1, limit=40, search='', filters=None, **kwargs):
        filters = filters or {}
        today = fields.Date.today()
        domain = []

        if filters.get('state'):
            domain.append(('state', '=', filters['state']))
        if filters.get('leave_type_id'):
            domain.append(('holiday_status_id', '=', int(filters['leave_type_id'])))
        if filters.get('current_only'):
            domain += [('date_from', '<=', today), ('date_to', '>=', today)]
        if search:
            domain += [('employee_id.name', 'ilike', search)]

        Leave = request.env['hr.leave'].sudo()
        total_count = Leave.search_count(domain)
        offset = (page - 1) * limit
        leaves = Leave.search(domain, offset=offset, limit=limit, order='id desc')

        records = []
        for l in leaves:
            records.append({
                'id': l.id,
                'employee_name': l.employee_id.name,
                'leave_type': l.holiday_status_id.name,
                'date_from': fields.Date.to_string(l.date_from),
                'date_to': fields.Date.to_string(l.date_to),
                'number_of_days': l.number_of_days,
                'state': l.state,
                'avatar_url': f'/web/image/hr.employee/{l.employee_id.id}/avatar_128',
            })

        leave_types = request.env['hr.leave.type'].sudo().search_read([], ['id', 'name'])

        return {
            'records': records,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit if total_count else 1,
            'filter_options': {'leave_types': leave_types}
        }

    # -------------------------------------------------------------
    # 4. RECORD DETAIL FORM VIEW (Modal Fetch)
    # -------------------------------------------------------------
    @http.route('/api/dashboard/record/details', type='json', auth='user', methods=['POST'], csrf=False)
    def get_record_details(self, model, record_id, **kwargs):
        rec = request.env[model].sudo().browse(int(record_id))
        if not rec.exists():
            return {'error': 'Record not found'}

        if model == 'hr.employee':
            return {
                'id': rec.id,
                'name': rec.name,
                'employee_number': rec.employee_number or 'N/A',
                'work_email': rec.work_email or 'N/A',
                'work_phone': rec.work_phone or 'N/A',
                'job_title': rec.job_title or 'N/A',
                'department': rec.department_id.name or 'N/A',
                'company': rec.company_id.name or 'N/A',
                'parent': rec.parent_id.name or 'N/A',
                'avatar_url': f'/web/image/hr.employee/{rec.id}/avatar_256',
            }
        elif model == 'hr.attendance':
            return {
                'id': rec.id,
                'employee_name': rec.employee_id.name,
                'check_in': str(rec.check_in),
                'check_out': str(rec.check_out) if rec.check_out else 'N/A',
                'worked_hours': round(rec.worked_hours, 2),
            }
        elif model == 'hr.leave':
            return {
                'id': rec.id,
                'employee_name': rec.employee_id.name,
                'leave_type': rec.holiday_status_id.name,
                'date_from': str(rec.date_from),
                'date_to': str(rec.date_to),
                'number_of_days': rec.number_of_days,
                'state': rec.state,
                'notes': rec.name or 'N/A',
            }