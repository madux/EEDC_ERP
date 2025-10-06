# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)

class PortalDashboard(http.Controller):

    # ---------- GET EMPLOYEE PROFILE IMAGE ----------
    def _get_profile_image_b64(self, user):
        """Return the best available *small* photo as base64 (ACL-safe via sudo)."""
        user = user.sudo()
        emp = user.employee_id
        # prefer employee photo → partner photo → user photo
        return (
            (emp and emp.image_128) or
            (user.partner_id and user.partner_id.image_128) or
            user.image_128
        ) or False

    def _can_read(self, record):
        """True if current user can read the record (rights + rules)."""
        try:
            rec = record.with_user(request.env.user)
            rec.check_access_rights('read')
            rec.check_access_rule('read')
            return True
        except Exception:
            return False

    def _get_profile_image_url(self, user):
        """Return a cache-friendly /web/image URL only if the user can read it."""
        emp = user.employee_id
        if emp and self._can_read(emp):
            return f"/web/image/hr.employee/{emp.id}/image_128?unique={emp.write_date or ''}"
        p = user.partner_id
        if p and self._can_read(p):
            return f"/web/image/res.partner/{p.id}/image_128?unique={p.write_date or ''}"
        if self._can_read(user):
            return f"/web/image/res.users/{user.id}/image_128?unique={user.write_date or ''}"
        return False  # force template to use base64 fallback

    # ---------- PAGE ROUTE ----------
    @http.route(["/my/portal/dashboard/<int:user_id>"], type='http', auth='user', website=True, website_published=True)
    def dashboardPortal(self, user_id):
        try:
            user = request.env['res.users'].sudo().browse([user_id])
            if not user.exists():
                return request.not_found()

            memo = request.env['memo.model'].sudo()
            memo_ids = memo.search([('employee_id', '=', user.employee_id.id)], order="id desc")

            vals = {
                "user": user,
                # "image": user.employee_id.image_512 or user.image_1920,
                "image": self._get_profile_image_b64(user),
                "image_url": self._get_profile_image_url(user),
                "memo_ids": memo_ids,

                # FIX: open_request previously used closed_files()
                "open_request": len(self.open_files(memo_ids)),
                "closed_request": len(self.closed_files(memo_ids)),
                "approved_request": len(self.approved_files(memo_ids)),

                "leave_remaining": user.employee_id.allocation_remaining_display,
                "template_name": "portal_dashboard_template_id",

                # Kept for backward-compat UI (unused by new charts)
                "performance_y_data_chart": json.dumps({"performance_y_data_chart": [
                    "KRA","Functional Competence","Leadership Competence"
                ]}),
                "performance_x_data_chart": self.get_pms_performance_json(user),
            }
            return request.render("portal_request.portal_dashboard_template_id", vals)
        except Exception as e:
            _logger.exception("dashboardPortal error: %s", e)
            return request.not_found()

    # ---------- JSON API FOR REDESIGNED DASHBOARD ----------
    @http.route('/portal_request/api/data', type='json', auth='user')
    def portal_request_data(self, user_id=None):
        """
        KPIs + chart payload + Highlights.
        - Workload Distribution & Highlights come from tm.task
        - Performance Measure comes from current-year PMS scores
        """
        try:
            # -------- resolve user / employee
            if user_id:
                user = request.env['res.users'].sudo().browse(int(user_id))
                if not user.exists():
                    return {"ok": False, "error": "User not found"}
            else:
                user = request.env.user  # no sudo → respect record rules
            emp = user.employee_id

            # -------- tasks scoped to this employee (same filter as /tm/api/board)
            Task = request.env['tm.task']  # no sudo (portal rules apply)
            tasks_domain = [("active", "=", True)]
            if emp:
                staff_code = (emp.employee_number or emp.barcode or "").strip()
                tasks_domain += ["|", ("employee_id", "=", emp.id), ("assignee_staff_id", "=", staff_code)]
            else:
                tasks_domain += [("id", "=", 0)]

            tasks = Task.search(tasks_domain)

            # KPIs from memos (unchanged)
            memo = request.env['memo.model'].sudo()
            memos = memo.search([('employee_id', '=', emp.id)]) if emp else memo.browse()
            open_cnt     = len(self.open_files(memos))
            closed_cnt   = len(self.closed_files(memos))
            approved_cnt = len(self.approved_files(memos))
            leave_remaining = emp.allocation_remaining_display if emp else 0
            
            # KPIs from tasks (you can keep your memo KPIs if needed; here we use tasks)
            # open_cnt   = len(tasks.filtered(lambda t: t.stage != 'done'))
            # closed_cnt = len(tasks.filtered(lambda t: t.stage == 'done'))
            # # "approved" is business-specific; keep your memo calc if you prefer.
            # approved_cnt = 0
            # leave_remaining = emp.allocation_remaining_display if emp else 0

            # -------- Workload distribution
            stages = ["todo", "in_progress", "review", "done"]
            label_by = dict(todo="To Do", in_progress="In Progress", review="Review", done="Done")
            counts = {k: 0 for k in stages}
            for t in tasks:
                if t.stage in counts:
                    counts[t.stage] += 1
            stage_distribution = [
                {"key": k, "label": label_by[k], "count": counts[k]}
                for k in stages
            ]

            # -------- Performance (PMS current year)
            kra, fc, lc = self._current_month_scores(emp, fallback_to_year=True)
            performance_rows = [
                {"name": "KRA",                   "count": kra or 0.0},
                {"name": "Functional Competence", "count": fc  or 0.0},
                {"name": "Leadership Competence", "count": lc  or 0.0},
            ]

            # -------- Highlights from tasks + payslips
            def _has_any_tag(record, needles):
                names = [(tg.name or '').lower() for tg in record.tag_ids]
                return any(any(n in nm for n in needles) for nm in names)

            doc_tasks = tasks.filtered(lambda t: _has_any_tag(t, ['documentation', 'document', 'docs']))
            rec_tasks = tasks.filtered(lambda t: _has_any_tag(t, ['recommend', 'recommendation']))
            plan_tasks = tasks.filtered(lambda t: _has_any_tag(t, ['planning', 'plan']))

            def _pct_done(subset):
                total = len(subset)
                if not total:
                    return 0
                done = len(subset.filtered(lambda t: t.stage == 'done'))
                return int(round((done * 100.0) / total))

            documentation_pct  = _pct_done(doc_tasks)
            recommendations_pct = _pct_done(rec_tasks)
            planning_count     = len(plan_tasks)
            backlog_count      = len(tasks.filtered(lambda t: t.stage != 'done'))  # or only 'todo' if you prefer

            payslips_count = 0
            try:
                if emp:
                    # count employee payslips (tweak states if your flow differs)
                    payslips_count = request.env['hr.payslip'].sudo().search_count([
                        ('employee_id', '=', emp.id),
                        ('state', 'in', ['done', 'paid', 'verify', 'hr_verified'])
                    ])
            except Exception:
                payslips_count = 0  # payroll not installed/accessible

            highlights = {
                "documentation_pct": documentation_pct,
                "recommendations_pct": recommendations_pct,
                "planning": planning_count,
                "backlog": backlog_count,
                "payslips": payslips_count,
            }

            data = {
                "open_request": open_cnt,
                "approved_request": approved_cnt,
                "closed_request": closed_cnt,
                "leave_remaining": leave_remaining,

                "employee_name": emp.name if emp else user.name,
                "department": (emp.department_id.name if emp and emp.department_id else "") or "",
                "role": (emp.job_id.name if emp and emp.job_id else "") or "",
                "manager": (emp.parent_id.name if emp and emp.parent_id else "") or "",

                "stage_distribution": stage_distribution,
                "performance_rows": performance_rows,
                "highlights": highlights,
            }
            return {"ok": True, "data": data}
        except Exception as e:
            _logger.exception("portal_request_data error: %s", e)
            return {"ok": False, "error": "Unexpected error"}

    # ---------- Helpers ----------
    def closed_files(self, memos):
        return memos.filtered(lambda m: m.state in ['Done'])

    def open_files(self, memos):
        # Not refused and not done ⇒ considered open
        return memos.filtered(lambda m: m.state not in ['Refuse', 'Done'])

    def approved_files(self, memos):
        # Your previous logic (keep as-is): not Refuse/submit/Sent
        return memos.filtered(lambda m: m.state not in ['Refuse', 'submit', 'Sent'])
    
    def _in_month(self, dt, month_start, next_month_start):
        return bool(dt and month_start <= dt.date() < next_month_start)

    def _current_month_scores(self, emp, fallback_to_year=True):
        """Return (kra, fc, lc) for the appraisee record updated in the current month.
        If none found and fallback_to_year=True, fall back to current-year scores.
        """
        kra = fc = lc = 0.0
        try:
            if not emp:
                return kra, fc, lc

            Appraisee = request.env['pms.appraisee'].sudo()
            apps = Appraisee.search([('employee_id', '=', emp.id)])
            if not apps:
                return kra, fc, lc

            today = fields.Date.today()
            month_start = today.replace(day=1)
            next_month_start = month_start + relativedelta(months=1)

            # restrict to current year like your previous helper
            year_apps = apps.filtered(
                lambda a: a.pms_year_id and a.pms_year_id.date_from
                and a.pms_year_id.date_from.strftime('%Y') == str(today.year)
            )

            # find one written in this month (prefer write_date, then create_date)
            def _pick_monthly(a):
                wd = a.write_date or a.create_date
                return self._in_month(wd, month_start, next_month_start)

            monthly = next((a for a in year_apps if _pick_monthly(a)), None)

            picked = monthly
            if not picked and fallback_to_year:
                # fallback: same record you used before (any current-year one)
                picked = next(iter(year_apps), None)

            if picked:
                kra = float(picked.final_kra_score or 0.0)
                fc  = float(picked.final_fc_score or 0.0)
                lc  = float(picked.final_lc_score or 0.0)
        except Exception as e:
            _logger.debug("Monthly score fetch failed: %s", e)
        return kra, fc, lc

    def _current_year_scores(self, emp):
        """Return (kra, fc, lc) floats for the current year if available; else zeros."""
        kra = fc = lc = 0.0
        try:
            if not emp:
                return kra, fc, lc
            appraisee_env = request.env['pms.appraisee'].sudo()
            employee_appraisees = appraisee_env.search([('employee_id', '=', emp.id)])
            if not employee_appraisees:
                return kra, fc, lc

            this_year = fields.Date.today().year
            current = next((a for a in employee_appraisees
                            if a.pms_year_id and a.pms_year_id.date_from and
                               a.pms_year_id.date_from.strftime("%Y") == str(this_year)), None)
            if current:
                kra = float(current.final_kra_score or 0.0)
                fc  = float(current.final_fc_score or 0.0)
                lc  = float(current.final_lc_score or 0.0)
        except Exception as e:
            _logger.debug("Score fetch failed: %s", e)
        return kra, fc, lc

    # Back-compat with your previous template use (returns JSON string)
    def get_pms_performance_json(self, user):
        kra, fc, lc = self._current_year_scores(user.employee_id)
        return json.dumps({'performance_x_data_chart': [kra, fc, lc]})
