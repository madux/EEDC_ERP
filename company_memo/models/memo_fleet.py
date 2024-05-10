from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class MemoFleet(models.Model):
    _inherit = 'memo.fleet'
    _description = '''This model holds the fleet transaction on a timely basis: 
    When employee books for a fleet, the fleet is then become unavailable.
    When the driver returns the vehicle - the fleet becomes available
    The also shows the driver responsible and the distances covered on a daily
    basis. (a table should hold the current trip where the driver starts and ends the trip: 
    this table contains the following fileds;
    start time - end time, 
    start location - destination location
    distance covered (mileage, trips, km/h), 
    vfs - volume of fuel currently assigned
    vefu - volume of extra fuel used
    Total number of fuel in litres used, (computated as = vfs - vefu) 

    map widget to show real time: not necessary)
    Computation of this distances determines the estimated mileage covered
    '''
    _order = 'code'

    code = fields.Char(
        'Ref#')
    
    vehicle_assigned = fields.Many2one(
        'product.product',
        string="Vehicle Assigned",
        required=True
        )
    memo_id = fields.Many2one(
        'memo.model',
        string="Memo ID",
        )
    
    driver_assigned = fields.Many2one(
        'hr.employee',
        string="Driver Assigned",
        )
    source_location_id = fields.Char(
        string="Start location",
        required=True
        )
    source_destination_id = fields.Char(
        string="Destination",
        required=True
        )
    distance_covered = fields.Char(
        string="Distance Covered",
        )
    distance_measured = fields.Selection([
        ('mile', 'Mile'),
        ('trip', 'Trips'),
        ('km', 'KM/PH'),
        ],
        string="Distance Measure", default="mile")
    
    start_time = fields.Datetime(
        string="Start time")
    
    end_time = fields.Datetime(
        string="End time")

    number_of_days_covered = fields.Char(
        string="Number of hours/Days/Weeks", 
        compute="compute_number_of_days_covered"
    )
    
    volume_of_current_fuel = fields.Char(
        string="Current fuel volume",
        required=True
        )
    volume_of_extra_fuel_used = fields.Char(
        string="Extra fuel volume Used",
        )
    
    total_fuel_used = fields.Char(
        string="Total fuel volume Used",
        compute="compute_total_fuel_used"
        )
    
    incident_report = fields.Text(
        string="Incident encountered",
        )
    
    require_maintenance = fields.Boolean(
        string="Required Maintenace",
        )
    state_maintenace_required = fields.Text(
        string="Maintenace description",
        )
    
    def action_start_fleet(self):
        self.fleet_component(
            code=self.code,
            volume_of_current_fuel=self.volume_of_current_fuel,
            vehicle_assigned=self.vehicle_assigned,
            driver_assigned=self.driver_assigned,
            source_location_id=self.source_location_id,
            source_destination_id=self.source_destination_id,
            website=False,
            )
    
    def fleet_component(self, **kwargs):
        code, volume_of_current_fuel = kwargs.get('code'), kwargs.get('volume_of_current_fuel')
        vehicle_assigned, driver_assigned = kwargs.get('vehicle_assigned'), kwargs.get('driver_assigned')
        source_location_id, source_destination_id = kwargs.get('source_location_id'), \
            kwargs.get('source_destination_id')
        if not any([
            code, volume_of_current_fuel, 
            vehicle_assigned, driver_assigned, 
            source_location_id, source_destination_id
            ]):
            ValidationErrordata =  {
                    'data': """
                        please provide the following parameteres: Vehicle assigned, 
                        code ,volume of current fuels location or destination must be provided
                        """,
                    }
            if kwargs.get('website'):
                return ValidationErrordata
            else:
                raise ValidationError(f"Error !! {ValidationErrordata.get('data')}")
            
        else:
            Fleet = self.env['memo.fleet'].search([('code', '=', code)], limit=1)
            if Fleet:
                Fleet.start_time = fields.Datetime.now()
            else:
                if kwargs.get('website'):
                    return {
                        'No fleet record found with the code provided'
                    }
                else:
                    raise ValidationError(
                        "Error !! No fleet record found with the code provided"
                        )
    
    @api.depends('start_time', 'end_time')
    def compute_number_of_days_covered(self):
        if self.start_time and self.self.end_time:
            self.number_of_days_covered = (self.end_time + self.start_time).days
        else:
            self.number_of_days_covered = False

    @api.depends(
            'volume_of_current_fuel', 
            'volume_of_extra_fuel_used'
            )
    def compute_total_fuel_used(self):
        if self.start_time and self.self.end_time:
            self.total_fuel_used = (
                self.volume_of_current_fuel + self.volume_of_extra_fuel_used
                )
        else:
            self.total_fuel_used = False
