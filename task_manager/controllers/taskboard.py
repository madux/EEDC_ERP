# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class TaskboardController(http.Controller):

    # Website page (renders login shell + board shell; JS populates)
    @http.route("/taskboard", type="http", auth="public", website=True)
    def taskboard_page(self, **kw):
        staff_id = request.session.get("tm_staff_id")
        employee = None
        if staff_id:
            employee = request.env["hr.employee"].sudo().search([
                ("active", "=", True), ("employee_number", "=", staff_id)
            ], limit=1)
        return request.render("task_manager.tm_taskboard_page", {"employee": employee})

    # Login: staff-id + default password (from ir.config_parameter)
    @http.route("/tm/api/login", type="json", auth="public", website=True, csrf=False)
    def api_login(self, staff_id=None, password=None):
        staff_id = (staff_id or "").strip()
        if not staff_id or not password:
            return {"ok": False, "message": "Missing credentials"}

        default_pw = request.env["ir.config_parameter"].sudo().get_param("tm.default_password", "12345")
        if password != default_pw:
            return {"ok": False, "message": "Invalid credentials"}

        emp = request.env["hr.employee"].sudo().search([
            ("active", "=", True), ("employee_number", "=", staff_id)
        ], limit=1)
        if not emp:
            return {"ok": False, "message": "Invalid credentials"}

        request.session["tm_staff_id"] = staff_id
        request.session["tm_staff_name"] = emp.name
        return {"ok": True, "name": emp.name}

    @http.route("/tm/api/logout", type="json", auth="public", website=True, csrf=False)
    def api_logout(self):
        request.session.pop("tm_staff_id", None)
        request.session.pop("tm_staff_name", None)
        return {"ok": True}

    # Fetch board data (grouped by stage) for current session staff_id
    @http.route("/tm/api/board", type="json", auth="public", website=True, csrf=False)
    def api_board(self):
        staff_id = request.session.get("tm_staff_id")
        if not staff_id:
            return {"ok": False, "message": "Not authenticated"}
        Task = request.env["tm.task"].sudo()
        tasks = Task.search([("assignee_staff_id", "=", staff_id), ("active", "=", True)])
        def _card(t):
            return {
                "id": t.id,
                "name": t.name,
                "priority": t.priority,
                "due_date": t.due_date and t.due_date.strftime('%Y-%m-%d') or None,
                "tags": [tag.name for tag in t.tag_ids],
                "stage": t.stage,
            }
        stages = ["todo", "in_progress", "review", "done"]
        grouped = {k: [] for k in stages}
        for t in tasks:
            grouped.setdefault(t.stage, []).append(_card(t))
        counts = {k: len(v) for k, v in grouped.items()}
        return {"ok": True, "data": grouped, "counts": counts, "staff_name": request.session.get("tm_staff_name")}

    # Move task to a new stage (employees cannot move to Done)
    @http.route("/tm/api/move", type="json", auth="public", website=True, csrf=False)
    def api_move(self, task_id=None, new_stage=None):
        staff_id = request.session.get("tm_staff_id")
        if not staff_id:
            return {"ok": False, "message": "Not authenticated"}
        if not task_id or not new_stage:
            return {"ok": False, "message": "Missing data"}
        Task = request.env["tm.task"].sudo()
        task = Task.browse(int(task_id))
        if not task or not task.exists() or task.assignee_staff_id != staff_id:
            return {"ok": False, "message": "Forbidden"}
        if new_stage == "done":
            return {"ok": False, "message": "Only managers can mark Done"}
        if not task.website_can_move_to(new_stage, is_manager=False):
            return {"ok": False, "message": "Invalid transition"}
        task.write({"stage": new_stage})
        return {"ok": True}