from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class accountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    code = fields.Char(string='Code')
    

class accountJournal(models.Model):
    _inherit = "account.journal"
    
    for_public_use = fields.Boolean(string="For Public user")
    code = fields.Char(
        string='Short Code',
        size=20, 
        required=True, 
        help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
     
    def _get_internal_users_ids(self):
        Group = self.env['res.groups']
        group_roles = self.env.ref('ik_multi_branch.account_major_user').id
        users = Group.browse([group_roles]).users
        return users and users.ids or []
    
    def get_filtered_journal_record(self):
        view_id_form = self.env.ref('account.view_account_journal_form')
        view_id_tree = self.env.ref('account.view_account_journal_tree')
        view_id_kanban = self.env.ref('account.account_journal_dashboard_kanban_view')
        user = self.env.user
        allowed_internal_users = self._get_internal_users_ids()
        record_ids = []
        if user.id in allowed_internal_users: 
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journals'),
                'res_model': 'account.journal',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': view_id_kanban.id,
                'views': [(view_id_kanban.id, 'kanban'), (view_id_tree.id, 'tree'), (view_id_form.id,'form')],
                'target': 'current',
                'domain': []
            }
        else:
            
            domain = [
                ('for_public_use', '=', False), 
                # ('branch_id', '=', user.branch_id.id),
                ('branch_id', 'in', user.branch_id.ids),
                # ('create_uid','=', user.id),
            ]
            non_user_journals = self.env['account.journal'].sudo().search(domain)
            record_ids = [res.id for res in non_user_journals]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journals'),
                'res_model': 'account.journal',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': view_id_kanban.id,
                'views': [(view_id_kanban.id, 'kanban'), (view_id_tree.id, 'tree'), (view_id_form.id,'form')],
                'target': 'current',
                'domain': [('id', 'in', record_ids)]
            } 
        
        
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