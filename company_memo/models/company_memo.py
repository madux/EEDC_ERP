from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from bs4 import BeautifulSoup
from odoo import http
import random
from lxml import etree

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
        ], string="Memo Type",default="Internal", required=True)

    name = fields.Char('Subject', size=400)
    code = fields.Char('Code', readonly=True)
    employee_id = fields.Many2one('hr.employee', string = 'Employee', default =_default_employee) 
    direct_employee_id = fields.Many2one('hr.employee', string = 'Employee') 
    set_staff = fields.Many2one('hr.employee', string = 'Employee')
    demo_staff = fields.Integer(string='User', compute="get_user_staff",
                                default=lambda self: self.env['res.users'].search([('id', '=', self.env.uid)], limit=1).id)
        
    user_ids = fields.Many2one('res.users', string = 'Beneficiary', default =_default_user)
    dept_ids = fields.Many2one('hr.department', string ='Department', 
    compute="employee_department", readonly = True, store =True)
    district_id = fields.Many2one("hr.district", string="District ID")
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    amountfig = fields.Float('Budget Amount', store=True, default=1.0)
    description_two = fields.Text('Reasons')
    phone = fields.Char('Phone', store=True)
    email = fields.Char('Email')
    reason_back = fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')
    file_namex = fields.Char("FileName")
    state = fields.Selection([('submit', 'Draft'),
                                ('Sent', 'Sent'),
                                ('Approve', 'Waiting For Payment / Confirmation'),
                                ('Approve2', 'Memo Approved'),
                                ('Done', 'Done'),
                                ('Refuse', 'Refused'),
                              ], string='Status', index=True, readonly=True,
                             copy=False, default='submit',
                             required=True,
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
    soe_advance_reference = fields.Many2one('memo.model', 'SOE ref.')
    cash_advance_reference = fields.Many2one('memo.model', 'Cash Advance ref.')
    date_deadline = fields.Date('Deadline date')
    status_progress = fields.Float(string="Progress(%)", compute='_progress_state')
    users_followers = fields.Many2many('hr.employee', string='Add followers') #, default=_default_employee)
    res_users = fields.Many2many('res.users', string='Approvers') #, default=_default_employee)
    comments = fields.Text('Comments', default="-")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='No. Attachments')
    partner_id = fields.Many2many('res.partner', string='Related Partners')
    approver_id = fields.Many2one('hr.employee', 'Approver')
    user_is_approver = fields.Boolean(string="User is approver", compute="compute_user_is_approver")

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
        "res.currency", default= lambda self: self.env.user.company_id.currency_id.id, readonly=True,
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

    product_ids = fields.One2many('request.line', 'memo_id', string ='Products') 
    leave_start_date = fields.Datetime('Leave Start Date',  default=fields.Date.today())
    leave_end_date = fields.Datetime('Leave End Date', default=fields.Date.today())
    leave_type_id = fields.Many2one('hr.leave.type', string="Leave type")

    # @api.depends('approver_id')
    def compute_user_is_approver(self):
        if self.approver_id and self.approver_id.user_id.id == self.env.user.id:
            self.user_is_approver = True

        elif self.employee_id.parent_id.user_id.id == self.env.user.id or \
        self.employee_id.administrative_supervisor_id.user_id.id == self.env.user.id:
            self.user_is_approver = True

        elif self.determine_if_user_is_config_approver():
            self.user_is_approver = True
        else:
            self.user_is_approver = False

    @api.model
    def fields_view_get(self, view_id='company_memo.memo_model_form_view_3', view_type='form', toolbar=False, submenu=False):
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

    @api.onchange('invoice_id')
    def get_amount(self):
        if self.invoice_id and self.invoice_id.state in ['posted', 'cancel']:
            self.invoice_id = False 
            return {
                'warning': {
                    'title': "Validation",
                    'message': "You selected an invoice that is either cancelled or posted already",
                }
            }
        self.amountfig = self.invoice_id.amount_total
         
    @api.depends('set_staff')
    def get_user_staff(self):
        if self.set_staff:
            self.demo_staff = self.set_staff.user_id.id
        else:
            self.demo_staff = False
        
    # @api.one
    # def write(self, vals):
    #     res = super(Memo_Model, self).write(vals)
    #     if self.state != "submit":
    #         for rec in self.res_users:
    #             if rec.id == self.env.uid:
    #                 raise ValidationError('You are not allowed to Edit this document')
    #         return res

    def print_memo(self):
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.memomodel_print_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_memo_model_report').report_action(self)
     
    def set_draft(self):
        for rec in self:
            rec.write({'state': "submit", 'direct_employee_id': False})
     
    def user_done_memo(self):
        for rec in self:
            rec.write({'state': "Done"})
     
    def Cancel(self):
        if self.employee_id.user_id.id != self.env.uid:
            raise ValidationError('Sorry!!! you are not allowed to cancel a memo not initiated by you.') 
        
        if self.state not in ['Refuse', 'Sent']:
            raise ValidationError('You cannot cancel a memo that is currently undergoing management approval')
        for rec in self:
            rec.write({
                'state': "submit", 
                'direct_employee_id': False, 
                'partner_id':False, 
                'users_followers': False,
                'set_staff': False,
                })

    def get_url(self, id, name):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (id, name)
        return "<a href={}> </b>Click<a/>. ".format(base_url)
    
    # get the employee's department
    @api.depends('employee_id')
    def employee_department(self):
        if self.employee_id:
            self.dept_ids = self.employee_id.department_id.id
            # self.district_id = self.employee_id.ps_district_id.id
        else:
            self.dept_ids = False
            # self.district_id = self.employee_id.ps_district_id.id

               
    """line 4 - 7 checks if the current user is the initiator of the memo, if true, raises warning error
    else: it opens the wizard"""

    def validator(self, msg):
        if self.employee_id.user_id.id == self.env.user.id:
            raise ValidationError("Sorry you are not allowed to reject /  return you own initiated memo") 
        # users = self.env['res.users'].browse([self.env.uid])
         
        # usr = self.mapped('res_users').filtered(lambda x: x.id == self.env.user.id)
        # if usr:
        #     raise ValidationError(msg)

    def determine_user_role(self):
        '''Checks if the  user is employee/administration / Memo manager / memo gm/ memo auditor / memo account
        returns true to be used to set the To field in wizard to the person's manager'''
        user_id = self.env['res.users'].browse([self.env.uid])
        sys_admin = user_id.has_group("base.group_system")
        hr_admin = user_id.has_group("hr.group_hr_manager")
        memo_manager = user_id.has_group("company_memo.mainmemo_manager")
        memo_audit = user_id.has_group("company_memo.mainmemo_audit")
        memo_account = user_id.has_group("company_memo.mainmemo_account")
        if any([sys_admin, hr_admin, memo_audit, memo_manager, memo_account]):
            return False 
        else:
            if not self.employee_id.parent_id:
                raise ValidationError('Please ensure you have a unit manager / head manager assigned to your record !')
            return True
    
                                    
    def validate_memo_for_approval(self):
        item_lines = self.mapped('product_ids')
        type_required_items = ['material_request', 'procurement_request', 'vehicle_request']
        if self.memo_type in type_required_items and self.state in ["Approve2"]:
            without_source_location_and_qty = item_lines.filtered(lambda sef: sef.source_location_id == False or sef.quantity_available < 1)
            if without_source_location_and_qty:
                 raise ValidationError("Please ensure all request lines has a source location and quantity greater than 0")

    def forward_memo(self): 
        if self.state == "submit":
            if not self.env.user.id == self.employee_id.user_id.id:#  or self.env.uid != self.create_uid:
                raise ValidationError('You cannot forward a memo at draft state because you are not the initiator')
        if self.state == "Sent":
            if self.env.user.id == self.employee_id.user_id.id:
                raise ValidationError("""
                                      You cannot forward this memo again \n \
                                       until returned or approved by superior!!!
                                      """) 
        users = self.env['res.users'].browse([self.env.uid])
        manager = users.has_group("company_memo.mainmemo_manager")
        admin = users.has_group("base.group_system")
        # dummy, view_id = self.env['ir.model.data'].get_object_reference('company_memo', 'memo_model_forward_wizard')
        view_id = self.env.ref('company_memo.memo_model_forward_wizard')
        is_officer = self.determine_user_role() # returns true or false 
        #usr = self.mapped('res_users').filtered(lambda x: x.id == self.env.user.id)
        #if usr:
         #   raise ValidationError('You have initially forwarded this document. Kindly reject, cancel or Wait for aproval')
        #else:
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
                    # 'default_date': self.date, 
                    'default_resp': self.env.uid,
                    # 'default_direct_employee_id': self.employee_id.parent_id.id,
                    'default_is_officer': is_officer,
                },
            }
    """The wizard action passes the employee whom the memo was director to this function."""

    def forward_memos(self, employee, comments): # Always available,  
        user_id = self.env['res.users'].search([('id','=',self.env.user.id)])
        lists2 = [y.partner_id.id for x in self.users_followers for y in x.user_id]
        # self.write({'partner_id': [(4, lists2)]}) 
        type = "loan request" if self.memo_type == "loan" else "memo"
        Beneficiary = self.employee_id.name or self.user_ids.name
        body_msg = f"""Dear {self.direct_employee_id.name or self.approver_id.name}, \n \
        <br/>I wish to notify you that a {type} with description, {self.name},<br/>  
        from {Beneficiary} (Department: {self.employee_id.department_id.name or "-"}) \
        was sent to you for review / approval. <br/> <br/>Kindly {self.get_url(self.id, self._name)} \
        <br/> Yours Faithfully<br/>{self.env.user.name}""" 
        self.mail_sending_direct(body_msg)
        self.direct_employee_id = False 
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
        mail_to = self.direct_employee_id.work_email or self.approver_id.work_email
        emails = (','.join(str(item2.work_email) for item2 in self.users_followers))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'email_cc': emails if self.users_followers else [],
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
            ('memo_type', '=', self.memo_type)
            ])
        memo_approver_ids = memo_settings.approver_ids
        user = self.env.user
        emloyee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if emloyee and emloyee.id in [emp.id for emp in memo_approver_ids]:
            return True
        else:
            return False
            
    def user_approve_memo(self): # Always available to Some specific groups
        return self.approve_memo()
    
    def approve_memo(self): # Always available to Some specific groups
        # users = self.env['res.users'].browse([self.env.uid])
        # manager = users.has_group("company_memo.mainmemo_manager")
        # if not manager: 
        is_config_approver = self.determine_if_user_is_config_approver()

        if self.env.uid == self.employee_id.user_id.id and not is_config_approver:
            raise ValidationError(
                """You are not Permitted to approve a Payment Memo. Forward it to the authorized Person
            """)
        body = "MEMO APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "request"
        body_msg = f"""Dear {self.employee_id.name}, </br>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.employee_id.department_id.name or self.user_ids.name} department have been approved by {self.env.user.name}.</br>\
                Accountant's/ Respective authority should take note. \
                </br>Kindly {self.get_url(self.id, self._name)} </br>\
                Yours Faithfully</br>{self.env.user.name}"""

        users = self.env['res.users'].browse([self.env.uid])
        if self.state in ["Approve", "Approve2", "Done"]:
            raise ValidationError("Sorry!!! this record have already been approved.")
        if self.memo_type in ["Payment", 'loan', 'cash_advance', 'soe', 'server_access']:
            self.state = "Approve"
        else: #lif self.memo_type == "Internal":
            self.state = "Approve2"
        
        self.write({'res_users': [(4, users.id)]})
        return self.generate_memo_artifacts(body_msg, body)
         
    def generate_memo_artifacts(self, body_msg, body):
        if self.memo_type == "material_request":
            return self.generate_stock_material_request(body_msg, body)
        elif self.memo_type == "procurement_request":
            self.generate_stock_procurement_request(body_msg, body) 
        elif self.memo_type == "vehicle_request":
            self.generate_vehicle_request(body_msg, body) 
        elif self.memo_type == "leave_request":
            self.generate_leave_request(body_msg, body)
        elif self.memo_type == "cash_advance":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type == "soe":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type == "server_access":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        else:
            pass 

    def generate_stock_material_request(self, body_msg, body):
        stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        destination_location_id = self.env.ref('stock.stock_location_customers')
        vals = {
            'scheduled_date': fields.Date.today(),
            'picking_type_id': stock_picking_type_out.id,
            'origin': self.code,
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
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        # self.follower_messages(body)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            view_id = self.env.ref('stock.view_picking_form').id
            return self.record_to_open(
                "stock.picking", 
                view_id,
                stock.id,
                f"Stock - {stock.name}"
                )
    
    def generate_stock_procurement_request(self, body_msg, body):
        stock_picking_type_in = self.env.ref('stock.picking_type_in')
        purchase_obj = self.env['purchase.order']
        vals = {
            'date_order': self.date,
            'picking_type_id': stock_picking_type_in.id,
            'origin': self.code,
            'memo_id': self.id,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'order_line': [(0, 0, {
                            'product_id': mm.product_id.id,
                            'name': mm.description,
                            'product_qty': mm.quantity_available,
                            'date_planned': self.date,
            }) for mm in self.product_ids]
        }
        po = purchase_obj.create(vals)
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        # self.follower_messages(body)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            view_id = self.env.ref('purchase.purchase_order_form').id
            self.mail_sending_direct(body_msg)
            self.follower_messages(body)
            return self.record_to_open(
                    "purchase.order", 
                    view_id,
                    po.id,
                    f"Purchase Order - {po.name}"
                    )

    def generate_vehicle_request(self, body_msg, body):
        self.state = 'Approve2'
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        # self.follower_messages(body)

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
        # self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        # self.follower_messages(body)

    def generate_move_entries(self):
        # self.follower_messages(body)
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
         positive product (storable product) , system should generate a stock picking to update the new product stock
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
            }) for mm in self.mapped('product_ids').filtered(lambda pr: pr.product_id and pr.product_id.detailed_type == "product" and pr.to_retire == True)]
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
                ('memo_type', '=', self.memo_type)
                ])
        memo_approver_ids = memo_settings.approver_ids
        for appr in memo_approver_ids:
            self.sudo().write({
                'users_followers': [(4, appr.id)] 
            })
      
    def view_related_record(self):
        if self.memo_type == "material_request":
            view_id = self.env.ref('stock.view_picking_form').id
            return self.record_to_open('stock.picking', view_id)
             
        elif self.memo_type == "procurement_request":
            view_id = self.env.ref('purchase.purchase_order_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type == "vehicle_request":
            # view_id = self.env.ref('stock.view_picking_form').id
            # self.record_to_open('purchase.order', view_id)
            pass 
        elif self.memo_type == "leave_request":
            view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type == "cash_advance":
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
        # self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)
    
     
    def generate_move_entriesxx(self):
        '''pr: product obj'''
        # journal_id = self.env['account.journal'].search([
        #     '|',('type', '=', 'cash'),
        #     ('type', '=', 'bank'),
        #     ], limit=1)
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'purchase'),
             ('code', '=', 'BILL')
             ], limit=1
        )
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
                'name': f"CASH ADV/ {self.code}",
                'move_type': 'in_receipt',
                'date': fields.Date.today(),
                'journal_id': journal_id.id,
                'invoice_line_ids': [(0, 0, {
                        'name': pr.product_id.name,
                        'ref': f'{self.code}: {pr.product_id.name}',
                        'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                        'price_unit': pr.amount_total,
                        'quantity': pr.quantity_available,
                        'discount': 0.0,
                        'product_uom_id': pr.product_id.uom_id.id,
                        'product_id': pr.product_id.id,
                }) for pr in self.product_ids],
            })
            # inv.post()
            # self.validate_invoice_and_post_journal(journal_id.id, inv)
        else:
            return inv
        return inv

    def validate_invoice_and_post_journal(
            self, journal_id, inv):
        """To be used only when they request for automatic payment generation"""
        account_payment_obj = self.env['account.payment'].sudo()
        outbound_payment_method = self.env['account.payment.method'].sudo().search(
            [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
        payment_method = 1
        if journal_id:
            payment_method = journal_id.outbound_payment_method_line_ids[0].id if journal_id.outbound_payment_method_line_ids else outbound_payment_method.id if outbound_payment_method else payment_method
        acc_values = {
            'invoice_ids': [(6, 0, [inv.id])],
            'amount': inv.amount_residual_signed,
            'ref': inv.name,
            'move_id': inv.id,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'journal_id': journal_id.id,
            # 'branch_id': 1, #sale_order.branch_id.id,
            'payment_method_id': payment_method,
            'partner_id': inv.partner_id.id,
        }
        payment = account_payment_obj.create(acc_values)
        payment.post()

    def Register_Payment(self):
        # dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')
        view_id = self.env.ref('account.view_account_payment_form')
        # if not self.vendor_id:
        #     raise ValidationError("Please select a Vendor")
        if (self.memo_type != "Payment") or (self.amountfig < 1):
            raise ValidationError("(1) Memo type must be 'Payment'\n (2) Amount must be greater than one to proceed with payment")
        #self.state = "Done"
        ret = {
                'name':'Register Memo Payment',
                'view_mode': 'form',
                'view_id': view_id.id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'domain': [],
                'context': {
                        'default_amount': self.amountfig,
                        'default_payment_type': 'outbound',
                        'default_partner_id':self.vendor_id.id or self.employee_id.user_id.partner_id.id, 
                        'default_memo_reference': self.id,
                        'default_communication': self.name,
                },
                'target': 'current'
                }
        return ret

    def generate_loan_entries(self):
        if self.loan_reference:
            raise ValidationError("You have generated a loan already for this record")
        # view_id = self.env['ir.model.data'].get_object_reference('account_loan', 'account_loan_form')
        view_id = self.env.ref('account_loan.account_loan_form')
        if (self.memo_type != "loan") or (self.loan_amount < 1):
            raise ValidationError("Check validation: \n (1) Memo type must be 'loan request'\n (2) Loan Amount must be greater than one to proceed with loan request")
        # try:
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
        # except Exception as e:
        #     _logger.info(f"Issue with Account loan ==> {e}") 

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
        # raise ValidationError([rec.name for rec in default_sender])
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
                order.status_progress = random.randint(99, 100) # 100 / len(order.state)

    def unlink(self):
        for delete in self.filtered(lambda delete: delete.state in ['Sent','Approve2', 'Approve']):
            raise ValidationError(_('You cannot delete a Memo which is in %s state.') % (delete.state,))
        return super(Memo_Model, self).unlink()

    
