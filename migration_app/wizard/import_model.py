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
import traceback
from psycopg2 import IntegrityError

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
            ('appraisal', 'Appraisal Setup'),
        ],
        string='Import Type', required=True, index=True,
        copy=True, default='', 
    )
    batch_size = fields.Integer("Batch Size", default=500, help="Number of records to process in each batch")
 
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
    
    def stream_excel_rows(self, sheet, batch_size=500):
        """Generator to yield Excel rows in batches without loading all data into memory"""
        current_batch = []
        
        for row_idx in range(1, sheet.nrows):
            row_data = [sheet.cell_value(row_idx, col) for col in range(sheet.ncols)]
            current_batch.append(row_data)
            
            if len(current_batch) >= batch_size:
                yield current_batch
                current_batch = []
                
        if current_batch:
            yield current_batch
    
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

    def validate_excel_structure(self, sheet):
        """Validate that the Excel has the expected structure"""
        if not sheet or sheet.nrows == 0:
            raise ValidationError("Excel file is empty")
        
        if sheet.nrows < 2:
            raise ValidationError("Excel file should have at least a header and one data row")
        
        if sheet.ncols < 26:
            raise ValidationError(f"Excel file should have at least 26 columns, found {sheet.ncols}")
        
        return True

    def get_company_and_district_id(self, district_name, company_external_id):
        """Get company and district ID, with predefined mappings and ilike search"""
        
        company_district_mappings = {
            'multi_company.company_firstpower': 'multi_company.branch0019',
            'multi_company.company_transpower': 'multi_company.branch0015', 
            'multi_company.company_new_era': 'multi_company.branch009',
            'multi_company.company_main_power': 'multi_company.branch0002',
            'multi_company.company_east_land': 'multi_company.branch003',
            'base.main_company': 'multi_company.branch001',
        }
        
        default_company = self.sudo().env.ref('base.main_company', raise_if_not_found=False)
        default_district = self.sudo().env.ref('multi_company.branch001', raise_if_not_found=False)  # CHQ
        
        company_id = None
        district_id = None
        
        if company_external_id:
            company_external_id = str(company_external_id).strip()
            # Company = self.env['res.company']
            # company_rec = Company.search([('name', 'ilike', company_name)], limit=1)
            company_rec = self.sudo().env.ref(company_external_id, raise_if_not_found=False)
            if company_rec:
                company_id = company_rec.id
            else:
                company_id = default_company.id if default_company else False
        else:
            company_id = default_company.id if default_company else False
        
        if district_name:
            district_name = str(district_name).strip()
            District = self.env['multi.branch']
            district_rec = District.search([('name', '=ilike', district_name)], limit=1)
            if district_rec:
                district_id = district_rec.id
            else:
                if company_external_id:
                    for comp_key, district_ref in company_district_mappings.items():
                        if comp_key == company_external_id:
                            mapped_district = self.sudo().env.ref(district_ref, raise_if_not_found=False)
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
    
    def create_department(self, name, company_id):
        """Create department with company context - Search first, create only if not found for the company
        args: company_id (returns id)
        """
        if not name:
            return None
            
        department_obj = self.env['hr.department'].sudo()
        name = str(name).strip()
        
        if not company_id:
            default_company = self.sudo().env.ref('base.main_company', raise_if_not_found=False)
            company_id = default_company.id if default_company else self.env.company.id
        
        domain = [('name', '=', name), ('company_id', '=', company_id)]
        depart_rec = department_obj.search(domain, limit=1)
        
        if depart_rec:
            if hasattr(depart_rec, 'active') and not depart_rec.active:
                depart_rec.sudo().write({'active': True})
            return depart_rec.id
        else:
            try:
                dept_vals = {'name': name, 'company_id': company_id}
                department_id = department_obj.with_company(company_id).sudo().create(dept_vals).id
                _logger.info(f"Created new department '{name}' for company {company_id}")
                return department_id
            except Exception as e:
                _logger.error(f"Failed to create department {name}: {str(e)}")
                return None

    def get_level_id(self, name):
        if not name:
            return False
        levelId = self.env['hr.level'].search([('name', '=', name)], limit=1)
        if levelId:
            return levelId.id
        else:
            return self.env['hr.level'].create({'name': name}).id
    
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
        if rec:
            return rec.id
        else:
            return self.env['hr.region'].create({'name': name}).id

    def get_grade_id(self, name):
        if not name:
            return False
        gradeId = self.env['hr.grade'].search([('name', '=', name)], limit=1)
        if gradeId:
            return gradeId.id
        else:
            return self.env['hr.grade'].create({'name': name}).id
    
    def get_designation_id(self, name, departmentid, company_id):
        """Get job/designation with company context - Search first, create only if not found for the company"""
        if not name:
            return False
            
        # if not company_id:
        #     default_company = self.sudo().env.ref('base.main_company', raise_if_not_found=False)
        #     company_id = default_company.id if default_company else self.env.company.id
        
        domain = [('name', '=', name), ('company_id', '=', company_id)]
        if departmentid:
            domain.append(('department_id', '=', departmentid))
            
        designationId = self.env['hr.job'].search(domain, limit=1)
        
        if designationId:
            if hasattr(designationId, 'active') and not designationId.active:
                designationId.sudo().write({'active': True})
            return designationId.id
        else:
            try:
                job_vals = {'name': name, 'company_id': company_id}
                if departmentid:
                    job_vals['department_id'] = departmentid
                job_id = self.env['hr.job'].with_company(company_id).sudo().create(job_vals).id
                _logger.info(f"Created new job '{name}' for company {company_id}")
                return job_id
            except Exception as e:
                _logger.error(f"Failed to create job {name}: {str(e)}")
                return None

    def get_unit_id(self, name):
        if not name:
            return False
        rec = self.env['hr.unit'].search([('name', '=', name)], limit=1)
        if rec:
            return rec.id
        else:
            return self.env['hr.unit'].create({'name': name}).id

    def get_sub_unit_id(self, name):
        if not name:
            return False
        rec = self.env['hr.work.unit'].search([('name', '=', name)], limit=1)
        if rec:
            return rec.id
        else:
            return self.env['hr.work.unit'].create({'name': name}).id
    
    def get_company_id(self, name):
        if not name:
            return False
        rec = self.env['res.company'].search([('name', '=', name)], limit=1)
        return rec.id if rec else False
    
    def safe_update_user_groups(self, user, additional_groups):
        """Safely update user groups while maintaining single user type"""
        if not user or not additional_groups:
            return
            
        try:
            user_types_category = self.env.ref('base.module_category_user_type', raise_if_not_found=False)
            if not user_types_category:
                return
                
            user_types_groups = self.env['res.groups'].search([
                ('category_id', '=', user_types_category.id)
            ])
            
            current_user_type_groups = user.groups_id.filtered(
                lambda g: g.category_id.id == user_types_category.id
            )
            
            if not current_user_type_groups:
                _logger.warning(f"User {user.login} has no user type groups")
                return
            
            current_other_groups = user.groups_id.filtered(
                lambda g: g.category_id.id != user_types_category.id
            )
            
            all_group_ids = list(set(
                current_user_type_groups.ids + 
                current_other_groups.ids + 
                additional_groups
            ))
            
            user.sudo().write({'groups_id': [(6, 0, all_group_ids)]})
            _logger.info(f"Updated groups for user {user.login} - preserved user type: {current_user_type_groups.mapped('name')}")
            
        except Exception as e:
            _logger.error(f"Failed to safely update groups for user {user.login}: {e}")
    
    # def ensure_user_has_company(self, user, company_id):
    #     """Ensure `user` has company_id in company_ids, and set company_id after that.
    #        Always add to company_ids before writing company_id to avoid 'not allowed companies' error.
    #     """
    #     if not user or not company_id:
    #         return
    #     try:
    #         if company_id not in user.company_ids.ids:
    #             user.sudo().write({'company_ids': [(4, company_id)]})
    #         user.sudo().write({'company_id': company_id})
    #     except Exception as e:
    #         _logger.error(f"Failed to ensure company {company_id} on user {user.id}: {e}")
    def ensure_user_has_company(self, user, company_id):
        """Ensure user has company_id in company_ids, and set company_id after that.
        IMPORTANT: Don't change user groups here to avoid user type conflicts.
        """
        if not user or not company_id:
            return
        try:
            if company_id not in user.company_ids.ids:
                user.sudo().write({'company_ids': [(4, company_id)]})
                _logger.info(f"Added company {company_id} to user {user.login}")
            
            if user.company_id.id != company_id:
                user.sudo().write({'company_id': company_id})
                _logger.info(f"Set current company {company_id} for user {user.login}")
                
        except Exception as e:
            _logger.error(f"Failed to ensure company {company_id} on user {user.id}: {e}")

    def unarchive_employee_if_needed(self, employee):
        """Unarchive employee if it's archived"""
        if employee and not employee.active:
            employee.sudo().write({'active': True})
            _logger.info(f"Unarchived employee: {employee.name}")

    def unarchive_user_if_needed(self, user):
        """Unarchive user if it's archived"""
        if user and not user.active:
            user.sudo().write({'active': True})
            _logger.info(f"Unarchived user: {user.login}")
            
    def parse_name(self, full_name):
            s = str(full_name).strip() if full_name is not None else ""
            if not s:
                return {'name': '', 'first_name': '', 'middle_name': '', 'last_name': ''}

            parts = [p for p in s.split() if p]
            # parts = [p.title() for p in parts]
            parts = [p.upper() for p in parts]

            if len(parts) == 1:
                surname = parts[0]
                return {'name': surname, 'first_name': '', 'middle_name': '', 'last_name': surname}
            if len(parts) == 2:
                surname, first = parts[0], parts[1]
                full = f"{surname} {first}"
                return {'name': full, 'first_name': first, 'middle_name': '', 'last_name': surname}

            surname, first = parts[0], parts[1]
            middle = ' '.join(parts[2:])
            full = f"{surname} {first} {middle}"
            return {'name': full, 'first_name': first, 'middle_name': middle, 'last_name': surname}
        


    def _link_user_to_employee(self, user, employee, company_id=None, reassign_conflict=False):
        """
        Safely link a user to an employee. Returns (True, None) or (False, reason).
        Default is safe: DO NOT reassign. Set reassign_conflict=True to unlink
        existing conflicting employee and reassign.
        """
        if not user or not employee:
            return False, "missing user or employee"

        Employee = self.env['hr.employee'].sudo()
        try:
            target_company = company_id or (employee.company_id.id if employee.company_id else None)

            conflict = Employee.search([('user_id', '=', user.id), ('company_id', '=', target_company)], limit=1)
            if conflict and conflict.id != employee.id:
                msg = ("user %s (id=%s) already linked to employee %s (id=%s) for company %s"
                    % (getattr(user, 'login', str(user.id)), user.id, getattr(conflict,'name','?'), conflict.id, target_company))
                _logger.warning("Link conflict: %s", msg)
                if not reassign_conflict:
                    return False, "conflict: " + msg
                try:
                    conflict.sudo().write({'user_id': False})
                    _logger.info("Unlinked user %s from employee %s (id=%s) to allow reassignment", getattr(user,'login',user.id), getattr(conflict,'name','?'), conflict.id)
                except Exception as e_unlink:
                    _logger.exception("Failed to unlink user from conflicting employee: %s", e_unlink)
                    return False, "failed to unlink conflict: %s" % e_unlink

            try:
                employee.sudo().write({'user_id': user.id})
                return True, None
            except IntegrityError as ie:
                _logger.exception("IntegrityError while linking user to employee: %s", ie)
                return False, "integrity error: %s" % ie
            except Exception as e:
                _logger.exception("Error while linking user to employee: %s", e)
                return False, str(e)

        except Exception as e_outer:
            _logger.exception("Unexpected error in _link_user_to_employee: %s", e_outer)
            return False, str(e_outer)

    def import_records_action(self):
        if not self.data_file:
            raise ValidationError('Please select file and type of file')
        
        file_datas = base64.b64decode(self.data_file)
        workbook = xlrd.open_workbook(file_contents=file_datas)
        sheet_index = int(self.index) if self.index else 0
        
        if sheet_index >= workbook.nsheets:
            raise ValidationError(f'Sheet index {sheet_index} does not exist. Workbook has {workbook.nsheets} sheets.')
        
        sheet = workbook.sheet_by_index(sheet_index)
        self.validate_excel_structure(sheet)
        
        errors = ['The Following messages occurred']
        employee_obj = self.env['hr.employee']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        
        def find_existing_employee(code):
            employee_id = False 
            if code:
                code = str(int(code)) if isinstance(code, float) else str(code)
                employee = self.env['hr.employee'].sudo().search([
                    '|', ('employee_number', '=', code), 
                    ('barcode', '=', code)], limit = 1)
                if employee:
                    employee_id = employee.id
                    self.unarchive_employee_if_needed(employee)
                            
                else:
                    employee_id = False 
            return employee_id
        
        # reviewer_group = self.env.ref("hr_pms.group_pms_reviewer")
        # officer_group = self.env.ref("hr_pms.group_pms_officer_id")
        # supervisor_group = self.env.ref("hr_pms.group_pms_supervisor")
        # manager_group = self.env.ref("hr_pms.group_pms_manager_id")
        def generate_emp_appraiser(employee, appraiser_code, type):
            appraiser = self.env['hr.employee'].sudo().search(['|', 
            ('employee_number', '=', appraiser_code), 
            ('barcode', '=', appraiser_code)
            ], limit = 1)
            emp_group = self.sudo().env.ref("hr_pms.group_pms_user_id")
            reviewer_group = self.sudo().env.ref("hr_pms.group_pms_reviewer")
            supervisor_group = self.sudo().env.ref("hr_pms.group_pms_supervisor")
            if appraiser and employee:
                self.unarchive_employee_if_needed(appraiser)
                
                if type == "ar":
                    employee.sudo().write({
                        'administrative_supervisor_id': appraiser.id
                        })
                    # raise ValidationError("this is the AR ======>{} and {} with".format(appraiser.name, employee.name, employee.administrative_supervisor_id.name))
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id])]
                    if appraiser.user_id:
                        self.unarchive_user_if_needed(appraiser.user_id)
                        appraiser.user_id.sudo().write({'groups_id':group_list})
                if type == "fr":
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id])]
                    employee.sudo().write({
                        'parent_id': appraiser.id
                    })
                    if appraiser.user_id:
                        self.unarchive_user_if_needed(appraiser.user_id)
                        appraiser.user_id.sudo().write({'groups_id':group_list})

                if type == "rr":
                    group_list = [(6, 0, [emp_group.id, supervisor_group.id, reviewer_group.id])]
                    # employee.reviewer_id = appraiser.id
                    employee.sudo().update({
                        'reviewer_id': appraiser.id
                    })
                    if appraiser.user_id:
                        self.unarchive_user_if_needed(appraiser.user_id)
                        appraiser.user_id.sudo().write({'groups_id':group_list})

        # def reset_employee_user_password(employee_id, user_id):
        #     if user_id:
        #         change_password_wiz = self.env['change.password.wizard'].sudo()
        #         change_password_user = self.env['change.password.user'].sudo()
        #         new_password = password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
        #         change_password_wiz_id = change_password_wiz.create({
        #             'user_ids': [(0, 0, {
        #                 'user_login': user_id.login, 
        #                 'new_passwd': new_password,
        #                 'user_id': user_id.id,
        #                 })]
        #         })
        #         change_password_wiz_id.user_ids[0].change_password_button()
        #         employee_id.migrated_password = new_password
        def reset_employee_user_password(employee_id, user_id):
            """Reset user password using change password wizard"""
            if user_id:
                try:
                    change_password_wiz = self.env['change.password.wizard'].sudo()
                    new_password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
                    change_password_wiz_id = change_password_wiz.create({
                        'user_ids': [(0, 0, {
                            'user_login': user_id.login, 
                            'new_passwd': new_password,
                            'user_id': user_id.id,
                            })]
                    })
                    change_password_wiz_id.user_ids[0].change_password_button()
                    employee_id.sudo().write({'migrated_password': new_password})
                except Exception as e:
                    _logger.error(f"Failed to reset password for user {user_id.login}: {e}")

       
        
        # def create_employee(vals):
        #     """Create employee and safely link a user if available.

        #     vals: dict expected to contain keys like:
        #         fullname, first_name, middle_name, last_name, staff_number,
        #         district, branch_id, gender, department_id, unit_id, sub_unit_id,
        #         employment_date, grade_id, level_id, hr_region_id, email, private_email,
        #         work_phone, phone, job_id, company_id
        #     """
        #     try:
        #         employee_vals = {
        #             'name': vals.get('fullname'),
        #             'first_name': vals.get('first_name'),
        #             'middle_name': vals.get('middle_name'),
        #             'last_name': vals.get('last_name'),
        #             'employee_number': vals.get('staff_number'),
        #             'ps_district_id': vals.get('district'),
        #             'branch_id': vals.get('branch_id'),
        #             'gender': vals.get('gender'),
        #             'department_id': vals.get('department_id'),
        #             'unit_id': vals.get('unit_id'),
        #             'work_unit_id': vals.get('sub_unit_id'),
        #             'employment_date': vals.get('employment_date'),
        #             'grade_id': vals.get('grade_id'),
        #             'level_id': vals.get('level_id'),
        #             'hr_region_id': vals.get('hr_region_id'),
        #             'work_email': vals.get('email'),
        #             'private_email': vals.get('private_email'),
        #             'work_phone': vals.get('work_phone'),
        #             'mobile_phone': vals.get('work_phone'),
        #             'phone': vals.get('phone'),
        #             'job_id': vals.get('job_id'),
        #             'company_id': vals.get('company_id'),
        #         }

        #         employee_id = self.env['hr.employee'].sudo().create(employee_vals)
        #         _logger.info("Created employee: %s with ID: %s", employee_id.name, employee_id.id)

        #         if not employee_id or not employee_id.exists():
        #             _logger.error("Employee creation failed - employee does not exist after creation")
        #             return False

        #         user_vals = {
        #             'fullname': vals.get('fullname'),
        #             'staff_number': vals.get('staff_number'),
        #             'email': vals.get('email'),
        #             'private_email': vals.get('private_email'),
        #             'company_id': vals.get('company_id'),
        #             'branch_id': vals.get('branch_id'),
        #         }

        #         user, password = generate_user(user_vals)

        #         if user:
        #             try:
        #                 try:
        #                     target_company_id = employee_id.company_id.id if employee_id and employee_id.company_id else vals.get('company_id')
        #                 except Exception:
        #                     target_company_id = vals.get('company_id')

        #                 conflict = self.env['hr.employee'].sudo().search([
        #                     ('user_id', '=', user.id),
        #                     ('company_id', '=', target_company_id)
        #                 ], limit=1)

        #                 if conflict and conflict.id != (employee_id.id if employee_id else False):
        #                     _logger.warning(
        #                         "Skipping linking: user %s (id=%s) is already linked to employee %s (id=%s) for company %s",
        #                         getattr(user, 'login', str(user.id)), getattr(user, 'id', user),
        #                         getattr(conflict, 'name', '?'), getattr(conflict, 'id', '?'),
        #                         target_company_id
        #                     )
        #                 else:
        #                     try:
        #                         employee_id.sudo().write({'user_id': user.id})
        #                     except IntegrityError as ie:
        #                         _logger.warning(
        #                             "IntegrityError linking user %s to employee %s: %s",
        #                             getattr(user, 'login', user.id), getattr(employee_id, 'id', '?'), ie
        #                         )
        #                     except Exception as e:
        #                         _logger.exception("Error linking user to employee: %s", e)

        #                     employee_id.refresh()
        #                     if employee_id.user_id and employee_id.user_id.id == user.id:
        #                         _logger.info(
        #                             "Successfully linked user %s (ID: %s) to employee %s (ID: %s)",
        #                             getattr(user, 'login', user.id), getattr(user, 'id', '?'),
        #                             getattr(employee_id, 'name', '?'), getattr(employee_id, 'id', '?')
        #                         )
        #                         if password:
        #                             try:
        #                                 reset_employee_user_password(employee_id, user)
        #                                 _logger.info("Password set for new user %s", getattr(user, 'login', user.id))
        #                             except Exception as e:
        #                                 _logger.warning("Failed to set password for user %s: %s", getattr(user, 'login', user.id), e)
        #                     else:
        #                         _logger.info("User %s was not linked to employee %s after write attempt", getattr(user, 'login', user.id), getattr(employee_id, 'id', '?'))

        #             except Exception as outer_e:
        #                 _logger.error("Unexpected error while attempting to link user to employee: %s\n%s", outer_e, traceback.format_exc())
        #         else:
        #             _logger.warning("Failed to create/find user for employee %s", employee_id.name)

        #         return employee_id

        #     except Exception as e:
        #         _logger.error("Error in create_employee: %s\n%s", e, traceback.format_exc())
        #         return False
        
        def create_employee(vals):
            """
            Create an hr.employee from vals and safely link or create a user.
            Returns the created hr.employee record on success, or False on failure.
            """
            try:
                employee_vals = {
                    'name': vals.get('fullname'),
                    'first_name': vals.get('first_name'),
                    'middle_name': vals.get('middle_name'),
                    'last_name': vals.get('last_name'),
                    'employee_number': vals.get('staff_number'),
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
                    'work_email': vals.get('email'),
                    'private_email': vals.get('private_email'),
                    'work_phone': vals.get('work_phone'),
                    'mobile_phone': vals.get('work_phone'),
                    'phone': vals.get('phone'),
                    'job_id': vals.get('job_id'),
                    'company_id': vals.get('company_id'),
                }

                employee_vals = {k: v for k, v in employee_vals.items() if v is not None}

                Employee = self.env['hr.employee'].sudo()
                
                employee_rec = Employee.create(employee_vals)
                _logger.info("Created employee: %s with ID: %s", getattr(employee_rec, 'name', '?'), getattr(employee_rec, 'id', '?'))

                if not employee_rec or not employee_rec.exists():
                    _logger.error("Employee creation failed - record does not exist after create.")
                    return False

                user_vals = {
                    'fullname': vals.get('fullname'),
                    'staff_number': vals.get('staff_number'),
                    'email': vals.get('email'),
                    'private_email': vals.get('private_email'),
                    'company_id': vals.get('company_id'),
                    'branch_id': vals.get('branch_id'),
                }

                try:
                    user, password = generate_user(user_vals)
                except Exception as e:
                    _logger.exception("generate_user raised an exception for %s: %s", user_vals.get('fullname'), e)
                    user, password = False, False

                if user:
                    target_company_id = employee_rec.company_id.id if employee_rec.company_id else vals.get('company_id')
                    
                    reassign_conflict = False
                    success, error_msg = self._link_user_to_employee(
                        user, employee_rec, company_id=target_company_id, reassign_conflict=reassign_conflict
                    )

                    if success:
                        if password:
                            try:
                                employee_rec.sudo().write({'migrated_password': password})
                                reset_employee_user_password(employee_rec, user)
                            except Exception as pw_exc:
                                _logger.warning("Failed to set password for %s: %s", employee_rec.name, pw_exc)
                        _logger.info("Successfully linked user %s to employee %s", user.login, employee_rec.name)
                    else:
                        _logger.warning("Failed to link user %s to employee %s: %s", user.login, employee_rec.name, error_msg)
                else:
                    _logger.info("No user created/found for employee %s (ID: %s)", employee_rec.name, employee_rec.id)

                return employee_rec

            except IntegrityError as db_ie:
                _logger.exception("IntegrityError during create_employee: %s", db_ie)
                return False
            except Exception as e:
                _logger.exception("Error in create_employee: %s", e)
                return False

        def generate_user(vals):
            """
            Create user is user does not exist
            Input: dict with keys like fullname, email, staff_number, company_id, branch_id
            returns: (user_record or False, password or False)
            """
            emp_portal_group = self.sudo().env.ref("base.group_portal", raise_if_not_found=False)

            email = (vals.get('email') or vals.get('private_email') or '') if vals else ''
            fullname = vals.get('fullname') or vals.get('name') or 'Unknown'
            branch_id = vals.get('branch_id')
            company_id = vals.get('company_id')
            staff_number = vals.get('staff_number') or ''
            _logger.info(f"Branch Id: {branch_id}")

            login = ''
            try:
                if isinstance(email, str) and email.strip() and email.strip().endswith('@enugudisco.com'):
                    login = email.strip()
                else:
                    login = str(staff_number).strip()
            except Exception:
                return False, False

            login = str(login).strip()

            User = self.env['res.users'].sudo()
            existing = User.search(['|', ('login', '=', email), ('login', '=', staff_number)], limit=1)
            # existing_staff_id = User.search(['|', ('login', '=', staff_number), ('login', '=', staff_number)], limit=1)
            # existing_email = User.search([('login', '=', email)])
            # if existing_email and existing_staff_id:
            #     existing_email.write({'active': False})
            #     existing = existing_staff_id
            #     existing.write({'login': login})
            # elif existing_staff_id and not existing_email:
            #     existing = existing_staff_id
            #     existing.write({'login': login})
            # elif existing_email and not existing_staff_id:
            #     existing = existing_email
            # else:
            #     return False, False
            if existing:
                _logger.info("Existing user found for login %s (id=%s). Reusing.", login, existing.id)
                try:
                    self.unarchive_user_if_needed(existing)
                    if company_id:
                        self.ensure_user_has_company(existing, company_id)
                except Exception:
                    _logger.exception("Failed to adjust existing user %s", login)
                existing.write({'branch_id': branch_id})
                return existing, False

            emp_conflict = self.env['hr.employee'].sudo().search([('user_id.login','=',login)], limit=1)
            if emp_conflict:
                _logger.warning("Login %s is already assigned to employee %s. Skipping user creation.", login, emp_conflict.name)
                return False, False

            password = ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10))
            base_user_vals = {
                'name': fullname,
                'login': login,
                'password': password,
                'branch_id': branch_id,
            }
            if company_id:
                base_user_vals['company_ids'] = [(6, 0, [company_id])]
                base_user_vals['company_id'] = company_id

            if emp_portal_group:
                base_user_vals['groups_id'] = [(6, 0, [emp_portal_group.id])]

            user = False
            try:
                _logger.info("Attempting to create user with login %s", base_user_vals['login'])
                user = User.create(base_user_vals)
                _logger.info("Created user %s (id=%s)", user.login, user.id)
                return user, password
            except Exception as e:
                _logger.exception("Failed to create user with login %s: %s", base_user_vals['login'], e)

            _logger.error("Unable to create user for %s (tried login(s) around %s).", fullname, login)
            return False, False
        
        
        batch_size = self.batch_size or 500
        total_rows = sheet.nrows - 1
        total_batches = (total_rows // batch_size) + (1 if total_rows % batch_size else 0)
        
        if self.import_type == "employee":
            batch_num = 0
            for batch_data in self.stream_excel_rows(sheet, batch_size):
                batch_num += 1
                _logger.info("Processing batch %s of %s (%s records)", batch_num, total_batches, len(batch_data))
                for row in batch_data:
                    row_label = row[0] if row and len(row) > 0 else 'Unknown'
                    try:
                        try:
                            with self.env.cr.savepoint():
                                if len(row) > 1 and find_existing_employee(row[1]):
                                    unsuccess_records.append(f'Employee with {str(row[1])} already exists')
                                    
                                    continue

                                static_emp_date = '01/01/2014'
                                emp_date = datetime.strptime(static_emp_date, '%d/%m/%Y')
                                appt_date = None
                                if len(row) > 14 and row[14]:
                                    v14 = row[14]
                                    if isinstance(v14, (int, float)):
                                        appt_date = datetime(*xlrd.xldate_as_tuple(v14, 0))
                                    elif isinstance(v14, str):
                                        if '-' in v14:
                                            d, m, y = v14.split('-')
                                            if len(y) == 2:
                                                y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                            appt_date = datetime.strptime(f"{d}-{m}-{y}", '%d-%b-%Y')
                                        elif '/' in v14:
                                            d, m, y = v14.split('/')
                                            if len(y) == 2:
                                                y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                            appt_date = datetime.strptime(f"{d}/{m}/{y}", '%d/%m/%Y')
                                        else:
                                            appt_date = datetime(*xlrd.xldate_as_tuple(float(v14), 0))

                                dt = appt_date or emp_date

                                company_id, branch_id = self.get_company_and_district_id(
                                    row[9] if len(row) > 9 else None,
                                    row[27] if len(row) > 27 else None
                                )
                                hr_district_name = row[9] if len(row) > 9 else None
                                hr_district_id = self.get_hr_district_id(hr_district_name)
                                departmentid = self.create_department(row[11], company_id) if len(row) > 11 and row[11] else None

                                name_data = self.parse_name(row[2] if len(row) > 2 else '')

                                vals = dict(
                                    serial = row[0] if len(row) > 0 else None,
                                    staff_number = str(int(row[1])) if len(row) > 1 and isinstance(row[1], (int, float)) else (row[1] if len(row) > 1 else None),
                                    fullname = name_data['name'],
                                    first_name = name_data['first_name'],
                                    middle_name = name_data['middle_name'],
                                    last_name = name_data['last_name'],
                                    level_id = self.get_level_id(row[3].strip()) if len(row) > 3 and row[3] else None,
                                    district = hr_district_id,
                                    branch_id = branch_id,
                                    gender = 'male' if len(row) > 10 and row[10] in ['m', 'M'] else 'female' if len(row) > 10 and row[10] in ['f', 'F'] else 'other',
                                    department_id = departmentid,
                                    unit_id = self.get_unit_id(row[12].strip()) if len(row) > 12 and row[12] else None,
                                    sub_unit_id = self.get_sub_unit_id(row[13].strip()) if len(row) > 13 and row[13] else None,
                                    employment_date = dt,
                                    grade_id = self.get_grade_id(row[15].strip()) if len(row) > 15 and row[15] else None,
                                    job_id = self.get_designation_id(row[16], departmentid, company_id) if len(row) > 16 and row[16] else None,
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
                                success_records.append(vals.get('fullname') or str(vals.get('staff_number')))

                        except Exception as sp_exc:
                            _logger.error("Row %s: exception in savepoint block: %s\n%s", row_label, sp_exc, traceback.format_exc())
                            unsuccess_records.append(f"Row {row_label}: {sp_exc}")
                            continue

                    except Exception as outer_exc:
                        _logger.error("Row %s: outer exception (possible aborted transaction): %s\n%s", row_label, outer_exc, traceback.format_exc())
                        try:
                            self.env.cr.rollback()
                            _logger.info("Rolled back cursor after aborted transaction - continuing at next row")
                        except Exception as rb_exc:
                            _logger.exception("Failed to rollback cursor after aborted transaction: %s", rb_exc)
                            raise
                        unsuccess_records.append(f"Row {row_label}: aborted transaction cleared, record skipped: {outer_exc}")
                        continue

                _logger.info("Completed batch %s of %s", batch_num, total_batches)
                
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
            errors.append("Unsuccessful Import(s):" +str(len(unsuccess_records)) + "Record(s): see more \n" +'\n'.join(unsuccess_records))
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

        elif self.import_type == "update":
            batch_num = 0
            for batch_data in self.stream_excel_rows(sheet, batch_size):
                batch_num += 1
                _logger.info(f"Processing update batch {batch_num} of {total_batches} ({len(batch_data)} records)")
                
                for row in batch_data:
                    row_label = row[0] if row and len(row) > 0 else 'Unknown'
                    try:
                        with self.env.cr.savepoint():
                            employee_code = str(int(row[1])) if type(row[1]) == float else row[1]
                            static_emp_date = '01/01/2014'
                            emp_date = datetime.strptime(static_emp_date, '%d/%m/%Y')
                            appt_date = None
                            
                            if len(row) > 14 and row[14]:
                                v14 = row[14]
                                if isinstance(v14, (int, float)):
                                    appt_date = datetime(*xlrd.xldate_as_tuple(v14, 0)) 
                                elif isinstance(v14, str):
                                    if '-' in v14:
                                        datesplit = v14.split('-')
                                        d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                        if len(y) == 2:
                                            y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                        appt_date = datetime.strptime(f"{d}-{m}-{y}", '%d-%b-%Y') 
                                    elif '/' in v14:
                                        datesplit = v14.split('/')
                                        d, m, y = datesplit[0], datesplit[1], datesplit[2]
                                        if len(y) == 2:
                                            y = f"20{y}" if int(y) <= 50 else f"19{y}"
                                        appt_date = datetime.strptime(f"{d}/{m}/{y}", '%d/%m/%Y') 
                                    else:
                                        appt_date = datetime(*xlrd.xldate_as_tuple(float(v14), 0))
                            
                            dt = appt_date or emp_date
                            
                            company_id, branch_id = self.get_company_and_district_id(
                                row[9] if len(row) > 9 else None,
                                row[27] if len(row) > 27 else None
                            )
                            hr_district_name = row[9] if len(row) > 9 else None
                            hr_district_id = self.get_hr_district_id(hr_district_name)
                            
                            departmentid = self.create_department(row[11], company_id) if len(row) > 11 and row[11] else None
                            
                            name_data = self.parse_name(row[2] if len(row) > 2 else '')
                            
                            employee_vals = {
                                'employee_number': employee_code,
                                'name': name_data['name'],
                                'first_name': name_data['first_name'],
                                'middle_name': name_data['middle_name'],
                                'last_name': name_data['last_name'],
                                'level_id': self.get_level_id(row[3].strip()) if len(row) > 3 and row[3] else None,
                                # 'ps_district_id': hr_district_id,
                                'branch_id': branch_id,
                                'gender': 'male' if len(row) > 10 and row[10] in ['m', 'M'] else 'female' if len(row) > 10 and row[10] in ['f', 'F'] else 'other',
                                'department_id': departmentid,
                                'unit_id': self.get_unit_id(row[12].strip()) if len(row) > 12 and row[12] else None,
                                'work_unit_id': self.get_sub_unit_id(row[13].strip()) if len(row) > 13 and row[13] else None,
                                'employment_date': dt,
                                'grade_id': self.get_grade_id(row[15].strip()) if len(row) > 15 and row[15] else None,
                                'job_id': self.get_designation_id(row[16], departmentid, company_id) if len(row) > 16 and row[16] else None, 
                                'work_email': row[24].strip() if len(row) > 24 and row[24] else None,
                                'private_email': row[24].strip() if len(row) > 24 and row[24] else None,
                                'work_phone': self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                                'phone': self.format_phone(row[25]) if len(row) > 25 and row[25] else None,
                                # 'company_id': company_id,
                                'parent_id': find_existing_employee(row[18]) if len(row) > 18 and row[18] else None,
                                'administrative_supervisor_id': find_existing_employee(str(row[20])) if len(row) > 20 and row[20] else None,
                                'reviewer_id': find_existing_employee(str(row[22])) if len(row) > 22 and row[22] else None,
                            }
                            # _logger.info(f"Employee vals = {employee_vals}")
                            
                            user_vals = {
                                'staff_number': employee_code,
                                'private_email': employee_vals.get('private_email'),
                                'email': employee_vals.get('work_email'),
                                'fullname': employee_vals.get('name'),
                                'company_id': company_id,
                                'branch_id': branch_id,
                            }
                            
                            employee_id = self.env['hr.employee'].sudo().search([
                                '|', ('employee_number', '=', employee_code), 
                                ('barcode', '=', employee_code)], limit=1)
                            
                            if employee_id:
                                self.unarchive_employee_if_needed(employee_id)
                                '''check if employee record has related user
                                    find user that has exist with the email address of current user 
                                    when the login of the current is employee_number and archive the user'''
                                def function_merge_existing_user(employee, val_dict):
                                    work_email = val_dict.get('email')
                                    staff_number = val_dict.get('staff_number')
                                    old_employee_user = employee.user_id
                                    existing_user_with_email = self.env['res.users'].search([('login', '=ilike', work_email)], limit=1)
                                    if existing_user_with_email:
                                        for ex in existing_user_with_email:
                                            employee.user_id = ex.existing_user_with_email.id
                                            ex.employee_id.active = False
                                        '''Archive the old records'''
                                        old_employee_user.active = False
                                if employee_id.user_id and company_id:
                                    try:
                                        self.unarchive_user_if_needed(employee_id.user_id)
                                        _logger.info("Unarchived user if needed.....")
                                        self.ensure_user_has_company(employee_id.user_id, company_id)
                                        _logger.info(f"Ensured user {employee_id.user_id.login} has access to company {company_id}")
                                    except Exception as e:
                                        _logger.error(f"Failed to ensure company access for user..... {employee_id.user_id.login}: {e}")
                                
                                _logger.info("About to update Employee......")
                                employee_id.sudo().update(employee_vals)
                                _logger.info("Updated Employee......")
                                
                                values = {
                                    'email': user_vals.get('email'),
                                    'staff_number': user_vals.get('staff_number'),
                                    }
                                function_merge_existing_user(employee_id, values)
                                if not employee_id.user_id:
                                    _logger.info("No user.....")
                                    try:
                                        user, password = generate_user(user_vals)
                                        if user:
                                            _logger.info("Generated user successfuly.....")
                                            success, error_msg = self._link_user_to_employee(
                                                user, employee_id, company_id=company_id, reassign_conflict=False
                                            )
                                            if success:
                                                if password:
                                                    employee_id.sudo().write({'migrated_password': password})
                                                _logger.info(f"Successfully linked new user {user.login} to employee {employee_id.name}")
                                            else:
                                                _logger.warning(f"Failed to link user {user.login} to employee {employee_id.name}: {error_msg}")
                                        else:
                                            _logger.info(f"No user created for employee {employee_id.name}")
                                    except Exception as e:
                                        _logger.error(f"Error creating/linking user for employee {employee_id.name}: {e}")
                                else:
                                    _logger.info("User exist")
                                    # employee_id.sudo().user_id.write({'branch_id':})
                                    generate_user(user_vals)
                                    if company_id:
                                        try:
                                            _logger.info("Guard 1")
                                            self.ensure_user_has_company(employee_id.user_id, company_id)
                                            # employee_id.user_id.write(user_vals)
                                            _logger.info("Guard 2")
                                        except Exception as e:
                                            _logger.error(f"Failed to ensure company access for existing user: {e}")
                                 
                                                
                                _logger.info(f'Updated records for {employee_id.employee_number} at line {row[0]}')
                                count += 1
                                success_records.append(employee_id.name)
                            else:
                                unsuccess_records.append(f"Employee {employee_code} not found")
                                
                    except Exception as e:
                        error_msg = f"Row {row_label}: Error updating {row[2] if len(row) > 2 else 'Unknown'} - {str(e)}"
                        _logger.error(error_msg)
                        unsuccess_records.append(error_msg)
                        continue
                        
                _logger.info(f"Completed update batch {batch_num} of {total_batches}")
            
            errors.append('Successful Update(s): ' +str(count))
            # errors.append('Unsuccessful Update(s): '+str(len(unsuccess_records))+' Record(s)')
            errors.append("Unsuccessful Import(s):" +str(len(unsuccess_records)) + "Record(s): see more \n" +'\n'.join(unsuccess_records))
            
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message)
                
        elif self.import_type == "appraisal":
            batch_num = 0
            for batch_data in self.stream_excel_rows(sheet, batch_size):
                batch_num += 1
                _logger.info(f"Processing appraisal batch {batch_num} of {total_batches} ({len(batch_data)} records)")
                
                for row in batch_data:
                    try:
                        with self.env.cr.savepoint():
                            employee_code = str(int(row[1])) if type(row[1]) == float else row[1]
                            
                            company_id, district_id = self.get_company_and_district_id(
                                row[9] if len(row) > 9 else None,
                                row[27] if len(row) > 27 else None
                            )
                            
                            vals = dict(
                                staff_number = employee_code,
                                functional_appraiser_id = row[18] if len(row) > 18 else None,
                                administrative_supervisor_id = row[20] if len(row) > 20 else None,
                                functional_reviewer_id = row[22] if len(row) > 22 else None, 
                                private_email = row[24].strip() if len(row) > 24 and row[24] else None,
                                email = row[24].strip() if len(row) > 24 and row[24] else None,
                                fullname = row[2].capitalize() if len(row) > 2 else None,
                                company_id = company_id,
                            )
                            
                            ## if fa, add, fr get the employee id, add the 
                            ## attributes to employee, also update the f employee user
                            ## group with the groups
                            employee_id = self.env['hr.employee'].sudo().search([
                            '|', ('employee_number', '=', employee_code), 
                            ('barcode', '=', employee_code)], limit = 1)
                            
                            if employee_id:
                                self.unarchive_employee_if_needed(employee_id)
                                
                                # employee_id.job_id.sudo().write({
                                #     'department_id': employee_id.department_id.id
                                # })
                                aa = row[20] if len(row) > 20 else None
                                fa = row[18] if len(row) > 18 else None 
                                rr = row[22] if len(row) > 22 else None
                                
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
                                            self.unarchive_user_if_needed(employee_id.user_id)
                                            self.ensure_user_has_company(employee_id.user_id, vals.get('company_id'))
                                        except Exception:
                                            _logger.exception("Failed to ensure company for existing user during appraisal")
                                            
                                _logger.info(f'Setting up appraisal for {employee_id.employee_number} at line {row[0]}')
                                count += 1
                                success_records.append(employee_id.name)
                            else:
                                unsuccess_records.append(f"Employee {employee_code} not found")
                                
                    except Exception as e:
                        error_msg = f"Row {row[0]}: Error setting up appraisal for {row[2] if len(row) > 2 else 'Unknown'} - {str(e)}"
                        _logger.error(error_msg)
                        unsuccess_records.append(error_msg)
                        continue
                        
                _logger.info(f"Completed appraisal batch {batch_num} of {total_batches}")
            
            errors.append('Successful Appraisal Setup(s): ' +str(count))
            errors.append('Unsuccessful Appraisal Setup(s): '+str(len(unsuccess_records))+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message)
                
        elif self.import_type == "email":
            batch_num = 0
            for batch_data in self.stream_excel_rows(sheet, batch_size):
                batch_num += 1
                _logger.info(f"Processing email batch {batch_num} of {total_batches} ({len(batch_data)} records)")
                
                for row in batch_data:
                    try:
                        with self.env.cr.savepoint():
                            if row[0] and len(row) > 3 and row[3]:
                                staff_number = str(row[0]).strip()
                                email = str(row[3]).strip()
                                employee_id = self.env['hr.employee'].sudo().search([
                                '|', ('employee_number', '=', staff_number), 
                                ('barcode', '=', staff_number)], limit = 1)
                                if employee_id:
                                    self.unarchive_employee_if_needed(employee_id)
                                    
                                    employee_id.sudo().write({
                                        'work_email': email
                                    })
                                    if employee_id.user_id and email.endswith('@enugudisco.com'):
                                        self.unarchive_user_if_needed(employee_id.user_id)
                                        employee_id.user_id.sudo().write({'login': email})
                                    count += 1
                                    success_records.append(employee_id.name)
                                else:
                                    unsuccess_records.append(f"Employee {staff_number} not found")
                            else:
                                unsuccess_records.append(f"Invalid row data: {row[0] if row else 'Empty Row'}")
                                
                    except Exception as e:
                        error_msg = f"Row {row[0] if row else 'Unknown'}: Error updating email - {str(e)}"
                        _logger.error(error_msg)
                        unsuccess_records.append(error_msg)
                        continue
                        
                _logger.info(f"Completed email batch {batch_num} of {total_batches}")
            
            errors.append('Successful Email Update(s): ' +str(count))
            errors.append('Unsuccessful Email Update(s): '+str(len(unsuccess_records))+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

    def confirm_notification2(self,popup_message):
        view = self.sudo().env.ref('migration_app.hr_migration_confirm_dialog_view')
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
    def confirm_notification(self, popup_message):
        try:
            return self.confirm_notification2(popup_message)
        except Exception as e:
            msg = str(e) or ""
            _logger.exception("confirm_notification failed on first attempt: %s", msg)
            if 'current transaction is aborted' in msg or 'InFailedSqlTransaction' in msg or 'commands ignored until end of transaction block' in msg:
                try:
                    _logger.info("Transaction aborted: performing env.cr.rollback() and retrying confirm_notification")
                    self.env.cr.rollback()
                except Exception as rb_exc:
                    _logger.exception("Rollback after aborted transaction failed: %s", rb_exc)
                    raise
                return self.confirm_notification2(popup_message)
            raise


class MigrationDialogModel(models.TransientModel):
    _name="hr.migration.confirm.dialog"
    _description = "Migration dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)