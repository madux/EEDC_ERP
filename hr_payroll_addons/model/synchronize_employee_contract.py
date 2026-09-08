from odoo import api, fields, models, _


class EmployeeContractCheckWizard(models.TransientModel):
    _name = "employee.contract.check.wizard"
    _description = "Employee Contract Check"

    message = fields.Text(
        string="Result",
        readonly=True,
    )

    missing_contract_count = fields.Integer(
        string="Active Employees Without Contract",
        readonly=True,
    )
    missing_contract_ids = fields.Many2many(
            'hr.contract',
            string="Active Employees Without Contract",
            readonly=True,
        )
    
    deactivated_contract_count = fields.Integer(
        string="Contracts Deactivated",
        readonly=True,
    )

    @api.model
    def create_check_result(self):
        """
        Check employee contract status.

        1. Find active employees without an ACTIVE contract.
        2. Automatically deactivate active contracts belonging
           to inactive employees.
        3. Create a temporary wizard containing the result.
        """

        Employee = self.env["hr.employee"]
        Contract = self.env["hr.contract"]

        missing_contracts = []
        contracts_to_deactivate = Contract.browse()

        # =========================================================
        # 1. CHECK ACTIVE EMPLOYEES
        # =========================================================

        active_employees = Employee.search([
            ("active", "=", True),
        ])

        for employee in active_employees:

            # Only an ACTIVE contract counts.
            active_contract = Contract.search([
                ("employee_id", "=", employee.id),
                ("active", "=", True),
            ], limit=1)

            if not active_contract:
                employee_number = (
                    employee.employee_number
                    if employee.employee_number
                    else "N/A"
                )

                missing_contracts.append(
                    f"{employee_number} - {employee.name} "
                    f"- Does not have an active contract"
                )

        # =========================================================
        # 2. FIND ACTIVE CONTRACTS BELONGING TO INACTIVE EMPLOYEES
        # =========================================================

        inactive_employees = Employee.search([
            ("active", "=", False),
        ])

        if inactive_employees:
            contracts_to_deactivate = Contract.search([
                ("employee_id", "in", inactive_employees.ids),
                ("active", "=", True),
            ])

        # =========================================================
        # 3. DEACTIVATE CONTRACTS
        # =========================================================

        deactivated_count = len(contracts_to_deactivate)

        if contracts_to_deactivate:
            self.missing_contract_ids = [(6, 0, contracts_to_deactivate.ids)]
            

        # =========================================================
        # 4. BUILD MESSAGE
        # =========================================================

        message_lines = []

        if missing_contracts:
            message_lines.append(
                "ACTIVE EMPLOYEES WITHOUT ACTIVE CONTRACT"
            )
            message_lines.append("=" * 55)

            message_lines.extend(missing_contracts)

            message_lines.append("")
            message_lines.append(
                f"Total: {len(missing_contracts)}"
            )
        else:
            message_lines.append(
                "ACTIVE EMPLOYEES WITHOUT ACTIVE CONTRACT"
            )
            message_lines.append("=" * 55)
            message_lines.append(
                "All active employees have an active contract."
            )

        message_lines.append("")
        message_lines.append(
            "CONTRACT DEACTIVATION"
        )
        message_lines.append("=" * 55)

        if deactivated_count:
            message_lines.append(
                f"{deactivated_count} active contract(s) "
                f"were automatically deactivated because "
                f"their employees are inactive."
            )
        else:
            message_lines.append(
                "No active contracts belonging to inactive "
                "employees were found."
            )

        # =========================================================
        # 5. CREATE TEMPORARY WIZARD
        # =========================================================

        wizard = self.create({
            "message": "\n".join(message_lines),
            "missing_contract_count": len(missing_contracts),
            "deactivated_contract_count": deactivated_count,
        })

        return wizard

    def deactivate_contract(self):
        for rec in self.missing_contract_ids:
            rec.write({
                        "active": False,
                    })
    def deactivate_employee_and_contract(self):
        for rec in self.missing_contract_ids:
            rec.employee_id.write({
                        "active": False,
                    })
            rec.write({
                        "active": False,
                    })

    def action_close(self):
        return {
            "type": "ir.actions.act_window_close",
        }