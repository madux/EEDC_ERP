# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


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
