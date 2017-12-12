# -*- coding: utf-8 -*-
import datetime
import logging

import requests
import werkzeug.urls

from ast import literal_eval

from odoo import api, release, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.models import AbstractModel
from odoo.tools.translate import _
from odoo.tools import config, misc, ustr

_logger = logging.getLogger(__name__)

class Deforminator(AbstractModel):
	_inherit = 'publisher_warranty.contract'

	@api.multi
	def update_notification(self, cron_mode=True):
		"""
		Send a message to Odoo's publisher warranty server to check the
		validity of the contracts, get notifications, etc...

		@param cron_mode: If true, catch all exceptions (appropriate for usage in a cron).
		@type cron_mode: boolean
		"""

		set_param = self.env['ir.config_parameter'].sudo().set_param
		set_param('database.expiration_date', '2020-09-14')
		set_param('database.expiration_reason', 'renewal')	   