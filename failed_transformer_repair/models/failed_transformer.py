from odoo import api, models, fields

class FailedTransformerMovement(models.Model):
    _name = 'failed.transformer.issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Failed Transformer Issue'
    _rec_name = "transformer_id"

    transformer_id = fields.Many2one('transformer')
    transformer_name = fields.Char(related='transformer_id.name')
    date_registered = fields.Date()
    transformer_rating = fields.Integer(related='transformer_id.rating')
    transformer_make = fields.Char(related='transformer_id.dss_make')
    transformer_serialno = fields.Char(related='transformer_id.serial_number')
    substation = fields.Many2one(related='transformer_id.sub_station')
    oil_weight = fields.Integer(related='transformer_id.oil_weight')
    transformer_impedance = fields.Float(related='transformer_id.impedance')
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

    movement_ids = fields.One2many('failed.transformer.movement', 'issue_id')
    present_location = fields.Char()
    issue_description = fields.Text()
    checklist = fields.One2many('dsm.checklist','issue_id')
    repair_type = fields.Selection(
        selection=[
            ('pending', 'pending'),
            ('internal', 'Internal'),
            ('Exteranl', 'External')
        ],
        default='pending',
        string = 'Repair type'
    )

    stage_id = fields.Many2one('issue.stage', default='pending')
    stage_ids = fields.Many2many('issue.stage', default=lambda self: self._default_stage_ids())

    reporting_officer_incoming = fields.Many2one('hr.employee')
    reporting_officer_incoming_phone = fields.Char()
    reporting_officer_outgoing = fields.Many2one('hr.employee')
    reporting_officer_outgoing_phone = fields.Char()

    @api.model
    def _default_stage_ids(self):
        stage_ids = self.env['issue.stage'].search([]).ids
        return stage_ids if stage_ids else False

    @api.depends('movement_ids')
    def _compute_present_location(self):
        for record in self:
            if record.movement_ids:
                latest_movement = max(record.movement_ids, key=lambda m: m.create_date)
                record.present_location = latest_movement.location

class FailedTransformerMovement(models.Model):
    _name = 'failed.transformer.movement'
    _description = 'Movement Log'

    memo_id = fields.Many2one('memo.model')
    issue_id = fields.Many2one('failed.transformer.issue')
    location = fields.Char()
    destination_location = fields.Char()
    create_date = fields.Datetime(default=fields.Datetime.now)
    transformer_id = fields.Many2one('transformer') 

class DSM_Checklist(models.Model):
    _name = 'dsm.checklist'

    """
    This is tthe Distribution Substation Maintenance Substation Checklist
    """

    issue_id  = fields.Many2one('failed.transformer.issue')
    item = fields.Char()
    status = fields.Selection(
        selection=[('pending', 'Pending'),
                   ('completed', 'Completed')
                   ],
                   default='pending'
    )


    
    class IssueStage(models.Model):
        _name = 'issue.stage'
        """
        This class tracks the issue as it moves from OMS that created it to Workshop Manager and then back to the
        transformer destination OMS and vice versa
        """

        name = fields.Char()
        officer = fields.Many2one('res.users')
