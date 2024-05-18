from odoo import api, models, fields

class Transformer(models.Model):
    _name = 'transformer'
    _description = 'Transformer'

    name = fields.Char(required=True)
    serial_number = fields.Char(string='Serial Number', required=True)
    district = fields.Many2one('hr.district')
    sub_station = fields.Many2one('injection.substation')
    dss_type = fields.Selection(
        selection=[('public', 'Public'),
                   ('private', 'Private'),
                   ('bulk', 'Bulk')]  # Corrected the casing of 'bulk'
    )
    dss_make = fields.Char()
    dss_capacity = fields.Integer()
    rating = fields.Integer()
    oil_weight = fields.Integer('Oil Weight (Kg)')
    impedance = fields.Integer()  # Corrected the casing of 'Integer'
    date_of_manufacture = fields.Date()
    location_address = fields.Char('Location Address')
    failed_transformer_movement_ids = fields.One2many('failed.transformer.issue', 'transformer_id')  # Changed field name to plural

class InjectionSubstation(models.Model):
    _name = 'injection.substation'
    _description = 'Injection Substation'

    name = fields.Char('Substation', required=True)  # Added required attribute
