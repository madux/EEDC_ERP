from odoo import http
from odoo.http import request

class RelativesDisclosureFormController(http.Controller):

    # @http.route('/relativesDisclosureForm', type='http', auth='public', website=True)
    @http.route('/relativesdisclosureform', type='http', auth='public', website=True)
    def relatives_disclosure_form(self, **post):
        return request.render('relatives_disclosure_form.website_relatives_disclosure_form', {})


    @http.route(['/relativesDisclosureForm/submit'], type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def relatives_disclosure_form_submit(self, **post):
        vals ={
            'employee_id': post.get('employee_id'),
            'staff_number': post.get('staff_number'),
            'designation': post.get('designation'),
            'location': int(post.get('location', 0)) or False,
            'department': int(post.get('department', 0)) or False,
            'state_of_origin': int(post.get('state_of_origin', 0)) or False,
            'village': post.get('village'),
            'town': post.get('town'),
            'lga': int(post.get('lga', 0)) or False,
            'permanent_address': post.get('permanent_address'),
            'gender': post.get('gender'),
            'marital_status': post.get('marital_status'),
            'maiden_name': post.get('maiden_name'),
        }
        record = request.env['relatives.disclosure.form'].sudo().create(vals)
        return request.render('relatives_disclosure_form.thank_you_template', {})
    #     return request.redirect('/relativesDisclosureForm/success')

    # @http.route('/relativesDisclosureForm/success', type='http', auth='user', website=True)
    # def relatives_disclosure_form_success(self, **post):
    #     return request.render('relatives_disclosure_form.website_relatives_disclosure_form_success', {})
