from odoo import http, fields
from odoo.exceptions import ValidationError
from odoo.tools import consteq, plaintext2html
from odoo.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import base64
import json
import logging
import random

_logger = logging.getLogger(__name__)

class EedcReport(http.Controller):
    
    @http.route(['/web/dataset/autocomplete_companies'], type='http', auth="user", methods=['POST', 'OPTIONS'], csrf=False)
    def autocomplete_companies(self, **post):
        """Autocomplete endpoint for company selection with CORS support"""
        
        if request.httprequest.method == 'OPTIONS':
            return self._build_cors_preflight_response()
        
        try:
            query = post.get('q', '').strip()
            limit = int(post.get('page_limit', 10))
            
            _logger.info(f"Company autocomplete - Query: '{query}', Limit: {limit}")
            
            domain = [('active', '=', True)]
            if query:
                domain.append(('name', 'ilike', query))
            
            companies = request.env['res.company'].search(domain, limit=limit)
            
            results = [{"id": company.id, "text": company.name} for company in companies]
            
            response_data = {
                "results": results,
                "pagination": {"more": len(companies) >= limit}
            }
            
            _logger.info(f"Company autocomplete response: {len(results)} companies found")
            
            response = request.make_response(
                json.dumps(response_data),
                headers=self._get_cors_headers()
            )
            return response
            
        except Exception as e:
            _logger.error(f"Company autocomplete error: {str(e)}", exc_info=True)
            error_response = {
                "results": [], 
                "pagination": {"more": False}, 
                "error": str(e)
            }
            return request.make_response(
                json.dumps(error_response),
                headers=self._get_cors_headers()
            )
    
    def _get_cors_headers(self):
        """Return CORS headers for cross-origin requests"""
        return [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),  # Or specify your domain: 'https://apps.myeedc.com'
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With'),
            ('Access-Control-Max-Age', '3600'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ]
    
    def _build_cors_preflight_response(self):
        """Build response for OPTIONS preflight request"""
        response = request.make_response('', headers=self._get_cors_headers())
        response.status_code = 204  # No Content
        return response