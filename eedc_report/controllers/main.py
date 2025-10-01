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
    @http.route(['/web/dataset/autocomplete_companies'], type='http', auth="user", methods=['POST'], csrf=False)
    def autocomplete_companies(self, **post):
        """Autocomplete endpoint for company selection"""
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
            
            _logger.info(f"Company autocomplete response: {response_data}")
            
            response = request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )
            return response
            
        except Exception as e:
            _logger.error(f"Company autocomplete error: {str(e)}")
            error_response = {"results": [], "pagination": {"more": False}, "error": str(e)}
            return request.make_response(
                json.dumps(error_response),
                headers=[('Content-Type', 'application/json')]
            )