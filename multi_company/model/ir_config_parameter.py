from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    check_company_strict = fields.Boolean(
        string="Strict Company Check",
        help="If enabled, Odoo will raise an error when cross-company "
             "records are inconsistent. Disable to bypass the UserError.",
        config_parameter='check.company.strict',
        default=False,
    )