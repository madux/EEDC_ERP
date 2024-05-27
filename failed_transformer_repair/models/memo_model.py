from odoo import api, models, fields

class memoModel(models.Model):
    _inherit = 'memo.model'

    # transformer repairs
    transformer_id = fields.Many2one('transformer', string="Transformer")
    transformer_issue_ids = fields.Many2many('failed.transformer.issue', string="Transformer issues")
    transformer_movement_ids = fields.Many2many('failed.transformer.movement', string="Transformer Movement")
    repair_replacement = fields.Selection(
        [
        ("repair", "repair"),
        ("replacement", "Replacement"), 
        ], string="Repair / Replacement")
    repair_type = fields.Selection(
        [
        ("internal", "Internal"),
        ("external", "External"), 
        ], string="Repair type")
    