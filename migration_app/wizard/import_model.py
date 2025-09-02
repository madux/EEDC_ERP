
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
    
    def format_phone(self, phone_value):
        """Format phone number properly"""
        if not phone_value:
            return False
        if type(phone_value) in [float, int]:
            return '0' + str(int(phone_value))
        return str(phone_value).strip()

    def safe_get_column(self, row, index, default=None):
        """Safely get column value with bounds checking"""
        try:
            return row[index] if len(row) > index and row[index] else default
        except (IndexError, TypeError):
            return default

    def validate_excel_structure(self, file_data):
        """Validate that the Excel has the expected structure"""
        if not file_data:
            raise ValidationError("Excel file is empty")
        
        expected_columns = 27
        first_row = file_data[0] if file_data else []
        
        if len(first_row) < 26:
            raise ValidationError(f"Excel file should have at least 26 columns, found {len(first_row)}")
        
        return True

    def get_company_and_district_id(self, district_name, company_name):
        """Get company and district ID, with predefined mappings and ilike search"""
        
        company_district_mappings = {
            'FIRST POWER': 'multi_company.branch0019',
            'TRANSPOWER': 'multi_company.branch0015', 
            'NEW ERA': 'multi_company.branch009',
            'MAINPOWER': 'multi_company.branch0002',
            'EAST LAND': 'multi_company.branch003',
            'HOLDCO': 'multi_company.branch001',
        }
        
        default_company = self.env.ref('multi_company.company_enugu_edp', raise_if_not_found=False)
        default_district = self.env.ref('multi_company.branch001', raise_if_not_found=False)  # CHQ
        
        company_id = None
        district_id = None
        
        if company_name:
            company_name = str(company_name).strip()
            Company = self.env['res.company']
            company_rec = Company.search([('name', 'ilike', company_name)], limit=1)
            if company_rec:
                company_id = company_rec.id
            else:
                company_id = default_company.id if default_company else False
        else:
            company_id = default_company.id if default_company else False
        
        if district_name:
            district_name = str(district_name).strip()
            District = self.env['multi.branch']
            district_rec = District.search([('name', 'ilike', district_name)], limit=1)
            if district_rec:
                district_id = district_rec.id
            else:
                if company_name:
                    for comp_key, district_ref in company_district_mappings.items():
                        if comp_key.upper() in company_name.upper():
                            mapped_district = self.env.ref(district_ref, raise_if_not_found=False)
                            district_id = mapped_district.id if mapped_district else None
                            break
                
                if not district_id and company_id == (default_company.id if default_company else False):
                    district_id = default_district.id if default_district else None
        else:
            district_id = default_district.id if default_district else None
            
        return company_id, district_id
    
    def get_hr_district_id(self, name):
        """Searches for a district in the hr.district model and creates it if not found."""
        if not name:
            return False
        
        District = self.env['hr.district']
        district_name = str(name).strip()
        district_rec = District.search([('name', 'ilike', district_name)], limit=1)
        
        if district_rec:
            return district_rec.id
        else:
            _logger.info(f"Creating new HR District: {district_name}")
            new_district = District.create({'name': district_name})
            return new_district.id
    
    def create_department(self, name, company_id=None):
        """Create department with company context - Fixed multi-company access"""
        department_obj = self.env['hr.department']
        if name:
            name = str(name).strip()
            
            if not company_id:
                default_company = self.env.ref('multi_company.company_enugu_edp', raise_if_not_found=False)
                company_id = default_company.id if default_company else self.env.company.id
            
            domain = [('name', '=', name), ('company_id', '=', company_id)]
            depart_rec = department_obj.search(domain, limit=1)
            
            if depart_rec:
                return depart_rec.id
            else:
                try:
                    # Switch to the target company context before creating
                    dept_vals = {'name': name, 'company_id': company_id}
                    department_id = department_obj.with_company(company_id).sudo().create(dept_vals).id
                    return department_id
                except Exception as e:
                    _logger.error(f"Failed to create department {name}: {str(e)}")
                    # Try to find existing department without company constraint as fallback
                    fallback_dept = department_obj.search([('name', '=', name)], limit=1)
                    if fallback_dept:
                        _logger.info(f"Using existing department {name} from different company")
                        return fallback_dept.id
                    return None
        else:
            return None
        

    def get_level_id(self, name):
        if not name:
            return False
        levelId = self.env['hr.level'].search([('name', '=', name)], limit=1)
        return levelId.id if levelId else self.env['hr.level'].create({'name': name}).id
    
    def get_district_id(self, name):
        """Searches for a district by name and creates it if not found."""
        if not name:
            return False
        
        District = self.env['multi.branch']
        district_rec = District.search([('name', '=', name.strip())], limit=1)
        if district_rec:
            return district_rec.id
        else:
            new_district = District.create({'name': name.strip()})
            return new_district.id
    
    
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
    
    def get_designation_id(self, name, departmentid, company_id=None):
        """Get job/designation with company context - Fixed multi-company access"""
        if not name:
            return False
            
        if not company_id:
            default_company = self.env.ref('multi_company.company_enugu_edp', raise_if_not_found=False)
            company_id = default_company.id if default_company else self.env.company.id
        
        domain = [('name', '=', name), ('company_id', '=', company_id)]
        if departmentid:
            domain.append(('department_id', '=', departmentid))
            
        designationId = self.env['hr.job'].search(domain, limit=1)
        
        if designationId:
            return designationId.id
        else:
            try:
                job_vals = {'name': name, 'company_id': company_id}
                if departmentid:
                    job_vals['department_id'] = departmentid
                return self.env['hr.job'].with_company(company_id).sudo().create(job_vals).id
            except Exception as e:
                _logger.error(f"Failed to create job {name}: {str(e)}")
                fallback_job = self.env['hr.job'].search([('name', '=', name)], limit=1)
                if fallback_job:
                    _logger.info(f"Using existing job {name} from different company")
                    return fallback_job.id
                return None

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
    
    def get_company_id(self, name):
        if not name:
            return False
        rec = self.env['res.company'].search([('name', '=', name)], limit=1)
        return rec.id if rec else False
    
    def ensure_user_has_company(self, user, company_id):
        """Ensure `user` has company_id in company_ids, and set company_id after that.
           Always add to company_ids before writing company_id to avoid 'not allowed companies' error.
        """
        if not user or not company_id:
            return
        try:
            if company_id not in user.company_ids.ids:
                user.sudo().write({'company_ids': [(4, company_id)]})
            user.sudo().write({'company_id': company_id})
        except Exception as e:
            _logger.error(f"Failed to ensure company {company_id} on user {user.id}: {e}")

    def import_records_action(self):
        if self.data_file:
            file_datas = base64.b64decode(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
            
            self.validate_excel_structure(file_data)
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
                # Ensure code is a string for the search
                code = str(int(code)) if isinstance(code, float) else str(code)
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
                    'branch_id': vals.get('branch_id'),
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
                    'company_id': vals.get('company_id'),
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

        def generate_user(vals):
            """Generate portal user by default, don't downgrade existing users.
               Ensures allowed companies are updated so writing company_id won't fail.
            """
            portal_group = self.env.ref("base.group_portal", raise_if_not_found=False)
            emp_group = self.env.ref("hr_pms.group_pms_user_id", raise_if_not_found=False)
            Group = self.env['res.groups'].sudo()

            group_list = [(4, portal_group.id)] if portal_group else []
            if emp_group:
                group_list.append((4, emp_group.id))

            groups_to_remove = Group.search(
                ['|','|',
                 ('name', '=', 'Contact Creation'),
                 ('name','=','Portal'),
                 ('id', 'in', [
                    self.env.ref('hr.group_hr_manager').id,
                    self.env.ref('hr.group_hr_user').id,
                 ])]
            )
            for group in groups_to_remove:
                tup = (3, group.id)
                group_list.append(tup)

            email = vals.get('email') or vals.get('private_email')
            fullname = vals.get('fullname')
            branch_id = vals.get('branch_id')
            company_id = vals.get('company_id')
            user, password = False, False
            login = email if email and email.endswith('@enugudisco.com') else vals.get('staff_number')

            if login:
                password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
                user_vals = {
                    'name': fullname,
                    'login': login,
                    # do NOT force company_id here until company_ids is set (below we handle correctly)
                    'branch_id': branch_id,
                }
                _logger.info(f"Creating/Getting employee Portal User..with password {password}.")

                User = self.env['res.users'].sudo()
                user = User.search([('login', '=', login)], limit=1)
                if user:
                    _logger.info("User already exists... keeping existing user type")
                    if company_id:
                        try:
                            self.ensure_user_has_company(user, company_id)
                        except Exception:
                            _logger.exception("Failed to add company to existing user")
                    password = False
                else:
                    if company_id:
                        user_vals['company_ids'] = [(6, 0, [company_id])]
                        user_vals['company_id'] = company_id
                    user = User.create(user_vals)
                    _logger.info("Created Portal User record...")
                    try:
                        user.sudo().write({'groups_id': group_list})
                    except Exception:
                        _logger.exception("Failed to assign groups to new user")
                return user, password
            return user, password
        
        if self.import_type == "employee":
            for row in file_data:
                try:
                    with self.env.cr.savepoint():
                        if find_existing_employee(row[1]):
                            unsuccess_records.append(f'Employee with {str(row[1])} Already exists')
                            continue
                        
                        static_emp_date = '01/01/2014'
                        emp_date = datetime.strptime(static_emp_date, '%d/%m/%Y')
                        appt_date = None

                        if row[14]:
                            if type(row[14]) in [int, float]:
                                appt_date = datetime(*xlrd.xldate_as_tuple(row[14], 0)) 
                            elif type(row[14]) in [str]:
                                if '-' in row[14]:
                                    datesplit = row[14].split('-') 
                                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                    if len(y) == 2:
                                        y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                    appt_date = f"{d}-{m}-{y}"
                                    appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                                elif '/' in row[14]:
                                    datesplit = row[14].split('/') 
                                    d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                    if len(y) == 2:
                                        y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                    appt_date = f"{d}/{m}/{y}"
                                    appt_date = datetime.strptime(appt_date, '%d/%m/%Y') 
                                else:
                                    appt_date = datetime(*xlrd.xldate_as_tuple(float(row[14]), 0))

                        dt = appt_date or emp_date
                        
                        company_id, branch_id = self.get_company_and_district_id(
                            row[9] if len(row) > 9 else None,
                            row[26] if len(row) > 26 else None
                        )
                        
                        hr_district_name = row[9] if len(row) > 9 else None
                        hr_district_id = self.get_hr_district_id(hr_district_name)
                        
                        departmentid = self.create_department(row[11], company_id) if row[11] else None
                        
                        vals = dict(
                            serial = row[0],
                            staff_number = str(int(row[1])) if type(row[1]) in [int, float] else row[1],
                            fullname = row[2].capitalize(),
                            level_id = self.get_level_id(row[3].strip()) if row[3] else None,
                            district = hr_district_id,
                            branch_id = branch_id,
                            gender = 'male' if row[10] in ['m', 'M'] else 'female' if row[10] in ['f', 'F'] else 'other',
                            department_id = departmentid,
                            unit_id = self.get_unit_id(row[12].strip()) if row[12] else None,
                            sub_unit_id = self.get_sub_unit_id(row[13].strip()) if row[13] else None,
                            employment_date = dt,
                            grade_id = self.get_grade_id(row[15].strip()) if row[15] else None,
                            job_id = self.get_designation_id(row[16], departmentid, company_id) if row[16] else None,
                            functional_appraiser_id = find_existing_employee(row[18]) if len(row) > 18 and row[18] else None,
                            administrative_supervisor_name = row[19] if len(row) > 19 and row[19] else None,
                            administrative_supervisor_id = find_existing_employee(str(row[20])) if len(row) > 20 and row[20] else None,
                            functional_reviewer_id = find_existing_employee(str(row[22])) if len(row) > 22 and row[22] else None,
                            email = row[24].strip() if len(row) > 24 and row[24] else None,
                            private_email = row[24].strip() if len(row) > 24 and row[24] else None, 
                            work_phone = self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                            phone = self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                            company_id = company_id,
                            # hr_region_id = self.get_region_id(row[XX]) if len(row) > XX and row[XX] else None,
                        )
                        create_employee(vals)
                        count += 1
                        success_records.append(vals.get('fullname'))
                
                # This outer 'except' will catch any error from inside the savepoint
                # or the find_existing_employee check before it. The transaction
                # for the next iteration of the loop will be clean.
                except Exception as e:
                    error_msg = f"Row {row[0]}: Error importing {row[2] if len(row) > 2 else 'Unknown'} - {str(e)}"
                    _logger.error(error_msg)
                    unsuccess_records.append(error_msg)
                    continue
                # except Exception as e:
                #     raise ValidationError(f"Issue at Line {row[0]}: Error message {e}")
                
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
            errors.append('Unsuccessful Import(s): '+str(len(unsuccess_records))+' Record(s)')
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
                            datesplit = row[14].split('-')
                            d, m, y = datesplit[0], datesplit[1], datesplit[2]
                            if len(y) == 2:
                                y = f"20{y}" if int(y) <= 50 else f"19{y}"
                            appt_date = f"{d}-{m}-{y}"
                            appt_date = datetime.strptime(appt_date, '%d-%b-%Y') 
                        elif '/' in row[14]:
                            datesplit = row[14].split('/')
                            d, m, y = datesplit[0], datesplit[1], datesplit[2]
                            if len(y) == 2:
                                y = f"20{y}" if int(y) <= 50 else f"19{y}"
                            appt_date = f"{d}/{m}/{y}"
                            appt_date = datetime.strptime(appt_date, '%d/%m/%Y') 
                        else:
                            appt_date = datetime(*xlrd.xldate_as_tuple(float(row[14]), 0)) #eg 4554545
                
                dt = appt_date or emp_date
                
                # Get company and district
                company_id, district_id = self.get_company_and_district_id(
                    row[9] if len(row) > 9 else None,  # district name
                    row[26] if len(row) > 26 else None  # company name
                )
                
                departmentid = self.create_department(row[11], company_id) if row[11] else None
                
                employee_vals = dict(
                    employee_number = str(int(row[1])),
                    # employee_identification_code = employee_code,
                    name = row[2].capitalize(),
                    level_id = self.get_level_id(row[3].strip()) if row[3] else None,
                    ps_district_id = district_id,
                    gender = 'male' if row[10] in ['m', 'M'] else 'female' if row[10] in ['f', 'F'] else 'other',
                    department_id = departmentid,
                    unit_id = self.get_unit_id(row[12].strip()) if row[12] else None,
                    work_unit_id = self.get_sub_unit_id(row[13].strip()) if row[13] else None,
                    employment_date = dt,
                    grade_id = self.get_grade_id(row[15].strip()) if row[15] else None,
                    job_id = self.get_designation_id(row[16], departmentid, company_id) if row[16] else None, 
                    work_email = row[24].strip() if len(row) > 24 and row[24] else None,
                    private_email = row[24].strip() if len(row) > 24 and row[24] else None,
                    work_phone = self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                    phone = self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                    company_id = company_id,
                    # hr_region_id = self.get_region_id(row[XX]) if len(row) > XX and row[XX] else None,
                )
                
                aa = row[20] if len(row) > 20 else None
                fa = row[18] if len(row) > 18 else None 
                rr = row[22] if len(row) > 22 else None
                
                vals = dict(
                    staff_number = employee_code,
                    functional_appraiser_id = fa,
                    administrative_supervisor_id = aa,
                    functional_reviewer_id = rr, 
                    private_email = employee_vals.get('private_email'),
                    email = employee_vals.get('work_email'),
                    fullname = employee_vals.get('name'),
                    company_id = employee_vals.get('company_id'),
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
                        if type(rr) == float else rr
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
                    else:
                        if vals.get('company_id') and employee_id.user_id:
                            try:
                                self.ensure_user_has_company(employee_id.user_id, vals.get('company_id'))
                            except Exception:
                                _logger.exception("Failed to ensure company for existing user during update")
                                
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
                if row[0] and len(row) > 3 and row[3]:
                    staff_number = str(row[0]).strip()
                    email = str(row[3]).strip()
                    employee_id = self.env['hr.employee'].search([
                    '|', ('employee_number', '=', staff_number), 
                    ('barcode', '=', staff_number)], limit = 1)
                    if employee_id:
                        employee_id.sudo().write({
                            'work_email': email
                        })
                        if employee_id.user_id and email.endswith('@enugudisco.com'):
                            employee_id.user_id.sudo().write({'login': email})
                        count += 1
                    else:
                        unsuccess_records.append(staff_number)
                else:
                    unsuccess_records.append(row[0] if row else 'Empty Row')
            
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
    _description = "Migration dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)

 