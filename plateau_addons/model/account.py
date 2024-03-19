from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class accountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    code = fields.Char(string='Code')
    

class accountJournal(models.Model):
    _inherit = "account.journal"

    code = fields.Char(
        string='Short Code',
        size=20, 
        required=True, 
        help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
    
class AccountInvoice(models.Model):
    _inherit = 'account.move'
     
    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            # journal = self.env['account.journal'].search([('allowed_branch_ids', 'in', )])
            branch_ids = [rec.id for rec in self.env.user.branch_ids if rec] + [self.env.user.branch_id.id]
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
                    #   , ('branch_id', 'in', branch_ids)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)