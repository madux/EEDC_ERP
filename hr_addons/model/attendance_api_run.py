import requests
import json

url = "http://localhost:8069/api/hr/attendance/bulk"

payload = {
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
        },
        {
            "employee_number": "EMP002",
            "attendance_date": "2026-09-30",
            "attendance_time": "08:15:00",
            "transaction_type": "check_in"
        },
        {
            "employee_number": "EMP002",
            "attendance_date": "2026-09-30",
            "attendance_time": "17:05:00",
            "transaction_type": "check_out"
        }
    ]
}

response = requests.post(
    url,
    json=payload,
    timeout=120
)

print("Status:", response.status_code)

try:
    result = response.json()
    print(json.dumps(result, indent=4))
except Exception:
    print(response.text)