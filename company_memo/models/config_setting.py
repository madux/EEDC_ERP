from odoo import models, fields, api, _
from odoo.exceptions import ValidationError 

MEMOTYPES = [
        'Payment',
        'loan',
        'Internal',
        'material_request',
        'procurement_request',
        'vehicle_request',
        'leave_request',
        'server_access',
        'cash_advance',
        'soe',
        ] 
DEFAULT_STAGES = [
    'Draft', 'Awaiting approval', 'Done'
]

class MemoStage(models.Model):
    _name = "memo.stage"
    _description = "Memo Stage"
    _order = 'sequence'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", required=True)
    active = fields.Boolean("Active", default=True)
    is_approved_stage = fields.Boolean("Is approved stage", help="if set true, it is used to determine if this stage is the final approved stage")
    approver_id = fields.Many2one("hr.employee", string="Responsible Approver")
    memo_config_id = fields.Many2one("memo.config", string="Parent settings")
    loaded_from_data = fields.Boolean(string="Loaded from data", default=False)

    @api.constrains('sequence')
    def _validate_sequence(self):
        """Check to ensure that record does not have same sequence"""
        if not self.loaded_from_data:
            memo_duplicate = self.env['memo.stage'].search([
                ('memo_config_id.memo_type', '=', self.memo_config_id.memo_type),
                ('sequence', '=', self.sequence),
                ('memo_config_id.department_id', '=', self.memo_config_id.department_id.id)
                ])
            if memo_duplicate and len(memo_duplicate.ids) > 1:
                raise ValidationError("You have already created a stage with the same sequence")


class MemoConfig(models.Model):
    _name = "memo.config"
    _description = "Memo setting"
    _rec_name = "memo_type"

    memo_type = fields.Selection(
        [
        ("Payment", "Payment"),
        ("loan", "Loan"),
        ("Internal", "Internal Memo"),
        ("material_request", "Material request"),
        ("procurement_request", "Procurement Request"),
        ("vehicle_request", "Vehicle request"),
        ("leave_request", "Leave request"),
        ("server_access", "Server Access Request"),
        ("cash_advance", "Cash Advance"),
        ("soe", "Statement of Expense"),
        ], string="Memo Type",default="", required=True)
    
    approver_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_memo_config_rel',
        'hr_employee_memo_id',
        'config_memo_id',
        string="Employees for Final Validation",
        required=True
        )
    
    stage_ids = fields.Many2many(
        'memo.stage',
        'memo_stage_rel',
        'memo_stage_id', 
        'memo_config_id',
        string="Stages",
        required=True,
        store=True,
        copy=False
        )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        copy=False
        )
    active = fields.Boolean(string="Active", default=True)

    @api.constrains('memo_type')
    def _check_duplicate_memo_type(self):
        memo = self.env['memo.config'].sudo()
        for rec in self:
            duplicate = memo.search([('memo_type', '=', rec.memo_type),('department_id', '=', rec.department_id.id)], limit=2)
            if len([r for r in duplicate]) > 1:
                raise ValidationError("A memo type has already been configured for this record, kindly locate it and select the approvers")
           

    def auto_configuration(self):
        # TODO: To be used to dynamically generate configurations 
        # for all departments using default stages such as 
        # Draft, Awaiting approval, Done
        # This will be used if no manual stages and configuration is done
        """Loop all departments, 
            Loop via memo type that does not have memo type and the department generated,
            if not found, 
            create or generate a memo.config --> Create the memo stages as above and then
            the Awaiting approval stage should be assigned with the department parent id
              memo that does not departments that does not have memo types configured"""
        approval_stage = DEFAULT_STAGES[1]
        department_ids = self.env['hr.department'].search([])
        if department_ids:
            for department in department_ids:
                for memotype in MEMOTYPES:
                    existing_memo_config = self.env['memo.config'].search([
                        ('memo_type','=', memotype), 
                        ('department_id', '=',department.id)
                        ], limit=1
                        )
                    if not existing_memo_config:
                        memo_config_vals = {
                            'active': True,
                            'memo_type': memotype,
                            'department_id': department.id,
                        }

                        memo_config = self.env['memo.config'].create(memo_config_vals)
                        stages = []
                        for count, st in enumerate(DEFAULT_STAGES):
                            stage_id = self.env['memo.stage'].create(
                                {'name': st,
                                 'approver_id': department.manager_id.id if st == approval_stage else False,
                                 'memo_config_id': memo_config.id,
                                 'is_approved_stage': True if st == approval_stage else False,
                                 'active': True,
                                 'sequence': count
                                 }
                            )
                            stages.append(stage_id.id)
                        memo_config.stage_ids = [(6, 0, stages)]
