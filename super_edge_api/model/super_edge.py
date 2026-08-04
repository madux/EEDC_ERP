# -*- coding: utf-8 -*-
import logging
import time

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# In-memory token cache, shared across calls within the same worker process.
# Keyed by base_url + appID so multiple configs (test/prod) don't collide.
_TOKEN_CACHE = {}

class SuperEdgeRevenueApi(models.Model):
    _name = "superedge.revenue.api"

    def action_fetch_transactions(self):
        """Authenticate and fetch posted transactions."""

        auth_url = "http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/token"
        transaction_url = "http://110.238.75.216:8580/amber2/collectmgmt_controller/erp/getTransactions"

        # Authentication payload
        auth_payload = {
            "grantType": "password",
            "userName": "EEDC",
            "password": "A1234"
        }

        # Step 1 - Authenticate
        auth_response = requests.post(
            auth_url,
            json=auth_payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        auth_response.raise_for_status()
        auth_result = auth_response.json()

        print("Authentication Response: %s", auth_result)

        # Adjust this according to the API response
        '''token = (
            auth_result.get("access_token")
            or auth_result.get("token")
            or auth_result.get("data", {}).get("access_token")
        )'''
        token = auth_result.get("accessToken")

        if not token:
            raise Exception("Authentication succeeded but no token was returned.")

        # Step 2 - Call Transactions API
        payload = {
            "serviceCode": "GetPostedTransactions",
            "msgID": "202604241141290616",
            "appID": "cdl",
            "signature": "ad9999c416cc3584b649d3ce486e02b4",
            "data": {
                "regionCode": "0101",
                "districtCode": "010101",
                "transactionDate": "2026-07-24",
                "summaryFlag": "Yes"
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        transaction_response = requests.post(
            transaction_url,
            json=payload,
            headers=headers,
            timeout=120
        )

        transaction_response.raise_for_status()
        transaction_result = transaction_response.json()

        print("Transaction Response: %s", transaction_result)

        # TODO: Process/save the transactions here

        print(transaction_result)
        
