# report/report_account_callover.py
from collections import OrderedDict, defaultdict
from odoo import models


MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'july', 'aug', 'sep', 'oct', 'nov', 'dec']
MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
 

class ReportAccountCallover(models.AbstractModel):
    _name = 'report.account_callover.report_account_callover_document'
    _description = 'Account Callover PDF Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.callover'].browse(docids)
        docs = docs.sorted(
            key=lambda r: (r.fiscalyear or '', r.branch_id.name or '', r.account_id.name or '')
        )

        grouped = OrderedDict()
        for rec in docs:
            fy = rec.fiscalyear or 'N/A'
            branch = rec.branch_id
            account = rec.account_id

            grouped.setdefault(fy, OrderedDict())
            grouped[fy].setdefault(branch, OrderedDict())
            if account in grouped[fy][branch]:
                grouped[fy][branch][account] |= rec          # union -> still a recordset
            else:
                grouped[fy][branch][account] = rec

        # ---- NEW: per-MDA (branch) summary across ALL fiscal years ----
        mda_ids = defaultdict(list)     # branch_id -> [record ids]
        branch_map = {}
        for rec in docs:
            bid = rec.branch_id.id or 0
            branch_map[bid] = rec.branch_id
            mda_ids[bid].append(rec.id)

        mda_summary = OrderedDict()
        for bid in sorted(mda_ids.keys(), key=lambda b: branch_map[b].name or ''):
            branch = branch_map[bid]
            recs = self.env['account.callover'].browse(mda_ids[bid])
            totals = {m: sum(recs.mapped(m)) for m in MONTHS}
            totals['total'] = sum(recs.mapped('total'))
            mda_summary[branch] = totals
        # -----------------------------------------------------------------

        return {
            'doc_ids': docids,
            'doc_model': 'account.callover',
            'docs': docs,
            'grouped_data': grouped,
            'mda_summary': mda_summary,
        }


class ReportAccountCalloverXlsx(models.AbstractModel):
    _name = 'report.account_callover.report_account_callover_xlsx'
    # _inherit = 'report.report_xlsx.abstract'
    _description = 'Account Callover Excel Report'

    def generate_xlsx_report(self, workbook, data, docs):
        sheet = workbook.add_worksheet('Callover Report')

        num_fmt_str = '#,##0.00'

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        fy_fmt = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'font_size': 12})
        mda_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_size': 11})
        subhead_fmt = workbook.add_format({'bold': True, 'italic': True, 'bg_color': '#F2F2F2'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1, 'align': 'center'})
        money_fmt = workbook.add_format({'num_format': num_fmt_str, 'border': 1})
        subtotal_fmt = workbook.add_format({'bold': True, 'num_format': num_fmt_str, 'border': 1, 'bg_color': '#F2F2F2'})
        subtotal_label_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2'})
        mda_summary_fmt = workbook.add_format({'bold': True, 'num_format': num_fmt_str, 'border': 1, 'bg_color': '#D9E1F2'})
        mda_summary_label_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white'})
        grand_fmt = workbook.add_format({'bold': True, 'num_format': num_fmt_str, 'border': 2, 'bg_color': '#2E5395', 'font_color': 'white'})
        grand_label_fmt = workbook.add_format({'bold': True, 'bg_color': '#2E5395', 'font_color': 'white'})

        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 13, 14)

        row = 0
        sheet.merge_range(row, 0, row, 13, 'Callover Report - Transactions by Month', title_fmt)
        row += 2

        docs = docs.sorted(key=lambda r: (r.fiscalyear or '', r.branch_id.name or '', r.account_id.name or ''))

        grouped = {}
        for rec in docs:
            grouped.setdefault(rec.fiscalyear, {}).setdefault(rec.branch_id, {}).setdefault(
                rec.account_id, self.env['account.callover']
            )
            grouped[rec.fiscalyear][rec.branch_id][rec.account_id] |= rec

        grand_total = [0.0] * 13

        # ---- track per-MDA totals across ALL fiscal years while looping ----
        mda_summary_totals = OrderedDict()   # branch -> [13 values]
        mda_order = []

        for fiscalyear, branches in grouped.items():
            sheet.merge_range(row, 0, row, 13, f'Fiscal Year: {fiscalyear}', fy_fmt)
            row += 1
            fy_total = [0.0] * 13

            for branch, accounts in branches.items():
                if branch not in mda_summary_totals:
                    mda_summary_totals[branch] = [0.0] * 13
                    mda_order.append(branch)

                sheet.merge_range(row, 0, row, 13, f'MDA: {branch.name or ""}', mda_fmt)
                row += 1
                mda_total = [0.0] * 13

                for account, recs in accounts.items():
                    sheet.write(row, 0, f'Subhead: {account.display_name or ""}', subhead_fmt)
                    row += 1

                    sheet.write(row, 0, 'Currency', header_fmt)
                    for i, label in enumerate(MONTH_LABELS):
                        sheet.write(row, i + 1, label, header_fmt)
                    sheet.write(row, 13, 'Total', header_fmt)
                    row += 1

                    subhead_total = [0.0] * 13
                    for rec in recs:
                        sheet.write(row, 0, rec.currency_id.name or '', money_fmt)
                        for i, m in enumerate(MONTHS):
                            val = getattr(rec, m) or 0.0
                            sheet.write_number(row, i + 1, val, money_fmt)
                            subhead_total[i] += val
                            mda_total[i] += val
                            fy_total[i] += val
                            grand_total[i] += val
                            mda_summary_totals[branch][i] += val
                        total_val = rec.total or 0.0
                        sheet.write_number(row, 13, total_val, money_fmt)
                        subhead_total[12] += total_val
                        mda_total[12] += total_val
                        fy_total[12] += total_val
                        grand_total[12] += total_val
                        mda_summary_totals[branch][12] += total_val
                        row += 1

                    sheet.write(row, 0, 'Subhead Total', subtotal_label_fmt)
                    for i in range(13):
                        sheet.write_number(row, i + 1, subhead_total[i], subtotal_fmt)
                    row += 2

                sheet.write(row, 0, f'{branch.name or ""} Total', subtotal_label_fmt)
                for i in range(13):
                    sheet.write_number(row, i + 1, mda_total[i], subtotal_fmt)
                row += 2

            sheet.write(row, 0, f'{fiscalyear} Total', fy_fmt)
            for i in range(13):
                sheet.write_number(row, i + 1, fy_total[i], subtotal_fmt)
            row += 3

        # ===== MDA SUMMARY - TOTAL PER MDA (ALL FISCAL YEARS) =====
        row += 1
        sheet.merge_range(row, 0, row, 13, 'MDA SUMMARY - TOTAL TRANSACTIONS PER MDA', mda_summary_label_fmt)
        row += 1

        sheet.write(row, 0, 'MDA', header_fmt)
        for i, label in enumerate(MONTH_LABELS):
            sheet.write(row, i + 1, label, header_fmt)
        sheet.write(row, 13, 'Total', header_fmt)
        row += 1

        mda_order_sorted = sorted(mda_order, key=lambda b: b.name or '')
        for branch in mda_order_sorted:
            totals = mda_summary_totals[branch]
            sheet.write(row, 0, branch.name or 'N/A', mda_summary_fmt)
            for i in range(13):
                sheet.write_number(row, i + 1, totals[i], mda_summary_fmt)
            row += 1
        row += 2

        # ===== GRAND SUMMARY - ALL RECORDS =====
        sheet.merge_range(row, 0, row, 13, 'GRAND SUMMARY - ALL RECORDS', grand_label_fmt)
        row += 1

        sheet.write(row, 0, 'Month Totals', header_fmt)
        for i, label in enumerate(MONTH_LABELS):
            sheet.write(row, i + 1, label, header_fmt)
        sheet.write(row, 13, 'Grand Total', header_fmt)
        row += 1

        sheet.write(row, 0, 'Amount', grand_label_fmt)
        for i in range(13):
            sheet.write_number(row, i + 1, grand_total[i], grand_fmt)


# class ReportAccountCallover(models.AbstractModel):
#     _name = 'report.account_callover.report_account_callover_document'
#     _description = 'Account Callover PDF Report'

#     def _get_report_values(self, docids, data=None):
#         docs = self.env['account.callover'].browse(docids)
#         docs = docs.sorted(
#             key=lambda r: (r.fiscalyear or '', r.branch_id.name or '', r.account_id.name or '')
#         )

#         grouped = OrderedDict()
#         for rec in docs:
#             fy = rec.fiscalyear or 'N/A'
#             branch = rec.branch_id
#             account = rec.account_id

#             grouped.setdefault(fy, OrderedDict())
#             grouped[fy].setdefault(branch, OrderedDict())
#             if account in grouped[fy][branch]:
#                 grouped[fy][branch][account] |= rec          # union -> still a recordset
#             else:
#                 grouped[fy][branch][account] = rec

#         return {
#             'doc_ids': docids,
#             'doc_model': 'account.callover',
#             'docs': docs,
#             'grouped_data': grouped,
#         }




# class AccountCalloverXlsx(models.AbstractModel):
#     _name = 'report.account_callover.report_account_callover_xlsx'
#     # _inherit = 'report.report_xlsx.abstract'
#     _description = 'Account Callover Excel Report'

#     def generate_xlsx_report(self, workbook, data, docs):
#         sheet = workbook.add_worksheet('Callover Report')

#         title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
#         fy_fmt = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'font_size': 12})
#         mda_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_size': 11})
#         subhead_fmt = workbook.add_format({'bold': True, 'italic': True, 'bg_color': '#F2F2F2'})
#         header_fmt = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1, 'align': 'center'})
#         money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
#         subtotal_fmt = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'bg_color': '#F2F2F2'})
#         subtotal_label_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2'})

#         sheet.set_column(0, 0, 28)
#         sheet.set_column(1, 13, 12)
#         sheet.set_column(14, 14, 15)

#         row = 0
#         sheet.merge_range(row, 0, row, 14, 'Callover Report - Transactions by Month', title_fmt)
#         row += 2

#         docs = docs.sorted(key=lambda r: (r.fiscalyear or '', r.branch_id.name or '', r.account_id.name or ''))

#         grouped = {}
#         for rec in docs:
#             grouped.setdefault(rec.fiscalyear, {}).setdefault(rec.branch_id, {}).setdefault(rec.account_id, self.env['account.callover'])
#             grouped[rec.fiscalyear][rec.branch_id][rec.account_id] |= rec

#         for fiscalyear, branches in grouped.items():
#             sheet.merge_range(row, 0, row, 14, f'Fiscal Year: {fiscalyear}', fy_fmt)
#             row += 1
#             fy_total = [0.0] * 13

#             for branch, accounts in branches.items():
#                 sheet.merge_range(row, 0, row, 14, f'MDA: {branch.name or ""}', mda_fmt)
#                 row += 1
#                 mda_total = [0.0] * 13

#                 for account, recs in accounts.items():
#                     sheet.write(row, 0, f'Subhead: {account.display_name or ""}', subhead_fmt)
#                     row += 1

#                     sheet.write(row, 0, 'Currency', header_fmt)
#                     for i, label in enumerate(MONTH_LABELS):
#                         sheet.write(row, i + 1, label, header_fmt)
#                     sheet.write(row, 13, 'Total', header_fmt)
#                     sheet.write(row, 14, 'Budget Balance', header_fmt)
#                     row += 1

#                     subhead_total = [0.0] * 13
#                     for rec in recs:
#                         sheet.write(row, 0, rec.currency_id.name or '', money_fmt)
#                         for i, m in enumerate(MONTHS):
#                             val = getattr(rec, m) or 0.0
#                             sheet.write(row, i + 1, val, money_fmt)
#                             subhead_total[i] += val
#                             mda_total[i] += val
#                             fy_total[i] += val
#                         sheet.write(row, 13, rec.total or 0.0, money_fmt)
#                         subhead_total[12] += rec.total or 0.0
#                         mda_total[12] += rec.total or 0.0
#                         fy_total[12] += rec.total or 0.0
#                         sheet.write(row, 14, rec.budget_balance or 0.0, money_fmt)
#                         row += 1

#                     sheet.write(row, 0, 'Subhead Total', subtotal_label_fmt)
#                     for i in range(13):
#                         sheet.write(row, i + 1, subhead_total[i], subtotal_fmt)
#                     row += 2

#                 sheet.write(row, 0, f'{branch.name or ""} Total', subtotal_label_fmt)
#                 for i in range(13):
#                     sheet.write(row, i + 1, mda_total[i], subtotal_fmt)
#                 row += 2

#             sheet.write(row, 0, f'{fiscalyear} Grand Total', fy_fmt)
#             for i in range(13):
#                 sheet.write(row, i + 1, fy_total[i], subtotal_fmt)
#             row += 3