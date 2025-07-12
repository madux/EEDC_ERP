import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class GISDataCollection(http.Controller):
   
    @http.route('/api/gis-data-collection', type='http', auth='user', methods=['POST'], csrf=False)
    def log_json_data(self):
        """
        GIS Data Collection API endpoint that accepts POST requests with JSON content
        and logs the received data for analysis before database sync.
        """
        try:
            # Get JSON data from request body
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                json_data = request.jsonrequest
            else:
                # Fallback method - read from request body
                request_data = request.httprequest.get_data()
                if request_data:
                    json_data = json.loads(request_data.decode('utf-8'))
                else:
                    json_data = {}
           
            _logger.info("Received GIS JSON data: %s", json.dumps(json_data, indent=2))
           
            # Log field names for database schema planning
            if isinstance(json_data, dict):
                field_names = list(json_data.keys())
                _logger.info("Fields detected: %s", field_names)
            elif isinstance(json_data, list) and json_data:
                # If it's a list, get field names from first item
                first_item = json_data[0] if json_data else {}
                if isinstance(first_item, dict):
                    field_names = list(first_item.keys())
                    _logger.info("Fields detected in array: %s", field_names)
                    _logger.info("Number of records: %d", len(json_data))
           
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'message': 'GIS data received and logged successfully',
                    'received_data': json_data
                }),
                headers={'Content-Type': 'application/json'}
            )
           
        except Exception as e:
            _logger.error("Error processing GIS JSON request: %s", str(e))
           
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': 'Failed to process GIS data',
                    'error': str(e)
                }),
                headers={'Content-Type': 'application/json'},
                status=400
            )

    @http.route('/api/health', type='http', auth='none', methods=['GET'], csrf=False)
    def health_check(self):
        """
        Simple health check endpoint
        """
        return request.make_response(
            json.dumps({
                'status': 'healthy',
                'message': 'GIS Data Collection API is running'
            }),
            headers={'Content-Type': 'application/json'}
        )

    @http.route('/api/gis-data-collection/test', type='http', auth='none', methods=['POST'], csrf=False)
    def test_endpoint(self):
        """
        Test endpoint without authentication for initial testing
        """
        try:
            # Get JSON data from request body
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                json_data = request.jsonrequest
            else:
                # Fallback method - read from request body
                request_data = request.httprequest.get_data()
                if request_data:
                    json_data = json.loads(request_data.decode('utf-8'))
                else:
                    json_data = {}
           
            _logger.info("TEST - Received GIS JSON data: %s", json.dumps(json_data, indent=2))
           
            return request.make_response(
                json.dumps({
                    'status': 'success',
                    'message': 'Test endpoint - GIS data received and logged successfully',
                    'received_data': json_data
                }),
                headers={'Content-Type': 'application/json'}
            )
           
        except Exception as e:
            _logger.error("TEST - Error processing GIS JSON request: %s", str(e))
           
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': 'Test endpoint - Failed to process GIS data',
                    'error': str(e)
                }),
                headers={'Content-Type': 'application/json'},
                status=400
            )