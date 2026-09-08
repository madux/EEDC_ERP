from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)
    
class LeaveAllocationWizard(models.Model):
    _name = "hr.leave.allocation.wizard"

    allocation_ids = fields.Many2many("hr.leave.allocation", string ="allocations")
  
 
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    duration = fields.Integer(string="Number in Days")

    def updateAllSelectedAllocations(self):
        for rec in self.allocation_ids:
            if self.duration > 0:
                rec.number_of_days_display = self.duration
            rec.date_from=self.start_date
            rec.date_to=self.end_date

    @api.onchange('end_date')
    def onchange_of_end_date(self):
        self.ensure_one()
        if self.end_date <= self.start_date:
            raise ValidationError('End date cannot be lesser than start date')

class HrLeaveDetails(models.Model):
    _inherit="hr.leave.allocation"

    def update_validity_action(self):
        rec_ids = self.env.context.get('active_ids', [])
 
        return {
              'name': 'LEAVE VALIDATION UPDATE',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.leave.allocation.wizard',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_allocation_ids': rec_ids,
              },
        }
    