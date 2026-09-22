from odoo import models, fields, _
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    move_to_category_id = fields.Many2one(
        'product.category',
        string='Move Products To',
        help='Select the category where all products in this category will be moved.'
    )

    def action_move_products(self):
        for category in self:
            if not category.move_to_category_id:
                raise UserError(_(
                    'Please select a destination category for "%s".'
                ) % category.name)

            if category.move_to_category_id == category:
                raise UserError(_(
                    'The destination category cannot be the same as the current category.'
                ))

            products = self.env['product.template'].search([
                ('categ_id', '=', category.id)
            ])

            if not products:
                raise UserError(_(
                    'There are no products in category "%s".'
                ) % category.name)

            products.write({
                'categ_id': category.move_to_category_id.id
            })

            # Clear the selected destination after moving
            category.move_to_category_id = False

        return True