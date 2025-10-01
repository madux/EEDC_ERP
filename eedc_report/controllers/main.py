from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class EedcReport(http.Controller):
    
    @http.route([
        '/report/html/<string:report_name>/<int:wizard_id>',
    ], type='http', auth="user", methods=['GET'], csrf=False)
    def report_html_wizard(self, report_name, wizard_id, **kw):
        """Custom route to handle report generation from wizard"""
        try:
            wizard = request.env['account.dynamic.report'].sudo().browse(wizard_id)
            if not wizard.exists():
                return request.not_found("Wizard not found")
            
            report_data = wizard._generate_report_data()
            
            data = {
                'doc_model': 'account.dynamic.report',
                'company_reports': report_data,
                'wizard_id': wizard_id,
                'wizard': wizard,
                'account_types': wizard._fields['account_type'].selection,
            }
            
            html = request.env['ir.qweb'].sudo()._render(
                'eedc_report.consolidated_district_report_template', 
                data
            )
            
            return request.make_response(
                html,
                headers=[
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('X-Frame-Options', 'SAMEORIGIN'),
                ]
            )
            
        except Exception as e:
            _logger.error(f"Report error: {str(e)}", exc_info=True)
            return request.make_response(
                f"<html><body><h3>Error generating report</h3><p>{str(e)}</p></body></html>",
                headers=[('Content-Type', 'text/html')]
            )
    
    @http.route(['/web/dataset/autocomplete_companies'], 
                type='http', auth="user", methods=['POST'], csrf=False)
    def autocomplete_companies(self, **kw):
        """HTTP autocomplete for companies"""
        _logger.info(f"Autocomplete KW: {kw}")
        try:
            q = kw.get('q', '').strip()
            try:
                page_limit = int(kw.get('page_limit', 15))
            except ValueError:
                page_limit = 15
            
            domain = [('active', '=', True)]
            if q:
                domain.append(('name', 'ilike', q))
                
            _logger.info(f"Autocomplete Search Domain: {domain}")
            
            companies = request.env['res.company'].search(domain, limit=page_limit)
            results = [{"id": c.id, "text": c.name} for c in companies]
            
            _logger.info(f"Result of search: {results}")
            
            response_data = {
                "results": results,
                "pagination": {"more": len(companies) >= page_limit}
            }
            
            return request.make_response(
                json.dumps(response_data),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            _logger.error(f"Autocomplete error: {str(e)}")
            return request.make_response(
                json.dumps({"results": [], "pagination": {"more": False}}),
                headers=[('Content-Type', 'application/json')]
            )