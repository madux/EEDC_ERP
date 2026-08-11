from odoo import api, fields, models
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = "res.users"

    def create_user_employees(self):
        users = self.env.context.get('active_ids', [])
        employee = self.env['hr.employee'].sudo()
        created = []
        not_created = []
        for rec in users:
            try:
                user = self.env['res.users'].sudo().browse([rec])
                user.write({
                    'email': user.email.replace(' ', '').replace(',', '').lower() if user.email else '',
                    'login': user.login.replace(' ', '').replace(',', '').lower() if user.login else ''
                    })
                employee_id = employee.search([('user_id', '=', user.id)])#, ['id', 'name'])
                if employee_id:
                    employee_id.update({'work_email': user.email})
                else:
                    employee.create({
                        'name': user.name, 
                        'work_email': user.email, 
                        'user_id': user.id
                    })
                    created.append("user created -- %s:" % (user.name))
            except Exception as e:
                not_created.append("Not created %s-- %s:" % (user.name, e))

        logs = created + not_created
        result_log = "\n".join(logs)
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.bulk.import.wizard",
            # "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": {'default_result_log': result_log},
        }

        