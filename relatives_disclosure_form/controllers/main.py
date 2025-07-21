from odoo import http, fields
from odoo.http import request
import base64
import logging
_logger = logging.getLogger(__name__)

class RelativesDisclosureFormController(http.Controller):

    @http.route('/relativesDisclosureForm', type='http', auth='public', website=True)
    def relatives_disclosure_form(self, **post):
        departments = request.env['hr.department'].sudo().search([])
        locations = request.env['hr.district'].sudo().search([])
        nigeria = request.env['res.country'].sudo().search([('code', '=', 'NG')], limit=1)

        states = request.env['res.country.state'].sudo().search([
            ('country_id', '=', nigeria.id),
            ('lga_ids', '!=', False)
        ]) if nigeria else []

        lgas = request.env['res.lga'].sudo().search([])

        return request.render('relatives_disclosure_form.relatives_disclosure_form_template', {
            'departments': departments,
            'locations': locations,
            'states': states,
            'lgas': lgas,
        })

    @http.route('/relativesDisclosureForm/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def relatives_disclosure_form_submit(self, **post):
        # Get the file
        signature_file = request.httprequest.files.get('signature_file')
        signature_data = False
        signature_filename = ''
        if signature_file:
            signature_data = base64.b64encode(signature_file.read())
            signature_filename = signature_file.filename

        # Handle relatives before creating form
        relative_names = request.httprequest.form.getlist('relative_name[]')
        relationships = request.httprequest.form.getlist('relationship[]')
        relative_districts = request.httprequest.form.getlist('relative_district[]')
        relative_departments = request.httprequest.form.getlist('relative_department[]')


        relative_ids = []
        for i in range(len(relative_names)):
            if relative_names[i].strip(): 
                relative_ids.append((0, 0, {
                    'relative_name': relative_names[i],
                    'relationship': relationships[i],
                    'relative_district': int(relative_districts[i]) if relative_districts[i] else False,
                    'relative_department': int(relative_departments[i]) if relative_departments[i] else False,
                }))

        vals = {
            'employee_id': post.get('employee_id'),
            'staff_number': post.get('staff_number'),
            'designation': post.get('designation'),
            'location': int(post.get('location')) if post.get('location') else False,
            'department': int(post.get('department')) if post.get('department') else False,
            'state_of_origin': int(post.get('state_of_origin')) if post.get('state_of_origin') else False,
            'village': post.get('village'),
            'town': post.get('town'),
            'lga': int(post.get('lga')) if post.get('lga') else False,
            'permanent_address': post.get('permanent_address'),
            'gender': post.get('gender'),
            'marital_status': post.get('marital_status'),
            'maiden_name': post.get('maiden_name'),
            'signature': signature_data,
            'signature_filename': signature_filename,
            'submission_date': fields.Datetime.now(),
            'relative_ids': relative_ids,
        }

        request.env['relatives.disclosure.form'].sudo().create(vals)
        return request.render('relatives_disclosure_form.thank_you_template', {})
    
    

    @http.route(['/relativesDisclosureForm/check_staffid'], type='json', website=True, auth="public", csrf=False)
    def check_staff_num(self, **post):
        staff_num = post.get('staff_num', '').strip()

        if not staff_num:
            return {
                "status": False,
                "data": {"name": "", "phone": "", "work_email": ""},
                "message": "No staff number provided.",
            }

        employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
        matched = employees.filtered(lambda e: e.employee_number and e.employee_number.strip() == staff_num)

        if matched:
            employee = matched[0]
            return {
                "status": True,
                "data": {
                    "name": employee.name or "",
                    "phone": employee.work_phone or employee.mobile_phone or "",
                    "work_email": employee.work_email or "",
                },
                "message": "",
            }

        return {
            "status": False,
            "data": {"name": "", "phone": "", "work_email": ""},
            "message": "Employee with staff ID provided does not exist. Contact Admin",
        }


    @http.route('/get_lgas_by_state', type='json', auth='public', csrf=False)
    def get_lgas_by_state(self, **post):
        try:
            # Handle both direct params and nested params structure
            state_id = post.get('state_id')
            if not state_id and 'params' in post:
                state_id = post['params'].get('state_id')
                
            if not state_id:
                _logger.warning("[LGA] state_id is missing.")
                return []

            try:
                state_id = int(state_id)
            except (ValueError, TypeError):
                _logger.error(f"[LGA] Invalid state_id: {state_id}")
                return []

            state = request.env['res.country.state'].sudo().browse(state_id)
            if not state.exists():
                _logger.warning(f"[LGA] No state found with ID {state_id}")
                return []

            lgas = state.lga_ids
            if not lgas:
                _logger.info(f"[LGA] No LGAs found for state {state.name}")
                return []

            result = [{'id': lga.id, 'name': lga.name} for lga in lgas]
            _logger.info(f"[LGA] Returning {len(result)} LGAs for state {state.name}")
            
            return result

        except Exception as e:
            _logger.error(f"[LGA] Exception occurred: {str(e)}")
            return []