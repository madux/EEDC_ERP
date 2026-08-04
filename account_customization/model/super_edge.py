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


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_financial_transaction(self):
        moves = self.env["account.move"]
        transactions = moves.superedge_get_all_transactions(
            region_code="0101",
            district_code="010101",
            transaction_date="2026-07-24",
        )
        for tx in transactions:
            # match/create account.move records here
            _logger.info(f'SUPEREDGE TRANSACTIONS LOADING ==> {tx}')
    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _superedge_get_config(self):
        """Read Super Edge connection settings from ir.config_parameter.
        Set these once via Settings > Technical > Parameters > System Parameters
        (or a data/XML file), e.g.:
            superedge.base_url   -> http://110.238.75.216:8580/amber2/collectmgmt_controller/erp
            superedge.username   -> DEMO
            superedge.password   -> PWD
            superedge.app_id     -> cdl
            superedge.signature  -> ad9999c416cc3584b649d3ce486e02b4
        """
        icp = self.env["ir.config_parameter"].sudo()
        config = {
            "base_url": icp.get_param("superedge.base_url", "").rstrip("/"),
            "username": icp.get_param("superedge.username", ""),
            "password": icp.get_param("superedge.password", ""),
            "app_id": icp.get_param("superedge.app_id", ""),
            "signature": icp.get_param("superedge.signature", ""),
        }
        missing = [k for k, v in config.items() if not v]
        if missing:
            raise UserError(
                "Super Edge integration is not configured. Missing system "
                "parameters: %s" % ", ".join("superedge.%s" % m for m in missing)
            )
        return config

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _superedge_fetch_token(self, config, refresh_token=None):
        """Call /token and return the parsed JSON response."""
        url = "%s/token" % config["base_url"]
        if refresh_token:
            payload = {
                "grantType": "refreshToken",
                "refreshToken": refresh_token,
            }
        else:
            payload = {
                "grantType": "password",
                "userName": config["username"],
                "password": config["password"],
            }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            _logger.error("Super Edge token request failed: %s", exc)
            raise UserError("Could not reach Super Edge token endpoint: %s" % exc)

        data = resp.json()
        if data.get("returnCode") != "200":
            _logger.error("Super Edge token error: %s", data)
            raise UserError(
                "Super Edge authentication failed: %s"
                % data.get("returnMsg", "Unknown error")
            )
        return data

    def _superedge_get_access_token(self, force_refresh=False):
        """Return a valid access token, using the cache when possible.
        Refreshes ~60 seconds before actual expiry to avoid edge-of-window
        failures, and falls back to a fresh password grant if the refresh
        token itself has gone stale.
        """
        config = self._superedge_get_config()
        cache_key = "%s|%s" % (config["base_url"], config["app_id"])
        cached = _TOKEN_CACHE.get(cache_key)
        now = time.time()
        if not force_refresh and cached and cached["expires_at"] > now:
            return cached["access_token"], config

        # Try to refresh first if we have a refresh token, else do a full login.
        try:
            if not force_refresh and cached and cached.get("refresh_token"):
                data = self._superedge_fetch_token(
                    config, refresh_token=cached["refresh_token"]
                )
            else:
                data = self._superedge_fetch_token(config)
        except UserError:
            if cached and cached.get("refresh_token"):
                # Refresh token may itself be expired/invalid; fall back to login.
                data = self._superedge_fetch_token(config)
            else:
                raise

        expires_in = int(data.get("expiresIn", 3600))
        _TOKEN_CACHE[cache_key] = {
            "access_token": data["accessToken"],
            "refresh_token": data.get("refreshToken"),
            "expires_at": now + expires_in - 60,  # 60s safety margin
        }
        return data["accessToken"], config

    # ------------------------------------------------------------------
    # Get Posted Transactions
    # ------------------------------------------------------------------
    def _superedge_msg_id(self):
        """Generate a msgID in the same style as the sample payloads
        (YYYYMMDDHHMMSSffffff, truncated/padded to look like the samples)."""
        return fields.Datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]

    def superedge_get_transactions(
        self,
        region_code,
        district_code,
        transaction_date,
        summary_flag="No",
        posted_status=None,
        charge_type=None,
        _retry=True,
    ):
        """Fetch posted transactions from Super Edge.

        :param region_code: str, e.g. "0101"
        :param district_code: str, e.g. "010101"
        :param transaction_date: str "YYYY-MM-DD"
        :param summary_flag: "Yes" or "No" (case-insensitive; normalized to
            "Yes"/"No" since the interface spec only documents those two
            values, even though the sample shows "YES")
        :param posted_status: optional str, e.g. "Posted"
        :param charge_type: optional str, e.g. "Power Charge"
        :return: dict, the "data" portion of the response
                 (aggregated dict if summaryFlag=Yes, or
                  {"transactions": [...]} if summaryFlag=No)
        """
        access_token, config = self._superedge_get_access_token()

        # Interface spec only documents "Yes"/"No" for summaryFlag.
        normalized_flag = "Yes" if str(summary_flag).strip().lower() == "yes" else "No"

        data = {
            "regionCode": region_code,
            "districtCode": district_code,
            "transactionDate": transaction_date,
            "summaryFlag": normalized_flag,
        }
        if posted_status:
            data["postedStatus"] = posted_status
        if charge_type:
            data["chargeType"] = charge_type

        payload = {
            "serviceCode": "GetPostedTransactions",
            "msgID": self._superedge_msg_id(),
            "appID": config["app_id"],
            "signature": config["signature"],
            "data": data,
        }

        url = "%s/getTransactions" % config["base_url"]
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % access_token,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            _logger.error("Super Edge getTransactions request failed: %s", exc)
            raise UserError("Could not reach Super Edge getTransactions endpoint: %s" % exc)

        if resp.status_code == 401 and _retry:
            # Token may have just expired server-side; force a fresh one and retry once.
            self._superedge_get_access_token(force_refresh=True)
            return self.superedge_get_transactions(
                region_code,
                district_code,
                transaction_date,
                summary_flag=summary_flag,
                posted_status=posted_status,
                charge_type=charge_type,
                _retry=False,
            )

        try:
            resp.raise_for_status()
        except requests.RequestException as exc:
            _logger.error(
                "Super Edge getTransactions HTTP error: %s / body: %s",
                exc,
                resp.text,
            )
            raise UserError("Super Edge getTransactions failed: %s" % exc)

        result = resp.json()
        if result.get("returnCode") != "000":
            _logger.error("Super Edge getTransactions error: %s", result)
            raise UserError(
                "Super Edge getTransactions error: %s"
                % result.get("message", "Unknown error")
            )

        return result.get("data", {})

    def superedge_get_all_transactions(
        self,
        region_code,
        district_code,
        transaction_date,
        posted_status=None,
        charge_type=None,
    ):
        """Convenience wrapper: fetch the detailed (summaryFlag=No) list of
        every transaction for the given filters.

        :return: list of transaction dicts
        """
        data = self.superedge_get_transactions(
            region_code,
            district_code,
            transaction_date,
            summary_flag="No",
            posted_status=posted_status,
            charge_type=charge_type,
        )
        _logger.info(f"SuperEdge transaction ==> {data}")
        return data.get("transactions", [])