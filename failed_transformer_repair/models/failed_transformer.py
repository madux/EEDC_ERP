from odoo import api, models, fields

class FailedTransformerMovement(models.Model):
    _name = 'failed.transformer.issue'
    _description = 'Failed Transformer Issue'

    transformer_id = fields.Many2one('transformer')
    transformer_name = fields.Char(related='transformer_id.name')
    date_registered = fields.Date()
    transformer_rating = fields.Integer(related='transformer_id.rating')
    transformer_make = fields.Char(related='transformer_id.dss_make')
    transformer_serialno = fields.Char(related='transformer_id.serial_number')
    substation = fields.Many2one(related='transformer_id.sub_station')
    oil_weight = fields.Integer(related='transformer_id.oil_weight')
    transformer_impedance = fields.Integer(related='transformer_id.impedance')  # Corrected this line
    transformer_date_of_manufacture = fields.Date(related='transformer_id.date_of_manufacture')
    state = fields.Selection(
        selection=[
            ('newly_failed', 'Newly Failed'),
            ('repaired', 'Repaired'),
            ('workshop', 'In Workshop'),
            ('vendor_workshop', 'vendor_Workshop'),
            ('completed', 'Completed'),
            ('closed', 'Closed'),
        ]
    )
    movement_direction = fields.Boolean(string='Current Movement Direction')

    movement_ids = fields.One2many('failed.transformer.movement', 'issue_id')  # Added inverse field
    present_location = fields.Char(compute='_compute_present_location')

    reporting_officer_incoming = fields.Many2one('hr.employee')  # Corrected May2one to Many2one
    reporting_officer_incoming_phone = fields.Char()
    reporting_officer_outgoing = fields.Many2one('hr.employee')  # Corrected May2one to Many2one
    reporting_officer_outgoing_phone = fields.Char()

    @api.depends('movement_ids')
    def _compute_present_location(self):
        for record in self:
            if record.movement_ids:
                latest_movement = max(record.movement_ids, key=lambda m: m.create_date)
                record.present_location = latest_movement.location

class MovementLog(models.Model):
    _name = 'failed.transformer.movement'
    _description = 'Movement Log'

    issue_id = fields.Many2one('failed.transformer.issue')  # Added inverse field
    location = fields.Char()
    create_date = fields.Datetime(default=fields.Datetime.now)  # Added create_date field
