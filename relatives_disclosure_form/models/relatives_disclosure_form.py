from odoo import models, fields, api, _

class RelativesDisclosureForm(models.Model):
    _name = 'relatives.disclosure.form'
    _description = 'Relatives Disclosure Form'

    employee_id = fields.Char(string='Employee', required=True)
    staff_number = fields.Char(string="Staff Number")
    designation = fields.Char(string="Designation")
    location = fields.Many2one('hr.district', string='Location')
    department = fields.Many2one('hr.department', string='Department')
    state_of_origin = fields.Many2one('res.country.state', string='State of Origin')
    village = fields.Char(string='Village')
    town = fields.Char(string='Town')
    lga = fields.Many2one('res.lga', string='LGA')
    permanent_address = fields.Char(string='Permanent Address')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    maiden_name = fields.Char(string='Maiden Name')
    has_relatives = fields.Boolean(string='Do you have relatives in the company?', default=False)
    relative_ids = fields.One2many('relatives.disclosure.form.relative', 'form_id', string='Relatives')
    signature = fields.Binary(string='Signature')
    date = fields.Date(string='Date', default=fields.Date.context_today)

class RelativesDisclosureFormRelative(models.Model):
    _name = 'relatives.disclosure.form.relative'
    _description = 'Relative in EEDC'

    form_id = fields.Many2one('relatives.disclosure.form', string='Disclosure Form', ondelete='cascade')
    relative_name = fields.Char(string='Relative Name', required=True)
    relationship = fields.Selection([
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('child', 'Child'),
        ('niece', 'Niece'),
        ('nephew', 'Nephew'),
        ('other', 'Other')
    ], string='Relationship', required=True)
    relative_district = fields.Many2one('hr.district', string='Relative District')
    relative_department = fields.Many2one('hr.department', string='Relative Department')

