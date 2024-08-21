from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import base64
import random
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
import base64
import io
import xlsxwriter

_logger = logging.getLogger(__name__)


class ImportApplicants(models.TransientModel):
    _name = 'hr.import_applicant.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    action_type = fields.Selection(
        [('upload', 'Applicant Upload'), ('download', 'Template Download')],
        string='Action Type',
        default='upload'
    )
    
    def download_template_action(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()


        headers = [
            'SN','Applicant\'s code','Email Address', 'Name', 'Active Email(s)', 'Gender', 'Active Phone', 'Highest Educational Qualification',
            'What is Your Course of Study?', 'Are You a graduate?','NYSC Certificate Number', 'Age','Position Applying for',
            'Have you worked with EEDC?', 'If you worked, how did you leave?', 'What is your currrent state of residence?'
            'If you are selected, which District (s) would you prefer based on proximity? (Select nearest districts to your residence)',
            'Are you APTIS?','What are your Relevant Skills/Competencies?'
        ]
        
        bold_format = workbook.add_format({'bold': True})
        
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold_format)

        workbook.close()
        
        output.seek(0)
        self.data_file = base64.b64encode(output.read())
        self.filename = 'Applicant_Template.xlsx'
        output.close()
        
        return {
        'type': 'ir.actions.act_url',
        'url': 'web/content/?model=hr.import_applicant.wizard&id=%s&field=data_file&filename_field=filename&filename=Applicant_Template.xlsx&download=true' % self.id,
        'target': 'self',
        'data_file': self.data_file,
        'filename': 'Applicant_Template.xlsx',
    }

    def create_job_position(self, name):
        job_position_obj = self.env['hr.job']
        if name:
            position_rec = job_position_obj.search([('name', '=', name.strip())], limit = 1)
            job_position = job_position_obj.create({
                        "name": name.strip()
                    }) if not position_rec else position_rec
            return job_position
        else:
            return None


    def create_contact(self, email, name, phone):
        if email:
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': name,
                    'email': email,
                    'phone': phone
                })
            return partner.id
        else:
            return None

    def import_records_action(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        errors = ['The Following messages occurred']
        employee_obj = self.env['hr.employee']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        
        def find_existing_applicant(email, applicant_code, job):
            applicant_id = False 
            if email:
                if applicant_code:
                    applicant = self.env['hr.applicant'].search([('applicant_code', '=', applicant_code)])
                    if not applicant:
                        applicant = self.env['hr.applicant'].search([
                        ('email_from', '=', email),
                        ('job_id', '=', job.id),
                        ('create_date', '>=', job.datetime_publish),
                        ('create_date', '<=', job.close_date),
                        ('active', '=', True)])
                else:
                    applicant = self.env['hr.applicant'].search([
                        ('email_from', '=', email),
                        ('job_id', '=', job.id),
                        ('create_date', '>=', job.datetime_publish),
                        ('create_date', '<=', job.close_date),
                        ('active', '=', True)])
                if applicant:
                    applicant_id = applicant.id
                else:
                    applicant_id = False 
                return applicant_id
            else:
                return False
        for row in file_data:
            posittion = self.create_job_position(row[11])
            email = row[2] or row[4]
            applicant_code = row[1].strip()
            if find_existing_applicant(email.strip(),applicant_code, posittion):
                unsuccess_records.append(f'Applicant with {str(email)} Already exists')
            else:
                
                full_name = row[3].split() if row[3] else False
                if full_name:
                    _logger.info(f'Full name = {full_name}')
                    partner_name = row[3].strip(),
                    applicant_data = {
                        'applicant_code': applicant_code,
                        'email_from': email,
                        'name': f"Applciation for {row[3]}",
                        'first_name': full_name[2] if len(full_name) > 2 else full_name[1] if len(full_name) > 1 else full_name[0] or None,
                        # maduka chris sopulu, maduka sopulu, maduka, none
                        'middle_name': full_name[1] if len(full_name) == 3 else "",
                        'last_name': full_name[0] if len(full_name) > 0 else "",
                        'partner_phone': row[5],
                        'partner_name': partner_name,
                        'highest_level_of_qualification': row[6],
                        'course_of_study': row[7],
                        'is_graduate': row[8],
                        'nysc_certificate_number': row[9],
                        'age': row[10],
                        'job_id': posittion.id,
                        'worked_at_eedc': row[12].lower() if row[12] in ['yes', 'no'] else False,
                        'describe_work_at_eedc': row[13],
                        'why_do_you_leave': row[14],
                        
                        'presentlocation': row[15],
                        'prefered_district': row[16].strip(),
                        'gender': row[17].lower(),
                        'is_aptis': row[18].strip(),
                        # 'skills': row[19].strip(),
                        'stage_id': self.env.ref('hr_recruitment.stage_job1').id,
                        'partner_id': self.create_contact(email.strip(), partner_name, row[5]),
                    }
                    applicant = self.env['hr.applicant'].sudo().create(applicant_data)
                    _logger.info(f'Applicant data: {applicant} at {row[0]}')
                    count += 1
                    success_records.append(applicant_data.get('name'))
                else:
                    unsuccess_records.append(f'Applicant with {str(row[0])} Does not have a name')
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def confirm_notification(self,popup_message):
        view = self.env.ref('hr_cbt_portal_recruitment.hr_import_applicants_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'hr.import_applicant.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }


class MigrationDialogModel(models.TransientModel):
    _name="hr.import_applicant.confirm.dialog"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)
