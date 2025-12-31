from odoo import models, fields, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class HRLeave(models.Model):
    _inherit = "hr.leave"

    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Request Reference')

    def action_approve(self):
        res = super(HRLeave, self).action_approve()
        if self.memo_id:
            self.memo_id.state = "Done"
        return res
    
    def action_validate(self):
        res = super(HRLeave, self).action_validate()
        if self.memo_id:
            self.memo_id.state = "Done"
        return res
    
    def action_refuse(self):
        res = super(HRLeave, self).action_refuse()
        if self.memo_id:
            self.memo_id.state = "Refuse"
        return res
    
    
class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    holiday_type = fields.Selection(
        selection_add=[
            ('grade', 'By Grade'),
            ('level', 'By Level')
        ],
        ondelete={
            'grade': 'set default',
            'level': 'set default'
        }
    )

    grade_id = fields.Many2one(
        'hr.grade',
        compute='_compute_from_holiday_type',
        store=True,
        string='Grade',
        readonly=False,
        # domain="[('company_id', 'in', [employee_company_id, False])]",  # Simplified domain
        states={
            'cancel': [('readonly', True)],
            'refuse': [('readonly', True)],
            'validate': [('readonly', True)]
        }
    )

    level_id = fields.Many2one(
        'hr.level',
        compute='_compute_from_holiday_type',
        store=True,
        string='Level',
        readonly=False,
        # domain="[('company_id', 'in', [employee_company_id, False])]",  # Simplified domain
        states={
            'cancel': [('readonly', True)],
            'refuse': [('readonly', True)],
            'validate': [('readonly', True)]
        }
    )

    
    _sql_constraints = [
        ('type_value',
         "CHECK( (holiday_type='employee' AND (employee_id IS NOT NULL OR multi_employee IS TRUE)) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL) or "
         "(holiday_type='grade' AND grade_id IS NOT NULL) or "
         "(holiday_type='level' AND level_id IS NOT NULL))",
         "The employee, department, company, category, grade or level of this request is missing."),
        ('duration_check',
         "CHECK( ( number_of_days > 0 AND allocation_type='regular') or (allocation_type != 'regular'))",
         "The duration must be greater than 0."),
    ]

    @api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        """Override to handle grade and level holiday types"""
        default_employee_ids = self.env['hr.employee'].browse(
            self.env.context.get('default_employee_id')
        ) or self.env.user.employee_id

        for allocation in self:
            if allocation.holiday_type == 'employee':
                if not allocation.employee_ids:
                    allocation.employee_ids = self.env.user.employee_id
                allocation.mode_company_id = False
                allocation.category_id = False
                allocation.grade_id = False
                allocation.level_id = False

            elif allocation.holiday_type == 'company':
                allocation.employee_ids = False
                if not allocation.mode_company_id:
                    allocation.mode_company_id = self.env.company
                allocation.category_id = False
                allocation.grade_id = False
                allocation.level_id = False

            elif allocation.holiday_type == 'department':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.category_id = False
                allocation.grade_id = False
                allocation.level_id = False

            elif allocation.holiday_type == 'category':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.grade_id = False
                allocation.level_id = False

            elif allocation.holiday_type == 'grade':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.category_id = False
                allocation.level_id = False
                # Optionally set default grade if none exists
                if not allocation.grade_id and self.env.user.employee_id.grade_id:
                    # Only set if the grade belongs to the current company
                    employee_grade = self.env.user.employee_id.grade_id
                    if employee_grade.company_id == self.env.company:
                        allocation.grade_id = employee_grade

            elif allocation.holiday_type == 'level':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.category_id = False
                allocation.grade_id = False
                # Optionally set default level if none exists
                if not allocation.level_id and self.env.user.employee_id.level_id:
                    # Only set if the level belongs to the current company
                    employee_level = self.env.user.employee_id.level_id
                    if employee_level.company_id == self.env.company:
                        allocation.level_id = employee_level

            else:
                allocation.employee_ids = default_employee_ids

    def name_get(self):
        """Override to include grade and level in name"""
        res = []
        for allocation in self:
            if allocation.holiday_type == 'company':
                target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                target = allocation.category_id.name
            elif allocation.holiday_type == 'grade':
                target = allocation.grade_id.name if allocation.grade_id else _('Grade')
            elif allocation.holiday_type == 'level':
                target = allocation.level_id.name if allocation.level_id else _('Level')
            elif allocation.employee_id:
                target = allocation.employee_id.name
            else:
                target = ', '.join(allocation.employee_ids.sudo().mapped('name'))

            res.append(
                (allocation.id,
                 _("Allocation of %(allocation_name)s : %(duration).2f %(duration_type)s to %(person)s",
                   allocation_name=allocation.holiday_status_id.sudo().name,
                   duration=allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                   duration_type=_('hours') if allocation.type_request_unit == 'hour' else _('days'),
                   person=target
                ))
            )
        return res

    def _action_validate_create_childs(self):
        """Override to handle grade and level allocations with multi-company support"""
        childs = self.env['hr.leave.allocation']

        _logger.info("=== ALLOCATION DEBUG START ===")
        _logger.info(f"Holiday Type: {self.holiday_type}")
        _logger.info(f"State: {self.state}")

        if self.state == 'validate' and (
            self.holiday_type in ['category', 'department', 'company', 'grade', 'level'] or
            (self.holiday_type == 'employee' and len(self.employee_ids) > 1)
        ):
            if self.holiday_type == 'employee':
                employees = self.employee_ids
            elif self.holiday_type == 'category':
                employees = self.category_id.employee_ids
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
            elif self.holiday_type == 'company':
                employees = self.env['hr.employee'].search([
                    ('company_id', '=', self.mode_company_id.id)
                ])
            elif self.holiday_type == 'grade':
                # Filter employees by grade AND company to respect multi-company rules
                if self.grade_id:
                    _logger.info(f"Searching employees with grade: {self.grade_id.name}")
                    _logger.info(f"Grade Company: {self.grade_id.company_id.name}")
                    
                    employees = self.env['hr.employee'].search([
                        ('grade_id', '=', self.grade_id.id),
                        ('company_id', '=', self.grade_id.company_id.id),
                        ('active', '=', True)
                    ])
                    
                    _logger.info(f"Found {len(employees)} employees")
                    for emp in employees:
                        _logger.info(f"  - {emp.name} (ID: {emp.id})")
                else:
                    _logger.warning("No grade_id set!")
                    employees = self.env['hr.employee']
                    
            elif self.holiday_type == 'level':
                # Filter employees by level AND company to respect multi-company rules
                if self.level_id:
                    _logger.info(f"Searching employees with level: {self.level_id.name}")
                    _logger.info(f"Level Company: {self.level_id.company_id.name}")
                    
                    employees = self.env['hr.employee'].search([
                        ('level_id', '=', self.level_id.id),
                        ('company_id', '=', self.level_id.company_id.id),
                        ('active', '=', True)
                    ])
                    
                    _logger.info(f"Found {len(employees)} employees")
                    for emp in employees:
                        _logger.info(f"  - {emp.name} (ID: {emp.id})")
                else:
                    _logger.warning("No level_id set!")
                    employees = self.env['hr.employee']
            else:
                employees = self.env['hr.employee']

            # Create child allocations for each employee
            if employees:
                _logger.info(f"Creating allocations for {len(employees)} employees")
                allocation_create_vals = self._prepare_holiday_values(employees)
                _logger.info(f"Prepared {len(allocation_create_vals)} allocation values")
                
                childs += self.with_context(
                    mail_notify_force_send=False,
                    mail_activity_automation_skip=True
                ).create(allocation_create_vals)

                _logger.info(f"Created {len(childs)} child allocations")
                
                if childs:
                    childs.action_validate()
                    _logger.info("Child allocations validated")
            else:
                # Log warning if no employees found for grade/level
                if self.holiday_type == 'grade':
                    msg = _("No active employees found with grade '%s'") % self.grade_id.name
                    _logger.warning(msg)
                    self._message_log(body=msg)
                elif self.holiday_type == 'level':
                    msg = _("No active employees found with level '%s'") % self.level_id.name
                    _logger.warning(msg)
                    self._message_log(body=msg)

        _logger.info("=== ALLOCATION DEBUG END ===")
        return childs
