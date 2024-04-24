from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from bs4 import BeautifulSoup
from odoo.tools import consteq, plaintext2html
from odoo import http
import random
from lxml import etree
from bs4 import BeautifulSoup

import logging

_logger = logging.getLogger(__name__)


class Memo_Model(models.Model):
    _name = "memo.model"
    _description = "Internal Memo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "id desc"
    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('memo.model')
        vals['code'] = str(sequence)
        return super(Memo_Model, self).create(vals)

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].sudo().read_group([
            ('res_model', '=', 'memo.model'), 
            ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_number = attachment.get(rec.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        # res = self.env['ir.actions.act_window'].xml_id('base', 'action_attachment')
        res = self.sudo().env.ref('base.action_attachment')
        res['domain'] = [('res_model', '=', 'memo.model'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'memo.model', 'default_res_id': self.id}
        return res
    
    # default to current employee using the system 
    def _default_employee(self):
        return self.env.context.get('default_employee_id') or \
        self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_user(self):
        return self.env.context.get('default_user_id') or \
         self.env['res.users'].search([('id', '=', self.env.uid)], limit=1)
 
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
    #     ], string="Memo Type", required=True)
    def get_publish_memo_types(self):
        memo_configs = self.env['memo.config'].search([('active', '=', True)])
        memo_type_ids = [r.memo_type.id for r in memo_configs]
        return [('id', 'in', memo_type_ids)]
     
    
    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=False,
        domain=lambda self: self.get_publish_memo_types(),
        )
    memo_type_key = fields.Char('Memo type key', readonly=True)
    name = fields.Char('Subject', size=400)
    code = fields.Char('Code', readonly=True)
    employee_id = fields.Many2one('hr.employee', string = 'Employee', default =_default_employee) 
    # district_id = fields.Many2one("hr.district", string="District ID")
    direct_employee_id = fields.Many2one('hr.employee', string = 'Employee') 
    set_staff = fields.Many2one('hr.employee', string = 'Employee')
    demo_staff = fields.Integer(string='User',
                                default=lambda self: self.env['res.users'].search([
                                    ('id', '=', self.env.uid)], limit=1).id, compute="get_user_staff",)
        
    user_ids = fields.Many2one('res.users', string = 'Beneficiary', default =_default_user)
    dept_ids = fields.Many2one('hr.department', string ='Department', readonly = True, store =True, compute="employee_department",)
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    amountfig = fields.Float('Budget Amount', store=True, default=1.0)
    description_two = fields.Text('Reasons')
    phone = fields.Char('Phone', store=True)
    email = fields.Char('Email', related='employee_id.work_email')
    reason_back = fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')
    file_namex = fields.Char("FileName")
    stage_id = fields.Many2one(
        'memo.stage', 
        string='Stage', 
        store=True,
        domain=lambda self: self._get_related_stage(),
        )
    state = fields.Selection([('submit', 'Draft'),
                                ('Sent', 'Sent'),
                                ('Approve', 'Waiting For Payment / Confirmation'),
                                ('Approve2', 'Memo Approved'),
                                ('Done', 'Completed'),
                                ('Refuse', 'Refused'),
                              ], string='Status', index=True, readonly=True,
                             copy=False, default='submit',
                             required=True,
                             store=True,
                             help='Request Report state')
    date = fields.Datetime('Request Date', default=fields.Datetime.now())
    invoice_id = fields.Many2one(
        'account.move', 
        string='Invoice', 
        store=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')]"
        )
    move_id = fields.Many2one(
        'account.move', 
        string='Move', 
        store=True,
        readonly=True
        )
    
    # @api.onchange('cash_advance_reference')
    # def cash_advance_reference(self):
    #     raise ValidationError('dere')
    #     if self.cash_advance_reference:
    #         raise ValidationError('dere')
    #         # if not self.employee_id:
    #         for rec in self.cash_advance_reference.mapped('product_ids').filtered(lambda s: s.retired == False):
    #             self.product_ids = [(0, 0, {
    #                 'memo_id': rec.id,
    #                 'product_id': rec.product_id.id,
    #                 'description': rec.description,
    #                 'amount_total': rec.amount_total,
    #             })]

    soe_advance_reference = fields.Many2one('memo.model', 'SOE ref.')
    cash_advance_reference = fields.Many2one(
        'memo.model', 
        'Cash Advance ref.')
    date_deadline = fields.Date('Deadline date')
    status_progress = fields.Float(string="Progress(%)", compute='_progress_state')
    users_followers = fields.Many2many('hr.employee', string='Add followers') #, default=_default_employee)
    res_users = fields.Many2many('res.users', string='Approvers') #, default=_default_employee)
    comments = fields.Text('Comments', default="-")
    supervisor_comment = fields.Html('Supervisor Comments', default="")
    manager_comment = fields.Html('Manager Comments', default="")
    is_supervior = fields.Boolean(string='is supervisor', compute="compute_employee_supervisor")
    is_manager = fields.Boolean(string="is_manager", compute="compute_employee_supervisor")
    
    # Fields for server request
    applicationChange = fields.Boolean(string="Application Change")
    datapatch = fields.Boolean(string="Data patch")
    enhancement = fields.Boolean(string="Enhancement")
    databaseChange = fields.Boolean(string="Database Change")
    osChange = fields.Boolean(string="OS Change")
    ids_on_os_and_db = fields.Boolean(string="IDS on OS and DB")
    versionUpgrade = fields.Boolean(string="version Upgrade")
    hardwareOption = fields.Boolean(string="hardware Option")
    otherChangeOption = fields.Boolean(string="Other Change")
    other_system_details = fields.Html(string="Specify Other reason")
    justification_reason = fields.Html(string="Justification Reason")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='No. Attachments')
    approver_id = fields.Many2one('hr.employee', 'Approver')
    approver_ids = fields.Many2many(
        'hr.employee',
        'memo_model_employee_rel',
        'memo_id',
        'hr_employee_id',
        string='Approvers'
        )
    user_is_approver = fields.Boolean(string="User is approver", compute="compute_user_is_approver")
    is_request_completed = fields.Boolean(
        string="is request completed", 
        default=False,
        help="Used to determine if the request business flow is completed. Hides all action buttons if checked")
    is_supervisor_commented = fields.Boolean(
        string="Supervisor commented?", 
        help="Used to determine if supervisor has commented"
        )
    is_manager_approved = fields.Boolean(
        string="Manager Approved?", 
        help="Used to determine if manager has approved from the website portal"
        )
    # Loan fields
    loan_type = fields.Selection(
        [
            # ("fixed-annuity", "Fixed Annuity"),
            # ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=False,
        help="Method of computation of the period annuity",
        readonly=True,
        states={"submit": [("readonly", False)]},
        default="interest",
    )
    loan_amount = fields.Monetary(
        currency_field="currency_id",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )
    currency_id = fields.Many2one(
        "res.currency", 
        default= lambda self: self.env.user.company_id.currency_id.id, 
        readonly=True,
    )
    periods = fields.Integer(
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
        help="Number of periods that the loan will last",
        default=12,
    )
    method_period = fields.Integer(
        string="Period Length (years)",
        default=1,
        help="State here the time between 2 depreciations, in months",
        required=False,
        readonly=True,
        states={"submit": [("readonly", False)]},
    )
    start_date = fields.Date(
        help="Start of the moves",
        readonly=True,
        states={"submit": [("readonly", False)]},
        copy=False,
    )
    loan_reference = fields.Integer(string="Loan Ref")
    active = fields.Boolean('Active', default=True)

    product_ids = fields.One2many('request.line', 'memo_id', string ='Request Line') 
    leave_start_date = fields.Datetime('Leave Start Date', default=fields.Date.today())
    leave_end_date = fields.Datetime('Leave End Date', default=fields.Date.today())
    request_date = fields.Datetime('Request Start Date')
    request_end_date = fields.Datetime('Request End Date')

    leave_type_id = fields.Many2one('hr.leave.type', string="Leave type")
    memo_setting_id = fields.Many2one(
        'memo.config', 
        string="Memo config id", 
        # related="stage_id.memo_config_id"
        )
    
    ###############3 RECRUITMENT ##### 
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },
                             help='The Job Position you expected to get more hired.',
                             )
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          readonly=True,
                          states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     },)
    
    established_position = fields.Selection([('yes', 'Yes'),
                                ('no', 'No'),
                              ], string='Established Position', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    recruitment_mode = fields.Selection([('Internal', 'Internal'),
                                ('External', 'External'),
                                ('Outsourced', 'Outsourced'),
                              ], string='Recruitment Mode', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'submit': [('required', True)],
                                     'submit':[('readonly', False)],
                                     })
    requested_department_id = fields.Many2one('hr.department', string ='Requested Department for Recruitment') 
    qualification = fields.Char('Qualification')
    age_required = fields.Char('Required Age')
    years_of_experience = fields.Char('Years of Experience')
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        required=False,
                                        index=True,
                                        )
    recommended_by = fields.Many2one('hr.employee', string='Recommended by',
                                     states={
                                         'submit':[('readonly', False)],
                                     })
    date_expected = fields.Date('Expected Date',
                                states={
                                         'submit': [('required', True)],
                                         'submit':[('readonly', False)],
                                     }, index=True)

    closing_date = fields.Date('Closing Date',
                                states={
                                         'submit': [('required', True)],
                                         'submit':[('readonly', False)],
                                     }, index=True)
    
    invoice_ids = fields.Many2many(
        'account.move', 
        'memo_invoice_rel',
        'memo_invoice_id',
        'invoice_memo_id',
        string='Invoice', 
        store=True,
        domain="[('type', 'in', ['in_invoice', 'in_receipt']), ('state', '!=', 'cancel')]"
        )
    
    # MEMO THINGS 
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'memo_ir_attachment_rel',
        'memo_ir_attachment_id',
        'ir_attachment_memo_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', 'memo.model')]"
        )
     
    internal_memo_option = fields.Selection(
        [
        ("all", "All"), 
        ("selected", "Selected"),
        ], string="All / Selected")
    
    partner_ids = fields.Many2many(
        'res.partner', 
        'memo_res_partner_rel',
        'memo_res_partner_id',
        'memo_partner_id',
        string='Partners', 
        )
    
    def send_memo_to_contacts(self):
        view_id = self.env.ref('mail.email_compose_message_wizard_form')
        return {
                'name': 'Send memo Message',
                'view_type': 'form',
                'view_id': view_id.id,
                "view_mode": 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_partner_ids': self.partner_ids.ids,
                    'default_subject': self.name,
                    'default_attachment_ids': self.attachment_ids.ids,
                    'default_body_html': self.description,
                    'default_body': self.description,
                },
            }

    computed_stage_ids = fields.Many2many('memo.stage', compute='_compute_stage_ids', store=True)

    @api.depends('stage_id.memo_config_id')
    def _compute_stage_ids(self):
        for record in self:
            if record.stage_id.memo_config_id:
                record.computed_stage_ids = record.stage_id.memo_config_id.stage_ids
            else:
                record.computed_stage_ids = False 
    # MEMO THINGS 
    
    ################################

    def _get_related_stage(self):
        if self.memo_type:
            domain = [
                ('memo_type', '=', self.memo_type.id), 
                ('department_id', '=', self.employee_id.department_id.id)
                ]
        else:
            domain=[('id', '=', 0)]
        return domain
    
    @api.onchange('invoice_ids')
    def get_amount(self):
        if self.invoice_ids:
            self.amountfig = sum([rec.amount_total for rec in self.invoice_ids])
    
    @api.onchange('memo_type')
    def get_default_stage_id(self):
        """ Gives default stage_id """
        
        if self.memo_type:
            if not self.employee_id.department_id:
                raise ValidationError("Contact Admin !!!  Employee must be linked to a department")
            if not self.res_users:
                department_id = self.employee_id.department_id
                ms = self.env['memo.config'].sudo().search([
                    ('memo_type', '=', self.memo_type.id),
                    ('department_id', '=', department_id.id)
                    ], limit=1)
                if ms:
                    memo_setting_stage = ms.stage_ids[0]
                    self.stage_id = memo_setting_stage.id if memo_setting_stage else False
                    self.memo_setting_id = ms.id
                    self.memo_type_key = self.memo_type.memo_key 
                    # self.res_users = [
                    #     (4, self.employee_id.administrative_supervisor_id.user_id.id),
                    #     ]
                    self.users_followers = [
                        (4, self.employee_id.administrative_supervisor_id.id),
                        ] 
                else:
                    self.memo_type = False
                    self.stage_id = False
                    self.memo_setting_id = False
                    self.memo_type_key = False
                    msg = f"No stage configured for department {department_id.name} and selected memo type. Please contact administrator"
                    return {'warning': {
                                'title': "Validation",
                                'message':msg,
                            }
                    }
        else:
            self.stage_id = False

    @api.depends('approver_id')
    def compute_user_is_approver(self):
        for rec in self:
            if rec.stage_id.is_approved_stage and self.env.user.id in [r.user_id.id for r in rec.stage_id.approver_ids]: 
                # self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids]
                rec.user_is_approver = True
                rec.users_followers = [(4, self.env.user.employee_id.id)]
            else:
                rec.user_is_approver = False
 
    @api.model
    def fields_view_get(
        self, 
        view_id='company_memo.memo_model_form_view_3', 
        view_type='form', 
        toolbar=False, 
        submenu=False):
        res = super(Memo_Model, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      toolbar=toolbar,
                                                      submenu = submenu)
        doc = etree.XML(res['arch']) 
        # users = self.env['memo.model'].search([('user_id', 'in', self.users_followers.user_id.id)])
        for rec in self.res_users:
            if rec.id == self.env.uid:
                for node in doc.xpath("//field[@name='users_followers']"):
                    node.set('modifiers', '{"readonly": true}') 
                    
                for node in doc.xpath("//button[@name='return_memo']"):
                    node.set('modifiers', '{"invisible": true}')
        res['arch'] = etree.tostring(doc)
        return res

    @api.depends('set_staff')
    def get_user_staff(self):
        if self.set_staff:
            self.demo_staff = self.set_staff.user_id.id
        else:
            self.demo_staff = False
    
    # get the employee's department
    @api.depends('employee_id')
    def employee_department(self):
        if self.employee_id:
            self.dept_ids = self.employee_id.department_id.id
            # self.district_id = self.employee_id.ps_district_id.id
        else:
            self.dept_ids = False
            # self.district_id = self.employee_id.ps_district_id.id
    
    @api.depends('employee_id')
    def compute_employee_supervisor(self):
        if self.employee_id:
            current_user = self.env.user
            if current_user.id == self.employee_id.administrative_supervisor_id.user_id.id:
                self.is_supervior = True
            else:
                self.is_supervior = False
            
            if current_user.id == self.employee_id.parent_id.user_id.id:
                self.is_manager = True
            else:
                self.is_manager = False
        else:
            self.is_supervior = False
            self.is_manager = False 

    def print_memo(self):
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.memomodel_print_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_memo_model_report').report_action(self)
     
    def set_draft(self):
        if self.env.uid != self.employee_id.user_id.id:
            raise ValidationError(
                "You are not allowed to resend this because you are not the initiator"
                )
        for rec in self:
            if rec.memo_setting_id and rec.memo_setting_id.stage_ids:
                draft_stage = rec.memo_setting_id.stage_ids[0]
                # removing user to allow resubmission
                user_id = self.mapped('res_users').filtered(
                    lambda user: user.id == self.env.uid
                    )
                if user_id:
                    rec.res_users = [(3, user_id.id)]
                rec.write({
                    'state': "submit", 
                    'direct_employee_id': False, 
                    'stage_id': draft_stage.id
                    })
     
    def user_done_memo(self):
        for rec in self:
            rec.write({'state': "Done"})
     
    def Cancel(self):
        if self.employee_id.user_id.id != self.env.uid:
            raise ValidationError(
                'Sorry!!! you are not allowed to cancel a memo not initiated by you.'
                ) 
        
        if self.state not in ['Refuse', 'Sent']:
            raise ValidationError(
                'You cannot cancel a memo that is currently undergoing management approval'
                )
        for rec in self:
            rec.write({
                'state': "submit", 
                'direct_employee_id': False, 
                'partner_id':False, 
                'users_followers': False,
                'set_staff': False,
                })

    # def get_url(self, id, name):
    #     base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #     base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
    #     return "<a href={}> </b>Click<a/>. ".format(base_url)

    def get_url(self, id):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += "/my/request/view/%s" % (id)
        return "<a href={}> </b>Click<a/>. ".format(base_url)
    
    """line 4 - 7 checks if the current user is the initiator of the memo, 
    if true, raises warning error else: it opens the wizard"""

    def validator(self, msg):
        if self.employee_id.user_id.id == self.env.user.id:
            raise ValidationError(
                "Sorry you are not allowed to reject /  return you own initiated memo"
                ) 

    # def determine_user_role(self):
    #     '''Checks if the  user is employee/administration 
    #     / Memo manager / memo gm/ memo auditor / memo account
    #     returns true to be used to set the To field in wizard to the person's manager'''
    #     user_id = self.env['res.users'].browse([self.env.uid])
    #     sys_admin = user_id.has_group("base.group_system")
    #     hr_admin = user_id.has_group("hr.group_hr_manager")
    #     memo_manager = user_id.has_group("company_memo.mainmemo_manager")
    #     memo_audit = user_id.has_group("company_memo.mainmemo_audit")
    #     memo_account = user_id.has_group("company_memo.mainmemo_account")
    #     if any([sys_admin, hr_admin, memo_audit, memo_manager, memo_account]):
    #         return False 
    #     else:
    #         if not self.employee_id.parent_id:
    #             raise ValidationError(
    #                 'Please ensure you have a unit manager / head manager assigned to your record !'
    #                 )
    #         return True
        
    def validate_memo_for_approval(self):
        item_lines = self.mapped('product_ids')
        type_required_items = ['material_request', 'procurement_request', 'vehicle_request']
        if self.memo_type.memo_key in type_required_items and self.state in ["Approve2"]:
            without_source_location_and_qty = item_lines.filtered(
                lambda sef: sef.source_location_id == False or sef.quantity_available < 1
                )
            if without_source_location_and_qty:
                 raise ValidationError(
                     """Please ensure all request lines 
                     has a source location and quantity greater than 0"""
                     )

    def forward_memo(self):
        if self.memo_type.memo_key == "Payment" and self.mapped('invoice_ids').filtered(
            lambda s: s.mapped('invoice_line_ids').filtered(lambda x: x.price_unit <= 0)
        ):
            raise ValidationError("All invoice line must have a price amount greater than 0")
        # if self.state == "submit":
        #     if not self.env.user.id == self.employee_id.user_id.id:#  or self.env.uid != self.create_uid:
        #         raise ValidationError('You cannot forward a memo at draft state because you are not the initiator')
        user_exist = self.mapped('res_users').filtered(
            lambda user: user.id == self.env.uid
            )
        if user_exist and self.env.user.id not in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You cannot forward this memo again unless returned / cancelled!!!"""
                ) 
        if self.memo_type.memo_key == "Payment" and self.amountfig <= 0:
            raise ValidationError("Payment amount must be greater than 0.0")
        elif self.memo_type.memo_key == "material_request" and not self.product_ids:
            raise ValidationError("Please add request line") 
        view_id = self.env.ref('company_memo.memo_model_forward_wizard')
        # is_officer = self.determine_user_role() # returns true or false 
        return {
                'name': 'Forward Memo',
                'view_type': 'form',
                'view_id': view_id.id,
                "view_mode": 'form',
                'res_model': 'memo.foward',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    'default_resp': self.env.uid,
                    # 'default_is_officer': is_officer,
                },
            }
    """The wizard action passes the employee whom the memo was director to this function."""
    def get_initial_stage(self, memo_type, department_id):
        memo_settings = self.env['memo.config'].sudo().search([
            ('memo_type.memo_key', '=', memo_type),
            ('department_id', '=', department_id)
            ], limit=1)
        if memo_settings and memo_settings.stage_ids:
            initial_stage_id = memo_settings.stage_ids[0]
        else:
            initial_stage_id= self.env.ref('company_memo.memo_initial_stage')
        return initial_stage_id
        
    def get_next_stage_artifact(self, current_stage_id, from_website=False):
        """
        args: from_website: used to decide if the record is 
        generated from the website or from odoo internal use
        """
        approver_ids = []
        memo_settings = self.env['memo.config'].sudo().search([
            ('memo_type', '=', self.memo_type.id),
            ('department_id', '=', self.employee_id.department_id.id)
            ], limit=1)
        memo_setting_stages = memo_settings.stage_ids
        # if not from_website and memo_setting_stages.index(current_stage_id.id) == 0:
        #     """Checks if the first index of the stages is the initial stage;
        #     Adds the employee manager or supervisor at the first stage
        #     """ 
        #     approver_ids += [
        #         self.employee_id.parent_id.id,
        #         self.employee_id.administrative_supervisor_id.id
        #     ]
        # _logger.info(f'Found memo_settings are {memo_settings} and stages {memo_settings.stage_ids} and current stage {current_stage_id}')
        
        if memo_settings and current_stage_id:
            mstages = memo_settings.stage_ids # [3,6,8,9]
            _logger.info(f'Found stages are {memo_setting_stages.ids}')
            last_stage = mstages[-1] if mstages else False # 'e.g 9'
            if last_stage and last_stage.id != current_stage_id.id:
                current_stage_index = memo_setting_stages.ids.index(current_stage_id.id)
                next_stage_id = memo_setting_stages.ids[current_stage_index + 1] # to get the next stage
            else:
                next_stage_id = self.stage_id.id
            next_stage_record = self.env['memo.stage'].browse([next_stage_id])
            if next_stage_record:
                approver_ids = next_stage_record.approver_ids.ids
            return approver_ids, next_stage_record.id
        else:
            raise ValidationError(
                "Please ensure to configure the Memo type for the employee department"
                )
    
    def update_final_state_and_approver(self, from_website=False):
        if from_website:
            # if from website args: prevents the update of stages and approvers 
            pass
        else:
            # updating the next stage
            approver_ids, next_stage_id = self.get_next_stage_artifact(self.stage_id)
            self.stage_id = next_stage_id
            # determining the stage to update the already existing state used to hide or display some components
            if self.stage_id:
                if self.stage_id.is_approved_stage:
                    if self.memo_type.memo_key in ["Payment", 'loan', 'cash_advance', 'soe']:
                        self.state = "Approve"
                    else:
                        self.state = "Approve2"
                # important: users_followers must be required in for them to see the records.
                if self.sudo().stage_id.approver_ids:
                    self.sudo().update({
                        'users_followers': [(4, appr.id) for appr in self.sudo().stage_id.approver_ids],
                        'set_staff': self.sudo().stage_id.approver_ids[0].id # FIXME To be reviewed
                        })
            if self.memo_setting_id and self.memo_setting_id.stage_ids:
                ms = self.memo_setting_id.stage_ids
                last_stage = ms[-1]
                # if id of next stage is the same with the id of the last stage of memo setting stages, 
                # write stage to done
                random_memo_approver_ids = [rec.id for rec in self.memo_setting_id.approver_ids if rec]
                if last_stage.id == next_stage_id:
                    self.sudo().write({
                            'state': 'Done'
                            })
                    if last_stage.approver_ids or random_memo_approver_ids:
                        # approver_id = last_stage.approver_id.id \
                        #         if last_stage.approver_id else random.choice(random_memo_approver_ids) \
                        #             if random_memo_approver_ids else False
                        approver_ids = last_stage.approver_id.ids or random_memo_approver_ids
                        self.sudo().write({
                            'approver_id': random.choice(approver_ids),
                            'approver_ids': [(4, appr) for appr in approver_ids],
                            # 'set_staff': approver_id
                            })
                    # else:
                    #     raise ValidationError("""
                    #                           Please contact admin to link the final validation Personnel 
                    #                           for this request. Go to memo setting for the memo type and department 
                    #                           to link the final stage approver or employees for final validation
                    #                           """)

    def confirm_memo(self, employee, comments, from_website=False): 
        # user_id = self.env['res.users'].search([('id','=',self.env.user.id)])
        # lists2 = [y.partner_id.id for x in self.users_followers for y in x.user_id]
        type = "loan request" if self.memo_type.memo_key == "loan" else "memo"
        Beneficiary = self.employee_id.name or self.user_ids.name
        body_msg = f"""Dear sir / Madam, \n \
        <br/>I wish to notify you that a {type} with description, {self.name},<br/>  
        from {Beneficiary} (Department: {self.employee_id.department_id.name or "-"}) \
        was sent to you for review / approval. <br/> <br/>Kindly {self.get_url(self.id)} \
        <br/> Yours Faithfully<br/>{self.env.user.name}""" 
        self.direct_employee_id = False 
        self.update_final_state_and_approver(from_website)
        self.mail_sending_direct(body_msg)
        body = "%s for %s initiated by %s, moved by- ; %s and sent to %s" %(
            type,
            self.name,
            Beneficiary,
            self.env.user.name,
            employee
            )
        body_main = body + "\n with the comments: %s" %(comments)
        self.follower_messages(body_main)

    def mail_sending_direct(self, body_msg): 
        subject = "Memo Notification"
        email_from = self.env.user.email
        follower_list = [item2.work_email for item2 in self.users_followers if item2.work_email]
        stage_followers_list = [
            appr.work_email for appr in self.stage_id.memo_config_id.approver_ids if appr.work_email
            ] if self.stage_id.memo_config_id.approver_ids else []
        email_list = follower_list + stage_followers_list
        # mail_to = self.approver_id.work_email or self.stage_id.approver_id.work_email \
        #     or self.direct_employee_id.work_email
        approver_emails = [eml.work_email for eml in self.stage_id.approver_ids if eml.work_email]
        mail_to = (','.join(approver_emails))
        emails = (','.join(elist for elist in email_list))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': emails,
                'body_html': body_msg
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        self.env['mail.mail'].sudo().send(mail_id)
    
    def _get_group_users(self):
        followers = []
        account_id = self.env.ref('company_memo.mainmemo_account')
        acc_group = self.env['res.groups'].search([('id', '=', account_id.id)], limit=1)
        for users in acc_group.users:
            employee = self.env['hr.employee'].search([('user_id', '=', users.id)])
            for rex in employee:
                followers.append(rex.id)
        return self.write({'users_followers': [(4, follow) for follow in followers]})
    
    def determine_if_user_is_config_approver(self):
        """
        This determines if the user is responsible to approve the memo as a Purchase Officer
        This will open up the procurement application to proceed with the respective record
        """
        memo_settings = self.env['memo.config'].sudo().search([
            ('id', '=', self.memo_setting_id.id)
            ])
        memo_approver_ids = memo_settings.approver_ids
        user = self.env.user
        emloyee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if emloyee and emloyee.id in [emp.id for emp in memo_approver_ids] or self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids]:
            return True
        else:
            return False

    def complete_memo_transactions(self): # Always available to Some specific groups
        body = "MEMO COMPLETION NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        body_msg = f"""Dear {self.employee_id.name}, 
        <br/>I wish to notify you that a {type} with description, '{self.name}',\
        from {self.employee_id.department_id.name or self.user_ids.name} \
        department have been Confirmed by {self.env.user.name}.<br/>\
        Respective authority should take note. \
        <br/>Kindly {self.get_url(self.id)} <br/>\
        Yours Faithfully<br/>{self.env.user.name}"""
        return self.generate_memo_artifacts(body_msg, body)

    def check_supervisor_comment(self):
        if self.memo_type.memo_key == "server_access":
            if self.employee_id.administrative_supervisor_id and not self.supervisor_comment:
                raise ValidationError(
                    """Please Inform the employee's supervisor to comment on this before approving 
                    """)
            elif not self.employee_id.administrative_supervisor_id and not self.manager_comment:
                raise ValidationError(
                    """Please Inform the employee's Manager to comment on this before approving 
                    """)
                    
    def user_approve_memo(self): # Always available to Some specific groups
        return self.approve_memo()

    def approve_memo(self): # Always available to Some specific groups
        ### check if supervisor has commented on the memo if it is server access
        self.check_supervisor_comment()
        is_config_approver = self.determine_if_user_is_config_approver()
        if self.env.uid == self.employee_id.user_id.id and not is_config_approver:
            raise ValidationError(
                """You are not Permitted to approve a Payment Memo. 
                Forward it to the authorized Person""")
        if self.env.uid not in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person"""
                )
        body = "MEMO APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "request"
        body_msg = f"""Dear {self.employee_id.name}, <br/>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.employee_id.department_id.name or self.user_ids.name} department have been approved by {self.env.user.name}.<br/>\
                Respective authority should take note. \
                <br/>Kindly {self.get_url(self.id)} <br/>\
                Yours Faithfully<br/>{self.env.user.name}"""
        users = self.env['res.users'].sudo().browse([self.env.uid])
        self.update_final_state_and_approver()
        self.sudo().write({'res_users': [(4, users.id)]})
        return self.generate_memo_artifacts(body_msg, body)
    
     
  
    def generate_memo_artifacts(self, body_msg, body):
        if self.memo_type.memo_key == "material_request":
            return self.generate_stock_material_request(body_msg, body)
        elif self.memo_type.memo_key == "procurement_request":
            return self.generate_stock_procurement_request(body_msg, body)
        elif self.memo_type.memo_key == "vehicle_request":
            self.generate_vehicle_request(body_msg) 
        elif self.memo_type.memo_key == "recruitment_request":
            self.generate_recruitment_request(body_msg) 
        elif self.memo_type.memo_key == "leave_request":
            self.generate_leave_request(body_msg, body)
        elif self.memo_type.memo_key == "cash_advance":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type.memo_key == "soe":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type.memo_key == "server_access":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        # elif self.memo_type.memo_key == "employee_update":
        #     return self.generate_employee_transfer(body_msg)
        #     # self.mail_sending_direct(body_msg)
        else:
            pass

    def generate_stock_material_request(self, body_msg, body):
        stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        existing_picking = stock_picking.search([('memo_id', '=', self.id)], limit=1)
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        destination_location_id = self.env.ref('stock.stock_location_customers')
        if not existing_picking:
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'origin': self.code,
                'memo_id': self.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'move_ids_without_package': [(0, 0, {
                                'name': self.code, 
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': destination_location_id.id,
                                'product_id': mm.product_id.id,
                                'product_uom_qty': mm.quantity_available,
                                'date_deadline': self.date_deadline,
                }) for mm in self.product_ids]
            }
            stock = stock_picking.sudo().create(vals)
        else:
            stock = existing_picking
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            view_id = self.env.ref('stock.view_picking_form').id
            ret = {
                'name': "Purchase Order",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.picking',
                'res_id': stock.id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'current'
                }
            return ret
            # return self.record_to_open(
            #     "stock.picking", 
            #     view_id,
            #     stock.id,
            #     f"Stock - {stock.name}"
            #     )

    def generate_stock_procurement_request(self, body_msg, body):
        """
        Check po record if already create, popup the wizard, 
        else create pO and pop up the wizard
        """
        stock_picking_type_in = self.env.ref('stock.picking_type_in')
        purchase_obj = self.env['purchase.order']
        existing_po = purchase_obj.search([('memo_id', '=', self.id)], limit=1)
        if not existing_po:
            vals = {
                'date_order': self.date,
                'picking_type_id': stock_picking_type_in.id,
                'origin': self.code,
                'memo_id': self.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'order_line': [(0, 0, {
                                'product_id': mm.product_id.id,
                                'name': mm.description or f'{mm.product_id.name} Requistion',
                                'product_qty': mm.quantity_available,
                                'price_unit': mm.amount_total,
                                'date_planned': self.date,
                }) for mm in self.product_ids]
            }
            po = purchase_obj.create(vals)
        else:
            po = existing_po
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            self.follower_messages(body)
            view_id = self.env.ref('purchase.purchase_order_form').id
            ret = {
                'name': "Purchase Order",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'purchase.order',
                'res_id': po.id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'new'
                }
            return ret
            # return self.record_to_open(
            #         "purchase.order", 
            #         view_id,
            #         po.id,
            #         f"Purchase Order - {po.name}"
            #         )

    def generate_vehicle_request(self, body_msg):
        # TODO: generate fleet asset
        self.state = 'Done'
        self.is_request_completed = True
        # self.sudo().update_final_state_and_approver()
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)

    def generate_recruitment_request(self, body_msg=False):
        """
        Create HR job application ready for publication 
        """
        recruitment_request_obj = self.env['hr.job.recruitment.request']
        existing_hrr = recruitment_request_obj.search([
            ('memo_id', '=', self.id),
            ], limit=1)
        if not existing_hrr:
            vals = {
                'job_tmp': self.job_tmp,
                'department_id': self.requested_department_id.id,
                'name': self.name,
                'memo_id': self.id,
                'recruitment_mode': self.recruitment_mode,
                'job_id': self.job_id.id,
                'user_id': self.employee_id.user_id.id,
                'user_to_approve_id': random.choice([r.user_id.id for r in self.stage_id.approver_ids]),
                'expected_employees': self.expected_employees,
                'recommended_by': self.recommended_by.user_id.id,
                'description': BeautifulSoup(self.description or "-", features="lxml").get_text(),
                'requirements': self.qualification,
                'age_required': self.age_required,
                'years_of_experience': self.years_of_experience,
                'state': 'confirmed',
                'date_expected': self.date_expected,
                'date_accepted': fields.Date.today(),
                'date_confirmed': fields.Date.today(),
            }
            rr_id = recruitment_request_obj.create(vals)
        else:
            rr_id = existing_hrr
        self.update_memo_type_approver()
        if body_msg:
            self.mail_sending_direct(body_msg)
        self.state = 'Done'
        """Check if the user is enlisted as the approver for memo type"""
        view_id = self.env.ref('hr_cbt_portal_recruitment.hr_job_recruitment_request_form_view').id
        ret = {
            'name': "Recruitment request",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.job.recruitment.request',
            'res_id': rr_id.id,
            'type': 'ir.actions.act_window',
            'domain': [],
            'target': 'current'
            }
        return ret

    def generate_leave_request(self, body_msg, body):
        leave = self.env['hr.leave'].sudo()
        vals = {
            'employee_id': self.employee_id.id,
            'request_date_from': self.leave_start_date,
            'request_date_to': self.leave_end_date,
            'name': BeautifulSoup(self.description or "Leave request", features="lxml").get_text(),
            'holiday_status_id': self.leave_type_id.id,
            'origin': self.code,
            'memo_id': self.id,
        }
        leave_id = leave.create(vals)
        leave_id.action_approve()
        leave_id.action_validate()
        self.state = 'Done'
        self.mail_sending_direct(body_msg)

    def generate_move_entries(self):
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type
            if approver is an account officer, system generates move and open the exact record"""
            view_id = self.env.ref('account.view_move_form').id
            # move_id = self.generate_move_entries()
            journal_id = self.env['account.journal'].search(
            [('type', '=', 'purchase'),
             ('code', '=', 'BILL')
             ], limit=1)
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            if not inv:
                partner_id = self.employee_id.user_id.partner_id
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'partner_id': partner_id.id,
                    'company_id': self.env.user.company_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    'name': f"CADV/ {self.code}",
                    'move_type': 'in_receipt',
                    'invoice_date': fields.Date.today(),
                    'date': fields.Date.today(),
                    'journal_id': journal_id.id,
                    'invoice_line_ids': [(0, 0, {
                            'name': pr.product_id.name if pr.product_id else pr.description,
                            'ref': f'{self.code}: {pr.product_id.name or pr.description}',
                            'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                            'price_unit': pr.amount_total,
                            'quantity': pr.quantity_available,
                            'discount': 0.0,
                            'code': pr.code,
                            'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                            'product_id': pr.product_id.id if pr.product_id else None,
                    }) for pr in self.product_ids],
                })
            self.move_id = inv.id
            return self.record_to_open(
            "account.move", 
            view_id,
            inv.id,
            f"Journal Entry - {inv.name}"
            ) 
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments")
        
    def generate_soe_entries(self):
        # self.follower_messages(body)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            self.write({
                'state': 'Approve2'
            })
            # """Check if the user is enlisted as the approver for memo type
            # if approver is an account officer, system generates move and open the exact record"""
            # view_id = self.env.ref('account.view_move_form').id
            # journal_id = self.env['account.journal'].search(
            # [('type', '=', 'sale'),
            #  ('code', '=', 'INV')
            #  ], limit=1)
            # # 5000 - 3000
            # account_move = self.env['account.move'].sudo()
            # inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            # if not inv:
            #     partner_id = self.employee_id.user_id.partner_id
            #     inv = account_move.create({ 
            #         'memo_id': self.id,
            #         'ref': self.code,
            #         'origin': self.code,
            #         'partner_id': partner_id.id,
            #         'company_id': self.env.user.company_id.id,
            #         'currency_id': self.env.user.company_id.currency_id.id,
            #         # Do not set default name to account move name, because it
            #         # is unique 
            #         'name': f"SOE {self.code}",
            #         'move_type': 'out_receipt',
            #         'invoice_date': fields.Date.today(),
            #         'date': fields.Date.today(),
            #         'journal_id': journal_id.id,
            #         'invoice_line_ids': [(0, 0, {
            #                 'name': pr.product_id.name if pr.product_id else pr.description,
            #                 'ref': f'{self.code}: {pr.product_id.name}',
            #                 'account_id': pr.product_id.property_account_income_id.id or pr.product_id.categ_id.property_account_income_categ_id.id if pr.product_id else journal_id.default_account_id.id,
            #                 'price_unit': pr.used_total,
            #                 'quantity': pr.used_qty,
            #                 'discount': 0.0,
            #                 'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
            #                 'product_id': pr.product_id.id if pr.product_id else None,
            #         }) for pr in self.product_ids],
            #     })
                # for pr in self.mapped('product_ids').filtered(lambda x: x.to_retire):
                #     cash_advance_amount = self.env['account.move.line'].search([
                #         ('code', '=', pr.code)
                #         ], limit=1) # locating the existing cash_advance_line to get the initial request amount
                #     if cash_advance_amount:
                #         approved_cash_advance_amount = cash_advance_amount.price_unit
                #         balance_remaining = approved_cash_advance_amount - pr.used_total # e.g 5000 - 3000 = 2000
                #         inv.invoice_line_ids = [(0, 0, {
                #                 'name': pr.product_id.name if pr.product_id else pr.description,
                #                 'ref': f'{self.code}: {pr.product_id.name}',
                #                 'account_id': pr.product_id.property_account_income_id.id or pr.product_id.categ_id.property_account_income_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                #                 'price_unit': balance_remaining, # pr.used_total,
                #                 'quantity': pr.used_qty,
                #                 'discount': 0.0,
                #                 'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                #                 'product_id': pr.product_id.id if pr.product_id else None,
                #         })]
                #         pr.update({'retired': True}) # updating the Line as retired
            # self.update_inventory_product_quantity()
                # return self.record_to_open(
                # "account.move", 
                # view_id,
                # inv.id,
                # f"Journal Entry SOE - {inv.name}"
                # ) 
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments")
         
    def record_to_open(self, model, view_id, res_id=False, name=False):
        obj = self.env[f'{model}'].search([('origin', '=', self.code)], limit=1)
        if obj:
            return self.open_related_record_view(
                model, 
                res_id if res_id else obj.id ,
                view_id,
                name if name else f"{obj.name}"
            )
        else:
            raise ValidationError("No related record found for the memo")

    def update_inventory_product_quantity(self):
        '''this will be used to raise a stock tranfer record. Once someone claimed he returned a 
         positive product (storable product) , 
         system should generate a stock picking to update the new product stock
         if product does not exist, To be asked for '''
        stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        partner_location_id = self.env.ref('stock.stock_location_customers')
        vals = {
            'scheduled_date': fields.Date.today(),
            'picking_type_id': stock_picking_type_out.id,
            'origin': self.code,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'move_ids_without_package': [(0, 0, {
                            'name': self.code, 
                            'picking_type_id': stock_picking_type_out.id,
                            'location_id': partner_location_id.id,
                            'location_dest_id': mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                            'product_id': mm.product_id.id,
                            'product_uom_qty': mm.quantity_available,
                            'date_deadline': self.date_deadline,
            }) for mm in self.mapped('product_ids').filtered(
                lambda pr: pr.product_id and pr.product_id.detailed_type == "product" and pr.to_retire == True)]
        }
        stock_picking.sudo().create(vals)

    def open_related_record_view(self, model, res_id, view_id, name="Record To approved"):
        ret = {
                'name': name,
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': model,
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'current'
                }
        return ret

    def update_memo_type_approver(self):
        """update memo type approver"""
        memo_settings = self.env['memo.config'].sudo().search([
                ('memo_type', '=', self.memo_type.id),
                ('department_id', '=', self.employee_id.department_id.id)
                ])
        memo_approver_ids = memo_settings.approver_ids
        for appr in memo_approver_ids:
            self.sudo().write({
                'users_followers': [(4, appr.id)] 
            })
      
    def view_related_record(self):
        if self.memo_type.memo_key == "material_request":
            view_id = self.env.ref('stock.view_picking_form').id
            return self.record_to_open('stock.picking', view_id)
             
        elif self.memo_type.memo_key == "procurement_request":
            view_id = self.env.ref('purchase.purchase_order_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type.memo_key == "vehicle_request":
            pass 
        elif self.memo_type.memo_key == "leave_request":
            view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type.memo_key == "cash_advance":
            view_id = self.env.ref('account.view_move_form').id
            return self.record_to_open('account.move', view_id)
        else:
            pass 

    def follower_messages(self, body):
        pass 
        # body= "RETURN NOTIFICATION;\n %s" %(self.reason_back)
        # body = body
        # records = self._get_followers()
        # followers = records
        # self.message_post(body=body)
        # self.message_post(body=body, 
        # subtype='mt_comment',message_type='notification',partner_ids=followers)
     
    # def generate_move_entriesxx(self):
    #     '''pr: product obj'''
    #     # journal_id = self.env['account.journal'].search([
    #     #     '|',('type', '=', 'cash'),
    #     #     ('type', '=', 'bank'),
    #     #     ], limit=1)
    #     journal_id = self.env['account.journal'].search(
    #         [('type', '=', 'purchase'),
    #          ('code', '=', 'BILL')
    #          ], limit=1
    #     )
    #     account_move = self.env['account.move'].sudo()
    #     inv = account_move.search([('memo_id', '=', self.id)], limit=1)
    #     if not inv:
    #         partner_id = self.employee_id.user_id.partner_id
    #         inv = account_move.create({ 
    #             'memo_id': self.id,
    #             'ref': self.code,
    #             'origin': self.code,
    #             'partner_id': partner_id.id,
    #             'company_id': self.env.user.company_id.id,
    #             'currency_id': self.env.user.company_id.currency_id.id,
    #             # Do not set default name to account move name, because it is unique 
    #             'name': f"CASH ADV/ {self.code}",
    #             'move_type': 'in_receipt',
    #             'date': fields.Date.today(),
    #             'journal_id': journal_id.id,
    #             'invoice_line_ids': [(0, 0, {
    #                     'name': pr.product_id.name,
    #                     'ref': f'{self.code}: {pr.product_id.name}',
    #                     'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
    #                     'price_unit': pr.amount_total,
    #                     'quantity': pr.quantity_available,
    #                     'discount': 0.0,
    #                     'product_uom_id': pr.product_id.uom_id.id,
    #                     'product_id': pr.product_id.id,
    #             }) for pr in self.product_ids],
    #         })
    #         # inv.post()
    #         # self.validate_invoice_and_post_journal(journal_id.id, inv)
    #     else:
    #         return inv
    #     return inv
    def validate_account_invoices(self):
        invalid_record = self.mapped('invoice_ids').filtered(lambda s: not s.partner_id or not s.payment_journal_id)
        if invalid_record:
            raise ValidationError("Partner, Payment journal must be selected. Also ensure the status is in draft")
        
    def action_post_and_vallidate_payment(self): # Register Payment
        self.validate_account_invoices()
        for count, rec in enumerate(self.invoice_ids, 1):
            if not rec.invoice_line_ids:
                raise ValidationError(
                    f'Invoice at line {count} does not have move lines'
                    )   
            else:
                if rec.payment_state == 'not_paid': 
                    if rec.state == 'draft':
                        rec.action_post()
        outbound_payment_method = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
        payment_method = 2
        journal_id = rec.payment_journal_id
        if journal_id:
            payment_method = journal_id.outbound_payment_method_line_ids[0].id if \
                journal_id.outbound_payment_method_line_ids else outbound_payment_method.id \
                    if outbound_payment_method else payment_method
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.invoice_ids.ids).create({
                'group_payment': False,
                'payment_method_line_id': payment_method,
            })._create_payments()
        self.finalize_payment()

    def finalize_payment(self):
        if self.invoice_ids:
            allpaid_invoice = self.mapped('invoice_ids').filtered(lambda s: s.payment_state in ['paid', 'in_payment'])
            if allpaid_invoice:
                self.state = "Done"
        else:
            self.state = "Done"
 
    def get_payment_method_line_id(self, payment_type, journal_id):
            if journal_id:
                available_payment_method_lines = journal_id._get_available_payment_method_lines(payment_type)
            else:
                available_payment_method_lines = False

            # Select the first available one by default.
            if available_payment_method_lines:
                payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                payment_method_line_id = False
            return payment_method_line_id
            
    def validate_invoice_and_post_journal(
            self, journal_id, inv): 
            """To be used only when they request for automatic payment generation"""
            account_payment = self.env['account.payment'].sudo()
            outbound_payment_method = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
            payment_method = 2
            if journal_id:
                payment_method = journal_id.outbound_payment_method_line_ids[0].id if \
                    journal_id.outbound_payment_method_line_ids else outbound_payment_method.id \
                        if outbound_payment_method else payment_method
                
            payment_method_line_id = self.get_payment_method_line_id('outbound', journal_id)
            payment_vals = {
                'date': fields.Date.today(),
                'amount': inv.amount_total,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'ref': inv.name,
                'move_id': inv.id,
                'journal_id': 8, #inv.payment_journal_id.id,
                'currency_id': inv.currency_id.id,
                'partner_id': inv.partner_id.id,
                'destination_account_id': inv.line_ids[1].account_id.id,
                'payment_method_line_id': payment_method, #payment_method_line_id.id if payment_method_line_id else payment_method,
            }
            payments = self.env['account.payment'].create(payment_vals)
            payments.action_post()

    def Register_Payment(self):
        if self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person
            """)
        view_id = self.env.ref('account.view_account_payment_form')
        if (self.memo_type.memo_key != "Payment") or (self.amountfig < 1):
            raise ValidationError("(1) Memo type must be 'Payment'\n (2) Amount must be greater than one to proceed with payment")
        account_payment_existing = self.env['account.payment'].search([
            ('memo_reference', '=', self.id)
            ], limit=1)
        vals = {
                'name':'Memo Payment',
                'view_mode': 'form',
                'view_id': view_id.id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'target': 'current'
                }
        if not account_payment_existing:
            vals.update({
                'context': {
                        'default_amount': self.amountfig,
                        'default_payment_type': 'outbound',
                        'default_partner_id':self.vendor_id.id or self.employee_id.user_id.partner_id.id, 
                        'default_memo_reference': self.id,
                        'default_communication': self.name,
                },
                'domain': [],
            })
        else:
            vals.update({
                'res_id': account_payment_existing.id
            })
        return vals

    def generate_loan_entries(self):
        if self.loan_reference:
            raise ValidationError("You have generated a loan already for this record")
        view_id = self.env.ref('account_loan.account_loan_form')
        if (self.memo_type.memo_key != "loan") or (self.loan_amount < 1):
            raise ValidationError("Check validation: \n (1) Memo type must be 'loan request'\n (2) Loan Amount must be greater than one to proceed with loan request")
        ret = {
            'name':'Generate loan request',
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'account.loan',
            'type': 'ir.actions.act_window',
            'domain': [],
            'context': {
                    'default_loan_type': self.loan_type,
                    'default_loan_amount': self.loan_amount,
                    'default_periods':self.periods or 12,  
                    'default_partner_id':self.employee_id.user_id.partner_id.id,  
                    'default_method_period':self.method_period,  
                    'default_rate': 15, 
                    'default_start_date':self.start_date, 
                    'default_name': self.code,
            },
            'target': 'current'
            }
        return ret

    def migrate_records(self):
        account_ref = self.env['account.payment'].search([])
        for rec in account_ref:
            memo_rec = self.env['memo.model'].search([('code', '=', rec.communication)])
            if memo_rec:
                memo_rec.state = "Done"
        
    def return_memo(self):
        msg = "You have initially forwarded this memo. Kindly use the cancel button or wait for approval"
        self.validator(msg)
        default_sender = self.mapped('res_users')
        last_sender = self.env['hr.employee'].search([('user_id', '=', default_sender[-1].id)]).id if default_sender else False
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'memo.back',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date,
                  'default_direct_employee_id': last_sender,
                  'default_resp':self.env.uid,
              },
        }
    
    @api.depends('state')
    # Depending on any field change (ORM or Form), the function is triggered.
    def _progress_state(self):
        for order in self:
            if order.state in ["submit", "Refuse"]:
                order.status_progress = random.randint(0, 5)
            elif order.state == "Sent":
                order.status_progress = random.randint(20, 60)
            elif order.state == "Approve":
                order.status_progress = random.randint(71, 95)
            elif order.state == "Approve2":
                order.status_progress = random.randint(71, 98)
            elif order.state == "Done":
                order.status_progress = random.randint(98, 100)
            else:
                order.status_progress = random.randint(0, 1) # 100 / len(order.state)
    
    expiry_mail_sent = fields.Boolean(default=False, copy=False)

    @api.model
    def _cron_notify_server_request_followers(self):
        """
        System should check all requests end date expired, and send message
        to server admin or followers. 
        """
        # for record in self:
        
        expired_memos = self.env['memo.model'].search([
            ('request_end_date', '<', fields.Datetime.now()),
            ('expiry_mail_sent', '=', False),
            ('memo_type', '=', 'server_access'),
            ])
        for exp in expired_memos:
            if exp.memo_setting_id and exp.memo_setting_id.approver_ids:
                body_msg = f"""Dear Sir, \n \
                    <br/>I wish to notify you that a server access request with description, {exp.name},<br/>  
                    from {exp.employee_id.name} \
                    has now expired. <br/> <br/>Go to the request {self.get_url(exp.id)} \
                """
                exp.mail_sending_direct(body_msg)
                exp.expiry_mail_sent = True
                # request_followers = [
                #     eml.work_email for eml in exp.memo_setting_id.approver_ids if eml.work_email
                #     ]
        

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.state in ['Sent','Approve2', 'Approve']):
            raise ValidationError(_('You cannot delete a Memo which is in %s state.') % (delete.state,))
        return super(Memo_Model, self).unlink()
