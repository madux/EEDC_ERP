# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BaseCompanyMonkeyPatch(models.AbstractModel):
    _inherit = 'base'

    def _check_company(self, fnames=None):
        """
        Monkey-patch wrapper for base._check_company.

        If system parameter 'check.company.strict' is False, suppress the UserError
        produced by the original implementation (log a warning instead).
        Otherwise, call the original behaviour.
        """
        ir_config = self.env['ir.config_parameter'].sudo()
        param = ir_config.get_param('check.company.strict')# , 'True')
        check_strict = str(param).strip().lower() in ('1', 'true', 'yes', True)

        # When strict checking is enabled, keep original behaviour
        if check_strict:
            return super(BaseCompanyMonkeyPatch, self)._check_company(fnames=fnames)

        # When strict checking disabled: call original but swallow UserError
        try:
            return super(BaseCompanyMonkeyPatch, self)._check_company(fnames=fnames)
        except UserError as e:
            # Log a short warning with the error text for debugging
            raise UserError("fire born")
            _logger.warning("Incompatible companies detected but 'check.company.strict'=False — suppressing UserError: %s", e)
            # Silently ignore the error and continue
            return