from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging
from datetime import datetime, timedelta
import xlrd
import traceback
import xlwt
from io import BytesIO

_logger = logging.getLogger(__name__)


class ImportLeaveAllocation(models.TransientModel):
    _name = 'hr.leave.allocation.import.wizard'
    _description = 'Leave Allocation Import Wizard'

    data_file = fields.Binary(string="Upload File (.xls)", required=True)
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    leave_type_id = fields.Many2one(
        'hr.leave.type', 
        string='Leave Type',
        help="Select a leave type to override the excel data. If not selected, leave type will be read from excel."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help="Select a company to override the excel data. If not selected, company will be read from excel or employee's company."
    )
    batch_size = fields.Integer("Batch Size", default=500, help="Number of records to process in each batch")
    allow_overlap = fields.Boolean(
        string="Allow Overlapping Allocations",
        default=False,
        help="If checked, will allow creating allocations that overlap with existing ones for the same leave type"
    )
    skip_duplicates = fields.Boolean(
        string="Skip Duplicates",
        default=True,
        help="Skip allocations that exactly match existing ones (same leave type, name, dates)"
    )

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

    def validate_excel_structure(self, sheet):
        """Validate that the Excel has the expected structure"""
        if not sheet or sheet.nrows == 0:
            raise ValidationError("Excel file is empty")
        
        if sheet.nrows < 2:
            raise ValidationError("Excel file should have at least a header and one data row")
        
        if sheet.ncols < 8:
            raise ValidationError(f"Excel file should have at least 8 columns, found {sheet.ncols}")
        
        return True

    def download_template(self):
        """Generate and download Excel template for leave allocation import"""
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Leave Allocations')
        
        header_style = xlwt.easyxf(
            'font: bold on, color white; '
            'pattern: pattern solid, fore_colour blue_grey; '
            'align: wrap on, vert centre, horiz center;'
        )
        
        sample_style = xlwt.easyxf('align: wrap on, vert centre;')
        
        headers = [
            'Employee Code',
            'Employee Name',
            'Leave Type',
            'Department',
            'Allocation Name',
            'Number of Days',
            'Valid From',
            'Valid To',
            'Company'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_style)
            worksheet.col(col).width = 5000
        
        sample_data = [
            ['63696', 'PANDEY SHAILJA', 'ANNUAL LEAVE (HOLDCO)', 'TECHNOLOGY', 
             'LEAVE ALLOCATION HOLDCO', '30', '2026-01-01', '2027-03-31', 'HOLDCO'],
            ['63773', 'ENGR. PRAVEEN CHORGHADE', 'ANNUAL LEAVE (HOLDCO)', '', 
             'LEAVE ALLOCATION HOLDCO', '30', '2026-01-01', '2027-03-31', 'HOLDCO'],
            ['64340', 'JOHN DOE', 'SICK LEAVE', 'HR', 
             'SICK LEAVE 2026', '15', '2026-01-01', '2026-12-31', 'Main Company'],
        ]
        
        for row_idx, row_data in enumerate(sample_data, start=1):
            for col_idx, cell_value in enumerate(row_data):
                worksheet.write(row_idx, col_idx, cell_value, sample_style)
        
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        
        template_data = base64.b64encode(output.read())
        
        attachment = self.env['ir.attachment'].create({
            'name': 'Leave_Allocation_Import_Template.xls',
            'datas': template_data,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def check_duplicate_allocation(self, employee_id, leave_type_id, allocation_name, date_from, date_to):
        """
        Check if an allocation with exact same details already exists
        Returns: (is_duplicate, existing_allocation)
        """
        if not self.skip_duplicates:
            return False, None
        
        domain = [
            ('employee_id', '=', employee_id),
            ('holiday_status_id', '=', leave_type_id),
            ('date_from', '=', date_from),
        ]
        
        if allocation_name:
            domain.append(('name', '=', allocation_name))
        
        if date_to:
            domain.append(('date_to', '=', date_to))
        
        existing = self.env['hr.leave.allocation'].search(domain, limit=1)
        
        if existing:
            return True, existing
        
        return False, None

    def check_overlapping_allocation(self, employee_id, leave_type_id, date_from, date_to, allocation_name):
        """
        Check if there's an overlapping allocation for the same leave type.
        Smart logic: Only flag as overlap if the allocations are truly the same period allocation.
        
        Logic:
        - If allocations have same name and dates overlap -> likely duplicate/renewal, flag it
        - If allocations have different names but dates overlap -> check if they're different periods
        - Allow renewals: 2025 leave expiring March 2026 + 2026 leave starting Jan 2026 = OK (different periods)
        
        Returns: (has_overlap, overlapping_allocation, reason)
        """
        if self.allow_overlap:
            return False, None, None
        
        if not date_to:
            domain = [
                ('employee_id', '=', employee_id),
                ('holiday_status_id', '=', leave_type_id),
                ('date_from', '<=', date_from),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', date_from),
            ]
        else:
            domain = [
                ('employee_id', '=', employee_id),
                ('holiday_status_id', '=', leave_type_id),
                '|',
                '&',
                ('date_from', '<=', date_from),
                '|',
                ('date_to', '>=', date_from),
                ('date_to', '=', False),
                '&',
                ('date_from', '<=', date_to),
                '|',
                ('date_to', '>=', date_to),
                ('date_to', '=', False),
            ]
        
        overlapping = self.env['hr.leave.allocation'].search(domain)
        
        if not overlapping:
            return False, None, None
        
        for existing in overlapping:
            existing_name = existing.name or ''
            new_name = allocation_name or ''
            
            overlap_start = max(date_from, existing.date_from)
            
            if date_to and existing.date_to:
                overlap_end = min(date_to, existing.date_to)
            elif date_to:
                overlap_end = date_to
            elif existing.date_to:
                overlap_end = existing.date_to
            else:
                overlap_end = None
            
            if overlap_end:
                overlap_days = (overlap_end - overlap_start).days
            else:
                overlap_days = 999999
            
            if existing_name and new_name and existing_name == new_name:
                reason = f"Same allocation name '{new_name}' with overlapping dates"
                return True, existing, reason
            
            # LOGIC 2: Check if they're different period allocations (renewals)
            # Extract years from allocation names if possible
            import re
            existing_years = set(re.findall(r'\b(20\d{2})\b', existing_name))
            new_years = set(re.findall(r'\b(20\d{2})\b', new_name))
            
            if existing_years and new_years and existing_years != new_years:
                _logger.info(
                    f"Allowing overlap: '{existing_name}' (years: {existing_years}) vs "
                    f"'{new_name}' (years: {new_years}) - Different period allocations"
                )
                continue  # This is OK - different period allocations
            
            # LOGIC 3: If overlap is small (< 90 days) and names are different, might be renewal
            # Example: 2025 leave expiring March 2026 + 2026 leave starting Jan 2026
            if overlap_days < 90 and existing_name != new_name:
                _logger.info(
                    f"Allowing small overlap ({overlap_days} days): '{existing_name}' vs '{new_name}' "
                    f"- Likely renewal/transition period"
                )
                continue 
            
            # LOGIC 4: Significant overlap with different or no names = potential duplicate
            if overlap_days >= 90:
                reason = (
                    f"Significant overlap ({overlap_days} days) with existing allocation "
                    f"'{existing_name}' from {existing.date_from} to {existing.date_to or 'indefinite'}"
                )
                return True, existing, reason
        
        return False, None, None

    def safe_get_column(self, row, index, default=None):
        """Safely get column value with bounds checking"""
        try:
            return row[index] if len(row) > index and row[index] else default
        except (IndexError, TypeError):
            return default

    def find_employee(self, employee_code):
        """Find employee by employee number or barcode"""
        if not employee_code:
            return False
        
        employee_code = str(int(employee_code)) if isinstance(employee_code, float) else str(employee_code)
        employee = self.env['hr.employee'].sudo().search([
            '|', 
            ('employee_number', '=', employee_code), 
            ('barcode', '=', employee_code)
        ], limit=1)
        
        if employee and not employee.active:
            employee.sudo().write({'active': True})
            _logger.info(f"Unarchived employee: {employee.name}")
        
        return employee if employee else False

    def find_leave_type(self, leave_type_name):
        """Find leave type by name (case-insensitive, partial match)"""
        if not leave_type_name:
            return False
        
        leave_type_name = str(leave_type_name).strip()
        
        # Try exact match first
        leave_type = self.env['hr.leave.type'].search([
            ('name', '=ilike', leave_type_name)
        ], limit=1)
        
        if leave_type:
            return leave_type.id
        
        # Try partial match
        leave_type = self.env['hr.leave.type'].search([
            ('name', 'ilike', leave_type_name)
        ], limit=1)
        
        if leave_type:
            _logger.info(f"Found leave type by partial match: '{leave_type_name}' -> '{leave_type.name}'")
            return leave_type.id
        
        _logger.warning(f"Leave type not found: {leave_type_name}")
        return False

    def find_company(self, company_name):
        """Find company by name (case-insensitive, partial match)"""
        if not company_name:
            return False
        
        company_name = str(company_name).strip()
        
        # Try exact match first
        company = self.env['res.company'].search([
            ('name', '=ilike', company_name)
        ], limit=1)
        
        if company:
            return company.id
        
        # Try partial match
        company = self.env['res.company'].search([
            ('name', 'ilike', company_name)
        ], limit=1)
        
        if company:
            _logger.info(f"Found company by partial match: '{company_name}' -> '{company.name}'")
            return company.id
        
        _logger.warning(f"Company not found: {company_name}")
        return False

    def parse_date(self, date_value):
        """Parse date from various formats"""
        if not date_value:
            return False
        
        try:
            # If it's an Excel date number
            if isinstance(date_value, (int, float)):
                return datetime(*xlrd.xldate_as_tuple(date_value, 0)).date()
            
            # If it's a string
            date_str = str(date_value).strip()
            
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            _logger.warning(f"Could not parse date: {date_value}")
            return False
            
        except Exception as e:
            _logger.error(f"Error parsing date {date_value}: {e}")
            return False

    def import_leave_allocations(self):
        """Main import method"""
        if not self.data_file:
            raise ValidationError('Please select an Excel file to import')
        
        file_datas = base64.b64decode(self.data_file)
        workbook = xlrd.open_workbook(file_contents=file_datas)
        sheet_index = int(self.index) if self.index else 0
        
        if sheet_index >= workbook.nsheets:
            raise ValidationError(f'Sheet index {sheet_index} does not exist. Workbook has {workbook.nsheets} sheets.')
        
        sheet = workbook.sheet_by_index(sheet_index)
        self.validate_excel_structure(sheet)
        
        errors = ['The following messages occurred:']
        count = 0
        skipped_duplicates = 0
        skipped_overlaps = 0
        success_records = []
        unsuccess_records = []
        
        batch_size = self.batch_size or 500
        total_rows = sheet.nrows - 1
        total_batches = (total_rows // batch_size) + (1 if total_rows % batch_size else 0)
        
        batch_num = 0
        for batch_data in self.stream_excel_rows(sheet, batch_size):
            batch_num += 1
            _logger.info(f"Processing leave allocation batch {batch_num} of {total_batches} ({len(batch_data)} records)")
            
            for row in batch_data:
                row_label = self.safe_get_column(row, 0, 'Unknown')
                
                try:
                    with self.env.cr.savepoint():
                        
                        employee_code = self.safe_get_column(row, 0)
                        employee_name = self.safe_get_column(row, 1)
                        leave_type_name = self.safe_get_column(row, 2)
                        department_name = self.safe_get_column(row, 3)
                        allocation_name = self.safe_get_column(row, 4)
                        number_of_days = self.safe_get_column(row, 5)
                        valid_from = self.safe_get_column(row, 6)
                        valid_to = self.safe_get_column(row, 7)
                        company_name = self.safe_get_column(row, 8)
                        
                        employee = self.find_employee(employee_code)
                        if not employee:
                            unsuccess_records.append(
                                f"Row {row_label}: Employee '{employee_code}' not found"
                            )
                            continue
                        
                        if self.leave_type_id:
                            leave_type_id = self.leave_type_id.id
                        else:
                            leave_type_id = self.find_leave_type(leave_type_name)
                            if not leave_type_id:
                                unsuccess_records.append(
                                    f"Row {row_label}: Leave type '{leave_type_name}' not found for employee {employee.name}"
                                )
                                continue
                        
                        if self.company_id:
                            company_id = self.company_id.id
                        elif company_name:
                            company_id = self.find_company(company_name)
                            if not company_id:
                                company_id = employee.company_id.id if employee.company_id else self.env.company.id
                                _logger.info(f"Using employee company for {employee.name}: {company_id}")
                        else:
                            company_id = employee.company_id.id if employee.company_id else self.env.company.id
                        
                        date_from = self.parse_date(valid_from)
                        date_to = self.parse_date(valid_to)
                        
                        if not date_from:
                            unsuccess_records.append(
                                f"Row {row_label}: Invalid 'Valid From' date for employee {employee.name}"
                            )
                            continue
                        
                        try:
                            days = float(number_of_days) if number_of_days else 0
                        except (ValueError, TypeError):
                            unsuccess_records.append(
                                f"Row {row_label}: Invalid number of days '{number_of_days}' for employee {employee.name}"
                            )
                            continue
                        
                        is_duplicate, duplicate_alloc = self.check_duplicate_allocation(
                            employee.id, leave_type_id, allocation_name, date_from, date_to
                        )
                        
                        if is_duplicate:
                            skipped_duplicates += 1
                            _logger.info(
                                f"Skipping duplicate allocation for {employee.name}: "
                                f"{allocation_name} ({date_from} - {date_to})"
                            )
                            continue
                        
                        has_overlap, overlap_alloc, overlap_reason = self.check_overlapping_allocation(
                            employee.id, leave_type_id, date_from, date_to, allocation_name
                        )
                        
                        if has_overlap:
                            skipped_overlaps += 1
                            _logger.info(
                                f"Skipping overlapping allocation for {employee.name}: {overlap_reason}"
                            )
                            unsuccess_records.append(
                                f"Row {row_label} ({employee.name}): Skipped - {overlap_reason}"
                            )
                            continue
                        
                        allocation_vals = {
                            'name': allocation_name or f"Allocation for {employee.name}",
                            'holiday_status_id': leave_type_id,
                            'employee_id': employee.id,
                            'number_of_days': days,
                            'date_from': date_from,
                            'holiday_type': 'employee',
                        }
                        
                        if date_to:
                            allocation_vals['date_to'] = date_to
                        
                        allocation = self.env['hr.leave.allocation'].sudo().create(allocation_vals)
                        
                        try:
                            if hasattr(allocation, 'action_confirm'):
                                allocation.action_confirm()
                            if hasattr(allocation, 'action_validate'):
                                allocation.action_validate()
                            elif hasattr(allocation, 'action_approve'):
                                allocation.action_approve()
                        except Exception as validate_error:
                            _logger.warning(
                                f"Could not auto-validate allocation for {employee.name}: {validate_error}"
                            )
                        
                        _logger.info(
                            f"Created leave allocation for {employee.name}: "
                            f"{days} days, Type: {allocation.holiday_status_id.name}, State: {allocation.state}"
                        )
                        
                        count += 1
                        success_records.append(f"{employee.name} - {days} days")
                    
                    self.env.cr.commit()
                    
                except Exception as e:
                    self.env.cr.rollback()
                    error_msg = f"Row {row_label}: {str(e)}"
                    _logger.error(f"Error processing row {row_label}: {error_msg}\n{traceback.format_exc()}")
                    unsuccess_records.append(error_msg)
            
            _logger.info(
                f"Completed leave allocation batch {batch_num} of {total_batches} "
                f"(Success: {count}, Duplicates: {skipped_duplicates}, Overlaps: {skipped_overlaps}, Failed: {len(unsuccess_records)})"
            )
        
        # Prepare result message
        errors.append(f'Successful Import(s): {count} Record(s)')
        if skipped_duplicates > 0:
            errors.append(f'Skipped Duplicates: {skipped_duplicates} Record(s)')
        if skipped_overlaps > 0:
            errors.append(f'Skipped Overlapping: {skipped_overlaps} Record(s)')
        if success_records:
            errors.append(f"\nSuccessfully imported:\n" + "\n".join(success_records[:50]))  # Show first 50
            if len(success_records) > 50:
                errors.append(f"... and {len(success_records) - 50} more")
        
        errors.append(f"\nUnsuccessful Import(s): {len(unsuccess_records)} Record(s)")
        if unsuccess_records:
            errors.append("Errors:\n" + "\n".join(unsuccess_records[:50]))  # Show first 50
            if len(unsuccess_records) > 50:
                errors.append(f"... and {len(unsuccess_records) - 50} more")
        
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    def confirm_notification(self, popup_message):
        """Show result dialog"""
        view = self.sudo().env.ref('migration_app.hr_migration_confirm_dialog_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
            'name': 'Import Result',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'res_model': 'hr.migration.confirm.dialog',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }


# class LeaveAllocationImportConfirmDialog(models.TransientModel):
#     _name = "leave.allocation.import.confirm.dialog"
#     _description = "Leave Allocation Import Dialog"
    
#     def get_default(self):
#         if self.env.context.get("message", False):
#             return self.env.context.get("message")
#         return False 

#     name = fields.Text(string="Message", readonly=True, default=get_default)