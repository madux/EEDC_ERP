from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

class HREMployeeTransfer(models.Model):
    _name = 'hr.employee.transfer'

    employee_ids = fields.Many2many('hr.employee')
    employee_transfer_lines = fields.One2many( 
        'hr.employee.transfer.line', 
        'employee_transfer_id', 
        string='Transfer Details'
        )
    transfer_initiator_uid = fields.Many2one(
        'res.users',
        default=lambda self: self.env.uid,
        string="Transfer Initiator",
        copy=False,
        readonly=True
    )
    memo_id = fields.Many2one(
        "memo.model", 
        string="Memo ID"
        )

    transfer_date = fields.Date('Initiation Date',
                                default=lambda self: fields.Date.context_today(self),
                                copy=False,
                                readonly=True
                                )

    

    def update_transfer_details(self):
        employee_ids = self.env.context.get('default_employee_ids', [])
        # raise ValidationError(self.id)
        # check validations,
        # go throught each line that the select option is checked,
        # update employee rec with the data eg department, role, district
        
        
        # new_transfer = self.env['hr.employee.transfer'].create({
        #     'employee_ids': [(6, 0, employee_ids)],
        #     'transfer_initiator_uid': self.env.user.id,
        #     'transfer_date': fields.Datetime.now(),
        #     'employee_transfer_lines': self.env.context.get('default_employee_transfer_lines', [])
        # })

        for tf_line in self.employee_transfer_lines:
            tf_line.employee_id.update({
                'department_id': tf_line.transfer_dept.id if tf_line.transfer_dept else tf_line.employee_id.department_id.id,
                'job_id': tf_line.new_role.id if tf_line.new_role else tf_line.employee_id.job_id.id,
                'ps_district_id': tf_line.new_district.id if tf_line.new_district else tf_line.employee_id.ps_district_id.id,
            })
        self.memo_id.finalize_employee_transfer()

class HREmployeeTransferLine(models.Model):
    _name = 'hr.employee.transfer.line'

    memo_id = fields.Many2one('memo.model', string='Memo ref')
    employee_transfer_id = fields.Many2one('hr.employee.transfer', string='Employee Transfer')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    current_dept_id = fields.Many2one('hr.department', string='Current Department')
    transfer_dept = fields.Many2one('hr.department', string='Transfer Department')
    new_role = fields.Many2one('hr.job', string='New Role')
    new_district = fields.Many2one('hr.district', string='New District')


