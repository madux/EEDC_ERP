from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class Document(models.Model):
    _inherit = 'documents.document'

    memo_category_id = fields.Many2one('memo.category', string="Category") 
    memo_id = fields.Many2one('memo.model', string="Memo") 
    submitted_date = fields.Date(
        string="submitted date")


class DocumentFolder(models.Model):
    _inherit = 'documents.folder'
    _description = 'Documents Workspace'
    _parent_name = 'parent_folder_id'
    _parent_store = True
    _order = 'sequence'

    department_ids = fields.Many2many(
        'hr.department', 
        string="Category")

    next_reoccurance_date = fields.Date(
        string="Next reoccurance date", compute="get_reoccurance_date")

    interval_period = fields.Integer(
        string="interval period", default=1)

    submission_maximum_range = fields.Integer(
        string="Maximum submission range", default=2)
    submission_minimum_range = fields.Integer(
        string="Minimum submission range", default=2)
    number_failed_submission = fields.Integer(
        string="Failed submission", 
        help='''update incrementally if the interval btw the current date and next 
        submission date exceeds the maximum date of submission''')
    number_successful_submission = fields.Integer(
        string="Successful submission", 
        compute="count_submitted_documents",
        help="Helps determine the number of submitted files")
    document_ids = fields.Many2many(
        'documents.document',
        string="Submitted documents")

    period_type = fields.Selection([
        ('months', 'Months'),
        ('days', 'Days'),
        ('years', 'Years'),
        # ('minutes', 'Minutes'),
        # ('hours', 'Hours'),
        ],
        string="Period type", default="months")

    success_rate = fields.Selection([
        ('100', '100 %'),
        ('70', '70 %'),
        ('40', '40 %'),
        ('10', '10 %'),
        ('0', '0 %'),
        ],
        string="Success rating")

    average_submission_rate = fields.Float(
        string="Average submission rate")

    number_of_awaiting = fields.Integer(
        string="Awaiting Submission",
          help='Identifies awaiting submission',
          compute="get_awaiting_submission")
    color = fields.Integer("Color Index", default=0)
    opened_documents = fields.Integer("Opened", default=0, compute="get_unapproved_submission")
    closed_documents = fields.Integer("Completed", default=0, compute="get_completed_submission") 

    def get_awaiting_submission(self):
        for t in self:
            memo = self.env['memo.model'].search([('document_folder', '=', t.id), ('state', '=', 'submit')])
            if t.name:
                t.number_of_awaiting = len([rec.id for rec in memo]) if memo else 0
            else:
                t.number_of_awaiting = False

    def get_unapproved_submission(self):
        for t in self:
            if t.name:
                memo = self.env['memo.model'].search([('document_folder', '=', t.id), ('state', '=', 'Sent')])
                t.opened_documents = len([rec.id for rec in memo]) if memo else 0
            else:
                t.opened_documents = False

    def get_completed_submission(self):
        for rec in self:
            if rec.name:
                memo = self.env['memo.model'].search([('document_folder', '=', rec.id), ('state', '=', 'Done')])
                rec.closed_documents = len([recw.id for recw in memo]) if memo else 0
            else:
                rec.closed_documents = False

    def update_next_occurrence_date(self):
        if self.period_type and self.interval_period:
            interval = self.interval_period
            recurrance_date = self.next_reoccurance_date if self.next_reoccurance_date else fields.Date.today()
            if self.period_type == 'months':
                self.next_reoccurance_date = recurrance_date + relativedelta(months=interval)
            elif self.period_type == 'years':
                self.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
            elif self.period_type == 'days':
                self.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
            # elif self.period_type == 'minutes':
            #     rec.next_reoccurance_date = recurrance_date + relativedelta(minutes=interval)
            # elif rec.period_type == 'hours':
            #     rec.next_reoccurance_date = recurrance_date + relativedelta(hours=interval)
        else:
            self.next_reoccurance_date = False

    @api.onchange('interval_period', 'period_type')
    def get_reoccurance_date(self):
        # TODO to be consider
        for rec in self:
            interval = rec.interval_period or 0
            if rec.period_type:
                recurrance_date = rec.next_reoccurance_date if rec.next_reoccurance_date else fields.Date.today()
                if rec.period_type == 'months':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(months=interval)
                elif rec.period_type == 'years':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
                elif rec.period_type == 'days':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
                # elif rec.period_type == 'minutes':
                #     rec.next_reoccurance_date = recurrance_date + relativedelta(minutes=interval)
                # elif rec.period_type == 'hours':
                #     rec.next_reoccurance_date = recurrance_date + relativedelta(hours=interval)
            else:
                rec.next_reoccurance_date = False

    @api.depends('document_ids')
    def count_submitted_documents(self):
        for rec in self:
            if rec.document_ids:
                rec.number_successful_submission = len(rec.document_ids.ids)
            else:
                rec.number_successful_submission = False

    def _cron_check_expiry(self):
        self.check_due_submission()

    def check_success_submission(self):
        pass 

    def check_due_submission(self):
        for rec in self:
            if rec.next_reoccurance_date and (rec.submission_maximum_range > 0):
                if (fields.Date.today() - rec.next_reoccurance_date).days > rec.submission_maximum_range:
                    document_within_range = rec.mapped('document_ids').filtered(
                        lambda s: s.submitted_date >= rec.next_reoccurance_date and s.submitted_date <= fields.Date.today() if s.submitted_date else False
                    )
                    if not document_within_range:
                        rec.number_failed_submission += 1

    def action_view_documents(self):
        view_id = self.env.ref('documents.document_view_kanban').id
        submitted_documents = self.document_ids
        ret = {
                'name': "Documents",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'documents.document', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', submitted_documents.ids)],
                'target': 'current'
                }
        return ret  

    def action_view_success_rate(self):
        pass

    def action_view_avg(self):
        pass

    def action_view_number_of_awaiting(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'submit')])
        ret = {
                'name': "Document requests",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret  

    def action_view_open_documents(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'Sent')])  
        ret = {
                'name': "Document requests",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret  

    def action_view_closed_documents(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'Done')])
        ret = {
                'name': "Documents",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret

