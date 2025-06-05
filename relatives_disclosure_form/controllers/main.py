from odoo import http, fields
from odoo.http import request

class RelativesDisclosureFormController(http.Controller):

    @http.route('/relativesDisclosureForm', type='http', auth='public', website=True)
    def relatives_disclosure_form(self, **post):
        departments = request.env['hr.department'].sudo().search([])
        locations = request.env['hr.district'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        lgas = request.env['res.lga'].sudo().search([])

        return request.render('relatives_disclosure_form.relatives_disclosure_form_template', {
            'departments': departments,
            'locations': locations,
            'states': states,
            'lgas': lgas,
            # You can also pass old values here for sticky form on error
        })

    @http.route('/relativesDisclosureForm/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def relatives_disclosure_form_submit(self, **post):
        # Convert string IDs to integers or set False if not provided
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
        }
        # Optionally: Validate required fields here
        request.env['relatives.disclosure.form'].sudo().create(vals)
        return request.render('relatives_disclosure_form.thank_you_template', {})

