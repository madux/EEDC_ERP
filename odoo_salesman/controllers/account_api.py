from odoo import http
from odoo.http import request
import json
import logging
# from odoo.addons.eha_auth.controllers.helpers import validate_token, validate_secret_key, invalid_response, valid_response
import werkzeug.wrappers
from odoo import fields
from odoo.exceptions import ValidationError
import functools
from datetime import datetime,date,timedelta


class AccountMoveAPI(http.Controller):

    def _authenticate(self):
        auth_header = request.httprequest.headers.get('Authorization')

        if not auth_header:
            return None, self._error("Missing Authorization header")

        try:
            token = auth_header.split("Bearer ")[1]
        except Exception:
            return None, self._error("Invalid Authorization format")

        user = request.env['user.api.token'].sudo().search([
            ('token', '=', token)
        ], limit=1)

        if not user:
            return None, self._error("Invalid API Token")
        return user, None  

    @http.route('/api/v2/create-move', type='json', auth='none', methods=['POST'], csrf=False)
    def create_move(self, **kwargs):
        """
            {
                "ref": "Cash Collection",
                "company_id": 1,
                "journal_id": "SAJ",
                "date": "2026-03-05",
                "move_type": "entry",
                "transactions": [
                    {
                    "description": "Revenue",
                    "amount": 40000,
                    "account_code": "43000",
                    "type": "credit"
                    },
                    {
                    "description": "Cash",
                    "amount": 40000,
                    "account_code": "10000",
                    "type": "debit"
                    }
                ]
                }
        """

        user, error = self._authenticate()
        if error:
            return error

        data = request.jsonrequest

        return self._generate_account_entry(user, data)

    def _generate_account_entry(self, user, data):
        env = request.env(user=user)

        # Validate
        if not data.get('transactions'):
            return self._error("transactions is required")

        company = env['res.company'].sudo().browse(int(data.get('company_id')))
        if not company.exists():
            return self._error("Invalid company_id")

        journal = env['account.journal'].sudo().search([
            '|',
            ('id', '=', data.get('journal_id')),
            ('code', '=', data.get('journal_id'))
        ], limit=1)

        if not journal:
            return self._error("Invalid journal")

        move_lines = []
        total_debit = 0
        total_credit = 0

        for line in data['transactions']:
            account = env['account.account'].sudo().search([
                ('code', '=', line.get('account_code')),
                ('company_id', '=', company.id)
            ], limit=1)

            if not account:
                return self._error(f"Account not found: {line.get('account_code')}")

            amount = float(line.get('amount', 0))
            typ = line.get('type')

            if typ not in ['debit', 'credit']:
                return self._error("type must be debit or credit")

            debit = amount if typ == 'debit' else 0
            credit = amount if typ == 'credit' else 0

            total_debit += debit
            total_credit += credit

            move_lines.append((0, 0, {
                'name': line.get('description'),
                'account_id': account.id,
                'debit': debit,
                'credit': credit,
            }))

        if total_debit != total_credit:
            return self._error(f"Unbalanced move D={total_debit} C={total_credit}")

        try:
            move = env['account.move'].sudo().create({
                'ref': data.get('ref'),
                'date': data.get('date'),
                'journal_id': journal.id,
                'company_id': company.id,
                'move_type': data.get('move_type', 'entry'),
                'line_ids': move_lines,
            })

            move.action_post()

        except Exception as e:
            _logger.exception("Creation failed")
            return self._error(str(e))

        return self._success({
            "id": move.id,
            "name": move.name
        })

    def _success(self, data=None, message="Success"):
        return {
            "success": True,
            "data": data or {},
            "message": message
        }


    def _error(self, message="Error", data=None):
        return {
            "success": False,
            "data": data or {},
            "message": message
        }

    @http.route('/api/v2/reverse-move', type='json', auth='none', methods=['POST'], csrf=False)
    def reverse_move(self, **kwargs):

        user, error = self._authenticate()
        if error:
            return error

        data = request.jsonrequest
        env = request.env(user=user)

        move = env['account.move'].sudo().browse(data.get('move_id'))

        if not move.exists():
            return self._error("Move not found")

        try:
            reverse = move._reverse_moves([{
                'ref': f"Reversal of {move.name}"
            }], cancel=True)

        except Exception as e:
            return self._error(str(e))

        return self._success({
            "reversal_id": reverse.id,
            "name": reverse.name
        })