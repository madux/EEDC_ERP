# -*- coding: utf-8 -*-
import base64
import datetime
from odoo import http, _, fields
from odoo.http import request

def _att_to_dict(att):
    return {
        'id': att.id,
        'name': att.name,
        'mimetype': att.mimetype or '',
    }
class TaskboardController(http.Controller):
    """
    Portal-authenticated taskboard endpoints.
    - Page + JSON routes require a logged-in website user (portal or internal).
    - Tasks are scoped to the current user's employee.
      Primary filter: task.employee_id == user.employee_id
      Fallback: task.assignee_staff_id == employee.employee_number (if provided)
    - Managers (group task_manager.group_tm_manager) can move to any stage, others cannot move to 'done'.
    """

    # -------- Page --------
    @http.route("/taskboard", type="http", auth="user", website=True)
    def taskboard_page(self, **kw):
        # Not logged-in? Odoo redirects to /web/login automatically.
        user = request.env.user
        return request.render(
            "task_manager.tm_taskboard_page",
            {"employee": user.employee_id, "user_name": user.name},
        )

    # -------- API: board --------
    @http.route("/tm/api/board", type="json", auth="user", website=True, csrf=False)
    def api_board(self):
        user = request.env.user
        emp = user.employee_id

        Task = request.env["tm.task"]  # no sudo → record rules/ACLs apply

        domain = [("active", "=", True)]
        if emp:
            # Prefer employee_id match, but also support legacy assignee_staff_id mapping
            staff_code = (emp.employee_number or emp.barcode or "").strip()
            # (active=True) AND (employee_id = emp OR assignee_staff_id = staff_code)
            domain += ["|", ("employee_id", "=", emp.id), ("assignee_staff_id", "=", staff_code)]
        else:
            # No linked employee → show nothing
            domain += [("id", "=", 0)]

        tasks = Task.search(domain, order="priority desc, due_date asc, id desc")

        def _card(t):
            desc = (t.description or "").strip()
            if desc and len(desc) > 300:
                desc = desc[:297] + "..."
            return {
                "id": t.id,
                "name": t.name,
                "description": desc,
                "priority": t.priority,
                "due_date": t.due_date and t.due_date.strftime("%Y-%m-%d") or None,
                "tags": [tag.name for tag in t.tag_ids],
                "stage": t.stage,
            }

        stages = ["todo", "in_progress", "review", "done"]
        grouped = {k: [] for k in stages}
        for t in tasks:
            grouped.setdefault(t.stage, []).append(_card(t))
        counts = {k: len(v) for k, v in grouped.items()}

        return {"ok": True, "data": grouped, "counts": counts, "staff_name": user.name}

    # -------- API: move --------
    @http.route("/tm/api/move", type="json", auth="user", website=True, csrf=False)
    def api_move(self, task_id=None, new_stage=None):
        user = request.env.user
        emp = user.employee_id
        if not task_id or not new_stage:
            return {"ok": False, "message": "Missing data"}

        Task = request.env["tm.task"]  # no sudo
        task = Task.browse(int(task_id))
        if not task.exists():
            return {"ok": False, "message": "Task not found"}

        # Ownership or manager?
        is_manager = user.has_group("task_manager.group_tm_manager")
        owned = False
        if emp:
            staff_code = (emp.employee_number or emp.barcode or "").strip()
            owned = (task.employee_id.id == emp.id) or (task.assignee_staff_id == staff_code)

        if not (is_manager or owned):
            return {"ok": False, "message": "Forbidden"}

        # Employees cannot move to Done
        if not is_manager and new_stage == "done":
            return {"ok": False, "message": "Only managers can mark Done"}

        if not task.website_can_move_to(new_stage, is_manager=is_manager):
            return {"ok": False, "message": "Invalid transition"}

        task.write({"stage": new_stage})
        return {"ok": True}
    
    ######### Modal ###########
    
    @http.route('/tm/api/task', type='json', auth='user', website=True)
    def api_task(self, task_id):
        t = request.env['tm.task'].browse(int(task_id))
        if not t.exists():
            return {'ok': False}

        prio_label = dict(t._fields['priority'].selection).get(t.priority, '')
        # oldest -> newest for WhatsApp style
        msgs = t.sudo().message_ids.sorted('date', reverse=False)[:200]

        def _day_label(dt):
            if not dt:
                return ''
            d = dt.date()
            today = fields.Date.context_today(t)
            if d == today:
                return "Today"
            if d == today - datetime.timedelta(days=1):
                return "Yesterday"
            return dt.strftime("%B %d, %Y")

        def _stage_line(mm):
            # Show "Review → In Progress (Stage)" if tracking changed 'stage'
            for tv in mm.tracking_value_ids:
                if (tv.field == 'stage') or (tv.field_desc or '').lower() == 'stage':
                    oldv = tv.old_value_char or '—'
                    newv = tv.new_value_char or '—'
                    return f"{oldv} → {newv} (Stage)"
            return None

        def _att_to_dict(a):
            return {'id': a.id, 'name': a.name, 'mimetype': a.mimetype}

        out = []
        for mm in msgs:
            kind = 'comment'
            body = mm.body or ''
            sline = _stage_line(mm)
            if sline:
                kind = 'system'
                body = sline  # plain text system line
            initials = (mm.author_id.display_name or '—').strip()[:1].upper()
            out.append({
                'author': mm.author_id.display_name or '—',
                'date': mm.date and mm.date.strftime('%Y-%m-%d %H:%M'),
                'day_label': _day_label(mm.date),
                'body': body,
                'kind': kind,                 # 'comment' | 'system'
                'initials': initials,
                'attachments': [_att_to_dict(a) for a in mm.attachment_ids],
            })

        return {
            'ok': True,
            'task': {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'priority': t.priority,
                'priority_label': prio_label,
                'due_date': t.due_date and t.due_date.strftime('%Y-%m-%d'),
                'tags': [tag.name for tag in t.tag_ids],
            },
            'messages': out,  # oldest → newest
        }

    # -------- chat: text-only posts --------
    @http.route('/tm/api/chat/post', type='json', auth='user', website=True, csrf=False)
    def api_chat_post(self, task_id, body):
        t = request.env['tm.task'].browse(int(task_id))
        if not t.exists():
            return {'ok': False}
        t.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_comment')
        m = t.sudo().message_ids.sorted('date', reverse=True)[0]
        return {'ok': True, 'message': {
            'author': m.author_id.display_name or '—',
            'date': m.date and m.date.strftime('%Y-%m-%d %H:%M'),
            'day_label': m.date and m.date.strftime('%B %d, %Y') or '',
            'body': m.body or '',
            'kind': 'comment',
            'initials': (m.author_id.display_name or '—')[:1].upper(),
            'attachments': [],  # text-only
        }}
    
    # chat: multipart post for comment + files
    @http.route('/tm/api/chat/post_http', type='http', auth='user', website=True, csrf=False, methods=['POST'])
    def api_chat_post_http(self, **kwargs):
        task_id = int(kwargs.get('task_id', '0') or 0)
        body = (kwargs.get('body') or '').strip()
        t = request.env['tm.task'].browse(task_id)
        if not t.exists():
            return request.make_json_response({'ok': False})

        files = request.httprequest.files.getlist('files')
        att_ids = []
        for f in files:
            content = f.read() or b''
            if not content:
                continue
            att = request.env['ir.attachment'].sudo().create({
                'name': f.filename,
                'datas': base64.b64encode(content),
                'res_model': 'tm.task',
                'res_id': t.id,
                'mimetype': f.mimetype,
            })
            att_ids.append(att.id)

        t.message_post(body=body or False, message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    attachment_ids=[(6, 0, att_ids)] if att_ids else False)

        m = t.sudo().message_ids.sorted('date', reverse=True)[0]
        payload = {
            'author': m.author_id.display_name or '—',
            'date': m.date and m.date.strftime('%Y-%m-%d %H:%M'),
            'body': m.body or '',
            'initials': (m.author_id.display_name or '—')[:1].upper(),
            'attachments': [_att_to_dict(a) for a in m.attachment_ids],
        }
        return request.make_json_response({'ok': True, 'message': payload})