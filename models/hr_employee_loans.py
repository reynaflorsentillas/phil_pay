# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time
from datetime import datetime, date, timedelta
from datetime import timezone
from datetime import time as datetime_time
from dateutil import relativedelta
import logging
import pytz
import base64
import os
import time
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class hr_employee_loans(models.Model):
	_name = 'hr.employee.loans'
	_inherit = "mail.thread"
	_description = 'Employee Loans'

	name = fields.Char('Name', track_visibility='onchange',default=lambda self: _('New Loans'),copy=False)
	loan_type = fields.Selection([('sss', 'SSS Loans'),('pagibig', 'Pagibig Loans'),('cash_advance', 'Cash Advance'),('other', 'Other')], string='Loan Type', track_visibility='onchange')
	loan_description = fields.Char('Other Loan Description')
	amortization_amount = fields.Float('Amortization Amount Per Cutoff', required=True, track_visibility='onchange')
	total_amortization_amount = fields.Float('Total Loan Amount', required=True, track_visibility='onchange')
	payroll_cutoff_payment_date = fields.Date('Payment Start Date', required=True, help='Payroll Start Date to be Paid', track_visibility='onchange')
	no_of_payments = fields.Integer('No. of Payments', required=True, track_visibility='onchange')
	employee_id = fields.Many2one('hr.employee', string='Employee', track_visibility='onchange')
	loan_sal_rule_id = fields.Many2one('hr.salary.rule', string='Loan Type', track_visibility='onchange')
	state = fields.Selection([('draft', 'Draft'),('approved', 'Approved'),('cancel', 'Cancel'),('paid', 'Paid') ], string='State', track_visibility='onchange', default='draft')


	@api.multi
	def approve_loan(self):
		self.ensure_one()
		self.write({'state': 'approved'})

	@api.multi
	def cancel_loan(self):
		self.ensure_one()
		self.write({'state': 'cancel'})

	@api.multi
	def paid_loan(self):
		self.ensure_one()
		self.write({'state': 'paid'})

	@api.model
	def create(self,vals):
		if vals.get('name', _('New Loans')) == _('New Loans'):
			vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.loans')
		return super(hr_employee_loans, self).create(vals)

class hr_salary_rule(models.Model):
	_inherit='hr.salary.rule'

	is_loan_rule = fields.Boolean(string='Appears on Employee Loan', default=False)

