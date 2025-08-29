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
    """Normalize all incoming filter params from the website widget."""
    return {
        'date_from': (params.get('date_from') or None),
        'date_to': (params.get('date_to') or None),
        'date_grain': (params.get('date_grain') or 'week'),
        'stages': params.get('stages') or [],
        'priorities': params.get('priorities') or [],
        'manager_id': int(params['manager_id']) if params.get('manager_id') else None,
        'employee_id': int(params['employee_id']) if params.get('employee_id') else None,
        'company_id': int(params['company_id']) if params.get('company_id') else None,
        'q': (params.get('q') or '').strip(),
    }

def _domain_from_filters(f):
    """Translate filters into an Odoo domain (v1 uses due_date as the date axis)."""
    dom = [('active', '=', True)]
    # date window (v1) -> due_date
    if f['date_from']:
        dom.append(('due_date', '>=', f['date_from']))
    if f['date_to']:
        dom.append(('due_date', '<=', f['date_to']))
    # stage/priority
    if f['stages']:
        dom.append(('stage', 'in', f['stages']))
    if f['priorities']:
        dom.append(('priority', 'in', f['priorities']))
    # ownership/company
    if f['manager_id']:
        dom.append(('manager_id', '=', f['manager_id']))
    if f['employee_id']:
        dom.append(('employee_id', '=', f['employee_id']))
    if f['company_id']:
        dom.append(('company_id', '=', f['company_id']))
    # search: name or staff-id
    if f['q']:
        dom = ['|', ('assignee_staff_id', 'ilike', f['q']), ('name', 'ilike', f['q'])] + dom
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
            # Logged-in but not allowed
            raise Forbidden("You don't have access to the Admin Dashboard.")
        # Render website QWeb template (make sure you created views/website_admin_dashboard.xml with this template id)
        return request.render('task_manager.tm_admin_dashboard_page', {})

    # ---------- JSON: KPIs ----------
    @http.route('/tm/admin/api/summary', type='json', auth='user', website=True, csrf=False)
    def api_summary(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task']   # no sudo → record rules apply
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

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

        Task = request.env['tm.task'].sudo()   # <- use sudo for unbiased metrics (optional)
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

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

        prio_order = ['2', '1', '0']  # 2=High, 1=Medium, 0=Low
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
            # keep both keys to be compatible with any frontend you already wrote
            'overdue_by_manager': overdue_by_manager,
            'by_manager_overdue': overdue_by_manager,
            'by_employee_done': by_employee_done,
        }}

    # ---------- JSON: time series ----------
    @http.route('/tm/admin/api/timeseries', type='json', auth='user', website=True, csrf=False)
    def api_timeseries(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task']
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        grain = (f.get('date_grain') or 'week').lower()
        gb_map = {'week': 'due_date:week', 'month': 'due_date:month'}
        gb = gb_map.get(grain, 'due_date:week')

        rows = Task.read_group(
            dom,
            ['id:count', 'stage'],
            [gb, 'stage'],
            lazy=False,
        )

        # Accumulate into period buckets
        buckets = {}  # period -> dict
        for r in rows:
            period = r.get(gb)
            if not period:
                continue
            stage = r.get('stage') or 'unknown'
            cnt = r.get('id_count', 0) or 0
            d = buckets.setdefault(period, {
                'period': period, 'total': 0,
                'todo': 0, 'in_progress': 0, 'review': 0, 'done': 0,
            })
            d['total'] += cnt
            if stage in d:
                d[stage] += cnt  # ignore 'unknown' stages

        points = sorted(buckets.values(), key=lambda x: x['period'])
        return {'ok': True, 'data': {'grain': grain, 'points': points}}

    # ---------- JSON: leaderboards ----------
    @http.route('/tm/admin/api/leaderboard', type='json', auth='user', website=True, csrf=False)
    def api_leaderboard(self, **params):
        user = request.env.user
        if not _has_access(user):
            return {'ok': False, 'message': 'Forbidden'}

        Task = request.env['tm.task']
        f = _parse_filters(params)
        dom = _domain_from_filters(f)

        # Top employees by Done
        emp_rows = Task.read_group(
            dom + [('stage', '=', 'done')],
            ['id:count', 'employee_id'],
            ['employee_id'],
            lazy=False,
        )
        # Sort in Python instead of orderby='id_count desc'
        emp_rows = sorted(emp_rows, key=lambda r: r.get('id_count', 0) or 0, reverse=True)[:10]
        employees_done = [{
            'id': (r['employee_id'][0] if r.get('employee_id') else False),
            'name': (r['employee_id'][1] if r.get('employee_id') else '—'),
            'count': r.get('id_count', 0) or 0,
        } for r in emp_rows]

        # Top employees by Overdue (not Done, due_date < today)
        today = fields.Date.context_today(Task)
        odom = dom + [('stage', '!=', 'done'), ('due_date', '!=', False), ('due_date', '<', today)]
        emp_over_rows = Task.read_group(
            odom,
            ['id:count', 'employee_id'],
            ['employee_id'],
            lazy=False,
        )
        emp_over_rows = sorted(emp_over_rows, key=lambda r: r.get('id_count', 0) or 0, reverse=True)[:10]
        employees_overdue = [{
            'id': (r['employee_id'][0] if r.get('employee_id') else False),
            'name': (r['employee_id'][1] if r.get('employee_id') else '—'),
            'count': r.get('id_count', 0) or 0,
        } for r in emp_over_rows]

        # Overdue by manager
        mgr_rows = Task.read_group(
            odom + [('manager_id', '!=', False)],
            ['id:count', 'manager_id'],
            ['manager_id'],
            lazy=False,
        )
        mgr_rows = sorted(mgr_rows, key=lambda r: r.get('id_count', 0) or 0, reverse=True)[:10]
        overdue_by_manager = [{
            'id': (r['manager_id'][0] if r.get('manager_id') else False),
            'name': (r['manager_id'][1] if r.get('manager_id') else '—'),
            'count': r.get('id_count', 0) or 0,
        } for r in mgr_rows]

        return {'ok': True, 'data': {
            'employees_done': employees_done,
            'employees_overdue': employees_overdue,
            'overdue_by_manager': overdue_by_manager,
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

        # free-text for list
        text_q = (params.get('text_q') or '').strip()
        if text_q:
            dom = ['|', ('assignee_staff_id', 'ilike', text_q), ('name', 'ilike', text_q)] + dom

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