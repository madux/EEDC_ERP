from odoo import models, fields, api, _
from odoo.exceptions import UserError
import re

class ProductCategory(models.Model):
    _inherit = 'product.category'

    move_to_category_id = fields.Many2one(
        'product.category',
        string='Move Products To',
        help='Select the category where all products in this category will be moved.'
    )
    active = fields.Boolean("Active", default=True)

    # TODONEW
    product_prefix = fields.Char(
            string='Product Prefix',
            copy=False,
        ) 
    product_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Product Sequence',
        readonly=True,
        copy=False,
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

    def _generate_prefix(self, name):
        """
        Generate a unique prefix.

        Examples:
            Cables                  -> CA-00
            Computer Accessories    -> COA-00
            Computer Accessories 2  -> COA-01
            Electrical Materials    -> ELM-00
            Electrical Services     -> ELS-00
        """

        words = (name or '').split()

        if not words:
            return False

        if len(words) > 1:
            first_word = words[0]
            last_word = words[-1]

            # First 2 letters of first word
            # + first letter of last word
            #
            # Computer Accessories -> COA
            # Electrical Materials -> ELM
            base = (
                first_word[:2] +
                last_word[0]
            ).upper()

        else:
            # Cables -> CA
            base = words[0][:2].upper()

        # Find prefixes globally.
        #
        # DO NOT filter by company here because
        # prefixes are shared across all companies.
        existing_categories = self.with_context(
            active_test=False
        ).search([
            ('product_prefix', '=like', f'{base}-%')
        ])

        numbers = []

        for category in existing_categories:

            prefix = category.product_prefix or ''

            match = re.search(
                r'-(\d+)$',
                prefix
            )

            if match:
                numbers.append(
                    int(match.group(1))
                )

        next_number = max(numbers or [-1]) + 1

        return f'{base}-{str(next_number).zfill(2)}'

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if (
                not vals.get('product_prefix')
                and vals.get('name')
            ):
                vals['product_prefix'] = (
                    self._generate_prefix(
                        vals['name']
                    )
                )

        categories = super().create(vals_list)

        for category in categories:

            if not category.product_sequence_id:
                category._create_product_sequence()

        return categories

    def write(self, vals):

        result = super().write(vals)

        for category in self:

            # Don't change an existing prefix.
            if not category.product_prefix:
                category.product_prefix = (
                    category._generate_prefix(
                        category.name
                    )
                )

            if not category.product_sequence_id:
                category._create_product_sequence()

        return result

    def _create_product_sequence(self):
        """
        Create a GLOBAL sequence.

        IMPORTANT:
        company_id is deliberately NOT specified.

        Therefore the sequence is shared by all companies.
        """

        self.ensure_one()

        if self.product_sequence_id:
            return self.product_sequence_id

        if not self.product_prefix:
            return False

        sequence = self.env['ir.sequence'].sudo().create({
            'name': f'{self.name} Product Sequence',
            'code': f'product.category.{self.id}',
            'implementation': 'standard',
            'padding': 6,
            'number_increment': 1,
            'number_next': 1,

            # IMPORTANT:
            # Do NOT put company_id here.
            #
            # This makes the sequence global.
            'company_id': False,
        })

        self.product_sequence_id = sequence.id

        return sequence