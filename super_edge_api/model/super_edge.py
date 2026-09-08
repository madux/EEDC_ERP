# -*- coding: utf-8 -*-
import logging
import time

import requests
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import requests
from requests.exceptions import RequestException
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# In-memory token cache, shared across calls within the same worker process.
# Keyed by base_url + appID so multiple configs (test/prod) don't collide.
_TOKEN_CACHE = {}

class SuperEdgeRevenueDataLine(models.Model):
    _name = "superedge.revenue.data"

    superedge_revenue_api_id = fields.Many2one('superedge.revenue.api', string="Revenue ID")
    branch_id = fields.Many2one('multi.branch', string="District")
    move_id = fields.Many2one('account.move', string="MoveID")
    regionCode = fields.Char(string="Region code")
    districtCode = fields.Char(string="districtCode")
    postedStatus = fields.Char(string="postedStatus")
    chargeType = fields.Char(string="chargeType", copy=True)
    debit = fields.Float(string="Debit")
    credit = fields.Float(string="Credit")
    transactionDate = fields.Date(string="transactionDate")
    transactionTime = fields.Char(string="transaction time")
    currency = fields.Char(string="Currency", copy=True)
    msgID = fields.Char(string="Transaction ID / MsgID", copy=True)

class SuperEdgeRevenueApi(models.Model):
    _name = "superedge.revenue.api"

    auth_url = fields.Char(string="Authentication Url", 
                                help="Authentication Url", 
                                default="http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/token", 
                                copy=True)
    transaction_url = fields.Char(string="Transaction url", 
                                    default="http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/getTransactions", 
                                    copy=True)
    grantType = fields.Char(string="grantType", default="password", copy=True)
    username = fields.Char(string="username", default="EEDC", copy=True)
    password = fields.Char(string="password", default="A1234", copy=True)
    serviceCode = fields.Char(string="password", default="GetPostedTransactions", copy=True)
    transaction_msgID = fields.Char(string="transaction MsgID", default="202604241141290616", copy=True)
    transaction_appID = fields.Char(string="APPID", default="cdl", copy=True)
    transactionSignature = fields.Char(string="TransactionSignature", default="ad9999c416cc3584b649d3ce486e02b4", copy=True)
    data_transactionDate = fields.Date(string="transactionDate", default=fields.Date.today(), copy=True)
    data_regionCode = fields.Char(string="RegionCode", default="0101", size=20)
    data_districtCode = fields.Char(
        string="DistrictCode",
        default="010101",
        size=20,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('completed', 'Completed')],
            string="Status",
            default="draft",
        )

    summaryFlag = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="summaryFlag", default="Yes", copy=True)
    superedge_api_data_ids = fields.One2many('superedge.revenue.data', 'superedge_revenue_api_id', string="Superedge Revenues")
    transaction_result = fields.Text(string="Transaction result")

    def action_fetch_transactions(self):
        for rec in self:
            icp = self.env["ir.config_parameter"].sudo()

            auth_url = rec.auth_url or icp.get_param(
                "super_edge_api.auth_url", ""
            ).rstrip("/")

            transaction_url = rec.transaction_url or icp.get_param(
                "super_edge_api.transaction_url", ""
            )

            auth_payload = {
                "grantType": rec.grantType,
                "userName": rec.username,
                "password": rec.password,
            }

            try:
                auth_response = requests.post(
                    auth_url,
                    json=auth_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )
                

                auth_response.raise_for_status()
                auth_result = auth_response.json()

                _logger.info(
                    "SuperEdge Authentication Response: %s",
                    auth_result,
                )

                token = auth_result.get("accessToken")

                if not token:
                    raise ValidationError(
                        "Authentication succeeded but no access token was returned."
                    )

                payload = {
                    "serviceCode": rec.serviceCode,
                    "msgID": rec.transaction_msgID,
                    "appID": rec.transaction_appID,
                    "signature": rec.transactionSignature,
                    "data": {
                        "regionCode": rec.data_regionCode,
                        "districtCode": rec.data_districtCode,
                        "transactionDate": fields.Date.to_string(
                            rec.data_transactionDate
                        ),
                        "summaryFlag": rec.summaryFlag,
                    },
                    
                }

                # payload = {
                #     "serviceCode": "GetPostedTransactions",
                #     "msgID": "202604241141290616",
                #     "appID": "cdl",
                #     "signature": "ad9999c416cc3584b649d3ce486e02b4",
                #     "data": {
                #         "regionCode": "0101",
                #         "districtCode": "010101",
                #         "transactionDate": "2026-07-24",
                #         "summaryFlag": "Yes"
                #     }
                # }

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                transaction_response = requests.post(
                    transaction_url,
                    # 'http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/getTransactions',
                    json=payload,
                    headers=headers,
                    timeout=120,
                )
                _logger.info("Transaction URL = %r", transaction_url)
                _logger.info("Final URL = %s", transaction_response.request.url)
                _logger.info("Status Code: %s", transaction_response.status_code)
                _logger.info("Response Text: %s", transaction_response.text)
                _logger.info(
                                f"Transaction payloads supplied: => {payload}, {headers}"
                            )

                transaction_response.raise_for_status()

                transaction_result = transaction_response.json()

                rec.transaction_result = json.dumps(
                    transaction_result,
                    indent=4,
                )

                _logger.info(
                    "SuperEdge Transaction Response: %s",
                    transaction_result,
                )

                rec.get_response_value(transaction_result)

            except RequestException as e:
                _logger.exception("SuperEdge API Error")
                raise ValidationError(
                    f"Unable to connect to SuperEdge API.\n{str(e)}"
                )
    
    def getBranch(self, districtCode):
        if not districtCode:
            raise ValidationError("Please provide superedge district code")
        branch= self.env['multi.branch'].sudo().search([
            ('districtCode', '=', districtCode)
            ], limit=1)
        if not branch:
            raise ValidationError(f"""
                            There is no District related to the districtCode 
                            {districtCode}""")
        else:
            return branch.id
        
    def get_response_value(self, responseData):
        """The response will look as follows 
        responseData = {'message': 'Successful', 'returnCode': '200', 'data': {
                'regionCode': '0101', 
                'districtCode': '010101', 
                'postedStatus': 'Posted', 'debit': 0, 'chargeType': 
                'Power Charge', 'credit': 2578.14, 'transactionDate': '2026-07-24', 
                'currency': 'NGN'}, 'msgID': '202604241141290616'}"""
        message = responseData.get('message')
        if message == "Transaction not found":
            raise ValidationError("Date supplied or Branch code supplied might be incorrect")
        if message == 'Successful':
            values = []
            data = responseData.get('data')
            if data:
                if self.summaryFlag == "Yes":
                    districtCode = data.get('districtCode', '')
                    values.append(dict(
                        districtCode = districtCode,
                        credit = data.get('credit', 0),
                        transactionDate = data.get('transactionDate', False),
                        currency = data.get('currency'),
                        regionCode = data.get('regionCode'),
                        msgID = responseData.get('msgID'),
                        branch_id = self.getBranch(districtCode),
                    ))
                else:
                    # get all transactions without summing them
                    for tr in data.get('transactions'): 
                        districtCode = tr.get('districtCode', '')
                        '''The response is array of objects e.g [{}]'''
                        values.append(dict(
                            districtCode = districtCode,
                            credit = tr.get('credit', 0),
                            debit = tr.get('debit', 0),
                            postedStatus = tr.get('postedStatus', 0),
                            transactionDate = tr.get('transactionDate', False),
                            currency = tr.get('currency'),
                            chargeType = tr.get('chargeType'),
                            regionCode = tr.get('regionCode'),
                            msgID = tr.get('transactionId'),
                            branch_id = self.getBranch(districtCode)
                        ))
            _logger.info(
                    "Logged Values: %s",
                    values,
                )
            self.write({
                'superedge_api_data_ids': [(5, 0, 0)]
            })
                    
            self.superedge_api_data_ids = [(0,0, vals) for vals in values]
             
            # transactionLine = self.env['superedge.revenue.data'].create(values)
            self.state = 'completed'
        else:
            raise ValidationError(f"""
                            App call is not responsive \n
                            See response code: {responseData.get('returnCode')}""")
    def rerun_action(self):
        self.state = "draft"
            
    # def button_generate_revenue_moves(self):
    #     for rec in self.superedge_api_data_ids:
    #         account_move = self.env['account.move'].search([('super_edge_msgID', '=', rec.msgID)], limit=1)
    #         if not account_move:
    #             '''check to avoid duplicate'''
    #             # TODO; GENERATE ACCOUUNTMOVE DATA
    #             pass
        
    def archive_unwanted_revenue(self):
        for rec in self.superedge_api_data_ids:
            if rec.active: 
                for ln in rec.line_ids:
                    ln.active = False 
                rec.active = False
            else:
                for ln in rec.line_ids:
                    ln.active = True 
                rec.active = True

    def button_generate_revenue(self):
        account_move = self.env['account.move']
        for count, rec in enumerate(self.superedge_api_data_ids, 1):
            # self.validate_account_artifacts(count, rec)
            # Skip if already generated
            if rec.move_id:
                continue
            amount = rec.credit or rec.debit
            if amount <= 0:
                continue
            # Revenue Account
            config_settings = f"""
            Go to Settings --> Districts, select {rec.branch_id.name} district 
            receivable, revenue, and bank journal is configurured.
            """
            journal = rec.branch_id.bank_journal_id
            if not journal:
                raise UserError(f"No Journal found for district at line {count}\n {config_settings}")
            revenue_account = rec.branch_id.account_revenue_id
            if not revenue_account:
                raise UserError(f"No account found for district at line {count} - \n {config_settings}")
            receivable_revenue_account = rec.branch_id.receivable_revenue_account_id
            if not receivable_revenue_account:
                raise UserError(f"""No receivable account found for district at line {count}.\n {config_settings}""")
            
            # Bank/Receivable Account
            bank_account = receivable_revenue_account
            vals = {
                'move_type': 'entry',
                'date': rec.transactionDate or fields.Date.today(),
                'journal_id': journal.id,
                'ref': rec.msgID,
                'branch_id': rec.branch_id.id if rec.branch_id else False,
                'line_ids': [
                    (0, 0, {
                        'name': rec.chargeType or 'Revenue',
                        'account_id': bank_account.id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': rec.chargeType or 'Revenue',
                        'account_id': revenue_account.id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            }
            move = account_move.create(vals)
            move.action_post()
            rec.move_id = move.id

    # def action_fetch_transactions(self):
        #     """Authenticate and fetch posted transactions."""
        #     icp = self.env["ir.config_parameter"].sudo()
        #     auth_url = self.auth_url or icp.get_param("super_edge_api.auth_url", "").rstrip("/")
        #     transaction_url = self.transaction_url or icp.get_param("super_edge_api.transaction_url", "")
        #     grantType = self.grantType or icp.get_param("super_edge_api.grantType", "")
        #     password = self.password or icp.get_param("super_edge_api.password", "")
        #     username = self.username or icp.get_param("super_edge_api.username", "")
            
        #     # auth_url = "http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/token"
        #     # transaction_url = "http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/getTransactions"
    
        #     # Authentication payload
        #     # auth_payload = {
        #     #     "grantType": "password",
        #     #     "userName": "EEDC",
        #     #     "password": "A1234"
        #     # } 
        #     # Step 2 - Call Transactions API
        #     # payload = {
        #     #     "serviceCode": "GetPostedTransactions",
        #     #     "msgID": "202604241141290616",
        #     #     "appID": "cdl",
        #     #     "signature": "ad9999c416cc3584b649d3ce486e02b4",
        #     #     "data": {
        #     #         "regionCode": "0101",
        #     #         "districtCode": "010101",
        #     #         "transactionDate": "2026-07-24",
        #     #         "summaryFlag": "Yes"
        #     #     }
        #     # }
        
        #     auth_payload = {
        #         "grantType": grantType,
        #         "userName": username,
        #         "password": password
        #     }
        #     # Step 1 - Authenticate
        #     auth_response = requests.post(
        #         auth_url,
        #         json=auth_payload,
        #         headers={"Content-Type": "application/json"},
        #         timeout=60
        #     )
        #     auth_response.raise_for_status()
        #     auth_result = auth_response.json()
        #     print("Authentication Response: %s", auth_result)
    
        #     # Adjust this according to the API response
        #     token = auth_result.get("accessToken")
    
        #     if not token:
        #         raise ValidationError("""Authentication succeeded but no token was returned. \n \
        #               This was because your configuration parameters are incorrect""")
            
        #     payload = {
        #         "serviceCode": self.serviceCode,
        #         "msgID": self.transaction_msgID,
        #         "appID": self.transaction_appID,
        #         "signature": self.transactionSignature,
        #         "data": {
        #             "regionCode": self.data_regionCode,
        #             "districtCode": self.data_districtCode,
        #             "transactionDate": datetime.strftime(self.data_transactionDate, '%Y-%m-%d'), # "2026-07-24",
        #             "summaryFlag": self.summaryFlag
        #         }
        #     }
        #     headers = {
        #         "Authorization": f"Bearer {token}",
        #         "Content-Type": "application/json"
        #     }
    
        #     transaction_response = requests.post(
        #         transaction_url,
        #         json=payload,
        #         headers=headers,
        #         timeout=120
        #     )
    
        #     transaction_response.raise_for_status()
        #     transaction_result = transaction_response.json()
        #     self.transaction_result = transaction_result
        #     _logger.info("Transaction Response: %s", transaction_result)
        #     # TODO: Process/save the transactions here
        #     self.get_response_value(transaction_result)
     