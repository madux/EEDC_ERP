
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

_logger = logging.getLogger(__name__)


class ImportRecords(models.TransientModel):
    _name = 'hr.import_record.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection([
            ('employee', 'Employee'),
            ('update', 'Update'),
            ('email', 'Email Update'),
        ],
        string='Import Type', required=True, index=True,
        copy=True, default='',
        track_visibility='onchange'
    )
 
    # def excel_reader(self, index=0):
    #     if self.data_file:
    #         file_datas = base64.decodestring(self.data_file)
    #         workbook = xlrd.open_workbook(file_contents=file_datas)
    #         sheet = workbook.sheet_by_index(index)
    #         data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
    #         data.pop(0)
    #         file_data = data
    #         return file_data
    #     else:
    #         raise ValidationError('Please select file and type of file')
    
    def create_department(self, name):
        department_obj = self.env['hr.department']
        if name:
            depart_rec = department_obj.search([('name', '=', name.strip())], limit = 1)
            department_id = department_obj.create({
                        "name": name
                    }).id if not depart_rec else depart_rec.id
            return department_id
        else:
            return None

    def get_level_id(self, name):
        if not name:
            return False
        levelId = self.env['hr.level'].search([('name', '=', name)], limit=1)
        return levelId.id if levelId else self.env['hr.level'].create({'name': name}).id
    
    def get_district_id(self, name):
        if not name:
            return False
        rec = self.env['hr.district'].search([('name', '=', name)], limit=1)
        return rec.id if rec else self.env['hr.district'].create({'name': name}).id
    
    def get_region_id(self, name):
        if not name:
            return False 
        rec = self.env['hr.region'].search([('name', '=', name)], limit=1)
        return rec.id if rec else self.env['hr.region'].create({'name': name}).id

    def get_grade_id(self, name):
        if not name:
            return False
        gradeId = self.env['hr.grade'].search([('name', '=', name)], limit=1)
        return gradeId.id if gradeId else self.env['hr.grade'].create({'name': name}).id
    
    def get_designation_id(self, name, departmentid):
        if not name:
            return False
        designationId = self.env['hr.job'].search([('name', '=', name), ('department_id', '=', departmentid)], limit=1)
        return designationId.id if designationId else self.env['hr.job'].create({'name': name, 'department_id': departmentid}).id

    def get_unit_id(self, name):
        if not name:
            return False
        rec = self.env['hr.unit'].search([('name', '=', name)], limit=1)
        return rec.id if rec else self.env['hr.unit'].create({'name': name}).id

    def get_sub_unit_id(self, name):
        if not name:
            return False
        rec = self.env['hr.work.unit'].search([('name', '=', name)], limit=1)
        return rec.id if rec else self.env['hr.work.unit'].create({'name': name}).id

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
        
        def find_existing_employee(code):
            employee_id = False 
            if code:
                code = str(int(code)) if type(code) == float else code 
                employee = self.env['hr.employee'].search([
                    '|', ('employee_number', '=', code), 
                    ('barcode', '=', code)], limit = 1)
                if employee:
                    employee_id = employee.id
                else:
                    employee_id = False 
            return employee_id
        
        # reviewer_group = self.env.ref("hr_pms.group_pms_reviewer")
        # officer_group = self.env.ref("hr_pms.group_pms_officer_id")
        # supervisor_group = self.env.ref("hr_pms.group_pms_supervisor")
        # manager_group = self.env.ref("hr_pms.group_pms_manager_id")
        def generate_emp_appraiser(employee, appraiser_code, type):
            appraiser = self.env['hr.employee'].search(['|', 
            ('employee_number', '=', appraiser_code), 
            ('barcode', '=', appraiser_code)
            ], limit = 1)
            emp_group = self.env.ref("hr_pms.group_pms_user_id")
            reviewer_group = self.env.ref("hr_pms.group_pms_reviewer")
            supervisor_group = self.env.ref("hr_pms.group_pms_supervisor")
            if appraiser and employee:
                if type == "ar":
                    employee.sudo().write({
                        'administrative_supervisor_id': appraiser.id
                        })
                    # raise ValidationError("this is the AR ======>{} and {} with".format(appraiser.name, employee.name, employee.administrative_supervisor_id.name))
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id])]
                    appraiser.user_id.sudo().write({'groups_id':group_list})
                if type == "fr":
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id])]
                    employee.sudo().write({
                        'parent_id': appraiser.id
                    })
                    appraiser.user_id.sudo().write({'groups_id':group_list})

                if type == "rr":
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id, reviewer_group.id])]
                    # employee.reviewer_id = appraiser.id
                    employee.sudo().update({
                        'reviewer_id': appraiser.id
                    })
                    appraiser.user_id.sudo().write({'groups_id':group_list})

        def reset_employee_user_password(employee_id, user_id):
            if user_id:
                change_password_wiz = self.env['change.password.wizard'].sudo()
                change_password_user = self.env['change.password.user'].sudo()
                new_password = password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
                change_password_wiz_id = change_password_wiz.create({
                    'user_ids': [(0, 0, {
                        'user_login': user_id.login, 
                        'new_passwd': new_password,
                        'user_id': user_id.id,
                        })]
                })
                change_password_wiz_id.user_ids[0].change_password_button()
                employee_id.migrated_password = new_password

        def create_employee(vals):
            employee_id = self.env['hr.employee'].sudo().create({
                        'name': vals.get('fullname'),
                        'employee_number': vals.get('staff_number'),
                        # 'employee_identification_code': vals.get('staff_number'),
                        'ps_district_id': vals.get('district'),
                        'gender': vals.get('gender'),
                        'department_id': vals.get('department_id'),
                        'unit_id': vals.get('unit_id'),
                        'work_unit_id': vals.get('sub_unit_id'),
                        'employment_date': vals.get('employment_date'),
                        'grade_id': vals.get('grade_id'),
                        'level_id': vals.get('level_id'),
                        'hr_region_id': vals.get('hr_region_id'),
                        # 'administrative_supervisor_id': vals.get('administrative_supervisor_id'),
                        # 'parent_id': vals.get('functional_appraiser_id'),
                        # 'reviewer_id': vals.get('functional_reviewer_id'),
                        'work_email': vals.get('email'),
                        'private_email': vals.get('private_email'),
                        'work_phone': vals.get('work_phone'),
                        'mobile_phone': vals.get('work_phone'),
                        'phone': vals.get('phone'),
                        'job_id': vals.get('job_id'),
                        # 'emergency_phone': vals.get('emergency_phone'),
                    })
            vals.update({'employment_date': employee_id.employment_date})
            user, password = generate_user(vals)
            employee_id.sudo().update({
                        'user_id': user.id if user else False,
                        'work_email': employee_id.work_email,
                        # 'migrated_password': password,
            }) 
            reset_employee_user_password(employee_id, user)

        def generate_user(
                vals,
                ):
            emp_group = self.env.ref("hr_pms.group_pms_user_id")
            Group = self.env['res.groups'].sudo()
            group_list = [(4, emp_group.id)]
            ## Removing Contact Creation and Employee group from Org. relateduser.
            groups_to_remove = Group.search(
                ['|','|',
                 ('name', '=', 'Contact Creation'),
                 ('name','=','Portal'),
                 ('id', 'in', [
                self.env.ref('hr_attendance.group_hr_attendance_manager').id,
                self.env.ref('hr_attendance.group_hr_attendance_user').id,
                self.env.ref('hr.group_hr_manager').id,
                self.env.ref('hr.group_hr_user').id,]),
                 ])
            for group in groups_to_remove:
                tup = (3,group.id)
                group_list.append(tup)
            email = vals.get('email') or vals.get('private_email')
            fullname = vals.get('fullname')
            user, password = False, False
            login = email if email and email.endswith('@enugudisco.com') else vals.get('staff_number') 

            if login:
                _logger.info('LOGGING FOUND')
                # empdate = datetime.strftime(vals.get('employment_date'), '%d-%m-Y')
                # employement_date = empdate.split('-') 
                # emp_day, emp_month = employement_date[0], employement_date[1]
                password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
                # password = "{}{}{}".format(vals.get('staff_number'),emp_day,emp_month)
                # _logger.info("DATE DATA IS {}  AND PASSWORD IS {}".format(employement_date, password))
                
                # ''.join(random.choice('eedcpasswodforxyzusers1234567') for _ in range(10))
                # '{}-{}'.format(fullname[:2].upper(), str(uuid.uuid4())[:8]), # MA-2132ERER
                user_vals = {
				'name' : fullname,
				'login' : login,
				'password': password,
                }
                _logger.info(f"Creating employee Rep User..with password {password} and {user_vals.get('password')}.")
                User = self.env['res.users'].sudo()
                user = User.search([('login', '=', login)],limit=1)
                if user:
                    _logger.info("User already exists...")
                    password = False
                else:
                    user = User.create(user_vals)
                    _logger.info("Creating User record...")
                _logger.info('Adding user to group ...')
                user.sudo().write({'groups_id':group_list})
                return user, user_vals.get('password')
            return user, password
        
        if self.import_type == "employee":
            for row in file_data:
                # try:
                if find_existing_employee(row[1]):
                    unsuccess_records.append(f'Employee with {str(row[1])} Already exists')
                else:
                    static_emp_date = '01/01/2014'
                    emp_date = datetime.strptime(static_emp_date, '%d/%m/%Y')
                    appt_date = None

                    if row[14]:
                        if type(row[14]) in [int, float]:
                            appt_date = datetime(*xlrd.xldate_as_tuple(row[14], 0)) 
                        elif type(row[14]) in [str]:
                            if '-' in row[14]:
                                # pref = str(row[14]).strip()[0:7] # 12-Jul-
                                # suff = '20'+ row[14].strip()[-2:] # 2022
                                datesplit = row[14].split('-') # eg. 09, jul, 22
                                d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                appt_date = f"{d}-{m}-20{y}"
                                appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                            elif '-' in row[14]:
                                datesplit = row[14].split('/') # eg. 09, jul, 22
                                d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                appt_date = f"{d}-{m}-20{y}"
                                appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                            else:
                                appt_date = datetime(*xlrd.xldate_as_tuple(float(row[14]), 0)) #eg 4554545

                    dt = appt_date or emp_date
                    departmentid = self.create_department(row[11])
                    vals = dict(
                        serial = row[0],
                        staff_number = str(int(row[1])) if type(row[1]) in [int, float] else row[1],
                        fullname = row[2].capitalize(),
                        level_id = self.get_level_id(row[3].strip()),
                        district = self.get_district_id(row[9].strip()),
                        gender = 'male' if row[10] in ['m', 'M'] else 'female' if row[10] in ['f', 'F'] else 'other',
                        department_id = departmentid,
                        unit_id = self.get_unit_id(row[12].strip()),
                        sub_unit_id = self.get_sub_unit_id(row[13].strip()),
                        employment_date = dt,# datetime.strptime(appt_date, '%m-%b-%Y') if row[14].strip() else False,
                        # employment_date = datetime.strptime(row[14], '%m/%d/%Y') if row[14] else False,
                        grade_id = self.get_grade_id(row[15].strip()),
                        job_id = self.get_designation_id(row[16], departmentid),
                        functional_appraiser_id = find_existing_employee(row[18]),
                        administrative_supervisor_name = row[19],
                        administrative_supervisor_id = find_existing_employee(str(row[20])),
                        functional_reviewer_id = find_existing_employee(str(row[22])),
                        email = row[24].strip(),
                        private_email = row[24].strip(), 
                        work_phone = '0' + str(int(row[25])) if row[25] and type(row[25]) in [float] else row[25] if row[25] else False,
                        phone = '0' + str(int(row[25])) if row[25] and type(row[25]) in [float] else row[25] if row[25] else False,
                        hr_region_id = self.get_region_id(row[26]),
                        )
                    create_employee(vals)
                    count += 1
                    success_records.append(vals.get('fullname'))
                # except Exception as e:
                #     raise ValidationError(f"Issue at Line {row[0]}: Error message {e}")
                
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
            errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

        elif self.import_type == "update":
            for row in file_data:
                ########################### This is for update purposes:
                employee_code = str(int(row[1])) if type(row[1]) == float else row[1]
                static_emp_date = '01/01/2014'
                emp_date = datetime.strptime(static_emp_date, '%d/%m/%Y')
                appt_date = None
                if row[14]:
                    if type(row[14]) in [int, float]:
                        appt_date = datetime(*xlrd.xldate_as_tuple(row[14], 0)) 
                    elif type(row[14]) in [str]:
                        if '-' in row[14]:
                            datesplit = row[14].split('-') # eg. 09, jul, 22
                            d, m, y = datesplit[0], datesplit[1], datesplit[2]
                            appt_date = f"{d}-{m}-20{y}"
                            appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                        elif '-' in row[14]:
                            datesplit = row[14].split('/') # eg. 09, jul, 22
                            d, m, y = datesplit[0], datesplit[1], datesplit[2]
                            appt_date = f"{d}-{m}-20{y}"
                            appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                        else:
                            appt_date = datetime(*xlrd.xldate_as_tuple(float(row[14]), 0)) #eg 4554545
                dt = appt_date or emp_date
                departmentid = self.create_department(row[11])
                employee_vals = dict(
                    employee_number = str(int(row[1])),
                    # employee_identification_code = employee_code,
                    name = row[2].capitalize(),
                    level_id = self.get_level_id(row[3].strip()),
                    ps_district_id = self.get_district_id(row[9].strip()),
                    gender = 'male' if row[10] in ['m', 'M'] else 'female' if row[10] in ['f', 'F'] else 'other',
                    department_id = departmentid,
                    unit_id = self.get_unit_id(row[12].strip()),
                    work_unit_id = self.get_sub_unit_id(row[13].strip()),
                    employment_date = dt,
                    # employment_date = datetime.strptime(row[14], '%m/%d/%Y') if row[14] else False,
                    grade_id = self.get_grade_id(row[15].strip()),
                    job_id = self.get_designation_id(row[16], departmentid), 
                    work_email = row[24].strip(),
                    private_email = row[24].strip(),
                    work_phone = '0' + str(int(row[25])) if row[25] and type(row[25]) in [float] else row[25] if row[25] else False,
                    phone = '0' + str(int(row[25])) if row[25] and type(row[25]) in [float] else row[25] if row[25] else False,
                    hr_region_id = self.get_region_id(26),
                    )
                # ######################################
                # THIS IS TO UPDATE THE EMPLOYEE DEPARTMENTAL MANAGER AND APPRAISERS 
                aa, fa, rr = row[20],row[18],row[22]
                vals = dict(
                    staff_number = employee_code,
                    functional_appraiser_id = fa,
                    administrative_supervisor_id = aa,
                    functional_reviewer_id = rr, 
                    private_email = employee_vals.get('private_email'),
                    email = employee_vals.get('work_email'),
                    fullname = employee_vals.get('name'),
                    )
                    ## if fa, add, fr get the employee id, add the 
                    ## attributes to employee, also update the f employee user
                    ## group with the groups
                employee_id = self.env['hr.employee'].search([
                '|', ('employee_number', '=', employee_code), 
                ('barcode', '=', employee_code)], limit = 1)
                if employee_id:
                    # employee_id.job_id.sudo().write({
                    #     'department_id': employee_id.department_id.id
                    # })
                    if aa:
                        administrative_supervisor_id = str(int(vals.get('administrative_supervisor_id'))) \
                        if type(aa) == float else aa
                        generate_emp_appraiser(
                            employee_id, 
                            administrative_supervisor_id, 
                            'ar', 
                            )
                    if fa:
                        functional_appraiser_id = str(int(vals.get('functional_appraiser_id'))) \
                        if type(fa) == float else fa
                        generate_emp_appraiser(
                            employee_id, 
                            functional_appraiser_id, 
                            'fr', 
                            )
                    if rr:
                        functional_reviewer_id = str(int(vals.get('functional_reviewer_id'))) \
                        if type(row[22]) == float else row[22]
                        generate_emp_appraiser(
                            employee_id, 
                            functional_reviewer_id,
                            'rr', 
                            )
                    employee_id.sudo().update(employee_vals)
                    if not employee_id.user_id:
                        # employee_vals['fullname'] = employee_vals.get('name')
                        user, password = generate_user(vals)
                        employee_id.sudo().write({
                            'user_id': user.id if user else False,
                        })
                        if password:
                            employee_id.sudo().write({
                                'migrated_password': password
                            })
                            
                    _logger.info(f'Updating records for {employee_id.employee_number} at line {row[0]}')
                    count += 1
                else:
                    unsuccess_records.append(employee_code)
            errors.append('Successful Update(s): ' +str(count))
            errors.append('Unsuccessful Update(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 
        elif self.import_type == "email":
            for row in file_data:
                if row[0] and row[3]:
                    staff_number = row[0].strip()
                    email = row[3].strip()
                    employee_id = self.env['hr.employee'].search([
                    '|', ('employee_number', '=', staff_number), 
                    ('barcode', '=', staff_number)], limit = 1)
                    if employee_id:
                        employee_id.sudo().write({
                            'work_email': email
                        })
                        count += 1
                else:
                    unsuccess_records.append(row[0])
            errors.append('Successful Update(s): ' +str(count))
            errors.append('Unsuccessful Update(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

    def confirm_notification(self,popup_message):
        view = self.env.ref('migration_app.hr_migration_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'hr.migration.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }


class MigrationDialogModel(models.TransientModel):
    _name="hr.migration.confirm.dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)

 