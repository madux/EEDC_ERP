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

class MemoSubStageLine(models.Model):
    _name = "memo.sub.stage"
    _description = "memo sub stage"

    name = fields.Char("Name", required=True)
    code = fields.Char("Name", required=False)
    memo_id = fields.Many2one(
        "memo.model", 
        string="Memo Ref"
        )
    sub_stage_id = fields.Many2one(
        "memo.stage", 
        string="Stage id"
        )
    sub_stage_done = fields.Boolean("Is Done", default=False)
    invoice_ids = fields.Many2many(
        'account.move', 
        'memo_sub_invoice_rel',
        'memo_sub_invoice_id',
        'invoice_sub_memo_id',
        string='Invoice', 
        store=True,
        domain="[('move_type', 'in', ['in_invoice', 'in_receipt']), ('state', '!=', 'cancel')]"
        )
    description = fields.Text("Description", required=False)
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'memo_sub_stage_ir_attachment_rel',
        'memo_sub_ir_attachment_id',
        'ir_sub_attachment_memo_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', '0')]"
        )
    
    approver_ids = fields.Many2many(
        "hr.employee", 
        string="Responsible Approvers")
    
    require_po_confirmation = fields.Boolean("Require PO confirmation", default=False)
    require_so_confirmation = fields.Boolean("Require SO confirmation", default=False)
    require_bill_payment = fields.Boolean("Require PO payment", default=False)
    require_waybill_detail = fields.Boolean("Require Inventory Reciept", default=False)

    def confirm_sub_stage_done(self):
        # validates to ensure all document and invoices are paid or attached
        # add all invoices and document to main invoice lines
        self.responsible_approver_right()
        if self.sub_stage_id.required_document_line:
            self.validate_compulsory_document()
        if self.sub_stage_id.required_invoice_line:
            self.validate_invoice_line()
        self.sub_stage_done = True
        if self.invoice_ids:
            self.memo_id.invoice_ids = [(4, rec.id) for rec in self.invoice_ids]
        if self.attachment_ids:
            self.memo_id.attachment_ids = [
            (4, rec.id) for rec in self.attachment_ids
            ]
        if self.memo_id.stage_id.require_po_confirmation or self.memo_id.stage_id.require_bill_payment:
            self.memo_id.procurement_confirmation()

    def responsible_approver_right(self):
        user =  self.env.user
        useritem = [r.user_id.id for r in self.approver_ids if self.approver_ids] + [r.user_id.id for r in self.sub_stage_id.memo_config_id.approver_ids] + [r.user_id.id for r in self.sub_stage_id.approver_ids]
        # raise ValidationError(useritem)
        if user.id not in useritem:
            raise ValidationError("You are not allowed to validate this task / process")

    def validate_compulsory_document(self):
        """Check if compulsory documents have uploaded"""  
        attachments = self.mapped('attachment_ids').filtered(
                    lambda iv: not iv.datas
                )
        if attachments:
            for count, doc in enumerate(attachments, 1):
                matching_attachment = self.sub_stage_id.mapped('required_document_line').filtered(
                    lambda dc: dc.name == doc.name
                )
                matching_stage_doc = matching_attachment and matching_attachment[0]
                if matching_stage_doc.compulsory and not doc.datas:
                    raise ValidationError(f"Attachment with name '{doc.stage_document_name}' at line {count} does not have any data attached")

    def validate_invoice_line(self):
        '''Check all invoice in draft and check if 
        the current stage that matches it is compulsory
        if compulsory, system validates it'''
        
        invoice_ids = self.mapped('invoice_ids').filtered(
                    lambda iv: iv.state in ['draft']
                )
                
        if invoice_ids:
            for count, inv in enumerate(invoice_ids, 1):
                matching_stage_invoice = self.sub_stage_id.mapped('required_invoice_line').filtered(
                    lambda rinv: rinv.name == inv.stage_invoice_name
                )
                matching_stage_invoice = matching_stage_invoice and matching_stage_invoice[0]
                if matching_stage_invoice.compulsory:
                    if inv.payment_state not in ['paid', 'partial', 'in_payment']:
                        raise ValidationError(f"Invoice at line {count} must be posted and paid before proceeding")
                    invoice_line = inv.mapped('invoice_line_ids')
                    if not invoice_line:
                        raise ValidationError(f"Add at least one invoice billing line at line {count}")
                    invoice_line_without_price = inv.mapped('invoice_line_ids').filtered(
                        lambda s: s.price_unit <= 0
                        )
                    if invoice_line_without_price:
                        raise ValidationError(f"All invoice line must have a price amount greater than 0 at line {count}")
                

class MemoStageDocumentLine(models.Model):
    _name = "memo.stage.document.line"
    _description = "memo.stage.document.line"
    
    name = fields.Char("Name", required=True)
    code = fields.Char("Code", required=False)
    compulsory = fields.Boolean("Compulsory", default=False)
    # memo_stage_id = fields.Many2one(
    #     "memo.stage", 
    #     string="Memo stage Ref"
    #     )
    memo_document_id = fields.Many2one(
        "memo.model", 
        string="Memo Ref"
        )
    

class MemoStageInvoiceLine(models.Model):
    _name = "memo.stage.invoice.line"
    _description = "MSIL"
    name = fields.Char("Name", required=True)
    compulsory = fields.Boolean("Is Compulsory", default=False)
    memo_invoice_id = fields.Many2one(
        "memo.model",
        string="Memo Ref"
        )
    move_type = fields.Selection(
        [
        ("customer", "Customer Invoice"),
        ("vendor", "Vendor Bills"),
        ],
        string="Invoice type",
        required=True,
    )
    code = fields.Char("Code", required=False)

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
    is_document = fields.Boolean("Is document", default=False)
    active = fields.Boolean("Active", default=True)
    allow_for_publish = fields.Boolean("Allow to be published?", default=True)

class MemoStage(models.Model):
    _name = "memo.stage"
    _description = "Memo Stage"
    _order = 'sequence'

    name = fields.Char("Name", required=False)
    sequence = fields.Integer("Sequence", required=False)
    description = fields.Text("description")
    active = fields.Boolean("Active", default=True)
    is_approved_stage = fields.Boolean("Is approved stage", help="if set true, it is used to determine if this stage is the final approved stage")
    approver_id = fields.Many2one("hr.employee", string="Responsible Approver")
    approver_ids = fields.Many2many("hr.employee", string="Responsible Approvers")
    memo_config_id = fields.Many2one("memo.config", string="Parent settings")
    loaded_from_data = fields.Boolean(string="Loaded from data", default=False)
    publish_on_dashboard = fields.Boolean("Publish on Dashboard", default=False)
    require_po_confirmation = fields.Boolean("Require PO confirmation", default=False)
    require_so_confirmation = fields.Boolean("Require SO confirmation", default=False)
    require_bill_payment = fields.Boolean("Require PO payment", default=False)
    require_waybill_detail = fields.Boolean("Require Inventory Reciept", default=False)
    memo_has_condition = fields.Boolean(string="Has condition",
                                      default=False, 
                                      help="If there is a condition of yer or no, system determines what stage to jump or move back to")
    
    yes_condition = fields.Boolean(string="Yes",
                                      default=False, 
                                      help="if condition is Yes, set the stage for yes condition")
    no_condition = fields.Boolean(string="No",
                                      default=False, 
                                      help="if condition is No, set the stage for No condition")
    # is_2nd_option = fields.Boolean(string="2nd Option",
    #                                   default=False, 
    #                                   help="when this is checked, system checks and jump to the next stage")
    

    @api.onchange('memo_has_condition')
    def onchange_has_condition(self):
        if self.memo_has_condition:
            self.yes_condition = True
            self.no_condition = True
        else:
            self.yes_condition = False
            self.no_condition = False

    # if system has condition,user must select stage to jump to
    yes_conditional_stage_id = fields.Many2one(
        "memo.stage", 
        string="First Option stage",
        help="Shows list of all the stages that has memo_config_id")
    
    no_conditional_stage_id = fields.Many2one(
        "memo.stage", 
        string="Second Option stage",
        help="Shows list of all the stages that has memo_config_id")
    
    dummy_memo_config_stage_ids = fields.Many2many(
        "memo.stage", 
        "dummy_memo_stage_rel",
        "dummy_memo_stage_id",
        "memo_stage_id",
        string="dummy config stages",
        help="Shows list of all the stages that has memo_config_id",
        compute="show_all_related_memo_config_stage")
    sub_stage_ids = fields.Many2many(
        "memo.stage",
        "sub_stage_rel",
        "sub_memo_stage_id",
        "memo_stage_id",
        string="Sub stages",
        help="This are sub stages of the parent stage")
    is_sub_stage = fields.Boolean("Is sub stage", default=False)

    required_invoice_line = fields.Many2many(
        'memo.stage.invoice.line',
        'memo_stage_invoice_rel',
        'memo_stage_invoice_id',
        'memo_stage_id',
        string='Invoice line required'
        )
    required_document_line = fields.Many2many(
        'memo.stage.document.line',
        'memo_stage_document_rel',
        'memo_stage_document_id',
        'memo_stage_id',
        string='Documents required'
        )
    
    @api.depends("memo_config_id")
    def show_all_related_memo_config_stage(self):
        if self.memo_config_id:
            memo_stage_ids = self.memo_config_id.mapped('stage_ids').filtered(lambda s: not s.is_sub_stage)
            self.dummy_memo_config_stage_ids = memo_stage_ids.ids
        else:
            self.dummy_memo_config_stage_ids = False

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
    _rec_name = "name"

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
    
    @api.constrains('branch_id', 'department_id', 'company_id')
    def constrain_company_branch_department(self):
        if self.branch_id.company_id and self.branch_id.company_id.id != self.company_id.id:
            raise ValidationError(f"District - {self.branch_id.name} must match the company selected: {self.company_id.name}") 

    def get_publish_memo_types(self):
        return [('allow_for_publish', '=', True)]

    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=False,
        domain=lambda self: self.get_publish_memo_types()
        )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
    )
    memo_key = fields.Char("Memo Key", related="memo_type.memo_key")
    name = fields.Char(
        string='Name', 
        copy=False, 
        )
    memo_category_id = fields.Many2one('memo.category', string="Category") 

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
        required=False,
        copy=False
        )
    department_ids = fields.Many2one(
        'hr.department',
        string='Department',
        required=False,
        copy=False
        )
    prefix_code = fields.Char(
        string='Prefix Code',
        copy=True,
        )
    department_code = fields.Char(
        string='Department Code',
        copy=True,
        help="Serves as the suffix code for the department in question"
        )
    send_to_initiator_on_refusal = fields.Boolean(string="Send to initiator",
                                      default=False, 
                                      help="Check if you want system to send straight to initiator upon refusal")
    
    has_transformer = fields.Boolean(string="For transformer", default=False)
    active = fields.Boolean(string="Active", default=True)
    allowed_for_company_ids = fields.Many2many(
        'res.partner', 
        'res_partner_memo_config_rel',
        'partner_id',
        'memo_setting_id',
        string="Allowed Partners",
        help="""
        If partners are selected, this will allow 
        employees with external user option to select 
        the list from the portal
        """
        )
    
    company_ids = fields.Many2many(
        'res.company', 
        'res_company_memo_config_rel',
        'company_id',
        'memo_setting_id',
        string="Allowed companies",
        help="""
        If companies are selected, this will allow 
        employees with external user option to select 
        the list from the portal
        """
        )
    
    allow_multi_vending_on_po = fields.Boolean(
        string="Allow Multi Vending", 
        default=True, 
        help="This only allow users to send PO request to multiple vendors")
    branch_ids = fields.Many2many(
        'multi.branch', 
        string='Districts / Branch(s)', 
        required=False)
    branch_id = fields.Many2one('multi.branch', string='District')
    
    receivable_account_id = fields.Many2one(
        "account.account", 
        string="Account Receivable"
        ) 
    payable_account_id = fields.Many2one(
        "account.account", 
        string="Account Payable"
        ) 
    advance_account_id = fields.Many2one(
        "account.account", 
        string="Advance Account"
        ) 
    expense_account_id = fields.Many2one(
        "account.account", 
        string="Expense Account"
        )

    
    def write(self, vals):
        res = super(MemoConfig, self).write(vals)
        self.update_parent_setting()
        return res
    
    def update_parent_setting(self):
        if self.stage_ids:
            for rec in self.stage_ids:
                rec.is_approved_stage = False
                rec.memo_config_id = self.id
            if len(self.stage_ids) > 2:
                self.stage_ids[-2].is_approved_stage = True

    @api.constrains('memo_type')
    def _check_duplicate_memo_type(self):
        memo = self.env['memo.config'].sudo()
        for rec in self:
            duplicate = memo.search([('memo_type', '=', rec.memo_type.id),
                                      ('memo_key', '!=', 'helpdesk'), 
                                      ('branch_id', '=', rec.branch_id.id),
                                      ('id', '!=', rec.id),
                                      ], limit=1)
            if duplicate:
                company_found = [
                        result for result in rec.company_ids.ids if result in duplicate.company_ids.ids 
                        ]
                
                if company_found:
                    #  if len([r for r in duplicate]) > 1:
                    raise ValidationError(
                    f"""A memo config with type {rec.memo_type.name}
                    and department: {rec.department_id.name}
                    has already been configured for this companies 
                    {','.join([self.env['res.company'].sudo().browse([r]).name for r in company_found])}, 
                    kindly discard locate it and select the approvers""")

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
                # raise ValidationError("Please select memo type!")
            self.active = True
        else:
            fleet_group.users = [(3, usr) for usr in approvers]
            self.active = False
            
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
                        ('department_id', '=', department.id)
                        ], limit=1
                        )
                    if not existing_memo_config:
                        memo_type_id = self.env['memo.type'].search([
                            ('memo_key','=', memotype.memo_key)]
                            , limit=1)
                        if not memo_type_id:
                            raise ValidationError(f'Memo type with key {memotype} on record does not exist. Contact admin to configure')
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
                'default_company_ids': self.company_ids.ids,
                'default_allow_multi_vending_on_po': self.allow_multi_vending_on_po,
                'default_branch_ids': [(4, self.branch_id.id)],
                'default_receivable_account_id': self.receivable_account_id.id,
                'default_payable_account_id': self.payable_account_id.id,
                'default_advance_account_id': self.advance_account_id.id,
                'default_expense_account_id': self.expense_account_id.id,
                
            },
        }
 
    def button_assign_employee(self):
        rec_ids = self.env.context.get('active_ids', [])
        Config = self.env['memo.config']
        return {
            'name': 'Employee Assign to Config Stages',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'memo.assign.stage.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                # 'default_employee_ids': self.stage_ids.ids,
                'default_dummy_config_ids': [(0, 0,
                    {
                        'memo_config_id': Config.browse([r]).id, 
                        'dummy_memo_stage_ids': Config.browse([r]).stage_ids.ids, 
                        'memo_stage_ids': Config.browse([r]).stage_ids.ids, 
                    }) for r in rec_ids],
                
            },
        }
  
  
class DummyMemoConfig(models.Model):
    _name = "dummy.memo.config"
    _description = "Model to memo assign stage"

    memo_config_wizard_id = fields.Many2one(
        'memo.assign.stage.wizard',
        string='Memo Assign Wizard ',
        )
    
    memo_config_id = fields.Many2one(
        'memo.config',
        string='Memo config',
        )
    
    memo_stage_ids = fields.Many2many(
        'memo.stage',
        string='Stage',
        )
    
    dummy_memo_stage_ids = fields.Many2many(
        'memo.stage',
        'dummy_memo_stage_rels',
        'memo_config_dummy_stage',
        'dummy_memo_stage_id',
        string='dummy stage ',
        )
    include_intial_done = fields.Boolean(
        'Include Draft & Done?',
        default=False
        )


class MemoAssignStages(models.Model):
    _name = "memo.assign.stage.wizard"
    _description = "Model to memo assign stage"

    dummy_config_ids = fields.One2many(
        'dummy.memo.config',
        'memo_config_wizard_id',
        string='Memo Config ids',
        )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employee',
        )
    
    
    def action_add(self):
        dummy_config_ids = self.sudo().dummy_config_ids
        for dmc in dummy_config_ids:
            dmc_stages = dmc.memo_config_id.stage_ids
            if dmc_stages:
                initial_stage = dmc_stages[0]        
                last_stage = dmc_stages[-1]
                for stg in dmc.memo_stage_ids:
                    if stg.id not in dmc_stages.ids:
                        raise ValidationError(f"Selected stage {[stg.id] - stg.name } not in select Config : [{dmc.memo_config_id.name}] stages")
                    
                    if stg.id in [initial_stage.id, last_stage.id]:
                        if dmc.include_intial_done:
                            stg.approver_ids = [(4, emp.id) for emp in self.employee_ids]
                    else:
                        stg.approver_ids = [(4, emp.id) for emp in self.employee_ids]
            
    def action_remove(self):
        dummy_config_ids = self.sudo().dummy_config_ids
        for dmc in dummy_config_ids:
            dmc_stages = dmc.memo_config_id.stage_ids
            if dmc_stages:
                for stg in dmc.memo_stage_ids:
                    if stg.id not in dmc_stages.ids:
                        raise ValidationError(f"Selected stage {[stg.id] - stg.name } not in select Config : [{dmc.memo_config_id.name}] stages")
                    
                    stg.approver_ids = [(3, emp.id) for emp in self.employee_ids]
            
class MemoCategory(models.Model):
    _name = "memo.category"
    _description = "Memo document Category"
    _rec_name = "name"

    name = fields.Char('Name')
    memo_config_ids = fields.Many2many(
        'memo.config',
        string='Memo config',
        )
    category_type = fields.Char('Type', placeholder="e.g helpdesk")
    

class MemoDialog(models.TransientModel):
    _name = "memo.dialog"
    _description = "Model to hold dialog messages "

    name = fields.Text('Message', readonly=True)
    
    

