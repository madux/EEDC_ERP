# -*- coding: utf-8 -*-
from odoo import fields, models, tools

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    active = fields.Boolean(default=True)

class AccountMoveCallover(models.Model):
    _inherit = "account.move"

    active = fields.Boolean(default=True)
    

class AccountCallover(models.Model):
    """Read-only SQL view that pivots account.move.line debit amounts
    (only lines that carry a memo_id) into monthly columns per
    account_id / branch_id / fiscal year.

    Being a SQL VIEW (_auto = False), it is recomputed live by
    PostgreSQL every time it is queried - opening the menu / clicking
    the action always shows fresh, dynamically-computed figures.
    """
    _name = 'account.callover'
    _description = 'Account Callover (Monthly Debit Summary)'
    _auto = False
    # _order = 'account_id, fiscalyear'
    _order = 'create_date desc'

    def view_move_action(self):
        if self.record_id:
            view_id = self.env.ref('account.view_move_form')
            val = {
                'name':'Transaction',
                'view_mode': 'form',
                'view_id': view_id.id,
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'res_id': self.record_id,
                'target': 'current'
                }
            return val
        else:
            pass 

    record_id = fields.Integer(string='Rid', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    branch_id = fields.Many2one('multi.branch', string='Branch', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    fiscalyear = fields.Char(string='Fiscal Year', readonly=True)

    jan = fields.Monetary(string='Jan', readonly=True, default=0.0, currency_field='currency_id')
    feb = fields.Monetary(string='Feb', readonly=True, default=0.0, currency_field='currency_id')
    mar = fields.Monetary(string='Mar', readonly=True, default=0.0, currency_field='currency_id')
    apr = fields.Monetary(string='Apr', readonly=True, default=0.0, currency_field='currency_id')
    may = fields.Monetary(string='May', readonly=True, default=0.0, currency_field='currency_id')
    jun = fields.Monetary(string='Jun', readonly=True, default=0.0, currency_field='currency_id')
    july = fields.Monetary(string='Jul', readonly=True, default=0.0, currency_field='currency_id')
    aug = fields.Monetary(string='Aug', readonly=True, default=0.0, currency_field='currency_id')
    sep = fields.Monetary(string='Sep', readonly=True, default=0.0, currency_field='currency_id')
    oct = fields.Monetary(string='Oct', readonly=True, default=0.0, currency_field='currency_id')
    nov = fields.Monetary(string='Nov', readonly=True, default=0.0, currency_field='currency_id')
    dec = fields.Monetary(string='Dec', readonly=True, default=0.0, currency_field='currency_id')
    total = fields.Monetary(string='Total', readonly=True, default=0.0, currency_field='currency_id')
    budget_balance = fields.Monetary(string='Budget Balance', readonly=True, default=0.0, currency_field='currency_id')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        sys_admin = self.env.user.has_group("base.group_system")

        if not sys_admin:
            branch_ids = tuple(self.env.user.branch_ids.ids) or (0,)
            show_all = f"AND am.branch_id IN {branch_ids}"
        else:
            show_all = ''

        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW account_callover AS (
                SELECT
                    row_number() OVER (
                        ORDER BY MIN(am.id), aml.account_id, am.branch_id, EXTRACT(YEAR FROM aml.date)
                    )                                                             AS id,
                    MIN(aml.id)                                                   AS record_id,
                    aml.account_id                                                AS account_id,
                    am.branch_id                                                  AS branch_id,
                    aml.company_id                                                AS company_id,
                    rc.currency_id                                                AS currency_id,
                    EXTRACT(YEAR FROM aml.date)::varchar                          AS fiscalyear,
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 1  THEN aml.price_total ELSE 0 END) AS "jan",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 2  THEN aml.price_total ELSE 0 END) AS "feb",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 3  THEN aml.price_total ELSE 0 END) AS "mar",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 4  THEN aml.price_total ELSE 0 END) AS "apr",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 5  THEN aml.price_total ELSE 0 END) AS "may",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 6  THEN aml.price_total ELSE 0 END) AS "jun",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 7  THEN aml.price_total ELSE 0 END) AS "july",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 8  THEN aml.price_total ELSE 0 END) AS "aug",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 9  THEN aml.price_total ELSE 0 END) AS "sep",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 10 THEN aml.price_total ELSE 0 END) AS "oct",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 11 THEN aml.price_total ELSE 0 END) AS "nov",
                    SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 12 THEN aml.price_total ELSE 0 END) AS "dec",
                    SUM(aml.price_total)                                                             AS "total"
                FROM account_move_line aml
                    JOIN account_move am     ON am.id = aml.move_id
                    LEFT JOIN res_company rc ON rc.id = aml.company_id
                WHERE aml.parent_state = 'posted' {show_all} 
                GROUP BY
                    aml.account_id,
                    am.branch_id,
                    aml.company_id,
                    rc.currency_id,
                    EXTRACT(YEAR FROM aml.date)
            )
        """)

        # WHERE
        #                     am.state = 'posted'
        #                     AND am.active IS TRUE
        #                     AND aml.active IS TRUE
        #                     AND aml.parent_state = 'posted'
        #                     {show_all}
#         self.env.cr.execute(f"""
#     CREATE OR REPLACE VIEW account_callover AS (
#         SELECT
#             row_number() OVER (
#                 ORDER BY MIN(am.id), aml.account_id, am.branch_id, EXTRACT(YEAR FROM aml.date)
#             )                                                             AS id,
#             MIN(aml.id)                                                   AS record_id,
#             aml.account_id                                                AS account_id,
#             am.branch_id                                                  AS branch_id,
#             aml.company_id                                                AS company_id,
#             rc.currency_id                                                AS currency_id,
#             EXTRACT(YEAR FROM aml.date)::varchar                          AS fiscalyear,
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 1  THEN aml.price_total ELSE 0 END) AS "jan",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 2  THEN aml.price_total ELSE 0 END) AS "feb",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 3  THEN aml.price_total ELSE 0 END) AS "mar",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 4  THEN aml.price_total ELSE 0 END) AS "apr",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 5  THEN aml.price_total ELSE 0 END) AS "may",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 6  THEN aml.price_total ELSE 0 END) AS "jun",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 7  THEN aml.price_total ELSE 0 END) AS "july",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 8  THEN aml.price_total ELSE 0 END) AS "aug",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 9  THEN aml.price_total ELSE 0 END) AS "sep",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 10 THEN aml.price_total ELSE 0 END) AS "oct",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 11 THEN aml.price_total ELSE 0 END) AS "nov",
#             SUM(CASE WHEN EXTRACT(MONTH FROM aml.date) = 12 THEN aml.price_total ELSE 0 END) AS "dec",
#             SUM(aml.price_total)                                                             AS "total",
#             SUM(COALESCE(nbl.budget_balance, 0))                                        AS "budget_balance"
#         FROM account_move_line aml
#         JOIN account_move am                    ON am.id = aml.move_id
#         LEFT JOIN res_company rc                ON rc.id = aml.company_id
#         LEFT JOIN ng_account_budget_line nbl    ON nbl.id = aml.ng_budget_line_id
#           AND aml.parent_state = 'posted' {show_all}
#         WHERE
#             am.state = 'posted'
#             AND am.active IS TRUE
#             AND aml.active IS TRUE
#             AND am.memo_id IS NOT NULL
#         GROUP BY
#             aml.account_id,
#             am.branch_id,
#             aml.company_id,
#             rc.currency_id,
#             EXTRACT(YEAR FROM aml.date)
#     )
# """)
    