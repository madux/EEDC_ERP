# -*- coding: utf-8 -*-
from odoo import models, api

class AccountGeneralLedgerReportHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        
        if getattr(report, 'filter_multi_branch', False):
            branches = self.env['multi.branch'].search([])
            previous_branches = (previous_options or {}).get('multi_branch', [])
            selected_ids = [b['id'] for b in previous_branches if b.get('selected')]
            
            options['multi_branch'] = [{
                'id': b.id,
                'name': b.name,
                'selected': b.id in selected_ids if selected_ids else False,
                'model': 'multi.branch',
            } for b in branches]
            options['selected_branch_names'] = [b['name'] for b in options['multi_branch'] if b.get('selected')]
        
        if getattr(report, 'filter_account_type', False):
            types = self.env['account.account.type'].search([])
            previous_types = (previous_options or {}).get('account_type', [])
            selected_ids = [t['id'] for t in previous_types if t.get('selected')]
            
            options['account_type'] = [{
                'id': t.id,
                'name': t.name,
                'selected': t.id in selected_ids if selected_ids else False,
                'model': 'account.account.type',
            } for t in types]
            options['selected_account_type_names'] = [t['name'] for t in options['account_type'] if t.get('selected')]
            
            if not selected_ids:
                options['account_display_name'] = 'All'
            elif len(selected_ids) == 1:
                options['account_display_name'] = [t['name'] for t in options['account_type'] if t.get('selected')][0]
            else:
                options['account_display_name'] = f"{len(selected_ids)} selected"

    @api.model
    def _get_options_domain(self, options, date_scope):
        domain = super()._get_options_domain(options, date_scope)
        
        if options.get('multi_branch'):
            selected = [b['id'] for b in options['multi_branch'] if b.get('selected')]
            if selected:
                domain.append(('branch_id', 'in', selected))
        
        if options.get('account_type'):
            selected = [t['id'] for t in options['account_type'] if t.get('selected')]
            if selected:
                domain.append(('account_id.user_type_id', 'in', selected))
        
        return domain
