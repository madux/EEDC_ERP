from odoo import http
from odoo.http import request
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)


# how to run using python request 
# import requests
# import json

# url = "http://localhost:8069/api/hr/attendance/bulk"

# payload = {
#     "attendance_records": [
#         {
#             "employee_number": "EMP001",
#             "attendance_date": "2026-09-30",
#             "attendance_time": "08:00:00",
#             "transaction_type": "check_in"
#         },
#         {
#             "employee_number": "EMP001",
#             "attendance_date": "2026-09-30",
#             "attendance_time": "17:00:00",
#             "transaction_type": "check_out"
#         },
#         {
#             "employee_number": "EMP002",
#             "attendance_date": "2026-09-30",
#             "attendance_time": "08:15:00",
#             "transaction_type": "check_in"
#         },
#         {
#             "employee_number": "EMP002",
#             "attendance_date": "2026-09-30",
#             "attendance_time": "17:05:00",
#             "transaction_type": "check_out"
#         }
#     ]
# }

# response = requests.post(
#     url,
#     json=payload,
#     timeout=120
# )

# print("Status:", response.status_code)

# try:
#     result = response.json()
#     print(json.dumps(result, indent=4))
# except Exception:
#     print(response.text)



Payload = {
        "attendance_records": [
            {
            "employee_number": "EMP001",
            "attendance_date": "2026-09-30",
            "attendance_time": "08:00:00",
            "transaction_type": "check_in"
            },
            {
            "employee_number": "EMP001",
            "attendance_date": "2026-09-30",
            "attendance_time": "17:00:00",
            "transaction_type": "check_out"
            }
        ]
    }


class AttendanceAPI(http.Controller):

    @http.route(
        '/api/hr/attendance/bulk',
        type='http',
        auth='none',
        csrf=False,
        methods=['POST']
    )
    def bulk_attendance(self, **kwargs):

        try:
            # ==========================================================
            # 1. READ JSON BODY
            # ==========================================================

            raw_data = request.httprequest.get_data(as_text=True)

            if not raw_data:
                return request.make_json_response({
                    'status': False,
                    'message': 'Empty request body'
                }, status=400)

            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError as e:
                return request.make_json_response({
                    'status': False,
                    'message': 'Invalid JSON payload',
                    'error': str(e)
                }, status=400)

            attendance_records = data.get('attendance_records', [])

            if not isinstance(attendance_records, list):
                return request.make_json_response({
                    'status': False,
                    'message': 'attendance_records must be a list'
                }, status=400)

            if not attendance_records:
                return request.make_json_response({
                    'status': False,
                    'message': 'No attendance records supplied'
                }, status=400)

            _logger.info(
                "Attendance API received %s records",
                len(attendance_records)
            )

            # ==========================================================
            # 2. ODOO MODELS
            # ==========================================================

            Employee = request.env['hr.employee'].sudo()
            Attendance = request.env['hr.attendance'].sudo()

            # ==========================================================
            # 3. LOAD EMPLOYEES ONCE
            # ==========================================================

            employee_numbers = list({
                str(record.get('employee_number')).strip()
                for record in attendance_records
                if record.get('employee_number')
            })

            employees = Employee.search([
                ('employee_number', 'in', employee_numbers)
            ])

            employee_map = {
                str(employee.employee_number).strip(): employee
                for employee in employees
            }

            # ==========================================================
            # 4. PARSE DATES FIRST
            # ==========================================================

            parsed_records = []

            for index, record in enumerate(attendance_records):

                employee_number = str(
                    record.get('employee_number') or ''
                ).strip()

                attendance_date = str(
                    record.get('attendance_date') or ''
                ).strip()

                attendance_time = str(
                    record.get('attendance_time') or ''
                ).strip()

                transaction_type = str(
                    record.get('transaction_type') or ''
                ).strip().lower()

                parsed_records.append({
                    'index': index,
                    'employee_number': employee_number,
                    'attendance_date': attendance_date,
                    'attendance_time': attendance_time,
                    'transaction_type': transaction_type,
                    'raw': record,
                })

            # ==========================================================
            # 5. DETERMINE DATE RANGE
            # ==========================================================

            valid_dates = []

            for record in parsed_records:

                if not record['attendance_date']:
                    continue

                try:
                    date_value = datetime.strptime(
                        record['attendance_date'],
                        '%Y-%m-%d'
                    ).date()

                    valid_dates.append(date_value)

                except ValueError:
                    continue

            if not valid_dates:
                return request.make_json_response({
                    'status': False,
                    'message': 'No valid attendance dates supplied'
                }, status=400)

            min_date = min(valid_dates)
            max_date = max(valid_dates)

            # ==========================================================
            # 6. LOAD EXISTING ATTENDANCES ONCE
            #
            # We load records whose check_in falls within the
            # requested date range.
            # ==========================================================

            existing_attendances = Attendance.search([
                ('check_in', '>=',
                 datetime.combine(min_date, datetime.min.time())),

                ('check_in', '<=',
                 datetime.combine(max_date, datetime.max.time())),
            ])

            # ==========================================================
            # 7. CREATE LOOKUP
            #
            # key:
            #     (employee_id, attendance_date)
            #
            # value:
            #     hr.attendance record
            # ==========================================================

            attendance_lookup = {}

            for attendance in existing_attendances:

                key = (
                    attendance.employee_id.id,
                    attendance.check_in.date()
                )

                attendance_lookup[key] = attendance

            # ==========================================================
            # 8. PROCESS RECORDS
            # ==========================================================

            pending_creates = {}

            pending_updates = {}

            failed = []

            created_count = 0
            updated_count = 0

            for record in parsed_records:

                employee_number = record['employee_number']
                attendance_date = record['attendance_date']
                attendance_time = record['attendance_time']
                transaction_type = record['transaction_type']

                # ------------------------------------------------------
                # Employee
                # ------------------------------------------------------

                employee = employee_map.get(employee_number)

                if not employee:
                    failed.append({
                        'index': record['index'],
                        'employee_number': employee_number,
                        'attendance_date': attendance_date,
                        'reason': 'Employee not found'
                    })
                    continue

                # ------------------------------------------------------
                # Required fields
                # ------------------------------------------------------

                if not attendance_date:

                    failed.append({
                        'index': record['index'],
                        'employee_number': employee_number,
                        'reason': 'attendance_date is required'
                    })
                    continue

                if not attendance_time:

                    failed.append({
                        'index': record['index'],
                        'employee_number': employee_number,
                        'attendance_date': attendance_date,
                        'reason': 'attendance_time is required'
                    })
                    continue

                # ------------------------------------------------------
                # Validate transaction type
                # ------------------------------------------------------

                if transaction_type not in (
                    'check_in',
                    'check_out'
                ):

                    failed.append({
                        'index': record['index'],
                        'employee_number': employee_number,
                        'attendance_date': attendance_date,
                        'reason': (
                            'transaction_type must be '
                            'check_in or check_out'
                        )
                    })
                    continue

                # ------------------------------------------------------
                # Parse datetime
                # ------------------------------------------------------

                try:

                    attendance_datetime = datetime.strptime(
                        f'{attendance_date} {attendance_time}',
                        '%Y-%m-%d %H:%M:%S'
                    )

                except ValueError:

                    failed.append({
                        'index': record['index'],
                        'employee_number': employee_number,
                        'attendance_date': attendance_date,
                        'attendance_time': attendance_time,
                        'reason': (
                            'Invalid date/time. Expected '
                            'YYYY-MM-DD and HH:MM:SS'
                        )
                    })
                    continue

                # ------------------------------------------------------
                # Lookup key
                # ------------------------------------------------------

                lookup_key = (
                    employee.id,
                    attendance_datetime.date()
                )

                # ======================================================
                # CHECK-IN
                # ======================================================

                if transaction_type == 'check_in':

                    # Existing database attendance
                    if lookup_key in attendance_lookup:

                        failed.append({
                            'index': record['index'],
                            'employee_number': employee_number,
                            'attendance_date': attendance_date,
                            'reason': 'Check-in already exists'
                        })

                        continue

                    # Another check-in already received in this
                    # same API request
                    if lookup_key in pending_creates:

                        failed.append({
                            'index': record['index'],
                            'employee_number': employee_number,
                            'attendance_date': attendance_date,
                            'reason': (
                                'Multiple check-ins supplied '
                                'for the same employee/date'
                            )
                        })

                        continue

                    # Create in memory first
                    pending_creates[lookup_key] = {
                        'employee_id': employee.id,
                        'check_in': attendance_datetime,
                    }

                    continue

                # ======================================================
                # CHECK-OUT
                # ======================================================

                if transaction_type == 'check_out':

                    # --------------------------------------------------
                    # Case 1:
                    # A new check-in was supplied earlier in the
                    # same API request.
                    # --------------------------------------------------

                    pending_checkin = pending_creates.get(
                        lookup_key
                    )

                    if pending_checkin:

                        if pending_checkin.get('check_out'):

                            failed.append({
                                'index': record['index'],
                                'employee_number': employee_number,
                                'attendance_date': attendance_date,
                                'reason': 'Check-out already supplied'
                            })

                            continue

                        pending_checkin['check_out'] = (
                            attendance_datetime
                        )

                        continue

                    # --------------------------------------------------
                    # Case 2:
                    # Existing database attendance
                    # --------------------------------------------------

                    existing_attendance = attendance_lookup.get(
                        lookup_key
                    )

                    if not existing_attendance:

                        failed.append({
                            'index': record['index'],
                            'employee_number': employee_number,
                            'attendance_date': attendance_date,
                            'reason': 'No matching check-in found'
                        })

                        continue

                    # --------------------------------------------------
                    # Check if already checked out
                    # --------------------------------------------------

                    if existing_attendance.check_out:

                        failed.append({
                            'index': record['index'],
                            'employee_number': employee_number,
                            'attendance_date': attendance_date,
                            'reason': 'Check-out already exists'
                        })

                        continue

                    # --------------------------------------------------
                    # Store update for later
                    # --------------------------------------------------

                    pending_updates[
                        existing_attendance.id
                    ] = {
                        'record': existing_attendance,
                        'check_out': attendance_datetime,
                    }

            # ==========================================================
            # 9. BULK CREATE
            # ==========================================================

            create_vals = list(
                pending_creates.values()
            )

            BATCH_SIZE = 1000

            created_attendances = []

            for i in range(
                0,
                len(create_vals),
                BATCH_SIZE
            ):

                batch = create_vals[
                    i:i + BATCH_SIZE
                ]

                created = Attendance.create(batch)

                created_attendances.extend(created)

            created_count = len(created_attendances)

            # ==========================================================
            # 10. APPLY CHECK-OUT UPDATES
            # ==========================================================

            for update in pending_updates.values():

                attendance = update['record']

                attendance.write({
                    'check_out': update['check_out']
                })

                updated_count += 1

            # ==========================================================
            # 11. RESPONSE
            # ==========================================================

            return request.make_json_response({
                'status': True,
                'message': 'Attendance processing completed',

                'received': len(attendance_records),

                'created': created_count,

                'updated': updated_count,

                'failed_count': len(failed),

                'failed': failed,
            })

        # ==============================================================
        # UNEXPECTED ERROR
        # ==============================================================

        except Exception as e:

            _logger.exception(
                'Attendance API unexpected error'
            )

            return request.make_json_response({
                'status': False,
                'message': 'An unexpected server error occurred',
                'error': str(e),
            }, status=500)