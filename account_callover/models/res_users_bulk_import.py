# -*- coding: utf-8 -*-
import base64
import io
import logging
import re
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# try:
#     import openpyxl
# except ImportError:
#     openpyxl = None

# DEFAULT_PASSWORD = "12345"

# ROLE_GROUPS = {
#     "CASHIER": ["ik_multi_branch.account_mda_user", "base.group_user"],
#     "DFS": ["ik_multi_branch.account_mda_user", "base.group_user"],
#     "DIA": ["ik_multi_branch.account_dia_user", "base.group_user"],
# }


# class ResUsersBulkImportWizard(models.TransientModel):
#     _name = "res.users.bulk.import.wizard"
#     _description = "Bulk User Upload"

#     file = fields.Binary(string="Excel File", required=True)
#     filename = fields.Char(string="File Name")
#     result_log = fields.Text(string="Import Log", readonly=True)

#     def action_import_users(self):
#         self.ensure_one()

#         if openpyxl is None:
#             raise UserError("The 'openpyxl' python library is not installed on the server.")

#         if not self.file:
#             raise UserError("Please attach an Excel file first.")

#         try:
#             wb = openpyxl.load_workbook(
#                 io.BytesIO(base64.b64decode(self.file)), data_only=True
#             )
#         except Exception as e:
#             raise UserError("Could not read the Excel file: %s" % e)

#         sheet = wb.active

#         created, updated, skipped, errors = [], [], [], []
#         Users = self.env["res.users"].sudo()
#         Branch = self.env["multi.branch"].sudo()

#         for row_index, row in enumerate(
#             sheet.iter_rows(min_row=2, values_only=True), start=2
#         ):
#             if not row or all(cell in (None, "") for cell in row):
#                 continue

#             name, email, mda_code, mda_name, role, password = (list(row) + [None] * 6)[:6]

#             if not email:
#                 errors.append("Row %s: missing EMAIL - skipped" % row_index)
#                 continue

#             name = (name or "").strip()
#             email = (email or "").strip().lower()
#             email = str(email).replace("'", '') if email else ''
#             mda_code = str(mda_code).replace("'", '') if mda_code else ''
#             password = str(password).replace("'", '') if password else ''
#             email = re.sub(r"\s+", "", email)
#             password = re.sub(r"\s+", "", password)
#             mda_code = re.sub(r"\s+", "", mda_code)
#             role = re.sub(r"\s+", "", role or "").upper() if role else ""

#             try:
#                 # Resolve branch first - needed for both create and update paths
#                 branch = False
#                 if mda_code:
#                     if not mda_code.startswith('0'):
#                         mda_code = '0' + mda_code
#                     branch = Branch.search([("code", "=", mda_code)], limit=1)
#                     if not branch:
#                         errors.append(
#                             "Row %s: MDA CODE '%s' not found for %s - branch left empty"
#                             % (row_index, mda_code, email)
#                         )
#                 existing_user = Users.search([("login", "=", email)], limit=1)

#                 if existing_user:
#                     # Update only branch_id / branch_ids on existing users
#                     if branch:
#                         existing_user.write({
#                             "branch_id": branch.id,
#                             "branch_ids": [(6, 0, [branch.id])],
#                         })
#                         updated.append(
#                             "Row %s: %s already exists - branch updated to %s"
#                             % (row_index, email, branch.name)
#                         )
#                     else:
#                         skipped.append(
#                             "Row %s: %s already exists - no valid MDA CODE, branch left unchanged"
#                             % (row_index, email)
#                         )
#                     continue

#                 group_xmlids = ROLE_GROUPS.get(role)
#                 if not group_xmlids:
#                     errors.append(
#                         "Row %s: unrecognised ROLE '%s' for %s - skipped"
#                         % (row_index, role, email)
#                     )
#                     continue

#                 group_ids = []
#                 for xmlid in group_xmlids:
#                     group = self.env.ref(xmlid, raise_if_not_found=False)
#                     if group:
#                         group_ids.append(group.id)

#                 vals = {
#                     "name": name or email,
#                     "login": email,
#                     "email": email,
#                     "password": password,
#                     "groups_id": [(6, 0, group_ids)],
#                     "branch_id": branch.id if branch else False,
#                     "branch_ids": [(6, 0, [branch.id])] if branch else [(5, 0, 0)],
#                 }

#                 Users.create(vals)
#                 created.append("Row %s: created %s (%s)" % (row_index, email, role))

#             except Exception as e:
#                 errors.append("Row %s: error for %s - %s" % (row_index, email, e))
#                 _logger.exception("Bulk user import failed on row %s", row_index)

#         log_lines = (
#             ["=== Created (%s) ===" % len(created)] + created
#             + ["", "=== Updated (%s) ===" % len(updated)] + updated
#             + ["", "=== Skipped (%s) ===" % len(skipped)] + skipped
#             + ["", "=== Errors (%s) ===" % len(errors)] + errors
#         )
#         self.result_log = "\n".join(log_lines)

#         return {
#             "type": "ir.actions.act_window",
#             "res_model": "res.users.bulk.import.wizard",
#             "res_id": self.id,
#             "view_mode": "form",
#             "target": "new",
#             "context": self.env.context,
#         }

    