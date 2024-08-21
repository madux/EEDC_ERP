from odoo import api, models, fields

class memoModel(models.Model):
    _inherit = 'memo.model'

    # transformer repairs
    transformer_id = fields.Many2one('transformer', string="Transformer")
    has_transformer = fields.Boolean(
        string='Has PO line', 
        help="used to show invoice when there is an PO setup in the memo_config_setting stages"
        )
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
    