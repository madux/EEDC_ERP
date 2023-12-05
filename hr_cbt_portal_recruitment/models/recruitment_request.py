from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HRJobRecruitmentRequest(models.Model):
    _name = 'hr.job.recruitment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_expected desc, id desc'
    _description = "Recruitment Request"

    @api.model
    def _get_default_dept(self):
        return self.env.user.employee_id.department_id
    
    name = fields.Char(string='Subject', size=512, required=False,
                       help='The subject of the recruitment request. E.g. Two new salesmen are requested for a new sales strategy',
                       states={'confirmed': [('readonly', True)],
                               'accepted':[('readonly', True)],
                               'recruiting':[('readonly', True)],
                               'done':[('readonly', True)]
                               },)
    
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             states={'confirmed': [('readonly', True)],
                                     'accepted':[('readonly', True)],
                                     'recruiting':[('readonly', True)],
                                     'done':[('readonly', True)]
                                     },
                             help='The Job Position you expected to get more hired.',
                             )
    memo_id = fields.Many2one('memo.model', string="Memo ID")
    recruitment_mode = fields.Selection([('Internal', 'Internal'),
                                ('External', 'External'),
                                ('Outsourced', 'Outsourced'),
                              ], string='Recruitment Mode', index=True,
                             copy=False,
                             readonly=True,
                             store=True,
                             states={'draft': [('required', True)],
                                     'draft':[('readonly', False)],
                                     })
    
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          help='If you don\'t select the requested position in the field above, you must specify a Job Title here. Upon this request is approved, the system can automatically create a new Job position and attach it to this request.')
    department_id = fields.Many2one('hr.department',
                                    string='Department',
                                    states={'confirmed': [('readonly', True)],
                                            'accepted':[('readonly', True)],
                                            'recruiting':[('readonly', True)],
                                            'done':[('readonly', True)]
                                            },
                                    default=_get_default_dept,
                                    required=False,
                                    index=True
                                    )
    user_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True, index=True)
    user_to_approve_id = fields.Many2one('res.users', string='To be approved By', readonly=True, index=True)
    recommended_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True, index=True)
    no_of_hired_employee = fields.Integer('Hired Employees')
                                        #   compute='_count_dept_employees', required=False)
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        states={'confirmed': [('readonly', True)],
                                                'accepted':[('readonly', True)],
                                                'recruiting':[('readonly', True)],
                                                'done':[('readonly', True)]
                                                },
                                        required=False,
                                        index=True
                                        )
    date_expected = fields.Date('Date Expected', required=False,
                                default=fields.Date.today, index=True)
    description = fields.Text('Job Description',
                              help='Please describe the job',
                              readonly=False,
                              states={'done':[('readonly', True)]},
                              required=False
                              )
    requirements = fields.Text('Job Requirements',
                               help='Please specify your requirements on new employees',
                               readonly=False,
                               states={'done':[('readonly', True)]},
                               required=False
                               )
    years_of_experience = fields.Char('Years of Experience')
    reason = fields.Text('Reason',
                         help='Please explain why you request to recruit more employee(s) for your department',
                         states={'confirmed': [('readonly', True)],
                                 'accepted':[('readonly', True)],
                                 'recruiting':[('readonly', True)],
                                 'done':[('readonly', True)]
                                 },
                         required=False
                         )
    state = fields.Selection([
                              ('draft', 'Draft'),
                              ('refused', 'Refused'),
                              ('confirmed', 'Waiting Approval'),
                              ('accepted', 'Approved'),
                              ('recruiting', 'In Recruitment'),
                              ('done', 'Done'),
                              ],
            string='Status', readonly=True, copy=False, index=True, default='draft', required=False,
            help='When the recruitment request is created the status is \'Draft\'.\
            \n It is confirmed by the user and request is sent to the Approver, the status is \'Waiting Approval\'.\
            \n If the Approver accepts it, the status is \'Approved\'.\
            \n If the associated job recruitment is started, the status is \'In Recruitment\'.\
            \n If the number new employees created in association with the request, the status turns to \'Done\' automatically. Or, it can manually be set to \'Done\' whenever an authorized person press button Done'
            )
    date_confirmed = fields.Date('Date Confirmed')
    date_accepted = fields.Date('Date Approved', copy=False,
                                  help="Date of the acceptance of the recruitment request. It's filled when the button Approve is pressed.")
    date_refused = fields.Date('Date Refused')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id
                                 )

    applicant_ids = fields.One2many('hr.applicant', 'request_id', string='Applicants', readonly=True, index=True)
    employee_ids = fields.One2many('hr.employee', 'request_id', string='Recruited Employees')#, compute='_compute_recruited_employees', store=True, index=True)
    employees_count = fields.Integer('# of Employees')#, compute='_count_recruited_employees', store=True, index=True)
    recruited_employees = fields.Float('Recruited Employees Rate')#, compute='_compute_recruited_employee_percentage')
    applicants_count = fields.Integer('# of Applications')#, compute='_count_applicants', store=True, index=True)

    def action_start_recruit(self):
        if self.user_to_approve_id.id != self.env.user_id.id:
            raise ValidationError("Ops! You are not responsible for starting this job postition recruitment")
        else:
            self.job_id.sudo().write({
                'name': self.job_id.name,
                'department_id': self.job_id.department_id.id,
                'no_of_recruitment': self.expected_employees,
                'request_id': self.id,
            })
            