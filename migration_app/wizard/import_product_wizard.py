
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


class ImportProductWizard(models.TransientModel):
    _name = 'import.product.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection([
            ('product', 'Create New Products'),
            ('update', 'Update Products'),
        ],
        string='Import Type', required=True, index=True,
        copy=True, default='', 
    )
    company_id = fields.Many2one("res.company","Company", required=True)
    location_id = fields.Many2one("stock.location","Store Location", required=True)
    product_id = fields.Many2one("product.product","Product")
    reset_count = fields.Boolean("Reset Quantity to Zero")
    property_stock_inventory = fields.Many2one("stock.location","Adjustment Store Location", required=True)
        
    def create_category(self, name):
        if not name:
            return self.env.ref('product.product_category_all').id #default category
        prod_category = self.env['product.category']
        name = name.strip().upper()
        prod_cat = prod_category.search([('name', '=', name)], limit = 1)
        if not prod_cat:
            product_category_id = prod_category.create({
                    "name": name,
                })
            return product_category_id.id
        else:
            return prod_cat.id
        
    def create_uom(self, name):
        if not name:
            return self.env.ref('uom.product_uom_unit').id
        prod_uom = self.env['uom.uom']
        name = name.strip().upper()
        p_uom = prod_uom.search([('name', '=', name)], limit = 1)
        if not p_uom:
            p_uom_id = prod_uom.create({
                    "name": name,
                    'category_id': 	self.env.ref('uom.product_uom_categ_unit').id
                })
            return p_uom_id.id
        else:
            return p_uom.id
        
    def _clean_numeric_value(self, value):
        """Clean and convert various formats to float"""
        if not value:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
            
            value = value.replace(',', '').replace(' ', '')
            
            try:
                return float(value)
            except ValueError:
                return 0.0
        
        return 0.0

    def import_records_action(self):
        if self.data_file:
            if self.location_id.company_id.id != self.company_id.id:
                raise ValidationError("Store location company must be same with selected company")
            if self.property_stock_inventory.company_id.id != self.company_id.id:
                raise ValidationError("Adjustment Store location company must be same with selected company")
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
        prod_obj = self.env['product.product']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        
        def find_existing_product(code):
            product_id = False
            if code:
                code = str(int(code)) if type(code) == float else code 
                product = self.env['product.product'].search([
                    ('default_code', '=', code), 
                    ('company_id', '=', self.company_id.id), 
                    ], limit = 1)
                if product:
                    product_id = product.id
                else:
                    product_id = False 
            return product_id
        
        def create_product(vals):
            prod_obj = self.env['product.product']
            default_code = vals.get('default_code')
            prod_rec = prod_obj.search([('default_code', '=', default_code),('company_id', '=', self.company_id.id)], limit = 1)
            product_id = prod_obj.sudo().create(vals).id if not prod_rec else prod_rec.id
            return product_id
         
        def create_stock_quant(product, location, qty):
            if qty <= 0:
                return
            self.env['stock.quant']._update_available_quantity(product, location, qty)
        
        if self.import_type == "product":
            for row in file_data:
                
                # try:
                name = str(row[1]).strip() if row[1] else ''
                unit_of_measure = str(row[2]).strip() if row[2] else ''
                unit_price = self._clean_numeric_value(row[3])
                qty = self._clean_numeric_value(row[4])
                categ_name = categ_name = str(row[5]).strip() if row[5] else ''
                stock_code = stock_code = str(row[6]).strip() if row[6] else ''
                if find_existing_product(row[1]):
                    unsuccess_records.append(f'Product with {str(row[1])} Already exists')
                else:
                    if name and stock_code:
                        _logger.info(f"Processing {row[0]} - {name} and the qty = {qty}")
                        
                        vals = {
                            'name': name,
                            'detailed_type': 'product',
                            'categ_id': self.create_category(categ_name),
                            'uom_id': self.env.ref('uom.product_uom_unit').id,
                            # 'list_price': unit_price,
                            'standard_price': unit_price,
                            'description': name,
                            'tracking': 'serial',
                            'default_code': stock_code,
                            'qty_available': qty,
                            'property_stock_inventory': self.property_stock_inventory.id,
                            'company_id': self.company_id.id
                        }
                        product = create_product(vals)
                        _logger.info(f"CREATED ODOO PRODUCT RECORD {self.env['product.product'].browse([product]).name} - {self.env['product.product'].browse([product]).qty_available}")
                        product_ref = self.env['product.product'].browse([product])
                        quant = self.update_product_quantity(product_ref,qty, self.location_id)
                        create_stock_quant(product_ref, self.location_id, vals.get('qty_available'))
                        success_records.append(vals.get('name'))
                    else:
                        unsuccess_records.append(f'Product at {count} does not have any name or code values')
                    count += 1
                
            errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
            errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 

        elif self.import_type == "update":
            for row in file_data:
                stock_code = stock_code = str(row[6]).strip() if row[6] else ''
                product = find_existing_product(stock_code)
                if product:
                    name = row[1]
                    unit_of_measure = row[2]
                    unit_price = row[3]
                    qty = row[4]
                    categ_name = row[5]
                    vals = {
                        'name': name,
                        'detailed_type': 'product',
                        'categ_id': self.create_category(categ_name),
                        'uom_id': self.create_uom(unit_of_measure),
                        'list_price': unit_price,
                        'description': name,
                        'tracking': 'serial',
                        'default_code': stock_code,
                        'qty_available': float(qty) if type(qty) in [str, int, float] else 0,
                        'company_id': self.company_id.id
                    }
                    product.update(vals)
                    self.update_product_quantity(product, vals.get('qty_available'), self.location_id)
                    create_stock_quant(product, self.location_id, vals.get('qty_available'))
                    # create_stock_quant(product, self.location_id, vals.get('qty_available'))
                    success_records.append(vals.get('name'))
                else:
                    unsuccess_records.append(f'Product at {count} could not be found')
                    
            errors.append('Successful Update(s): ' +str(count))
            errors.append('Unsuccessful Update(s): '+str(unsuccess_records)+' Record(s)')
            if len(errors) > 1:
                message = '\n'.join(errors)
                return self.confirm_notification(message) 
        
    def check_product_availability(self):
        if not self.product_id:
            raise ValidationError("Please select product and location ")
        total_availability = self.env['stock.quant'].sudo()._get_available_quantity(
                    self.product_id, self.location_id, allow_negative=False)
        raise ValidationError(f"Here is the available qty total_availability == {total_availability}")
        
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
        
        
    # Assuming you have a reference to the Odoo environment 'env'
# This can be used in a server action, a custom model method, or an Odoo shell script.

    def update_product_quantity(self, product_id, new_quantity, location_id):
        """
        Updates a product's stock quantity by creating and applying a stock quant.

        :param product_id: The ID of the product.product record.
        :param new_quantity: The target quantity to set.
        :param location_id: The ID of the stock.location record. If not provided,
                            the default stock location is used.
        """
        # 1. Find the product and location
        domain = [
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id)
        ]
        quant = self.env['stock.quant'].search(domain, limit=1)
        if self.import_type == 'product':
            domain = [
                ('product_id', '=', product_id.id),
                ('location_id', '=', location_id.id)]
            quant = self.env['stock.quant'].search(domain, limit=1)
            quant.inventory_quantity = 0
            quant.action_apply_inventory()
            
        if not quant:
            # Create a new quant record if none exists for this product in the location
            quant = self.env['stock.quant'].create({
                'product_id': product_id.id,
                'location_id': location_id.id,
                'inventory_quantity': new_quantity,
            })
            
        # else:
        #     # Update the existing quant with the new inventory quantity
        quant.action_apply_inventory()
        
        # quant.write({'inventory_quantity': new_quantity})
        # quant.action_apply_inventory()

        # Log the change
        # self.env.cr.commit()  # Ensure the changes are committed if used outside a transaction
        print(f"Product {product_id.name} quantity in {location_id.name} updated to {new_quantity}.")

     

 