from odoo import http, fields
from odoo.http import request
import base64

class RelativesDisclosureFormController(http.Controller):

    @http.route('/relativesDisclosureForm', type='http', auth='public', website=True)
    def relatives_disclosure_form(self, **post):
        departments = request.env['hr.department'].sudo().search([])
        locations = request.env['hr.district'].sudo().search([])
        nigeria = request.env['res.country'].sudo().search([('code', '=', 'NG')], limit=1)
        states = request.env['res.country.state'].sudo().search([('country_id', '=', nigeria.id)]) if nigeria else []
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
        relative_names = request.params.getlist('relative_name[]')
        relationships = request.params.getlist('relationship[]')
        relative_districts = request.params.getlist('relative_district[]')
        relative_departments = request.params.getlist('relative_department[]')

        relative_ids = []
        for i in range(len(relative_names)):
            if relative_names[i].strip():  # Skip empty rows
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
