from odoo import api, fields, models


class MemoApprovalWizard(models.TransientModel):
    _name = "memo.approval.wizard"
    _description = "Store Confirmation Wizard"

    memo_id = fields.Many2one(
        'memo.model',
        required=True,
        readonly=True
    )

    operation_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        required=True
    )
    is_inter_district_transfer = fields.Boolean("Is inter district transfer", readonly=True)

    body_msg = fields.Text(
            string='Message',
            help="Message holder"
        )
    
    source_location_id = fields.Many2one(
            'stock.location',
            string='Source Location',
            required=True
        )
    destination_location_id = fields.Many2one(
            'stock.location',
            string='Destination Location',
            required=True
        )
    dummy_source_location_ids = fields.Many2many(
        'stock.location',
        'dummy_source_location_rel',
        'res_memo_approval_id', 
        'stock_location_id', 
        # compute='_compute_location_options',
    )

    dummy_operation_type_ids = fields.Many2many(
            'stock.picking.type',
            # compute='_compute_location_options',
        )

    dummy_destination_location_ids = fields.Many2many(
        'stock.location',
        'dummy_destination_location_rel',
        'res_memo_approval_id', 
        'stock_location_id', 
        # compute='_compute_location_options',
    )

    no_destination_location_found = fields.Boolean(
        # compute='_compute_location_options',
    )

    def compute_location_options(self, memo_id):

        StockLocation = self.env['stock.location']
        PickingType = self.env['stock.picking.type'].sudo()

        dummy_source_location_ids = []
        dummy_destination_location_ids = []
        dummy_operation_type_ids = []
        no_destination_location_found = False

        if not memo_id:
            return (
                dummy_source_location_ids,
                dummy_destination_location_ids,
                dummy_operation_type_ids,
                no_destination_location_found
            )

        memo = memo_id

        # ==========================================================
        # SOURCE LOCATIONS
        # ==========================================================

        source_locations = StockLocation.search([
            ('usage', '=', 'internal'),
            ('branch_id', '=', memo.branch_id.id),
        ])

        dummy_source_location_ids = source_locations.ids.copy()

        if memo.source_location_id:
            dummy_source_location_ids.append(
                memo.source_location_id.id
            )

        # ==========================================================
        # DETERMINE TRANSFER TYPE
        # ==========================================================

        is_inter_district = (
            memo.memo_setting_id.inter_district
            or memo.is_inter_district_transfer
        )

        # ==========================================================
        # INTER-DISTRICT
        # ==========================================================

        if is_inter_district:

            # Source locations
            source_locations = StockLocation.search([
                ('usage', '=', 'outgoing'),
                ('company_id', '=', memo.memo_setting_id.company_id.id),
            ])

            dummy_source_location_ids = source_locations.ids.copy()

            if memo.source_location_id:
                dummy_source_location_ids.append(
                    memo.source_location_id.id
                )

            # Destination locations
            destination_locations = StockLocation.search([
                ('usage', '=', 'customer'),
                ('branch_id', '=', memo.branch_id.id),
            ])

            # Internal operation types
            op_type = PickingType.search([
                ('company_id', '=', memo.memo_setting_id.company_id.id),
                ('code', '=', 'outgoing'),
            ])

            dummy_operation_type_ids = op_type.ids.copy()

            if memo.picking_type_id:
                dummy_operation_type_ids.append(
                    memo.picking_type_id.id
                )

        # ==========================================================
        # NORMAL TRANSFER
        # ==========================================================

        else:

            destination_locations = StockLocation.search([
                ('usage', 'in', ['customer']),
                ('company_id', '=', memo.employee_id.company_id.id),
            ])

            # Outgoing operation types
            op_type = PickingType.search([
                ('company_id', '=', memo.memo_setting_id.company_id.id),
                ('code', '=', 'outgoing'),
            ])

            dummy_operation_type_ids = op_type.ids.copy()

            if memo.picking_type_id:
                dummy_operation_type_ids.append(
                    memo.picking_type_id.id
                )

        # ==========================================================
        # DESTINATION IDS
        # ==========================================================

        dummy_destination_location_ids = destination_locations.ids.copy()

        if memo.dest_location_id:
            dummy_destination_location_ids.append(
                memo.dest_location_id.id
            )

        # Remove duplicates
        dummy_source_location_ids = list(
            set(dummy_source_location_ids)
        )

        dummy_destination_location_ids = list(
            set(dummy_destination_location_ids)
        )

        dummy_operation_type_ids = list(
            set(dummy_operation_type_ids)
        )

        no_destination_location_found = not bool(
            destination_locations
        )

        return (
            dummy_source_location_ids,
            dummy_destination_location_ids,
            dummy_operation_type_ids,
            no_destination_location_found
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        memo = self.env['memo.model'].browse(
            self.env.context.get('active_id')
        )
        if memo:
            dummy_source_location_ids,dummy_destination_location_ids,dummy_operation_type_ids,no_destination_location_found = self.compute_location_options(memo)
            res.update({
                'memo_id': memo.id,
                'destination_location_id': memo.dest_location_id.id or False,
                'source_location_id': memo.source_location_id.id or False,
                'dummy_source_location_ids': [(6, 0, dummy_source_location_ids)],
                'dummy_destination_location_ids': [(6, 0, dummy_destination_location_ids)],
                'dummy_operation_type_ids': [(6, 0, dummy_operation_type_ids)],
                'no_destination_location_found': no_destination_location_found,

            })

        return res

    def action_confirm(self):
        self.ensure_one()
        
        memo = self.memo_id
        memo.dest_location_id = self.destination_location_id.id
        memo.source_location_id = self.source_location_id.id
        memo.picking_type_id = self.operation_type_id.id
        memo.generate_external_internal_stock_material_request(self.body_msg)
        # Call your memo approval logic
        return {
            'type': 'ir.actions.act_window_close',
        }