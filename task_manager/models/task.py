from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
from collections import defaultdict

class TmTaskTag(models.Model):
    _name = "tm.task.tag"
    _description = "Task Tag"

    name = fields.Char(required=True)
    color = fields.Integer(default=0)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

class TmTask(models.Model):
    _name = "tm.task"
    _description = "Task"
    _order = "priority desc, due_date asc, id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    # --- identity & company ---
    key = fields.Char("Key", readonly=True, copy=False, index=True, default="/")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, index=True)

    # --- core fields ---
    name = fields.Char(required=True, tracking=True)
    description = fields.Text()

    assignee_staff_id = fields.Char(string="Staff ID", index=True, required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", tracking=True, index=True)

    stage = fields.Selection([
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
    ], default="todo", required=True, index=True, tracking=True)

    priority = fields.Selection([
        ("0", "Low"), ("1", "Medium"), ("2", "High")
    ], default="0", index=True, tracking=True)

    due_date = fields.Date(tracking=True)
    tag_ids = fields.Many2many("tm.task.tag", string="Tags")

    manager_id = fields.Many2one("res.users", string="Manager", tracking=True)

    # Review / completion
    last_review_note = fields.Text()
    last_reviewed_by = fields.Many2one("res.users")
    last_reviewed_on = fields.Datetime()

    # Health
    is_blocked = fields.Boolean(default=False)
    blocked_reason = fields.Char()

    # Date helpers (stored for speed)
    is_overdue = fields.Boolean(compute="_compute_dates", store=True, index=True)
    days_left = fields.Integer(compute="_compute_dates", store=True)

    active = fields.Boolean(default=True)

    # ------- Create/Write normalizations & policies ---------
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        today = fields.Date.context_today(self)
        for vals in vals_list:
            s = vals.get("assignee_staff_id")
            if isinstance(s, str):
                vals["assignee_staff_id"] = s.strip()
            # sequence
            if not vals.get('key') or vals.get('key') == '/':
                vals['key'] = seq.next_by_code('tm.task') or '/'
            # default employee from staff id
            if not vals.get('employee_id') and vals.get('assignee_staff_id'):
                emp = self.env['hr.employee'].search([
                    ('active', '=', True), ('employee_number', '=', vals['assignee_staff_id'])
                ], limit=1)
                if emp:
                    vals['employee_id'] = emp.id
        return super().create(vals_list)

    def write(self, vals):
        if 'assignee_staff_id' in vals and isinstance(vals['assignee_staff_id'], str):
            vals['assignee_staff_id'] = vals['assignee_staff_id'].strip()
        # stage policies
        stage_before = {rec.id: rec.stage for rec in self}
        res = super().write(vals)
        if 'stage' in vals:
            for rec in self:
                old, new = stage_before.get(rec.id), rec.stage
                if old != new:
                    if new == 'review' and not (vals.get('last_review_note') or rec.last_review_note):
                        raise ValidationError(_("A review note is required to move to Review."))
                    if new == 'done':
                        if rec.is_blocked and not self.env.user.has_group('task_manager.group_tm_manager'):
                            raise ValidationError(_("Blocked tasks can only be completed by a manager."))
                        rec.with_context(tracking_disable=True).write({
                            'last_reviewed_by': self.env.user.id,
                            'last_reviewed_on': fields.Datetime.now(),
                        })
                        rec.message_post(body=_("Marked Done by %s") % self.env.user.display_name)
        return res

    # ------- Validations ---------
    @api.constrains("assignee_staff_id")
    def _check_staff(self):
        for rec in self:
            if not rec.assignee_staff_id or not rec.assignee_staff_id.strip():
                raise ValidationError(_("Staff ID cannot be empty or spaces only."))

    # ------- Onchanges (link staff id <-> employee) ---------
    @api.onchange('assignee_staff_id')
    def _onchange_staff_id(self):
        if self.assignee_staff_id:
            emp = self.env['hr.employee'].search([
                ('active', '=', True), ('employee_number', '=', self.assignee_staff_id.strip())
            ], limit=1)
            self.employee_id = emp

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.employee_number:
            self.assignee_staff_id = self.employee_id.employee_number

    # ------- Date helpers ---------
    @api.depends('due_date', 'stage')
    def _compute_dates(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.due_date:
                rec.days_left = (rec.due_date - today).days
                rec.is_overdue = rec.stage != 'done' and rec.due_date < today
            else:
                rec.days_left = False
                rec.is_overdue = False

    # Simple helper to control website moves (unchanged)
    def website_can_move_to(self, target_stage, is_manager=False):
        self.ensure_one()
        if is_manager:
            return target_stage in {"todo", "in_progress", "review", "done"}
        allowed = {
            "todo": {"in_progress", "review", "todo"},
            "in_progress": {"todo", "review", "in_progress"},
            "review": {"in_progress", "todo", "review"},
            "done": set(),
        }
        return target_stage in allowed.get(self.stage, set())
    
    def _cron_daily_digest(self):
        Task = self.sudo()
        today = fields.Date.context_today(self)
        by_user = defaultdict(lambda: {'email_to': '', 'overdue': 0, 'today': 0})
        tasks = Task.search([('active','=',True), ('employee_id.user_id','!=',False)])
        for t in tasks:
            user = t.employee_id.user_id
            d = by_user[user.id]
            d['email_to'] = user.partner_id.email or user.email
            if t.due_date == today and t.stage != 'done':
                d['today'] += 1
            if t.is_overdue:
                d['overdue'] += 1
        tmpl = self.env.ref('task_manager.mail_tmpl_tm_digest', raise_if_not_found=False)
        if tmpl:
            for data in by_user.values():
                if data['email_to']:
                    tmpl.sudo().with_context(lang=self.env.user.lang).send_mail(self.env['tm.task'].create({}), email_values={}, force_send=True, notif_layout=False, render_template=False, raise_exception=False, email_to=data['email_to'], values=data)

    def _cron_escalate_overdue(self):
        Task = self.sudo()
        today = fields.Date.context_today(self)
        overdue = Task.search([('active','=',True), ('stage','!=','done'), ('due_date','!=',False)])
        for t in overdue:
            if (today - t.due_date).days > 2 and t.manager_id and (t.manager_id.partner_id.email or t.manager_id.email):
                body = _("Task %s is overdue by %s days.") % (t.display_name, (today - t.due_date).days)
                t.message_post(partner_ids=[t.manager_id.partner_id.id], body=body, message_type='comment', subtype_xmlid='mail.mt_comment')

    
    # Priority badge colours:
    priority_badge = fields.Html(
        compute="_compute_priority_badge",
        sanitize=False,  # keep as False so our <span> renders
        readonly=True,
    )

    @api.depends("priority")
    def _compute_priority_badge(self):
        # map selection values -> (label, bg color class)
        colors = {
            "0": ("Low", "bg-secondary"),
            "1": ("Medium", "bg-warning"),
            "2": ("High", "bg-danger"),
        }
        for rec in self:
            key = rec.priority or "0"
            label, bg = colors.get(key, ("Low", "bg-secondary"))
            # white text + tooltip with the label
            rec.priority_badge = (
                f"<span class='badge rounded-pill {bg} text-white' "
                f"title='{label}' aria-label='{label}'>{label}</span>"
            )