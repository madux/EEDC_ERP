from odoo import http, fields
from odoo.http import request
import datetime
from odoo.modules.module import get_resource_path

class AttendanceDashboardController(http.Controller):

    @http.route('/attendance-reporting', type='http', auth='user')
    def show_payroll_list(self, **kw):
        """Display memo list view"""
        file_path = get_resource_path(
            'hr_addons',
            'static/html',
            'attendance.html'
        )
        
        if not file_path:
            return "HTML file not found."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        return request.make_response(
            html,
            headers=[('Content-Type', 'text/html')]
        )
 

class AttendanceDashboardController(http.Controller):

    @http.route('/api/attendance/dashboard', type='json', auth='user', methods=['POST'], csrf=False)
    def get_dashboard_data(self, **kwargs):
        today = fields.Date.today()
        start_of_day = datetime.datetime.combine(today, datetime.time.min)
        end_of_day = datetime.datetime.combine(today, datetime.time.max)

        # 1. Fetch Active Employees Only
        employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
        total_employees = len(employees)

        # 2. Fetch Today's Attendance Records for Active Employees
        attendances = request.env['hr.attendance'].sudo().search([
            ('check_in', '>=', start_of_day),
            ('check_in', '<=', end_of_day),
            ('employee_id.active', '=', True)
        ])

        attended_emp_ids = set()
        logs = []
        late_count = 0
        work_start_hour = 9

        # Date string formatted for display (e.g., "30 Sep 2026")
        formatted_date = today.strftime('%d %b %Y')

        # 3. Process Attendance Log Entries
        for att in attendances:
            emp = att.employee_id
            attended_emp_ids.add(emp.id)
            
            check_in_dt = fields.Datetime.context_timestamp(request.env.user, att.check_in) if att.check_in else None
            check_out_dt = fields.Datetime.context_timestamp(request.env.user, att.check_out) if att.check_out else None

            is_late = check_in_dt and (check_in_dt.hour > work_start_hour or (check_in_dt.hour == work_start_hour and check_in_dt.minute > 0))
            if is_late:
                late_count += 1

            status = "Late" if is_late else "Present"
            emp_code = emp.employee_number or emp.barcode or f"EMP-{emp.id}"

            logs.append({
                'id': att.id,
                'employee_id': emp.id,
                'employee_name': emp.name,
                'employee_code': emp_code,
                'date': check_in_dt.strftime('%d %b %Y') if check_in_dt else formatted_date,
                'department': emp.department_id.name or 'Unassigned',
                'district': emp.branch_id.name if hasattr(emp, 'branch_id') and emp.branch_id else 'Unassigned',
                'company': emp.company_id.name or 'Unassigned',
                'avatar_url': f'/web/image/hr.employee/{emp.id}/avatar_128',
                'check_in': check_in_dt.strftime('%I:%M %p') if check_in_dt else '-- : --',
                'check_out': check_out_dt.strftime('%I:%M %p') if check_out_dt else '-- : --',
                'worked_hours': round(att.worked_hours, 2) if att.worked_hours else 0.0,
                'status': status
            })

        # 4. Process Absent Active Employees
        absent_employees = employees.filtered(lambda e: e.id not in attended_emp_ids)
        for emp in absent_employees:
            leave = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', emp.id),
                ('date_from', '<=', end_of_day),
                ('date_to', '>=', start_of_day),
                ('state', '=', 'validate')
            ], limit=1)

            status = "On Leave" if leave else "Absent"
            emp_code = emp.employee_number or emp.barcode or f"EMP-{emp.id}"

            logs.append({
                'id': f"absent_{emp.id}",
                'employee_id': emp.id,
                'employee_name': emp.name,
                'employee_code': emp_code,
                'date': formatted_date,
                'department': emp.department_id.name or 'Unassigned',
                'district': emp.branch_id.name if hasattr(emp, 'branch_id') and emp.branch_id else 'Unassigned',
                'company': emp.company_id.name or 'Unassigned',
                'avatar_url': f'/web/image/hr.employee/{emp.id}/avatar_128',
                'check_in': '-- : --',
                'check_out': '-- : --',
                'worked_hours': 0.0,
                'status': status
            })

        present_count = len(attended_emp_ids)
        absent_count = len(absent_employees)

        # 5. Weekly Trend (Last 5 Days)
        weekly_labels = []
        weekly_data = []
        for i in range(4, -1, -1):
            day_date = today - datetime.timedelta(days=i)
            day_start = datetime.datetime.combine(day_date, datetime.time.min)
            day_end = datetime.datetime.combine(day_date, datetime.time.max)
            
            day_count = request.env['hr.attendance'].sudo().search_count([
                ('check_in', '>=', day_start),
                ('check_in', '<=', day_end),
                ('employee_id.active', '=', True)
            ])
            
            rate = round((day_count / total_employees * 100), 1) if total_employees else 0
            weekly_labels.append(day_date.strftime('%a'))
            weekly_data.append(rate)

        return {
            'summary': {
                'total_personnel': total_employees,
                'present': present_count,
                'late': late_count,
                'absent': absent_count,
                'present_rate': round((present_count / total_employees * 100), 1) if total_employees else 0
            },
            'weekly_trend': {
                'labels': weekly_labels,
                'data': weekly_data
            },
            'logs': logs
        }