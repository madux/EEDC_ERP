import json
import logging
import psycopg2
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import config

_logger = logging.getLogger(__name__)


class GISDataCollection(http.Controller):
    
    def db_connection(self):
        """Connect to source database using environment variables."""
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
        GIS Data Collection API endpoint that accepts POST requests with JSON content,
        parses the data, and inserts it into the 'gis_cng_data' table.
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
                    data_map = {
                        'staff_full_name': record.get("Staff_Full_Name"),
                        'staff_id': record.get("Staff_id"),
                        'input_form74_number': record.get("Input_Form74_Number"),
                        'customer_name': record.get("Customer_Name"),
                        'customer_address': record.get("Customer_Address"),
                        'customer_phone_number': record.get("Customer_Phone_Number"),
                        'customer_alternative_phone_number': record.get("Customer_Alternative_Phone_Number"),
                        'district': record.get("District"),
                        'date': record.get("Date"),
                        'remarks': ", ".join(record.get("_notes", [])) or None,
                    }

                    lat, lon, alt, acc = None, None, None, None
                    location_string = record.get("Record_your_current_location")
                    if isinstance(location_string, str):
                        parts = location_string.split()
                        if len(parts) == 4:
                            lat = parts[0]
                            lon = parts[1]
                            alt = parts[2]
                            acc = parts[3]
                    
                    data_map.update({
                        'current_location_latitude': lat,
                        'current_location_longitude': lon,
                        'current_location_altitude': alt,
                        'current_location_accuracy': acc
                    })

                    columns = data_map.keys()
                    values = [data_map[col] for col in columns]
                    
                    sql = f"""
                        INSERT INTO gis_cng_data ({', '.join(columns)})
                        VALUES ({', '.join(['%s'] * len(values))})
                    """
                    
                    cursor.execute(sql, values)
                    _logger.info("Prepared to insert data for Form74: %s", data_map['input_form74_number'])

                conn.commit()
                
                return self._make_json_response({
                    'status': 'success',
                    'message': f"Successfully inserted {len(records)} record(s).",
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