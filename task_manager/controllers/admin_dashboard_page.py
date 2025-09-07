# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from werkzeug.exceptions import Forbidden
from math import ceil

# =========================
# Admin Dashboard (Website)
# =========================
# - Page:      GET  /tm/admin        -> renders QWeb page (website)
# - Endpoints: POST /tm/admin/api/*  -> JSON for charts/tiles (frontend only)
#
# Keep everything in this one controller file for neatness (no backend client action).

def _has_access(user):
    """Allow System Admins or TM Managers."""
    return user.has_group('base.group_system') or user.has_group('task_manager.group_tm_manager')

def _parse_filters(params):
    f = {
        'date_from': params.get('date_from') or None,
        'date_to': params.get('date_to') or None,
        'group_by': params.get('group_by') or '',    # optional
        'text_q': (params.get('text_q') or '').strip(),
    }
    return f


# def _any_of(clauses):
#     """Builds (A OR B OR C) in Odoo domain syntax."""
#     clauses = [c for c in clauses if c] or []
#     if not clauses:
#         return []
#     dom = clauses[0]
#     for c in clauses[1:]:
#         dom = ['|', dom, c]
#     return dom

# def _text_domain(text):
#     """
#     Free-text across multiple fields.
#     AND across words, OR across fields.
#     Produces a valid Odoo domain in prefix form.
#     """
#     text = (text or '').strip()
#     if not text:
#         return []

#     terms = [t for t in text.split() if t]
#     if not terms:
#         return []

#     fields = [
#         'name',
#         'key',
#         'assignee_staff_id',
#         'employee_id.name',
#         'manager_id.name',
#     ]

#     # OR-reduce: A OR B OR C  =>  ['|', ['|', A, B], C]
#     def _or_reduce(conds):
#         it = iter(conds)
#         expr = next(it)
#         for c in it:
#             expr = ['|', expr, c]
#         return expr

#     # AND-reduce: X AND Y AND Z  =>  ['&', ['&', X, Y], Z]
#     def _and_reduce(parts):
#         it = iter(parts)
#         expr = next(it)
#         for p in it:
#             expr = ['&', expr, p]
#         return expr

#     per_term_exprs = []
#     for term in terms:
#         field_conds = [(f, 'ilike', term) for f in fields]
#         per_term_exprs.append(_or_reduce(field_conds))

#     # AND across all term expressions (every word must match somewhere)
#     return _and_reduce(per_term_exprs)

def _any_of(clauses):
    """Return a flat OR chain in prefix form: ['|','|', A, B, C]."""
    clauses = [c for c in clauses if c]
    if not clauses:
        return []
    if len(clauses) == 1:
        return [clauses[0]]
    return (['|'] * (len(clauses) - 1)) + clauses

def _all_of(group_tokens):
    """AND a list of domain token lists: ['&','&', <g1...>, <g2...>, <g3...>]"""
    groups = [g if isinstance(g, list) else [g] for g in group_tokens if g]
    if not groups:
        return []
    if len(groups) == 1:
        return groups[0]
    flat = []
    for g in groups:
        flat.extend(g)
    return (['&'] * (len(groups) - 1)) + flat

def _text_domain(text):
    """
    Free-text across multiple fields, AND across words, OR across fields,
    using *flat* prefix tokens compatible with search().
    """
    text = (text or '').strip()
    if not text:
        return []

    terms = [t for t in text.split() if t]
    if not terms:
        return []

    fields = ['name', 'key', 'assignee_staff_id', 'employee_id.name', 'manager_id.name']

    per_term = []
    for term in terms:
        conds = [(f, 'ilike', term) for f in fields]   # A,B,C,D,E
        per_term.append(_any_of(conds))                # -> ['|','|','|','|', A,B,C,D,E]

    # AND all the per-term OR groups together
    return _all_of(per_term)



def _attach_text_query(dom, q):
    """Make q match task name/key/staff-id/employee/manager."""
    q = (q or '').strip()
    if not q:
        return dom
    return dom + _any_of([
        ('name', 'ilike', q),
        ('key', 'ilike', q),
        ('assignee_staff_id', 'ilike', q),
        ('employee_id.name', 'ilike', q),
        ('manager_id.name', 'ilike', q),
    ])

def _domain_from_filters(f):
    dom = [('active', '=', True)]

    df = f.get('date_from')
    dt = f.get('date_to')
    if df: dom.append(('due_date', '>=', df))
    if dt: dom.append(('due_date', '<=', dt))

    for key, field in (('stages','stage'), ('priorities','priority')):
        vals = f.get(key) or []
        if vals: dom.append((field, 'in', vals))

    if f.get('manager_id'):  dom.append(('manager_id', '=', f['manager_id']))
    if f.get('employee_id'): dom.append(('employee_id', '=', f['employee_id']))
    if f.get('company_id'):  dom.append(('company_id', '=', f['company_id']))

    q = (f.get('q') or '').strip()
    if q:
        dom = _attach_text_query(dom, q)
    return dom




def _count_from_row(r, *extra_keys):
    # Prefer id_count, then __count, then any extra alias we hint
    for k in ('id_count', '__count', *extra_keys):
        if k in r and r[k] is not None:
            return r[k] or 0
    return 0

class TMAdminDashboardPage(http.Controller):

    # ---------- Page ----------
    @http.route('/tm/admin', type='http', auth='user', website=True)
    def admin_dashboard_page(self, **kw):
        user = request.env.user
        if not _has_access(user):
            raise Forbidden("You don't have access to the Admin Dashboard.")
        return request.render('task_manager.tm_admin_dashboard_page', {})

    # ---------- JSON: KPIs ----------
    @http.route('/tm/admin/api/summary', type='json', auth='user', website=True, csrf=False)
    def api_summary(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task']   
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        # free-text domain
        text_q = f.get('text_q') or ''
        if text_q:
            dom += _text_domain(text_q)

        total = Task.search_count(dom)

        today = fields.Date.context_today(Task)
        due_today = Task.search_count(dom + [('due_date', '=', today)])
        overdue = Task.search_count(dom + [('due_date', '!=', False), ('stage', '!=', 'done'), ('due_date', '<', today)])
        blocked = Task.search_count(dom + [('is_blocked', '=', True)])

        # Done in period: prefer last_reviewed_on if date range present; else just count done with current domain
        done_dom = dom + [('stage', '=', 'done')]
        if f['date_from'] or f['date_to']:
            rng = []
            if f['date_from']:
                rng.append(('last_reviewed_on', '>=', f['date_from'] + ' 00:00:00'))
            if f['date_to']:
                rng.append(('last_reviewed_on', '<=', f['date_to'] + ' 23:59:59'))
            done_period = Task.search_count(done_dom + rng)
        else:
            done_period = Task.search_count(done_dom)

        return {'ok': True, 'data': {
            'total': total,
            'overdue': overdue,
            'due_today': due_today,
            'done_period': done_period,
            'blocked': blocked,
        }}

    # ---------- JSON: distributions (stage/priority/overdue by manager/done by employee) ----------
    @http.route('/tm/admin/api/distribution', type='json', auth='user', website=True, csrf=False)
    def api_distribution(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task'].sudo()   
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        # free-text domain
        text_q = f.get('text_q') or ''
        if text_q:
            dom += _text_domain(text_q)

        # label maps from selections
        stage_labels = dict(Task._fields['stage'].selection)
        prio_labels  = dict(Task._fields['priority'].selection)

        # ---- by stage (stable order)
        rows = Task.read_group(dom, ['id:count', 'stage'], ['stage'], lazy=False)
        # normalize counts by any alias Odoo may give
        counts_by_stage = {}
        for r in rows:
            k = r.get('stage') or 'unknown'
            counts_by_stage[k] = _count_from_row(r, 'stage_count')

        stage_order = ['todo', 'in_progress', 'review', 'done']
        by_stage = [{
            'key': k,
            'label': stage_labels.get(k, k or '—'),
            'count': counts_by_stage.get(k, 0),
        } for k in stage_order]

        # ---- by priority (stable order High→Low)
        rows = Task.read_group(dom, ['id:count', 'priority'], ['priority'], lazy=False)
        counts_by_prio = {}
        for r in rows:
            k = str(r.get('priority') or '0')
            counts_by_prio[k] = _count_from_row(r, 'priority_count')

        prio_order = ['2', '1', '0']  
        by_priority = [{
            'key': k,
            'label': prio_labels.get(k, k),
            'count': counts_by_prio.get(k, 0),
        } for k in prio_order]

        # ---- overdue by manager (not Done, due_date < today)
        today = fields.Date.context_today(Task)
        overdue_dom = dom + [
            ('stage', '!=', 'done'),
            ('due_date', '!=', False),
            ('due_date', '<', today),
        ]
        rows = Task.read_group(overdue_dom, ['id:count', 'manager_id'], ['manager_id'], lazy=False)
        overdue_by_manager = [{
            'id':   (r['manager_id'][0] if r.get('manager_id') else False),
            'name': (r['manager_id'][1] if r.get('manager_id') else '—'),
            'count': _count_from_row(r),
        } for r in rows]
        overdue_by_manager.sort(key=lambda x: x['count'], reverse=True)

        # ---- done by employee
        rows = Task.read_group(dom + [('stage', '=', 'done')], ['id:count', 'employee_id'], ['employee_id'], lazy=False)
        by_employee_done = [{
            'id':   (r['employee_id'][0] if r.get('employee_id') else False),
            'name': (r['employee_id'][1] if r.get('employee_id') else '—'),
            'count': _count_from_row(r),
        } for r in rows]
        by_employee_done.sort(key=lambda x: x['count'], reverse=True)

        return {'ok': True, 'data': {
            'by_stage': by_stage,
            'by_priority': by_priority,
            'overdue_by_manager': overdue_by_manager,
            'by_manager_overdue': overdue_by_manager,
            'by_employee_done': by_employee_done,
        }}

    # ---------- JSON: leaderboard (top employees done, top overdue employees, top managers done) ----------
    @http.route('/tm/admin/api/leaderboard', type='json', auth='user', website=True, csrf=False)
    def api_leaderboard(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task'].sudo()
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        # free-text domain
        text_q = f.get('text_q') or ''
        if text_q:
            dom += _text_domain(text_q)

        # Top Employees by Done
        emp_done_rg = Task.read_group(dom + [('stage', '=', 'done')], ['id:count'], ['employee_id'], lazy=False)
        employees_done = [{
            'id':   r['employee_id'] and r['employee_id'][0],
            'name': r['employee_id'] and r['employee_id'][1] or '—',
            'count': _count_from_row(r, 'employee_id_count'),
        } for r in emp_done_rg]
        employees_done.sort(key=lambda x: x['count'], reverse=True)
        employees_done = employees_done[:10]
        
        # Top Employees by Overdue (not Done, due_date < today)
        today = fields.Date.context_today(Task)
        overdue_dom = dom + [('due_date', '!=', False), ('stage', '!=', 'done'), ('due_date', '<', today)]
        emp_over_rg = Task.read_group(overdue_dom, ['id:count'], ['employee_id'], lazy=False)
        employees_overdue = [{
            'id':   r['employee_id'] and r['employee_id'][0],
            'name': r['employee_id'] and r['employee_id'][1] or '—',
            'count': _count_from_row(r, 'employee_id_count'),
        } for r in emp_over_rg]
        employees_overdue.sort(key=lambda x: x['count'], reverse=True)
        employees_overdue = employees_overdue[:10]

        # Top Managers by Done
        mgr_done_rg = Task.read_group(dom + [('stage', '=', 'done')], ['id:count'], ['manager_id'], lazy=False)
        managers_done = [{
            'id':   r['manager_id'] and r['manager_id'][0],
            'name': r['manager_id'] and r['manager_id'][1] or '—',
            'count': _count_from_row(r, 'manager_id_count'),
        } for r in mgr_done_rg]
        managers_done.sort(key=lambda x: x['count'], reverse=True)
        managers_done = managers_done[:10]


        return {'ok': True, 'data': {
            'employees_done': employees_done,
            'employees_overdue': employees_overdue,
            'managers_done': managers_done,
        }}

    # ---------- JSON: search (name or staff-id) ----------
    @http.route('/tm/admin/api/search', type='json', auth='user', website=True, csrf=False)
    def api_search(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        q = (params.get('q') or '').strip()
        if not q:
            return {'ok': True, 'matches': []}

        Emp = request.env['hr.employee'].sudo()
        dom = ['|', ('name', 'ilike', q), ('employee_number', 'ilike', q)]
        emps = Emp.search(dom, limit=20)

        matches = [{
            'employee_id': e.id,
            'name': e.name,
            'staff_id': e.employee_number or '',
            'manager_name': e.parent_id and e.parent_id.name or '',
        } for e in emps]
        return {'ok': True, 'matches': matches}
    

    # ---------- filters, group, sort, paging ----------
    @http.route('/tm/admin/api/tasks', type='json', auth='user', website=True, csrf=False)
    def api_tasks(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task']
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        # free-text domain
        text_q = f.get('text_q') or ''
        if text_q:
            dom += _text_domain(text_q)

        # quick backend-like filters
        quick = params.get('quick_filters') or []
        today = fields.Date.context_today(Task)
        if 'overdue' in quick:
            dom += [('due_date', '!=', False), ('stage', '!=', 'done'), ('due_date', '<', today)]
        if 'due_today' in quick:
            dom += [('due_date', '=', today)]
        if 'due_week' in quick:
            dom += [('days_left', '>=', 0), ('days_left', '<=', 6)]
        if 'mine' in quick:
            dom += [('employee_id.user_id', '=', user.id)]
        if 'imanage' in quick:
            dom += [('manager_id', '=', user.id)]


        # paging & sort
        page = max(int(params.get('page') or 1), 1)
        limit = max(min(int(params.get('limit') or 20), 200), 1)
        offset = (page - 1) * limit

        sort_by = params.get('sort_by') or 'priority desc, due_date asc, id desc'
        # allow a few safe fields
        allowed = {
            'key': 'key asc',
            'name': 'name asc',
            'employee_id': 'employee_id asc',
            'stage': 'stage asc',
            'priority': 'priority desc',
            'due_date': 'due_date asc',
            'manager_id': 'manager_id asc',
        }
        order = allowed.get(sort_by, sort_by)

        total = Task.search_count(dom)
        rows = Task.search(dom, order=order, offset=offset, limit=limit)

        def _row(t):
            prio_label = dict(t._fields['priority'].selection).get(t.priority, '')
            return {
                'id': t.id,
                'key': t.key,
                'name': t.name,
                'employee': t.employee_id and t.employee_id.name or '',
                'employee_id': t.employee_id.id or False,
                'stage': t.stage,
                'priority': t.priority,
                'priority_label': prio_label,
                'due_date': t.due_date and t.due_date.strftime('%Y-%m-%d') or '',
                'manager': t.manager_id and t.manager_id.name or '',
                'manager_id': t.manager_id.id or False,
            }

        # optional: group headers (client can insert where value changes)
        group_by = (params.get('group_by') or '').strip()  # e.g., 'stage', 'employee_id'
        group_value = None
        if group_by in {'stage', 'priority', 'employee_id', 'manager_id', 'company_id'}:
            # adjust sort to keep groups contiguous if not already sorted
            pass

        return {'ok': True, 'data': {
            'page': page,
            'pages': ceil(total / float(limit)) if total else 1,
            'limit': limit,
            'total': total,
            'rows': [_row(t) for t in rows],
        }}