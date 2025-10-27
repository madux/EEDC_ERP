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
import traceback
from psycopg2 import IntegrityError
import odoorpc as orpc

_logger = logging.getLogger(__name__)


class MigrationRpc(models.Model):
    _name = 'migration.odoo.rpc'

    def import_account_move(self):
        orpc.ODOO()
        