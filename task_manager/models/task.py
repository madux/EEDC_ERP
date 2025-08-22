from odoo import api, fields, models, _

class TmTaskTag(models.Model):
    _name = "tm.task.tag"
    _description = "Task Tag"

    name = fields.Char(required=True)
    color = fields.Integer(default=0)

class TmTask(models.Model):
    _name = "tm.task"
    _description = "Task (Website Board)"
    _order = "priority desc, due_date asc, id desc"

    name = fields.Char(required=True)
    description = fields.Text()

    assignee_staff_id = fields.Char(string="Staff ID", index=True, required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee")

    stage = fields.Selection([
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
        ], default="todo", required=True, index=True)

    priority = fields.Selection([
        ("0", "Low"),
        ("1", "Medium"),
        ("2", "High"),
        ], default="0", index=True)

    due_date = fields.Date()
    tag_ids = fields.Many2many("tm.task.tag", string="Tags")

    manager_id = fields.Many2one("res.users", string="Manager")

    last_review_note = fields.Text()
    last_reviewed_by = fields.Many2one("res.users")
    last_reviewed_on = fields.Datetime()

    active = fields.Boolean(default=True)

     # ------- Normalization goes in create/write ----------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            s = vals.get("assignee_staff_id")
            if isinstance(s, str):
                vals["assignee_staff_id"] = s.strip()
        return super().create(vals_list)

    def write(self, vals):
        s = vals.get("assignee_staff_id")
        if isinstance(s, str):
            vals["assignee_staff_id"] = s.strip()
        return super().write(vals)

    # ------- Constraint only validates; no writes ----------
    @api.constrains("assignee_staff_id")
    def _check_staff(self):
        for rec in self:
            if not rec.assignee_staff_id or not rec.assignee_staff_id.strip():
                raise ValidationError(_("Staff ID cannot be empty or spaces only."))


    # @api.constrains("assignee_staff_id")
    # def _constrain_staff(self):
    #     for rec in self:
    #         if rec.assignee_staff_id:
    #             rec.assignee_staff_id = rec.assignee_staff_id.strip()

    # Simple helper to control website moves
    def website_can_move_to(self, target_stage, is_manager=False):
        self.ensure_one()
        if is_manager:
            return target_stage in {"todo", "in_progress", "review", "done"}
        # employee: no direct move to done
        allowed = {
            "todo": {"in_progress", "review", "todo"},
            "in_progress": {"todo", "review", "in_progress"},
            "review": {"in_progress", "todo", "review"},
            "done": set(),
        }
        return target_stage in allowed.get(self.stage, set())