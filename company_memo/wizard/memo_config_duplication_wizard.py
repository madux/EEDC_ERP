from odoo import models, fields, api
from odoo import Command
from odoo.exceptions import ValidationError

class MemoConfigDuplicationWizard(models.TransientModel):
    _name = 'memo.config.duplication.wizard'

    dept_ids = fields.Many2many('hr.department', string="Departments", required='1')
    dummy_memo_stage_ids = fields.Many2many('dummy.memo.stage', 'duplication_wizard_id')
    

    @api.model
    def default_get(self, fields):
        res = super(MemoConfigDuplicationWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            dummy_memo_stage_ids = []
            for stage in memo_config.stage_ids:
                dummy_memo_stage = self.env['dummy.memo.stage'].create({
                    'name': stage.name,
                    'sequence': stage.sequence,
                    'active': stage.active,
                    'approver_ids': stage.approver_ids,
                    'is_approved_stage': stage.is_approved_stage,
                })
                dummy_memo_stage_ids.append(dummy_memo_stage.id)
            res.update({'dummy_memo_stage_ids': [(6, 0, dummy_memo_stage_ids)]})
        return res





            
    def duplicate_memo_config(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            for dept in self.dept_ids:
                stage_ids = []
                new_config = self.env['memo.config'].create({
                'department_id': dept.id,
                'memo_type': memo_config.memo_type.id,
                'approver_ids': [(6, 0, memo_config.approver_ids.ids)],
                })
                if self.dummy_memo_stage_ids:
                    for sequence, stage in enumerate(self.dummy_memo_stage_ids, 900): 
                        new_stage = self.env['memo.stage'].create({
                            'name': stage.name,
                            'sequence': sequence,
                            'active': True,
                            'loaded_from_data': True,
                            'approver_ids': [(6, 0, stage.approver_ids.ids)],
                            'is_approved_stage': stage.is_approved_stage,
                            'memo_config_id': new_config.id,
                        })
                        stage_ids.append(new_stage.id)
                    new_config.update({'stage_ids': stage_ids})
            # return {
            #     'name': 'New Memo Config',
            #     'view_mode': 'form',
            #     'res_id': new_config.id, 
            #     'res_model': 'memo.config',
            #     'view_type': 'form',
            #     'type': 'ir.actions.act_window',
            #     'target': 'current',
            # }






class DummyMemoStage(models.TransientModel):
    _name = 'dummy.memo.stage'

    duplication_wizard_id = fields.Many2one('memo.config.duplication.wizard', string='Duplication Wizard')
    memo_stage_id = fields.Many2one('memo.stage')
    name = fields.Char(string="Stage Name")
    sequence = fields.Integer(string="Sequence")
    active = fields.Boolean(string="Active")
    approver_ids = fields.Many2many('hr.employee', 'employee_wizard_rel', 'employee_id', 'employee_wizard_id', string="Approvers")
    is_approved_stage = fields.Boolean(string="Is Approved Stage")



