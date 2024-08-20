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
            'Email', 'Full Name', 'Phone', 'Gender',
            'NYSC Completed (Yes/No)', 'NYSC Certificate Link',
            'Professional Certification (Yes/No)', 'Certification Link',
            'Job Position'
        ]
        
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

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
            position_rec = job_position_obj.search([('name', '=', name.strip().title())], limit = 1)
            job_position = job_position_obj.create({
                        "name": name.strip().title()
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
        
        def find_existing_applicant(email,job):
            applicant_id = False 
            if email: 
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
            posittion = self.create_job_position(row[8])
            if find_existing_applicant(row[1].strip(), posittion):
                unsuccess_records.append(f'Applicant with {str(row[1])} Already exists')
            else:
                full_name = row[1].split()
                _logger.info(f'Full name = {full_name}')
                applicant_data = {
                    'name': row[1],
                    'first_name': full_name[1] if len(full_name) > 1 else None,
                    'middle_name': full_name[2] if len(full_name) == 3 else None,
                    'last_name': full_name[0],
                    'email_from': row[0],
                    'partner_phone': row[2],
                    'gender': row[3].lower(),
                    'has_completed_nysc': 'Yes' if row[4].lower() == 'yes' else 'No',
                    'nysc_certificate_link': row[5],
                    'has_professional_certification': 'Yes' if row[6].lower() == 'yes' else 'No',
                    'professional_certificate_link': row[7],
                    'job_id': posittion.id,
                    'stage_id': self.env.ref('hr_recruitment.stage_job1').id
                    # 'partner_id': self.create_contact(row[0].strip(), row[1], row[2])
                }
                applicant = self.env['hr.applicant'].sudo().create(applicant_data)
                _logger.info(f'Applicant data: {applicant}')
                count += 1
                success_records.append(applicant_data.get('name'))
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
    
    # def download_template_action(self):
    # # Create a simple Excel template
    #     import io
    #     import xlsxwriter

    #     output = io.BytesIO()
    #     workbook = xlsxwriter.Workbook(output)
    #     worksheet = workbook.add_worksheet()

    #     # Add headers for the template
    #     headers = [
    #         'Email', 'Full Name', 'Phone', 'Gender',
    #         'NYSC Completed (Yes/No)', 'NYSC Certificate Link',
    #         'Professional Certification (Yes/No)', 'Certification Link',
    #         'Job Position'
    #     ]
    #     for col_num, header in enumerate(headers):
    #         worksheet.write(0, col_num, header)

    #     workbook.close()

    #     # Encode the output to Base64 and return as an attachment
    #     output.seek(0)
    #     template_data = base64.b64encode(output.read())
    #     output.close()

    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': 'web/content/?model=hr.import_applicant.wizard&id=%s&field=data_file&filename_field=filename&filename=Applicant_Template.xlsx&download=true' % self.id,
    #         'target': 'self',
    #         'data_file': template_data,
    #         'filename': 'Applicant_Template.xlsx',
    #     }



class MigrationDialogModel(models.TransientModel):
    _name="hr.import_applicant.confirm.dialog"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)
