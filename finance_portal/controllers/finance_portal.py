# -*- coding: utf-8 -*-
"""
finance_portal/controllers/finance_portal.py
============================================
Routes:
  GET  /finance-portal                        → serve finance_portal.html
  POST /finance-portal/dashboard              → KPI cards
  POST /finance-portal/payments               → list supplier / customer payments
  POST /finance-portal/payment/<int:id>       → single payment detail
  POST /finance-portal/payment/create         → create account.move (vendor bill / customer invoice)
  POST /finance-portal/payment/confirm/<int:id> → post/confirm a draft move
  POST /finance-portal/payment/cancel/<int:id>  → reset to draft / cancel
  POST /finance-portal/meta/journals          → journal list
  POST /finance-portal/meta/partners          → partner list
  POST /finance-portal/meta/accounts          → account.account list
  POST /finance-portal/meta/taxes             → account.tax list
  POST /finance-portal/meta/payment_terms     → account.payment.term list
  POST /finance-portal/meta/branches          → multi.branch list
  POST /finance-portal/meta/currencies        → res.currency list
"""

import json
import os
import logging
from datetime import date, datetime

from odoo import http
from odoo.http import request
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


def _fmt(val):
    try:
        return '{:,.2f}'.format(float(val or 0))
    except Exception:
        return '0.00'


def _ids(raw):
    try:
        return [int(x) for x in (raw or []) if x]
    except Exception:
        return []


def _parse_date(s, fallback=None):
    if not s:
        return fallback
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return fallback


# ─────────────────────────────────────────────────────────────────────────────

class FinancePortalController(http.Controller):

    # ── Serve HTML shell ─────────────────────────────────────────────
    @http.route('/finance-portal', type='http', auth='user', methods=['GET'])
    def index(self, **kw):
        fpath = get_resource_path('finance_portal', 'static/html', 'finance_portal.html')
        if not fpath or not os.path.exists(fpath):
            return request.make_response(
                '<h3>finance_portal.html not found</h3>',
                headers=[('Content-Type', 'text/html')]
            )
        with open(fpath, 'r', encoding='utf-8') as fh:
            html = fh.read()

        env  = request.env
        user = env.user

        # User branch (multi.branch guard)
        user_branch_id   = None
        user_branch_name = ''
        if hasattr(user, 'branch_id') and user.branch_id:
            user_branch_id   = user.branch_id.id
            user_branch_name = user.branch_id.name

        companies = env['res.company'].sudo().search([])
        branches  = []
        if 'multi.branch' in env:
            branches = [{'id': b.id, 'name': b.name, 'company_id': b.company_id.id}
                        for b in env['multi.branch'].sudo().search([])]

        meta = {
            'user_id':           user.id,
            'user_name':         user.name,
            'company_id':        user.company_id.id,
            'company_name':      user.company_id.name,
            'currency_id':       user.company_id.currency_id.id,
            'currency_symbol':   user.company_id.currency_id.symbol or '₦',
            'user_branch_id':    user_branch_id,
            'user_branch_name':  user_branch_name,
            'companies': [{'id': c.id, 'name': c.name} for c in companies],
            'branches':  branches,
            'today':     date.today().isoformat(),
        }

        tag = f'<meta name="fp-meta" content=\'{json.dumps(meta, ensure_ascii=False)}\'>\n'
        html = html.replace('</head>', tag + '</head>', 1)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ── Dashboard ─────────────────────────────────────────────────────
    @http.route('/finance-portal/dashboard', type='json', auth='user', methods=['POST'])
    def dashboard(self, **post):
        env         = request.env
        company_ids = _ids(post.get('company_ids'))
        date_from   = _parse_date(post.get('date_from'), date(date.today().year, 1, 1))
        date_to     = _parse_date(post.get('date_to'),   date.today())

        AM  = env['account.move'].sudo()
        AML = env['account.move.line'].sudo()

        def move_domain(move_types, states=None, extra=None):
            d = [('move_type', 'in', move_types),
                 ('date', '>=', date_from), ('date', '<=', date_to)]
            if states:
                d.append(('state', 'in', states))
            if company_ids:
                d.append(('company_id', 'in', company_ids))
            if extra:
                d += extra
            return d

        def agg(moves):
            total = sum(moves.mapped('amount_total'))
            return {'count': len(moves), 'total': round(total, 2), 'total_fmt': _fmt(total)}

        # Supplier (vendor bills) — in_invoice / in_receipt
        sup_posted  = AM.search(move_domain(['in_invoice','in_receipt'], ['posted']))
        sup_draft   = AM.search(move_domain(['in_invoice','in_receipt'], ['draft']))

        # Customer (invoices) — out_invoice / out_receipt
        cust_posted = AM.search(move_domain(['out_invoice','out_receipt'], ['posted']))
        cust_draft  = AM.search(move_domain(['out_invoice','out_receipt'], ['draft']))

        # Aged payable (posted, not fully paid)
        aged_payable_moves = AM.search(
            move_domain(['in_invoice','in_receipt'], ['posted'],
                        [('payment_state', 'not in', ['paid','in_payment'])]))
        aged_payable = sum(aged_payable_moves.mapped('amount_residual'))

        # Aged receivable
        aged_recv_moves = AM.search(
            move_domain(['out_invoice','out_receipt'], ['posted'],
                        [('payment_state', 'not in', ['paid','in_payment'])]))
        aged_recv = sum(aged_recv_moves.mapped('amount_residual'))

        # Credit notes
        credit_notes = AM.search(move_domain(['in_refund','out_refund'], ['posted']))
        # Debit notes
        debit_notes  = AM.search(move_domain(['in_invoice','out_invoice'], ['posted'],
                                              [('ref', 'like', 'DN')]))

        # Tax paid
        tax_line_domain = [
            ('move_id.state', '=', 'posted'),
            ('tax_line_id', '!=', False),
            ('date', '>=', date_from), ('date', '<=', date_to),
        ]
        if company_ids:
            tax_line_domain.append(('company_id', 'in', company_ids))
        tax_lines    = AML.search(tax_line_domain)
        total_tax    = abs(sum(tax_lines.mapped('balance')))

        # Monthly trend (last 6 months) for chart
        from dateutil.relativedelta import relativedelta
        from datetime import timedelta
        monthly = []
        for i in range(5, -1, -1):
            ms = (date_to.replace(day=1) - relativedelta(months=i))
            me = ms + relativedelta(months=1) - timedelta(days=1)
            bd = [('state', 'in', ['posted']), ('date', '>=', ms), ('date', '<=', me)]
            if company_ids:
                bd.append(('company_id', 'in', company_ids))
            sup_m  = sum(AM.search(bd + [('move_type', 'in', ['in_invoice','in_receipt'])]).mapped('amount_total'))
            cust_m = sum(AM.search(bd + [('move_type', 'in', ['out_invoice','out_receipt'])]).mapped('amount_total'))
            monthly.append({'month': ms.strftime('%b %Y'), 'supplier': round(sup_m,2), 'customer': round(cust_m,2)})

        return {
            'status': True,
            'supplier_posted':  agg(sup_posted),
            'supplier_draft':   agg(sup_draft),
            'customer_posted':  agg(cust_posted),
            'customer_draft':   agg(cust_draft),
            'aged_payable':     {'total': round(aged_payable,2), 'total_fmt': _fmt(aged_payable),
                                  'count': len(aged_payable_moves)},
            'aged_receivable':  {'total': round(aged_recv,2), 'total_fmt': _fmt(aged_recv),
                                  'count': len(aged_recv_moves)},
            'credit_notes':     agg(credit_notes),
            'debit_notes':      agg(debit_notes),
            'tax_paid':         {'total': round(total_tax,2), 'total_fmt': _fmt(total_tax)},
            'monthly':          monthly,
        }

    # ── List payments ──────────────────────────────────────────────────
    @http.route('/finance-portal/payments', type='json', auth='user', methods=['POST'])
    def list_payments(self, **post):
        env         = request.env
        ptype       = post.get('payment_type', 'supplier')   # 'supplier' | 'customer'
        state       = post.get('state', '')
        company_ids = _ids(post.get('company_ids'))
        date_from   = _parse_date(post.get('date_from'), date(date.today().year, 1, 1))
        date_to     = _parse_date(post.get('date_to'),   date.today())
        search_q    = (post.get('search') or '').strip()
        page        = int(post.get('page', 1))
        per_page    = int(post.get('per_page', 50))

        move_types = ['in_invoice','in_receipt'] if ptype == 'supplier' else ['out_invoice','out_receipt']
        domain = [
            ('move_type', 'in', move_types),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if state:
            domain.append(('state', '=', state))
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if search_q:
            domain.append('|')
            domain.append(('name', 'ilike', search_q))
            domain.append(('partner_id.name', 'ilike', search_q))

        AM    = env['account.move'].sudo()
        total = AM.search_count(domain)
        moves = AM.search(domain, order='date desc, id desc',
                           limit=per_page, offset=(page-1)*per_page)

        rows = []
        for m in moves:
            rows.append({
                'id':            m.id,
                'name':          m.name or '/',
                'date':          m.date.strftime('%Y-%m-%d') if m.date else '',
                'partner':       m.partner_id.name or '',
                'journal':       m.journal_id.name or '',
                'amount':        _fmt(m.amount_total),
                'amount_due':    _fmt(m.amount_residual),
                'currency':      m.currency_id.symbol or '',
                'state':         m.state,
                'payment_state': m.payment_state or '',
                'move_type':     m.move_type,
                'ref':           m.ref or '',
                'branch':        getattr(m, 'branch_id', False) and m.branch_id.name or '',
            })

        return {
            'status':   True,
            'rows':     rows,
            'total':    total,
            'page':     page,
            'per_page': per_page,
            'pages':    max(1, -(-total // per_page)),
        }

    # ── Single payment detail ──────────────────────────────────────────
    @http.route('/finance-portal/payment/<int:move_id>', type='json', auth='user', methods=['POST'])
    def payment_detail(self, move_id, **post):
        env  = request.env
        move = env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return {'status': False, 'message': 'Record not found'}

        lines = []
        for ln in move.invoice_line_ids:
            lines.append({
                'id':           ln.id,
                'account_id':   ln.account_id.id,
                'account_name': ln.account_id.name,
                'account_code': ln.account_id.code,
                'description':  ln.name or '',
                'quantity':     ln.quantity,
                'price_unit':   ln.price_unit,
                'price_subtotal': _fmt(ln.price_subtotal),
                'price_total':    _fmt(ln.price_total),
                'tax_ids':      [{'id': t.id, 'name': t.name} for t in ln.tax_ids],
                'currency':     ln.currency_id.symbol or '',
                'branch':       getattr(ln, 'branch_id', False) and ln.branch_id.name or '',
            })

        return {
            'status': True,
            'move': {
                'id':            move.id,
                'name':          move.name or '/',
                'date':          move.date.isoformat() if move.date else '',
                'invoice_date':  move.invoice_date.isoformat() if move.invoice_date else '',
                'invoice_date_due': move.invoice_date_due.isoformat() if move.invoice_date_due else '',
                'partner_id':    move.partner_id.id,
                'partner_name':  move.partner_id.name or '',
                'journal_id':    move.journal_id.id,
                'journal_name':  move.journal_id.name or '',
                'move_type':     move.move_type,
                'state':         move.state,
                'payment_state': move.payment_state or '',
                'amount_untaxed': _fmt(move.amount_untaxed),
                'amount_tax':    _fmt(move.amount_tax),
                'amount_total':  _fmt(move.amount_total),
                'amount_residual': _fmt(move.amount_residual),
                'currency':      move.currency_id.symbol or '',
                'ref':           move.ref or '',
                'narration':     move.narration or '',
                'payment_term':  move.invoice_payment_term_id.name or '',
                'company':       move.company_id.name or '',
                'branch':        getattr(move, 'branch_id', False) and move.branch_id.name or '',
            },
            'lines': lines,
        }

    # ── Create payment / invoice ───────────────────────────────────────
    @http.route('/finance-portal/payment/create', type='json', auth='user', methods=['POST'])
    def create_payment(self, **post):
        """
        Creates an account.move (vendor bill or customer invoice).
        Expected post keys:
          move_type         : in_invoice | in_receipt | out_invoice | out_receipt
          partner_id        : int
          journal_id        : int
          invoice_date      : YYYY-MM-DD
          invoice_date_due  : YYYY-MM-DD (optional)
          payment_term_id   : int (optional)
          ref               : str
          narration         : str
          currency_id       : int
          lines             : list of {account_id, description, quantity, price_unit, tax_ids, branch_id, currency_id}
        """
        env       = request.env
        move_type = post.get('move_type', 'in_invoice')

        if move_type not in ('in_invoice','in_receipt','out_invoice','out_receipt','in_refund','out_refund'):
            return {'status': False, 'message': 'Invalid move_type'}

        inv_date = _parse_date(post.get('invoice_date')) or date.today()
        inv_due  = _parse_date(post.get('invoice_date_due'))

        vals = {
            'move_type':    move_type,
            'invoice_date': inv_date,
            'ref':          post.get('ref') or '',
            'narration':    post.get('narration') or '',
        }

        partner_id = int(post.get('partner_id') or 0)
        if partner_id:
            vals['partner_id'] = partner_id

        journal_id = int(post.get('journal_id') or 0)
        if journal_id:
            vals['journal_id'] = journal_id

        payment_term_id = int(post.get('payment_term_id') or 0)
        if payment_term_id:
            vals['invoice_payment_term_id'] = payment_term_id

        if inv_due:
            vals['invoice_date_due'] = inv_due

        currency_id = int(post.get('currency_id') or 0)
        if currency_id:
            vals['currency_id'] = currency_id

        # Invoice lines
        line_cmds = []
        for ln in (post.get('lines') or []):
            account_id = int(ln.get('account_id') or 0)
            if not account_id:
                continue
            tax_ids = _ids(ln.get('tax_ids'))
            ln_vals = {
                'account_id':  account_id,
                'name':        ln.get('description') or '/',
                'quantity':    float(ln.get('quantity') or 1),
                'price_unit':  float(ln.get('price_unit') or 0),
                'tax_ids':     [(6, 0, tax_ids)],
            }
            branch_id = int(ln.get('branch_id') or 0)
            if branch_id and 'multi.branch' in env:
                ln_vals['branch_id'] = branch_id
            if ln.get('currency_id'):
                ln_vals['currency_id'] = int(ln['currency_id'])
            line_cmds.append((0, 0, ln_vals))

        if not line_cmds:
            return {'status': False, 'message': 'At least one invoice line is required'}

        vals['invoice_line_ids'] = line_cmds

        try:
            move = env['account.move'].sudo().create(vals)
            return {
                'status': True,
                'move_id': move.id,
                'name':    move.name or '/',
                'message': 'Payment created successfully',
            }
        except Exception as exc:
            _logger.exception('Error creating payment')
            return {'status': False, 'message': str(exc)}

    # ── Confirm (post) ────────────────────────────────────────────────
    @http.route('/finance-portal/payment/confirm/<int:move_id>', type='json', auth='user', methods=['POST'])
    def confirm_payment(self, move_id, **post):
        env  = request.env
        move = env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return {'status': False, 'message': 'Record not found'}
        try:
            move.action_post()
            return {'status': True, 'message': f'{move.name} confirmed/posted'}
        except Exception as exc:
            return {'status': False, 'message': str(exc)}

    # ── Cancel / reset to draft ───────────────────────────────────────
    @http.route('/finance-portal/payment/cancel/<int:move_id>', type='json', auth='user', methods=['POST'])
    def cancel_payment(self, move_id, **post):
        env  = request.env
        move = env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return {'status': False, 'message': 'Record not found'}
        try:
            if move.state == 'posted':
                move.button_draft()
            elif move.state == 'draft':
                move.button_cancel()
            return {'status': True, 'message': f'{move.name} reset to draft'}
        except Exception as exc:
            return {'status': False, 'message': str(exc)}

    # ── Meta: journals ────────────────────────────────────────────────
    @http.route('/finance-portal/meta/journals', type='json', auth='user', methods=['POST'])
    def meta_journals(self, **post):
        jtype       = post.get('type', '')   # 'purchase' | 'sale' | ''
        company_ids = _ids(post.get('company_ids'))
        domain = []
        if jtype:
            domain.append(('type', '=', jtype))
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        journals = request.env['account.journal'].sudo().search(domain)
        return {
            'status': True,
            'journals': [{'id': j.id, 'name': j.name, 'type': j.type,
                           'currency': j.currency_id.symbol or ''} for j in journals],
        }

    # ── Meta: partners ────────────────────────────────────────────────
    @http.route('/finance-portal/meta/partners', type='json', auth='user', methods=['POST'])
    def meta_partners(self, **post):
        q       = (post.get('q') or '').strip()
        ptype   = post.get('type', '')   # 'supplier' | 'customer' | ''
        domain  = [('active', '=', True)]
        if ptype == 'supplier':
            domain.append(('supplier_rank', '>', 0))
        elif ptype == 'customer':
            domain.append(('customer_rank', '>', 0))
        if q:
            domain.append(('name', 'ilike', q))
        partners = request.env['res.partner'].sudo().search(domain, limit=80)
        return {
            'status': True,
            'partners': [{'id': p.id, 'name': p.name, 'email': p.email or '',
                           'phone': p.phone or ''} for p in partners],
        }

    # ── Meta: accounts ────────────────────────────────────────────────
    @http.route('/finance-portal/meta/accounts', type='json', auth='user', methods=['POST'])
    def meta_accounts(self, **post):
        q           = (post.get('q') or '').strip()
        company_ids = _ids(post.get('company_ids'))
        domain = []
        if q:
            domain += ['|', ('code', 'ilike', q), ('name', 'ilike', q)]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        accounts = request.env['account.account'].sudo().search(domain, limit=200)
        return {
            'status': True,
            'accounts': [{'id': a.id, 'name': f'{a.code} – {a.name}',
                           'code': a.code, 'type': a.account_type} for a in accounts],
        }

    # ── Meta: taxes ───────────────────────────────────────────────────
    @http.route('/finance-portal/meta/taxes', type='json', auth='user', methods=['POST'])
    def meta_taxes(self, **post):
        company_ids = _ids(post.get('company_ids'))
        domain = [('active', '=', True)]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        taxes = request.env['account.tax'].sudo().search(domain)
        return {
            'status': True,
            'taxes': [{'id': t.id, 'name': t.name, 'amount': t.amount,
                        'type': t.amount_type} for t in taxes],
        }

    # ── Meta: payment terms ───────────────────────────────────────────
    @http.route('/finance-portal/meta/payment_terms', type='json', auth='user', methods=['POST'])
    def meta_payment_terms(self, **post):
        terms = request.env['account.payment.term'].sudo().search([('active', '=', True)])
        return {
            'status': True,
            'terms': [{'id': t.id, 'name': t.name} for t in terms],
        }

    # ── Meta: branches ────────────────────────────────────────────────
    @http.route('/finance-portal/meta/branches', type='json', auth='user', methods=['POST'])
    def meta_branches(self, **post):
        company_ids = _ids(post.get('company_ids'))
        if 'multi.branch' not in request.env:
            return {'status': True, 'branches': []}
        domain = [('company_id', 'in', company_ids)] if company_ids else []
        branches = request.env['multi.branch'].sudo().search(domain)
        return {
            'status': True,
            'branches': [{'id': b.id, 'name': b.name} for b in branches],
        }

    # ── Meta: currencies ──────────────────────────────────────────────
    @http.route('/finance-portal/meta/currencies', type='json', auth='user', methods=['POST'])
    def meta_currencies(self, **post):
        currencies = request.env['res.currency'].sudo().search([('active', '=', True)])
        return {
            'status': True,
            'currencies': [{'id': c.id, 'name': c.name, 'symbol': c.symbol} for c in currencies],
        }
