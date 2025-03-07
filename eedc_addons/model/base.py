from odoo import models, fields, api, _

class District(models.Model):
    _inherit = "hr.district"

    name = fields.Char('District') 
    code = fields.Char('Code')
    lga_id = fields.Many2one('res.lga', 'LGA')
    state_id = fields.Many2one('res.country.state', 'State')
    company_id = fields.Many2one('res.company', string='Company')

    ###### 
    telephone_no = fields.Char("Telephone No")
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=True, default=lambda self: self.env['res.company']._company_default_get())
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char(required=False)
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one("res.country.state", string='State', domain="[('country_id', '=?', country_id)]")
    is_testcenter = fields.Boolean('Is Test Center?')
    is_online_store = fields.Boolean('Is Online store?')
    alias_display = fields.Char(string="Alias", 
    help="This will be the name to display on the dropdown for shop")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    branch_id = fields.Many2one('multi.branch', string='Branch')
    parent_id = fields.Integer('Branch ID')
    district_id = fields.Many2one('hr.district', string='Related District')
    simplybook_location_id = fields.Char(string="Simplybook ID")
    active = fields.Boolean(default=True)


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    lga_ids = fields.One2many('res.lga', 'state_id', string="LGA(s)") 
 

class LGA(models.Model):
    _name = "res.lga"

    name = fields.Char('Name')
    code = fields.Char('Code')
    state_id = fields.Many2one('res.country.state', 'State', required=True)
    # state_name = fields.Char('Compute state', compute="get_real_state")

    # @api.depends('state_name')
    # def get_real_state(self):
    #     self.ensure_one()
    #     state = self.env['res.country.state'].search([('name', '=', self.state_name)], limit=1)
    #     self.state_id = state.id if state else None


class BusinessUnit(models.Model):
    _inherit = "hr.work.unit"

    code = fields.Char('Code')


class HrRank(models.Model):
    _name = "hr.rank"

    name = fields.Char('Rank')
    code = fields.Char('Code')
    salary_range = fields.Text(string='Salary Range')
    grade_id = fields.Many2one('hr.grade', string='Grade')


class HrRank(models.Model):
    _inherit = "hr.grade"

    name = fields.Char('Grade')
    code = fields.Char('Code')


class HRExperience(models.Model):
    _name = "hr.experience"

    name = fields.Char(
        'Name'
        )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
        )
    institution = fields.Char(
        'Institution'
        )
    start_date = fields.Date(
        'Start Date'
        )
    end_date = fields.Date(
        'End Date'
        )
    expiry_date = fields.Date(
        'Expiry Date'
        )
    cert_number = fields.Char(
        'Certificate'
        )
    issue_by = fields.Char('Issue by')


class HRCertification(models.Model):
    _name = "hr.certification"

    name = fields.Char(
        'Name'
        )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
        )
    institution = fields.Many2one(
        'res.partner',
        'Institution'
        )
    start_date = fields.Date(
        'Start Date'
        )
    end_date = fields.Date(
        'End Date'
        )
    expiry_date = fields.Date(
        'Expiry Date'
        )
    cert_number = fields.Char('Certificate')
    issue_by = fields.Char('Issue by')


class HRAcademic(models.Model):
    _name = "hr.academic"

    name = fields.Char(
        'Name'
        )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
        )
    institution = fields.Many2one(
        'res.partner',
        'Institution'
        )
    start_date = fields.Date(
        'Start Date'
        )
    end_date = fields.Date(
        'End Date'
        )
    expiry_date = fields.Date(
        'Expiry Date'
        )
    cert_number = fields.Char(
        'Certificate'
        )
    field_of_study = fields.Char(
        'Field of Study'
        )
    issue_by = fields.Char('Issue by')

