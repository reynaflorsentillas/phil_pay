# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
from datetime import datetime, date, timedelta
from datetime import timezone
from datetime import time as datetime_time
from dateutil import relativedelta
import logging
import pytz
from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)

class PhilHolidays(models.Model):
	_name = 'phil_pay.holidays'
	_description = 'Philippine Holidays'

	name = fields.Char(
		string='Holiday Name',
		size=64,
		required=True,
		readonly=False
		)

	holiday_date = fields.Date(
		string='Holiday Date',
		required=True
	)

	holiday_type = fields.Selection([('1', 'Regular'),
		('2', 'Special')])

class AttendanceExtension(models.Model):
	_inherit = 'hr.attendance'

	is_regular_holiday = fields.Boolean(
		string='Regular Holiday',
		compute = '_compute_is_regular_holiday',
		store=True
	)

	is_special_holiday = fields.Boolean(
		string='Special Holiday',
		compute = '_compute_is_special_holiday',
		store=True
	)

	is_double_holiday = fields.Boolean(
		string='Double Holiday',
		compute = '_compute_is_double_holiday',
		store=True
	)

	is_rest_day = fields.Boolean(
		string='Rest Day',
		compute= '_compute_is_rest_day',
		store=True,
		
	)

	late_hours = fields.Float(
		string='Lates in Hours',
		readonly=True,
		compute = '_compute_lates',
		store=True
	)

	raw_attendance_id = fields.Many2one(
		string='Raw Attendance ID',
		relation='attendance.raw.main'
	)

	@api.depends('late_hours', 'is_rest_day')
	def _compute_lates(self):
		for rec in self:
			if rec.is_rest_day == False:
				d1 = fields.Datetime.from_string(rec.check_in)
				day_of_week = d1.weekday()
				r = rec.employee_id.contract_id.resource_calendar_id.attendance_ids.search([('dayofweek','=', day_of_week)])
				# check_in_time = d1.time()

				user_tz = self.env.user.tz
				#raise Warning(user_tz)
				local = pytz.timezone(user_tz)


				td = timedelta(hours= r[0].hour_from)
				work_time = (datetime(d1.year,d1.month, d1.day)+td)
				work_time = local.localize(work_time)
				rec.late_hours = 0
				d1 = d1.replace(tzinfo=local)
				if d1.astimezone(local) > work_time:				
					late_result = d1.astimezone(local) - work_time
					
					# subtract check in time
					if late_result.seconds >= 0:
						if (late_result.seconds / 3600) < 8:
							rec.late_hours = late_result.seconds / 3600

	night_hours = fields.Float(
	    string='Night Hours',
	    readonly=True, 
	    compute= '_compute_night_hours',
	    store=True,
	)

	@api.depends('night_hours', 'check_out', 'check_in')
	def _compute_night_hours(self):
		for rec in self:
			try:
				user_tz = self.env.user.tz
				local = pytz.timezone(user_tz)
				d1 = fields.Datetime.from_string(rec.check_out).astimezone(local)
				d2 = fields.Datetime.from_string(rec.check_in).astimezone(local)
				night_minutes = 0
				delta = timedelta(minutes=1)
				while d2 < d1:
					if d2.hour > 22 or d2.hour < 6:
						night_minutes += 1
					d2 += delta

				rec.night_hours = night_minutes / 60
			except Exception as e:
				pass
			

	undertime_hours = fields.Float(
	    string='Undertime',
	    readonly=True, 
	    compute= '_compute_undertime',
	    store=True,
	)

	@api.depends('undertime_hours', 'late_hours', 'worked_hours', 'is_rest_day')
	def _compute_undertime(self):
		for rec in self:
			if rec.is_rest_day == False:
				rec.undertime_hours = 0
				if rec.worked_hours - 1 < 8:
					rec.undertime_hours = 8 - (rec.worked_hours - 1) - rec.late_hours			

	overtime_hours = fields.Float(
	    string='Overtime Hours',
	    readonly=True, 
	    compute = '_compute_overtime',
	    store=True,
	)

	@api.depends('worked_hours')
	def _compute_overtime(self):
		for rec in self:
			rec.overtime_hours = 0
			if rec.worked_hours - 1 > 9 and rec.worked_hours - 1 < 14:
				rec.overtime_hours = (rec.worked_hours - 1) - 8



	regular_holiday_hours = fields.Float(
		string='Regular Holiday Hours',
		readonly=True, 
		compute = '_compute_holiday_hours',
		store=True,
	)

	@api.depends('is_regular_holiday','check_in')
	@api.multi
	def _compute_is_regular_holiday(self):
		for rec in self:
			#raise Warning(1111)
			#user_tz = self.env.user.tz
			#local = pytz.timezone(user_tz)
			#delta = timedelta(days=1)
			fmt = '%Y-%m-%d %H:%M:%S'
			check_in = rec.check_in
			d1 = datetime.strptime(rec.check_in, fmt).date() #+ delta

			r = self.env['phil_pay.holidays'].search([('holiday_date', '=', d1.strftime('%Y-%m-%d')),('holiday_type','=','1')])
			#raise Warning(check_in)
			if r:
				rec.is_regular_holiday = True
			else:
				rec.is_regular_holiday = False

	@api.depends('is_special_holiday','check_in')
	def _compute_is_special_holiday(self):
		for rec in self:
			#delta = timedelta(days=1)
			fmt = '%Y-%m-%d %H:%M:%S'
			d1 = datetime.strptime(rec.check_in, fmt).date() #+ delta
			r = self.env['phil_pay.holidays'].search([('holiday_date', '=', d1.strftime('%Y-%m-%d')),('holiday_type','=','2')])
			if r:
				rec.is_special_holiday = True
			else:
				rec.is_special_holiday = False


	@api.depends('is_double_holiday','check_in')
	def _compute_is_double_holiday(self):
		for rec in self:
			fmt = '%Y-%m-%d %H:%M:%S'
			#delta = timedelta(days=1)
			d1 = datetime.strptime(rec.check_in, fmt).date() #+ delta
			r = self.env['phil_pay.holidays'].search_count([('holiday_date', '=', d1.strftime('%Y-%m-%d'))])
			if r > 1:
				rec.is_double_holiday = True
			else:
				rec.is_double_holiday = False

	@api.depends('is_rest_day', 'check_in')
	def _compute_is_rest_day(self):
		for rec in self:				
			fmt = '%Y-%m-%d %H:%M:%S'
			d1 = datetime.strptime(rec.check_in, fmt).date()
			day_of_week = d1.weekday()
			search_result = rec.employee_id.contract_id.resource_calendar_id.attendance_ids.search_count([('dayofweek','=', day_of_week)])
			if search_result != 0:
				rec.is_rest_day = False
			else:
				rec.is_rest_day = True



	@api.depends('regular_holiday_hours', 'worked_hours')
	def _compute_holiday_hours(self):
		for rec in self:
			fmt = '%Y-%m-%d %H:%M:%S'
			d1 = datetime.strptime(rec.check_in, fmt).date()
			r = self.env['phil_pay.holidays'].search([('holiday_date', '=', d1.strftime('%Y-%m-%d'))])
			if r:
				if rec.worked_hours >= 8:
					rec.regular_holiday_hours = 8
				else:
					rec.regular_holiday_hours = rec.worked_hours

class PayslipComputations(models.Model):
	_inherit = 'hr.payslip'


	tax_amount =fields.Float(
		string='Tax',
	)

	convert_leaves = fields.Boolean(
		string='Convert Leaves?',
		default=False
	)

	is_backpay = fields.Boolean(
		string='Back Pay?',
		default=False
	)	

	@api.multi
	def compute_sheet(self):
		res = super(PayslipComputations, self).compute_sheet()
		if res:
			for payslip in self:
				if payslip.line_ids:
					amt = 0.00
					for line in payslip.line_ids:
						if line.code in ['BASIC_BI_MONTHLY']:
							amt += line.total
						elif line.code in ['SSS_CONTRI','PAG_CONTRI','PHC_CONTRI',]:
							amt -= line.total
					amt = self.get_tax(amt, payslip.employee_id)
					payslip.write({'tax_amount': amt})
		return res

	@api.model
	def _get_payslip_lines(self, contract_ids, payslip_id):
		result = super(PayslipComputations,self)._get_payslip_lines(contract_ids, payslip_id)
		if result:
			#Get Loans
			payslip_obj = self.env['hr.payslip'].search([('id','=', payslip_id)])
			loans_obj = self.env['hr.employee.loans'].search([('state','=', 'approved'),
															  ('employee_id','=', payslip_obj.employee_id.id),
															  ('payroll_cutoff_payment_date','>=', payslip_obj.date_from)])

			for loan in loans_obj:
				int_res = 0
				while(int_res<= len(result)-1):
					_logger.info(result[int_res]['code'])
					if result[int_res]['code'] == loan.loan_sal_rule_id.code:
						result[int_res]['amount'] = loan.amortization_amount
						result[int_res]['amount_python_compute'] = loan.amortization_amount						
						result[int_res]['loan_payment_tempo_id'] = loan.id

						rule_obj = self.env['hr.salary.rule'].search([('code','=',loan.loan_sal_rule_id.code)])
						rule_obj.write({'amount_python_compute': 'result=' + str(loan.amortization_amount)})
						
					int_res +=1
		return result

	@api.onchange('employee_id', 'date_from', 'date_to')
	def onchange_employee2(self):

		lines = []
		# Ordinary day 100% or 1
		reg_days= self.env['hr.attendance'].search_count([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		reg_days_worked = {
				'name': 'Total Regular Days Worked',
				'code': 'REGDAYS',
				'amount': reg_days,
				'contract_id':  self.contract_id
				}

		lines.append(reg_days_worked)
		# Sunday or rest day 130% or 1.3
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Rest Day Hours Worked', #C1
				'code': 'RD', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		
		# Special day 130% or 1.3

		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Special Holiday Hours Worked', #C1
				'code': 'SH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)

		# Special day falling on rest day 150% or 1.5
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Rest Day and Special Holiday Hours Worked', #C1
				'code': 'RDSH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Regular Holiday 200% or 2
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Regular Holiday Hours Worked', #C1
				'code': 'RH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Regular Holiday falling on rest day 260% or 2.6
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Rest Day and Regular Holiday Hours Worked', #C1
				'code': 'RDRH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Double holiday 300% or 3
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Double Holiday Hours Worked', #C1
				'code': 'DH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Double holiday falling on rest day 390% or 3.9
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to)])
		for x in res:
			if x.worked_hours > 5 and x.worked_hours <= 9:
				x.worked_hours = x.worked_hours - 1
			elif x.worked_hours > 9:
				x.worked_hours = 8
			else:
				x.worked_hours = x.worked_hours
			amt += x.worked_hours
		units_worked = {
				'name': 'Total Rest Day and Double Holiday Hours Worked', #C1
				'code': 'RDDH', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Ordinary day, night shif t 1 x 1.1 = 1.1 or 110%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Ordinary Day Night Shift Hours Worked', #C1
				'code': 'NS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Rest day, night shif t 1.3 x 1.1 = 1.43 or 143%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Rest Day Night Shift Hours Worked', #C1
				'code': 'RDNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Special day, night shif t 1.3 x 1.1 = 1.43 or 143%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Special Day Night Shift Hours Worked', #C1
				'code': 'SDNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Special day, rest day, night shif t 1.5 x 1.1 = 1.65 or 165%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Special Day Rest Day Night Shift Hours Worked', #C1
				'code': 'SDRDNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Regular Holiday, night shif t 2 x 1.1 = 2.2 or 220%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Regular Holiday Night Shift Hours Worked', #C1
				'code': 'RHNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Regular Holiday, rest day, night shif t 2.6 x 1.1 = 2.86 or 286%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Regular Holiday Rest Day Night Shift Hours Worked', #C1
				'code': 'RHRDNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Double holiday, night shif t 3 x 1.1 = 3.3 or 330%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Double Holiday Night Shift Hours Worked', #C1
				'code': 'DHNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Double holiday, rest day,night shif t 3.9 x 1.1 = 4.29 or 429%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('night_hours','>',0)])
		for x in res:
			if x.night_hours > 5 and x.night_hours <= 9:
				x.night_hours = x.night_hours - 1
			elif x.night_hours > 9:
				x.night_hours = 8
			else:
				x.night_hours = x.night_hours
			amt += x.night_hours
		units_worked = {
				'name': 'Double Holiday Rest Day Night Shift Hours Worked', #C1
				'code': 'DHRDNS', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}

		lines.append(units_worked)
		# Ordinary day, overtime (OT) 1 x 1.25 = 1.25 or 125%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours

		units_worked = {
				'name': 'Ordinary Day Overtime', #C1
				'code': 'OT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Rest day, overtime 1.3 x 1.3 = 1.69 or 169%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Rest Day Overtime', #C1
				'code': 'RDOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Special day, overtime 1.3 x 1.3 = 1.69 or 169%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Special Day Overtime', #C1
				'code': 'SHOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Special day, rest day, overtime 1.5 x 1.3 = 1.95 or 195%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Special Day Rest Day Overtime', #C1
				'code': 'SDRDOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Regular Holiday, overtime 2 x 1.3 = 2.6 or 260%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Regular Holiday Overtime', #C1
				'code': 'RHOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Regular Holiday, rest day, overtime 2.6 x 1.3 = 3.38 or 338%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
			('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Regular Holiday Rest Day Overtime', #C1
				'code': 'RHRDOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Double holiday, overtime 3 x 1.3 = 3.9 or 390%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Double Holiday Overtime', #C1
				'code': 'DHOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Double holiday, rest day, overtime 3.9 x 1.3 = 5.07 or 507%
		amt = 0
		res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
			('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('overtime_hours','>',0)])
		for x in res:
			amt += x.overtime_hours
		units_worked = {
				'name': 'Double Holiday Rest Day Overtime', #C1
				'code': 'DHRDOT', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		# Ordinary day, night shif t, overtime 1 x 1.1 x 1.25 = 1.375 or 137.5%
		# Rest day, night shif t, overtime 1.3 x 1.1 x 1.3 = 1.859 or 185.9%
		# Special day, night shif t, overtime 1.3 x 1.1 x 1.3 = 1.859 or 185.9%
		# Special day, rest day, night shift, OT 1.5 x 1.1 x 1.3 = 2.145 or 214.5%
		# Regular Holiday, night shif t, OT 2 x 1.1 x 1.3 = 2.86 or 286%
		# Reg. Holiday, rest day, night shift, OT 2.6 x 1.1 x 1.3 = 3.718 or 371.8%
		# Double holiday, night shif t, OT 3 x 1.1 x 1.3 = 4.29 or 429%
		# Double holiday, rest day, night shift, OT 3.9 x 1.1 x 1.3 = 5.577 or 557.7%
		#SH Not Worked
		#Lates
		amt = 0
		res= self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id),
			('check_in', '>=', self.date_from), ('check_out', '<=', self.date_to), ('late_hours','>',0)])
		for x in res:
			amt += x.late_hours
		units_worked = {
				'name': 'Lates in Hours', #C1
				'code': 'Lates', #C2
				'amount': amt,
				'contract_id':  self.contract_id
				}
		lines.append(units_worked)
		#Absences
		date_from = self.date_from
		date_to = self.date_to
		fmt = '%Y-%m-%d'
		d1 = datetime.strptime(date_from, fmt)
		d2 = datetime.strptime(date_to, fmt)    
		total_days = (d2-d1).days
		d = d1
		delta = timedelta(days=1)

		#Check for # of workdays
		total_workdays = 0
		while d <= d2:
			is_holiday = False
			r = self.env['phil_pay.holidays'].search_count([('holiday_date', '=', d.strftime(fmt))])
			if r != 0:
				#its a holiday
				is_holiday = True
			#check if work day
			day_of_week = d.weekday()
			search_result = self.contract_id.resource_calendar_id.attendance_ids.search_count([('dayofweek','=', day_of_week)])
			if search_result != 0:
				is_work_day = True
				if is_holiday == False:
					total_workdays += 1	
			
			d += delta

		if reg_days < total_workdays:
			val = total_workdays - reg_days
			units_worked = {
				'name': 'Absences in Days', #C1
				'code': 'Absent', #C2
				'amount': val,
				'contract_id':  self.contract_id
				}
			lines.append(units_worked)
		else:
			units_worked = {
				'name': 'Absences in Days', #C1
				'code': 'Absent', #C2
				'amount': 0,
				'contract_id':  self.contract_id
				}
			lines.append(units_worked)

		self.input_line_ids = lines

	def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
		result = super(PayslipComputations, self).onchange_employee_id(date_from, date_to, employee_id, contract_id)
		#raise Warning(res)
		if result:
			#raise Warning(result)
			contract_id = result['value']['contract_id']
			lines = []
			# Ordinary day 100% or 1
			reg_days= self.env['hr.attendance'].search_count([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			reg_days_worked = {
					'name': 'Total Regular Days Worked',
					'code': 'REGDAYS',
					'amount': reg_days,
					'contract_id':  contract_id
					}

			lines.append(reg_days_worked)
			# Sunday or rest day 130% or 1.3
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Rest Day Hours Worked', #C1
					'code': 'RD', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			
			# Special day 130% or 1.3

			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Special Holiday Hours Worked', #C1
					'code': 'SH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)

			# Special day falling on rest day 150% or 1.5
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Rest Day and Special Holiday Hours Worked', #C1
					'code': 'RDSH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Regular Holiday 200% or 2
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Regular Holiday Hours Worked', #C1
					'code': 'RH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Regular Holiday falling on rest day 260% or 2.6
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Rest Day and Regular Holiday Hours Worked', #C1
					'code': 'RDRH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Double holiday 300% or 3
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Double Holiday Hours Worked', #C1
					'code': 'DH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Double holiday falling on rest day 390% or 3.9
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to)])
			for x in res:
				if x.worked_hours > 5 and x.worked_hours <= 9:
					x.worked_hours = x.worked_hours - 1
				elif x.worked_hours > 9:
					x.worked_hours = 8
				else:
					x.worked_hours = x.worked_hours
				amt += x.worked_hours
			units_worked = {
					'name': 'Total Rest Day and Double Holiday Hours Worked', #C1
					'code': 'RDDH', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Ordinary day, night shif t 1 x 1.1 = 1.1 or 110%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Ordinary Day Night Shift Hours Worked', #C1
					'code': 'NS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Rest day, night shif t 1.3 x 1.1 = 1.43 or 143%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Rest Day Night Shift Hours Worked', #C1
					'code': 'RDNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Special day, night shif t 1.3 x 1.1 = 1.43 or 143%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Special Day Night Shift Hours Worked', #C1
					'code': 'SDNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Special day, rest day, night shif t 1.5 x 1.1 = 1.65 or 165%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Special Day Rest Day Night Shift Hours Worked', #C1
					'code': 'SDRDNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Regular Holiday, night shif t 2 x 1.1 = 2.2 or 220%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Regular Holiday Night Shift Hours Worked', #C1
					'code': 'RHNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Regular Holiday, rest day, night shif t 2.6 x 1.1 = 2.86 or 286%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Regular Holiday Rest Day Night Shift Hours Worked', #C1
					'code': 'RHRDNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Double holiday, night shif t 3 x 1.1 = 3.3 or 330%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Double Holiday Night Shift Hours Worked', #C1
					'code': 'DHNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Double holiday, rest day,night shif t 3.9 x 1.1 = 4.29 or 429%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('night_hours','>',0)])
			for x in res:
				if x.night_hours > 5 and x.night_hours <= 9:
					x.night_hours = x.night_hours - 1
				elif x.night_hours > 9:
					x.night_hours = 8
				else:
					x.night_hours = x.night_hours
				amt += x.night_hours
			units_worked = {
					'name': 'Double Holiday Rest Day Night Shift Hours Worked', #C1
					'code': 'DHRDNS', #C2
					'amount': amt,
					'contract_id':  contract_id
					}

			lines.append(units_worked)
			# Ordinary day, overtime (OT) 1 x 1.25 = 1.25 or 125%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours

			units_worked = {
					'name': 'Ordinary Day Overtime', #C1
					'code': 'OT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Rest day, overtime 1.3 x 1.3 = 1.69 or 169%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Rest Day Overtime', #C1
					'code': 'RDOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Special day, overtime 1.3 x 1.3 = 1.69 or 169%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Special Day Overtime', #C1
					'code': 'SHOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Special day, rest day, overtime 1.5 x 1.3 = 1.95 or 195%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', True), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Special Day Rest Day Overtime', #C1
					'code': 'SDRDOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Regular Holiday, overtime 2 x 1.3 = 2.6 or 260%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Regular Holiday Overtime', #C1
					'code': 'RHOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Regular Holiday, rest day, overtime 2.6 x 1.3 = 3.38 or 338%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', False), 
				('is_regular_holiday', '=', True), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Regular Holiday Rest Day Overtime', #C1
					'code': 'RHRDOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Double holiday, overtime 3 x 1.3 = 3.9 or 390%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', False), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Double Holiday Overtime', #C1
					'code': 'DHOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Double holiday, rest day, overtime 3.9 x 1.3 = 5.07 or 507%
			amt = 0
			res= self.env['hr.attendance'].search([('is_rest_day', '=', True), ('is_double_holiday', '=', True), 
				('is_regular_holiday', '=', False), ('is_special_holiday', '=', False), ('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('overtime_hours','>',0)])
			for x in res:
				amt += x.overtime_hours
			units_worked = {
					'name': 'Double Holiday Rest Day Overtime', #C1
					'code': 'DHRDOT', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			# Ordinary day, night shif t, overtime 1 x 1.1 x 1.25 = 1.375 or 137.5%
			# Rest day, night shif t, overtime 1.3 x 1.1 x 1.3 = 1.859 or 185.9%
			# Special day, night shif t, overtime 1.3 x 1.1 x 1.3 = 1.859 or 185.9%
			# Special day, rest day, night shift, OT 1.5 x 1.1 x 1.3 = 2.145 or 214.5%
			# Regular Holiday, night shif t, OT 2 x 1.1 x 1.3 = 2.86 or 286%
			# Reg. Holiday, rest day, night shift, OT 2.6 x 1.1 x 1.3 = 3.718 or 371.8%
			# Double holiday, night shif t, OT 3 x 1.1 x 1.3 = 4.29 or 429%
			# Double holiday, rest day, night shift, OT 3.9 x 1.1 x 1.3 = 5.577 or 557.7%
			#SH Not Worked
			#Lates
			amt = 0
			res= self.env['hr.attendance'].search([('employee_id', '=', employee_id),
				('check_in', '>=', date_from), ('check_out', '<=', date_to), ('late_hours','>',0)])
			for x in res:
				amt += x.late_hours
			units_worked = {
					'name': 'Lates in Hours', #C1
					'code': 'Lates', #C2
					'amount': amt,
					'contract_id':  contract_id
					}
			lines.append(units_worked)
			#Absences
			date_from = date_from
			date_to = date_to
			fmt = '%Y-%m-%d'
			d1 = datetime.strptime(date_from, fmt)
			d2 = datetime.strptime(date_to, fmt)    
			total_days = (d2-d1).days
			d = d1
			delta = timedelta(days=1)

			#Check for # of workdays
			total_workdays = 0
			while d <= d2:
				is_holiday = False
				r = self.env['phil_pay.holidays'].search_count([('holiday_date', '=', d.strftime(fmt))])
				if r != 0:
					#its a holiday
					is_holiday = True
				#check if work day
				day_of_week = d.weekday()
				contract_object = self.env['hr.contract'].search([('id','=', contract_id)])
				search_result = contract_object.resource_calendar_id.attendance_ids.search_count([('dayofweek','=', day_of_week)])
				if search_result != 0:
					is_work_day = True
					if is_holiday == False:
						total_workdays += 1	
				
				d += delta

			if reg_days < total_workdays:
				val = total_workdays - reg_days
				units_worked = {
					'name': 'Absences in Days', #C1
					'code': 'Absent', #C2
					'amount': val,
					'contract_id':  contract_id
					}
				lines.append(units_worked)
			else:
				units_worked = {
					'name': 'Absences in Days', #C1
					'code': 'Absent', #C2
					'amount': 0,
					'contract_id':  contract_id
					}
				lines.append(units_worked)
			
			result['value']['input_line_ids'] = lines

		return result

	@api.model
	def get_tax(self, amount=0.00, employee_id=''):
		tax_table_exemption = {
				1: [0, 0],
				2: [0, .05],
				3: [20.83,.10],
				4: [104.17,.15],
				5: [354.17, .20],
				6: [937.50, .25],
				7: [2083.33, .30],
				8: [5208.33, .32],
				9: [5208.33, .32],
		}
		tax_table = {
			'S/ME': {
				1: [1],
				2: [2083.00],
				3: [2500.00],
				4: [3333.00],
				5: [5000.00],
				6: [7917.00],
				7: [12500.00],
				8: [22917.00],
				9: [99999999.00],
			},
			'S/ME1': {
				1: [1],
				2: [3125.00],
				3: [3542.00],
				4: [4375.00],
				5: [6042.00],
				6: [8958.00],
				7: [13542.00],
				8: [23958.00],
				9: [99999999.00],
			},
			'S/ME2': {
				1: [1],
				2: [4162.00],
				3: [4583.00],
				4: [5417.00],
				5: [7083.00],
				6: [10000.00],
				7: [14583.00],
				8: [25000.00],
				9: [99999999.00],
			},
			'S/ME3': {
				1: [1],
				2: [5208.00],
				3: [5625.00],
				4: [6458.00],
				5: [8125.00],
				6: [11042.00],
				7: [15625.00],
				8: [26042.00],
				9: [99999999.00],
			},
			'S/ME4': {
				1: [1],
				2: [6250.00],
				3: [6667.00],
				4: [7500.00],
				5: [9167.00],
				6: [12083.00],
				7: [16667.00],
				8: [27083.00],
				9: [99999999.00],
			},
		}

		#Check MArital Status
		stat = 'S/ME'
		raw_tax = 0.00
		if employee_id.children > 0:
			if employee_id.children >=4:
				stat = stat + '4'
			else:
				stat = stat + '' + str(employee_id.children)
		table_tax_now = tax_table[stat]
		#raise Warning(table_tax_now)
		for table in table_tax_now:

			if amount < table_tax_now[table][0]:
				if table_tax_now[table] == 9:
					raw_tax = round(table_tax_now[8][0] - amount,2)
				else:
					#raise Warning(stat)
					raw_tax = round(amount-table_tax_now[table-1 if table-1 > 0 else 1 ][0],2)
				_logger.info(tax_table[stat])
				_logger.info(raw_tax)
				_logger.info((tax_table_exemption[table-1 if table-1 > 0 else 1][0]))
				_logger.info((raw_tax * tax_table_exemption[table-1 if table-1 > 0 else 1][1]))
				final_tax = tax_table_exemption[table-1 if table-1 > 0 else 1][0] + (raw_tax * tax_table_exemption[table-1 if table-1 > 0 else 1][1])		
				return final_tax

	@api.multi
	def action_payslip_done(self):
		result = super(PayslipComputations,self).action_payslip_done()
		if result:
			#Check If Theres a Loan Payment, Then update the Employee Loan Table
			for payslip in self:
				for payslip_detail in payslip.details_by_salary_rule_category:
					if payslip_detail.salary_rule_id.is_loan_rule == True:
						loan_obj = self.env['hr.employee.loans'].search([('id', '=', payslip_detail.loan_payment_tempo_id.id)])
						if loan_obj:
							write_list = {}
							write_list = {'no_of_payments': loan_obj.no_of_payments -1}						
							if loan_obj.no_of_payments -1 <=0:
								write_list['state'] = 'paid'
								loan_obj.write(write_list)
		return result


class PayslipLines(models.Model):
	_inherit = 'hr.payslip.line'

	loan_payment_id = fields.Many2one(
			'hr.employee.loans',
			string='Employee Loans'
		)
	loan_payment_tempo_id= fields.Many2one(
			'hr.employee.loans',
			string='Temporary Employee Loans'
		)


class EmployeeExtension(models.Model):
	_inherit = 'hr.employee'


	sss_number = fields.Char(
		string='SSS',
	)

	biometric_number = fields.Char(
		string='Biometric ID'
	)

   
	tin_number = fields.Char(
		string='TIN',
	)

	hdmf_number = fields.Char(
		string='HDMF',
	)

	philhealth_number = fields.Char(
		string='PhilHealth',
	)

	education_ids = fields.One2many(
		'phil_pay.education',
		'employee_id',
		string='Field Label',
	)

	ca_ids = fields.One2many(
		'phil_pay.corrective_actions',
		'employee_id',
		string='Corrective Actions',
	)

	wh_ids = fields.One2many(
		'phil_pay.work_history',
		'employee_id',
		string='Work History',
	)

class Education(models.Model):
	_name = 'phil_pay.education'

	name = fields.Char(
		string='Institution Name',
	)

	degree_type = fields.Selection([('Undergraduate', 'Undergraduate'), ('Post Graduate', 'Post Graduate'), ('Others', 'Others')])

	year_attended = fields.Char(
		string='Year Attended',
	)

	year_graduated = fields.Char(
		string='Year Graduated',
	)

	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
	)

class CorrectiveActions(models.Model):
	_name = 'phil_pay.corrective_actions'

	reason = fields.Text(
		string='Details of CA',
	)

	date_given = fields.Date(
		string='Date CA Given'
	)

	supervisor = fields.Many2one(
		'hr.employee',
		string='Direct Supervisor',
	)

	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
	)

class WorkHistory(models.Model):
	_name = 'phil_pay.work_history'

	company_name = fields.Char(
		string='Company',
	)

	position = fields.Char(
		string='Position',
	)

	year_started = fields.Date(
		string='Employment Date'
	)

	date_resigned = fields.Date(
		string='Date Resigned'
	)

	reason = fields.Text(
		string='Reason for leaving',
	)

	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
	)

class Contracts(models.Model):
	_inherit = 'hr.contract'

	Allowance = fields.Float(
		string='Allowance(s)',
	)

	adr = fields.Float(
	    string='Applicable Daily Rate',
	    readonly=True,
	    compute = '_compute_adr'
	)

	sss_contri =fields.Float(
		string="SSS Contribution",
		readonly=True,
		compute= '_goverment_contribution'
	)

	pagibig_contri =fields.Float(
		string="Pagibig Contribution",
		readonly=True,
		compute= '_goverment_contribution'
	)

	phic_contri =fields.Float(
		string="Philhealth Contribution",
		readonly=True,
		compute= '_goverment_contribution'
	)

	is_mwe = fields.Boolean(
		string="MWE?",
		default=False
	)


	@api.depends('adr', 'wage', 'Allowance')
	def _compute_adr(self):
		for record in self:
			record.adr = ((record.wage + record.Allowance) * 12) / 261 


	@api.depends('wage')
	def _goverment_contribution(self):
		#raise Warning(self.get_ssscontribution(self.wage))
		self.sss_contri = self.get_ssscontribution(self.wage)
		self.phic_contri = self.get_phicContribution(self.wage)
		self.pagibig_contri = 100.00
		#pass
		#self.sss_contri
	@api.model
	def get_phicContribution(self, amount=0.00):
		contri_tabe = {
			1:[8000.00, 999.99],
			2:[9000.00, 999.99],
			3:[10000.00, 999.99],
			4:[11000.00, 999.99],
			5:[12000.00, 999.99],
			6:[13000.00, 999.99],
			7:[14000.00, 999.99],
			8:[15000.00, 999.99],
			9:[16000.00, 999.99],
			10:[17000.00, 999.99],
			11:[18000.00, 999.99],
			12:[19000.00, 999.99],
			13:[20000.00, 999.99],
			14:[21000.00, 999.99],
			15:[22000.00, 999.99],
			16:[23000.00, 999.99],
			17:[24000.00, 999.99],
			18:[25000.00, 999.99],
			19:[26000.00, 999.99],
			20:[27000.00, 999.99],
			21:[28000.00, 999.99],
			22:[29000.00, 999.99],
			23:[30000.00, 999.99],
			24:[31000.00, 999.99],
			25:[32000.00, 999.99],
			26:[33000.00, 999.99],
			27:[34000.00, 999.99],
			28:[35000.00, 999.99],
		}
		for contri in contri_tabe:
			if amount <= (contri_tabe[contri][0] + contri_tabe[contri][1]):
				return round(contri_tabe[contri][0] * .0125,1)
			elif amount > 35000.00:
				return round(contri_tabe[28][0] * .0125,1)

	@api.model
	def get_ssscontribution(self, amount=0.00):
		sss_contribution = {
				1: [1000.00, 249.99, 10.00],
				2: [1500.00, 249.99, 10.00],
				3: [2000.00, 249.99, 10.00],
				4: [2500.00, 249.99, 10.00],
				5: [3000.00, 249.99, 10.00],
				6: [3500.00, 249.99, 10.00],
				7: [4000.00, 249.99, 10.00],
				8: [4500.00, 249.99, 10.00],
				9: [5000.00, 249.99, 10.00],
				10: [5500.00, 249.99, 10.00],
				11: [6000.00, 249.99, 10.00],
				12: [6500.00, 249.99, 10.00],
				13: [7000.00, 249.99, 10.00],
				14: [7500.00, 249.99, 10.00],
				15: [8000.00, 249.99, 10.00],
				16: [8500.00, 249.99, 10.00],
				17: [9000.00, 249.99, 10.00],
				18: [9500.00, 249.99, 10.00],
				19: [10000.00, 249.99, 10.00],
				20: [10500.00, 249.99, 10.00],
				21: [11000.00, 249.99, 10.00],
				22: [11500.00, 249.99, 10.00],
				23: [12000.00, 249.99, 10.00],
				24: [12500.00, 249.99, 10.00],
				25: [13000.00, 249.99, 10.00],
				26: [13500.00, 249.99, 10.00],
				27: [14000.00, 249.99, 10.00],
				28: [14500.00, 249.99, 10.00],
				29: [15000.00, 249.99, 10.00],
				30: [15500.00, 249.99, 10.00],
				31: [16000.00, 249.99, 10.00],
		}

		#Computation for SSS
		#for contri in sss_contribution:
			#_logger.info(contri)
		for contri in sss_contribution:
			if amount <= (sss_contribution[contri][0] + sss_contribution[contri][1]):
				return round(sss_contribution[contri][0] * 0.03633125,1)
			elif amount > 15750.00:
				return round(sss_contribution[31][0] * 0.03633125,1)


# class phil_pay(models.Model):
#     _name = 'phil_pay.phil_pay'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100