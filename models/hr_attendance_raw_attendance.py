# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import time
from datetime import datetime, date, timedelta
# from datetime import timezone
from datetime import time as datetime_time
from dateutil import relativedelta
import logging
import pytz
import base64
import os
import time
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class attendance_raw_logs(models.Model):
	_name = 'attendance.raw.main'
	_description = 'Attendance Dat File Uploader'

	name = fields.Char(
		string='Sequence',
		default=lambda self: _('New Attendance Dat File'),
		size=64,
		)

	import_file = fields.Binary(
		string='Import Dat File' 
		)

	attendace_ids = fields.One2many(
		'hr.attendance',
		'raw_attendance_id',
		string='Attendances',
		ondelete='restrict'		
		)

	raw_attendance_ids = fields.One2many(
		'attendance.raw.list',
		'raw_attendance_id',
		string='Attendances'
		)

	@api.model
	def create(self, values):
		if values.get('name', _('New Attendance Dat File')) == _('New Attendance Dat File'):
			values['name'] = self.env['ir.sequence'].next_by_code('attendance.raw.main')
		res = super(attendance_raw_logs, self).create(values)
		return res

	@api.one
	def create_raw_attendance(self): #, raw_main_id, uid
		if not self.import_file:
			raise UserError('No File Found. Please Upload the Log File.')
		elif len(self.import_file) == 0:
			raise UserError('No File Found. Please Upload the Log File.')



		FILENAME = "/opt/Log_File/newfile_dat_file_"+str(self._uid) +".dat"
		with open(FILENAME, "wb") as f:
			text = self.import_file
			f.write(base64.b64decode(text))
			#raise Warning(f.readline())

		f.close()
		with open(FILENAME, "r") as f:
			lines = f.readlines()
			user_tz = self.env.user.tz
			local = pytz.timezone(user_tz)
			if lines:
				raw_list_obj = self.env['attendance.raw.list'].search([('raw_attendance_id', '=', self.id)])
				#if raw_list_obj:
				#for lst in raw_list_obj:
				#	if lst.name == '1':
				#		_logger.info(lst.date_time_logs)
				res = raw_list_obj.unlink()
				#if res:
				raw_list_obj_1 = self.env['attendance.raw.list']
				for line in lines:
					if line:
						line_list = line.split()
						datetime_log = fields.Datetime.from_string(line_list[1] + ' ' + line_list[2])#datetime.strptime(line_list[1] + ' ' + line_list[2], '%Y-%m-%d %H:%M:%S').replace(tzinfo=local)
						#if line_list[0] == '1' and line_list[1] == '2011-08-16':
								#_logger.info(line.split())
								#_logger.info(datetime_log)
						#raise Warning(datetime_log.replace(tzinfo=local))
						hour_date = timedelta(hours=8)


						_logger.info(datetime_log)
						_logger.info(datetime_log - hour_date)
						raw_list_obj_1.create({'raw_attendance_id': self.id, 'name': line_list[0], 'date_time_logs': datetime_log - hour_date, 'date_logs': line_list[1]})
		f.close()
		os.remove(FILENAME)


	@api.one
	def create_attendance(self):
		user_tz = self.env.user.tz
		local = pytz.timezone(user_tz)
		if not self.import_file:
			raise UserError('No File Found. Please Upload the Log File.')
		elif len(self.import_file) == 0:
			raise UserError('No File Found. Please Upload the Log File.')

		raw_list_obj = self.env['attendance.raw.list'].search([('raw_attendance_id', '=', self.id)])
		obj_employees = self.env['hr.employee'].search([('biometric_number', '!=', False)])
		raw_list_model = self.env['attendance.raw.list']

		if not raw_list_obj:
			raise UserError('No Raw Attendance Found. Please Upload the Log File and Submit to Generate the Raw Attendance.')
		elif len(raw_list_obj) == 0:
			raise UserError('No Raw Attendance Found. Please Upload the Log File and Submit to Generate the Raw Attendance.')


		#To Get the Distinct Dates in the Logs
		dates_lst = []
		if raw_list_obj:
			for raw in raw_list_obj:
				if len(dates_lst) > 0:
					if raw.date_logs not in dates_lst:
						dates_lst.append(raw.date_logs)
				else:
					dates_lst.append(raw.date_logs)

		if obj_employees:
			for employee in obj_employees:
				for dt_lst in dates_lst:

					#Due to Looping and Distinction of Records by Date, Some Logs have no Log in Dates
					#This will handle the Logs that does not Exists
					raw_list_obj_asc_rec = raw_list_model.search([('date_logs', '=', dt_lst),('name', '=', employee.biometric_number)])

					if raw_list_obj_asc_rec:
						raw_list_obj_asc_rec = False
						raw_list_obj_desc_rec = False
						raw_list_obj_asc_rec = raw_list_model.search([('date_logs', '=', dt_lst),('name', '=', employee.biometric_number),('raw_attendance_id', '=', self.id)], limit=1, order='date_time_logs asc')
						raw_list_obj_desc_rec = raw_list_model.search([('date_logs', '=', dt_lst),('name', '=', employee.biometric_number),('raw_attendance_id', '=', self.id)], limit=1, order='date_time_logs desc')
						#FIRST Criteria
						hr_attendance_add =self.env['hr.attendance']
						hr_attendance =self.env['hr.attendance'].search([('employee_id','=', employee.id),
																		 ('check_in','=', raw_list_obj_asc_rec.date_time_logs),
																		 ('check_out','=', raw_list_obj_desc_rec.date_time_logs),])
						if not hr_attendance:
							hr_attendance_add.create({
								'raw_attendance_id': self.id,
								'employee_id': employee.id,
								'check_in': raw_list_obj_asc_rec.date_time_logs,
								'check_out': raw_list_obj_desc_rec.date_time_logs
								})





	#@api.one
	#def create_attendance(self):
	#	employee_obj = self.env['hr.employee'].search([])
#
#		for employee in employee_obj:
#			if employee:
#				pass

class attendance_raw_logs_lines(models.Model):
	_name='attendance.raw.list'
	_order='name, date_time_logs'
	_description = 'Attendance Dat File Uploader List'


	raw_attendance_id = fields.Many2one(
		relation='attendance.raw.main',
		string='Attendance Raw Main',
		ondelete='cascade'
		)

	name = fields.Char(
		string='Biometrics Number',
		size=64,
		)

	date_logs = fields.Date(
		string='Date'
		)

	date_time_logs = fields.Datetime(
		string='Log Date Time' 
		)