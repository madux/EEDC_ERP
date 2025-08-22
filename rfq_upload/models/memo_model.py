# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
import pandas as pd
import logging

_logger = logging.getLogger(__name__)

class MemoModel(models.Model):
    _inherit = 'memo.model'

    # --- Fields to store RFQ upload results ---
    rfq_excel_file = fields.Binary(string="RFQ Excel File", readonly=True, copy=False)
    rfq_excel_filename = fields.Char(string="RFQ Filename", readonly=True, copy=False)
    rfq_uploaded = fields.Boolean(string="RFQ Uploaded", default=False, readonly=True, copy=False)
    rfq_upload_date = fields.Datetime(string="RFQ Upload Date", readonly=True, copy=False)

    def action_upload_rfq_wizard(self):
        """Opens the RFQ Upload Wizard."""
        self.ensure_one()
        return {
            'name': _('RFQ Upload Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_memo_id': self.id}
        }

    def download_rfq_template(self):
        """Generates and returns the RFQ Excel template with pre-populated product data."""
        self.ensure_one()
        template_data = self._get_template_data()
        if not template_data.get('PRODUCT CODE'):
            raise ValidationError(_("There are no request items in this memo to generate a template for."))

        try:
            df = pd.DataFrame(template_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='RFQ_Template', index=False)
                worksheet = writer.sheets['RFQ_Template']
                for idx, col in enumerate(df):
                    max_len = max((df[col].astype(str).map(len).max(), len(str(df[col].name)))) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50) # Cap width at 50

            excel_file = base64.b64encode(output.getvalue())
            filename = f'RFQ_Template_{self.code or "New"}.xlsx'
            
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': excel_file,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("Error generating RFQ template: %s", str(e))
            raise ValidationError(_("Failed to generate template: %s") % str(e))

    def create_or_update_po_from_rfq(self, rfq_data, options):
        """
        Creates Purchase Orders from the validated RFQ data provided by the wizard.
        `options` is a dictionary containing flags from the wizard, e.g., {'create_vendors': True}
        """
        self.ensure_one()
        created_pos = self.env['purchase.order']
        
        group_by_vendor = options.get('group_by_vendor', True)
        
        if group_by_vendor:
            vendor_groups = {}
            for row in rfq_data:
                vendor_code = row.get('VENDOR CODE', '').strip()
                vendor_name = row.get('VENDOR NAME', '').strip()
                key = vendor_code if vendor_code else vendor_name
                if not key:
                    continue
                if key not in vendor_groups:
                    vendor_groups[key] = {'lines': [], 'vendor_info': row}
                vendor_groups[key]['lines'].append(row)
            groups = list(vendor_groups.values())
        else:
            groups = []
            for row in rfq_data:
                vendor_name = (row.get('VENDOR NAME') or '').strip()
                vendor_code = (row.get('VENDOR CODE') or '').strip()
                if not (vendor_name or vendor_code):
                    continue
                groups.append({'vendor_info': row, 'lines': [row]})

        # for key, data in vendor_groups.items():
        for data in groups:
            partner = self._find_or_create_vendor(data['vendor_info'], options)
            if not partner:
                _logger.warning(f"Skipping PO for vendor '{data['vendor_info']}' as they could not be found or created.")
                continue

            order_lines = []
            for line_data in data['lines']:
                line_vals = self._prepare_po_line_from_rfq(line_data, options)
                if line_vals:
                    order_lines.append((0, 0, line_vals))
            
            if order_lines:
                po_vals = {
                    'partner_id': partner.id,
                    'memo_id': self.id,
                    'date_order': fields.Date.today(),
                    'origin': self.code,
                    'memo_type_key': self.memo_type_key,
                    'memo_type': self.memo_type.id if self.memo_type else False,
                    'order_line': order_lines,
                    'rfq_source': 'excel_upload'
                }
                po = self.env['purchase.order'].with_context(rfq_excel_upload=True).create(po_vals)
                created_pos |= po
                
                if created_pos:
                    self.update({
                        'po_ids': [(4, po.id) for po in created_pos]
                    })
        # if created_pos:
        #     self.write({'po_ids': [(4, id) for id in created_pos.ids]})
        
        return created_pos

    def _get_template_data(self):
        """Extracts product data from the memo's request lines to pre-populate the template."""
        template_data = {
            'VENDOR CODE': [],'VENDOR NAME': [], 'VENDOR EMAIL': [], 'VENDOR PHONE': [],
            'PRODUCT CODE': [], 'PRODUCT NAME': [], 'PRODUCT DESCRIPTION': [],
            'QTY TO SUPPLY': [], 'PRICE PER QUANTITY': [],
            'MEMO_NUMBER': [], 'REQUEST_LINE_ID': []
        }
        if not self.product_ids:
            return {}

        for line in self.product_ids:
            for key in ['VENDOR CODE' ,'VENDOR NAME', 'VENDOR EMAIL', 'VENDOR PHONE', 'PRICE PER QUANTITY']:
                template_data[key].append('')
            
            template_data['PRODUCT CODE'].append(line.product_id.default_code or '')
            template_data['PRODUCT NAME'].append(line.product_id.name or '')
            template_data['PRODUCT DESCRIPTION'].append(line.description or line.product_id.name or '')
            template_data['QTY TO SUPPLY'].append(line.quantity_available or 1.0)
            template_data['MEMO_NUMBER'].append(self.code or '')
            template_data['REQUEST_LINE_ID'].append(line.id)
            
        return template_data

    def _find_or_create_vendor(self, vendor_data, options):
        """Finds an existing vendor or creates a new one based on wizard options."""
        vendor_code = vendor_data.get('VENDOR CODE', '').strip()
        vendor_name = vendor_data.get('VENDOR NAME', '').strip()
        vendor_email = vendor_data.get('VENDOR EMAIL', '').strip()
        
        domain = [('vendor_code', '=ilike', vendor_code)]
        if vendor_email:
            domain = ['|', ('email', '=ilike', vendor_email)] + domain

        partner = self.env['res.partner'].search(domain, limit=1)
        
        if not partner and options.get('create_vendors'):
            partner = self.env['res.partner'].create({
                'vendor_code': vendor_code,
                'name': vendor_name,
                'email': vendor_email,
                'phone': vendor_data.get('VENDOR PHONE'),
                'is_company': True,
                'supplier_rank': 1,
            })
        return partner

    def _prepare_po_line_from_rfq(self, line_data, options):
        """Prepares a dictionary of values for a purchase.order.line from a row of RFQ data."""
        product_code = line_data.get('PRODUCT CODE', '').strip()
        product_name = line_data.get('PRODUCT NAME', '').strip()

        product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
        if not product and options.get('create_products'):
            product = self.env['product.product'].create({
                'name': product_name or product_code,
                'default_code': product_code,
                'detailed_type': 'product',
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'purchase_ok': True,
                'sale_ok': False,
            })
        
        if not product:
            return None
            
        return {
            'product_id': product.id,
            'name': line_data.get('PRODUCT DESCRIPTION') or product.name,
            'product_qty': float(line_data.get('QTY TO SUPPLY', 1)),
            'price_unit': float(line_data.get('PRICE PER QUANTITY', 0)),
            'product_uom': product.uom_po_id.id,
            'date_planned': fields.Date.today(),
        }