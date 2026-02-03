import json
import logging
import psycopg2
import requests

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import config
from datetime import date, datetime

_logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_INSTALLED = True
except ImportError:
    requests = None
    REQUESTS_INSTALLED = False
    _logger.warning(
        "The 'requests' library is not installed. "
        "Image download functionality will be disabled. "
        "To enable it, please run 'pip install requests' on your server."
    )


class GISDataCollection(http.Controller):
    
    def db_connection(self):
        """GIS Data Collection API endpoint that accepts POST requests with JSON content,
        parses the data, and inserts it into the 'gis_cng_data' table."""
        try:
            conn = psycopg2.connect(
                dbname=config.get("gis_db_name"),
                user=config.get("gis_db_user"),
                password=config.get("gis_db_pass"),
                host=config.get("gis_db_host"),
                port=config.get("gis_db_port")
            )
            return conn
        except Exception as e:
            _logger.error("Database Connection Error: %s", str(e))
            raise ValidationError(f"Failed to connect to source database: {str(e)}")

    @http.route('/api/gis-data-collection', type='http', auth='none', methods=['POST'], csrf=False)
    def gis_data_collection(self):
        """
        Processes and inserts GIS data idempotently into the database.
        """
        try:
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                json_data = request.jsonrequest
            else:
                request_data = request.httprequest.get_data()
                json_data = json.loads(request_data.decode('utf-8')) if request_data else {}
            
            if not json_data:
                return self._make_json_response({'status': 'error', 'message': 'No data received.'}, status=400)

            records = json_data if isinstance(json_data, list) else [json_data]
            _logger.info("Processing %d record(s).", len(records))

            conn = None
            cursor = None
            try:
                conn = self.db_connection()
                cursor = conn.cursor()

                for record in records:
                    image_data = None
                    if REQUESTS_INSTALLED and record.get("_attachments") and isinstance(record["_attachments"], list):
                        image_url = record["_attachments"][0].get("download_url")
                        if image_url:
                            try:
                                response = requests.get(image_url.strip(), timeout=15)
                                response.raise_for_status()
                                image_data = response.content
                                _logger.info(f"Successfully downloaded image for Form74: {record.get('Input_Form74_Number')}")
                            except requests.exceptions.RequestException as e:
                                _logger.error(f"Failed to download image from {image_url}: {e}")
                                image_data = None
                    
                    data_map = {
                        'submission_uuid': record.get("_uuid"),
                        'staff_full_name': record.get("Staff_Full_Name"),
                        'staff_id': record.get("Staff_id"),
                        'input_form74_number': record.get("Input_Form74_Number"),
                        'customer_name': record.get("Customer_Name"),
                        'customer_address': record.get("Customer_Address"),
                        'customer_phone_number': record.get("Customer_Phone_Number"),
                        'customer_alternative_phone_number': record.get("Customer_Alternative_Phone_Number"),
                        'district': record.get("District"),
                        'date': record.get("Date"),
                        'remarks': record.get("Remarks") or None,
                        'remark_capture': image_data,
                    }

                    lat, lon, alt, acc = None, None, None, None
                    location_string = record.get("Record_your_current_location")
                    if isinstance(location_string, str):
                        parts = location_string.split()
                        if len(parts) == 4:
                            lat, lon, alt, acc = parts[0], parts[1], parts[2], parts[3]
                    
                    data_map.update({
                        'current_location_latitude': lat,
                        'current_location_longitude': lon,
                        'current_location_altitude': alt,
                        'current_location_accuracy': acc
                    })

                    columns = [k for k, v in data_map.items() if v is not None]
                    values = [data_map[col] for col in columns]
                    
                    sql = f"""
                        INSERT INTO gis_cng_data ({', '.join(columns)})
                        VALUES ({', '.join(['%s'] * len(values))})
                        ON CONFLICT (submission_uuid) DO NOTHING
                    """
                    
                    cursor.execute(sql, values)
                    _logger.info("Processed record with UUID: %s", data_map.get('submission_uuid'))
                
                conn.commit()
                
                return self._make_json_response({
                    'status': 'success',
                    'message': f"Successfully processed {len(records)} record(s).",
                }, status=201)

            except Exception as e:
                if conn:
                    conn.rollback()
                _logger.error("Database insertion failed: %s", str(e))
                return self._make_json_response({
                    'status': 'error',
                    'message': 'Database operation failed.',
                    'error': str(e)
                }, status=500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

        except Exception as e:
            _logger.error("Error processing GIS JSON request: %s", str(e))
            return self._make_json_response({
                'status': 'error',
                'message': 'Failed to process GIS data.',
                'error': str(e)
            }, status=400)

    def _make_json_response(self, data, status=200):
        """Helper to create a JSON response."""
        return request.make_response(
            json.dumps(data),
            headers={'Content-Type': 'application/json'},
            status=status
        )
    
    # ... health_check and test_endpoint methods remain the same ...
    @http.route('/api/health', type='http', auth='none', methods=['GET'], csrf=False)
    def health_check(self):
        """Simple health check endpoint."""
        return self._make_json_response({
            'status': 'healthy',
            'message': 'GIS Data Collection API is running'
        })

    @http.route('/api/gis-data-collection/test', type='http', auth='none', methods=['POST'], csrf=False)
    def test_endpoint(self):
        """Test endpoint without authentication for initial testing."""
        try:
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                json_data = request.jsonrequest
            else:
                request_data = request.httprequest.get_data()
                json_data = json.loads(request_data.decode('utf-8')) if request_data else {}
            
            _logger.info("TEST - Received GIS JSON data: %s", json.dumps(json_data, indent=2))
            
            return self._make_json_response({
                'status': 'success',
                'message': 'Test endpoint - GIS data received and logged successfully',
                'received_data': json_data
            })
        except Exception as e:
            _logger.error("TEST - Error processing GIS JSON request: %s", str(e))
            return self._make_json_response({
                'status': 'error',
                'message': 'Test endpoint - Failed to process GIS data',
                'error': str(e)
            }, status=400)