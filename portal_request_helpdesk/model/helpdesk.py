from datetime import datetime, timedelta
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"
    _order = "id desc"
    
    is_published = fields.Boolean(string="Is published")
    
    
class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('HelpdeskTicketModel')
        vals['code'] = str(sequence)
        return super(HelpdeskTicket, self).create(vals)
    
    code = fields.Char(
        string="Code", 
        ) 
    deadline_date = fields.Date(
        string="Deadline date", 
        )
    request_date = fields.Date(
        string="Request date", 
        )  
    
     