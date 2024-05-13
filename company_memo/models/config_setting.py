from odoo import models, fields, api, _
from odoo.exceptions import ValidationError 

MEMOTYPES = [
        'Payment',
        'loan',
        'Internal',
        'employee_update',
        'material_request',
        'procurement_request',
        'vehicle_request',
        'leave_request',
        'server_access',
        'cash_advance',
        'soe',
        'recruitment_request',
        ] 
DEFAULT_STAGES = [
    'Draft', 'Awaiting approval', 'Done'
]

class MemoType(models.Model):
    _name = "memo.type"
    _description = "Memo Type"

    name = fields.Char("Name", required=True)
    memo_key = fields.Char(
        "Key", 
        required=True,
        help="""e.g material_request; This is used to 
        request the static Id of the memo type for use in conditioning
        """,
        )
    active = fields.Boolean("Active", default=True)
    allow_for_publish = fields.Boolean("Allow to be published?", default=True)

class MemoStage(models.Model):
    _name = "memo.stage"
    _description = "Memo Stage"
    _order = 'sequence'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", required=True)
    active = fields.Boolean("Active", default=True)
    is_approved_stage = fields.Boolean("Is approved stage", help="if set true, it is used to determine if this stage is the final approved stage")
    approver_id = fields.Many2one("hr.employee", string="Responsible Approver")
    approver_ids = fields.Many2many("hr.employee", string="Responsible Approvers")
    memo_config_id = fields.Many2one("memo.config", string="Parent settings")
    loaded_from_data = fields.Boolean(string="Loaded from data", default=False)

    @api.constrains('sequence')
    def _validate_sequence(self):
        """Check to ensure that record does not have same sequence"""
        if not self.loaded_from_data:
            memo_duplicate = self.env['memo.stage'].search([
                ('memo_config_id.memo_type', '=', self.memo_config_id.memo_type.id),
                ('sequence', '=', self.sequence),
                ('memo_config_id.department_id', '=', self.memo_config_id.department_id.id)
                ])
            if memo_duplicate and len(memo_duplicate.ids) > 1:
                raise ValidationError("You have already created a stage with the same sequence")


class MemoConfig(models.Model):
    _name = "memo.config"
    _description = "Memo setting"
    _rec_name = "memo_type"

    # memo_type = fields.Selection(
    #     [
    #     ("Payment", "Payment"),
    #     ("loan", "Loan"),
    #     ("Internal", "Internal Memo"),
    #     ("employee_update", "Employee Update Request"),
    #     ("material_request", "Material request"),
    #     ("procurement_request", "Procurement Request"),
    #     ("vehicle_request", "Vehicle request"),
    #     ("leave_request", "Leave request"),
    #     ("server_access", "Server Access Request"),
    #     ("cash_advance", "Cash Advance"),
    #     ("soe", "Statement of Expense"),
    #     ("recruitment_request", "Recruitment Request"),
    #     ], string="Memo Type",default="", required=True)
    def get_publish_memo_types(self):
        return [('allow_for_publish', '=', True)]

    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=False,
        domain=lambda self: self.get_publish_memo_types()
        )
    
    @api.onchange('active')
    def onchange_active(self):
        fleet_group = self.env.ref(
                        'company_memo.group_memo_fleet'
                    )
        approvers = []
        for app in self.stage_ids:
            if app.approver_ids:
                approvers += [r.user_id.id for r in app.approver_ids]
        if self.active:
            if self.memo_type:
                if self.memo_type.memo_key == "vehicle_request":
                    fleet_group.users = [(4, usr) for usr in approvers]
            else:
                raise ValidationError("Please select memo type!")
            self.active = True
        else:
            fleet_group.users = [(3, usr) for usr in approvers]
            self.active = False


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
    allowed_for_company_ids = fields.Many2many(
        'res.partner', 
        'res_partner_memo_config_rel',
        'partner_id',
        'memo_setting_id',
        string="Allowed companies",
        help="""
        If companies are selected, this will allow 
        employees with external user option to select 
        the list from the portal
        """
        )

    @api.constrains('memo_type')
    def _check_duplicate_memo_type(self):
        memo = self.env['memo.config'].sudo()
        for rec in self:
            duplicate = memo.search([('memo_type', '=', rec.memo_type.id),('department_id', '=', rec.department_id.id)], limit=2)
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
        MEMOTYPES = self.env['memo.type'].search([])
        if department_ids:
            for department in department_ids:
                for memotype in MEMOTYPES:
                    existing_memo_config = self.env['memo.config'].search([
                        ('memo_type.memo_key','=', memotype), 
                        ('department_id', '=',department.id)
                        ], limit=1
                        )
                    if not existing_memo_config:
                        memo_type_id = self.env['memo.type'].search([
                            ('memo_key','=', memotype.memo_key)]
                            , limit=1)
                        if not memo_type_id:
                            raise ValidationError(f'Memo type with key {memotype} does not exist. Contact admin to configure')
                        memo_config_vals = {
                            'active': True,
                            'memo_type': memo_type_id.id,
                            'department_id': department.id,
                        }

                        memo_config = self.env['memo.config'].create(memo_config_vals)
                        stages = []
                        for count, st in enumerate(DEFAULT_STAGES):
                            stage_id = self.env['memo.stage'].create(
                                {'name': st,
                                 'approver_ids': [(4, department.manager_id.id)] if st == approval_stage else False,
                                 'memo_config_id': memo_config.id,
                                 'is_approved_stage': True if st == approval_stage else False,
                                 'active': True,
                                 'sequence': count
                                 }
                            )
                            stages.append(stage_id.id)
                        memo_config.stage_ids = [(6, 0, stages)]

    def custom_duplicate(self):
        return {
            'name': 'Duplicate Memo Config',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'memo.config.duplication.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_employees_follow_up_ids': self.approver_ids.ids,
                'default_allowed_companies_ids': self.allowed_for_company_ids.ids,
            },
        }


class MemoCategory(models.Model):
    _name = "memo.category"
    _description = "Memo document Category"

    name = fields.Char('Name')


class MemoDialog(models.TransientModel):
    _name = "memo.dialog"
    _description = "Model to hold dialog messages "

    name = fields.Text('Message', readonly=True)
    
