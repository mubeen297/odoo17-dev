from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError
from datetime import datetime, timedelta, time
import pytz
from pytz import timezone


class DailyAttendanceLogsWags(models.Model):
	_name = 'daily.attendance.logs.wags'
	_description = 'Daily Attendance Logs'
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = 'employee_id'
	_order = "create_date desc"


	employee_id = fields.Many2one('hr.employee.wags',string="Employee Name", tracking=True)
	user_id = fields.Many2one('res.users',string="User", tracking=True)
	shift_id = fields.Many2one('attendance.shift.wags', string='Shift', tracking=True)
	date = fields.Date(string="Date", tracking=True, default=fields.Date.today())
	checkin = fields.Datetime(string="Checkin", tracking=True)
	active = fields.Boolean(default=True)
	checkout = fields.Datetime(string="Checkout", tracking=True)
	total_time = fields.Float(string="Total Time", tracking=True)
	early = fields.Selection([
		('in', 'Early In'),
		('out', 'Early Out'),
		], string="Early In / Out", tracking=True)
	late = fields.Selection([
		('in', 'Late In'),
		('out', 'Late Out'),
		], string="Late In / Out", tracking=True)
	attendance_status = fields.Selection([
		('present', 'Present'),
		('absent', 'Absent'),
		('holiday', 'Holiday'),
		('half_leave','Half Leave'),
		('national_holiday','National Holiday'),
		('leave', 'Leave'),
		], string="Attendance Status",default='absent' ,tracking=True)
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	
	raw_attendance_ids = fields.One2many('raw.attendance.wags', 'daily_attendance_id', string='Punch Attendance')
	holiday_ref = fields.Many2one('hr.holidays.wags',string="Holiday Ref",tracking=True)
	national_holiday = fields.Many2one('holidays.attendance',string="National Holiday",tracking=True)


	def update_holidays(self):
		holidays = self.env['holidays.tree'].search([('date','=',self.date),('holidays_attendance_id.stages','=','validated')])
		if holidays:
			self.national_holiday = holidays.holidays_attendance_id.id
			self.attendance_status = 'national_holiday'

	def update_attendance(self):
		self.update_attendance_status()
		# self.update_attendance_schedule()

	def update_attendance_status(self):
		
		attendance_status = ""
		if self.raw_attendance_ids:
			attendance_status = 'present'
		
		if self.working_schedule_id:
			holiday_days = self.working_schedule_id.attendance_ids.filtered(
				lambda r: self.date.strftime('%A').lower() in r.day_of_week and r.is_holiday
			)
			if holiday_days:
				attendance_status = "holiday"
				self.shift_id = holiday_days[0].shift_id.id
			else:
				self.shift_id = self.working_schedule_id.attendance_ids.filtered(
					lambda r: self.date.strftime('%A').lower() in r.day_of_week
				).mapped('shift_id').id

				self.attendance_status = "holiday"

		if self.holiday_ref:
			attendance_status = 'leave'

		self.attendance_status = attendance_status




	def update_attendance_schedule(self):
		if self.shift_id:
			""" Note : 5 hours added due to gap in server time of 5 hours  """
			shift_in_time = self.shift_id.intime if self.shift_id else False
			shift_out_time = self.shift_id.outtime if self.shift_id else False
			shift_in_datetime = datetime.strptime(str(shift_in_time), '%H.%M')
			shift_out_datetime = datetime.strptime(str(shift_out_time), '%H.%M')

			new_check_in = self.checkin + timedelta(hours=5) if self.checkin else False
			new_check_out = self.checkout + timedelta(hours=5) if self.checkout else False
			check_in_time = new_check_in.strftime('%H:%M')
			check_out_time = new_check_out.strftime('%H:%M')
			if check_in_time > shift_in_datetime.strftime('%H:%M'):
				self.late = 'in'
			if check_out_time > shift_out_datetime.strftime('%H:%M'):
				self.late = 'out'
			if check_in_time < shift_in_datetime.strftime('%H:%M'):
				self.early = 'in'
			if check_out_time < shift_out_datetime.strftime('%H:%M'):
				self.early = 'out'




	def update_early_late(self):
		for attendance in self:
			if attendance.checkin and attendance.shift_id:
				shift_intime = attendance.shift_id.intime
				shift_outtime = attendance.shift_id.outtime

				local_tz = self.env.user.tz or 'UTC'
				user_tz = timezone(local_tz)

				checkin_dt = datetime.strptime(str(attendance.checkin), "%Y-%m-%d %H:%M:%S")
				checkout_dt = datetime.strptime(str(attendance.checkout), "%Y-%m-%d %H:%M:%S") if attendance.checkout else False

				shift_intime_dt = datetime.strptime(str(shift_intime).replace('12:00', '00:00'), "%H:%M")
				shift_outtime_dt = datetime.strptime(str(shift_outtime).replace('24:00', '00:00'), "%H:%M")

				checkin_dt = user_tz.localize(checkin_dt)
				checkout_dt = user_tz.localize(checkout_dt) if checkout_dt else False

				early_in_minutes = (checkin_dt - shift_intime_dt).total_seconds() / 60.0
				late_in_minutes = (shift_outtime_dt - checkin_dt).total_seconds() / 60.0

				early_out_minutes = (checkout_dt - shift_intime_dt).total_seconds() / 60.0 if checkout_dt else False
				late_out_minutes = (shift_outtime_dt - checkout_dt).total_seconds() / 60.0 if checkout_dt else False

				# Update 'early' and 'late' fields based on the calculated values
				if early_in_minutes > 0:
					attendance.early = 'in'
				elif late_in_minutes > 0:
					attendance.late = 'in'

				if early_out_minutes and early_out_minutes > 0:
					attendance.early = 'out'
				elif late_out_minutes and late_out_minutes > 0:
					attendance.late = 'out'



	@api.model
	def daily_attendance_details(self, attendance_details):
		"""API function for Get Daly Logs"""
		employee_id = attendance_details.get('employee_id')
		attendance_limit = attendance_details.get('attendance_limit')

		limit = 0
		if attendance_limit == 'pos_attendance_limit':
			limit = self.env.user.company_id.pos_attendance_limit
		else:
			limit = self.env.user.company_id.app_attendance_limit


		limit_days = datetime.now() - timedelta(days=limit)

		records = self.search([
			('employee_id', '=', employee_id),
			('date', '>=', limit_days),
			('date', '<=', datetime.now())
		], order='date desc')

		grouped_records = {'active_attendance': None, 'monthly_datewise_attendance': {}}

		yesterday_date = datetime.now().date() - timedelta(days=1)
		
		for record in records:

			record.update_punch_details()

			last_record = record.raw_attendance_ids[0] if record.raw_attendance_ids else None
			last_checkin = last_checkout = False

			if last_record:
				last_checkin = last_record.final_checkin
				last_checkout = last_record.final_checkout

			if record.shift_id and record.shift_id.overlapping and record.date >= yesterday_date:
				overlapping = True

			else:
				overlapping = False

			record_data = {
				'log_attendance_id': record.id,
				'employee_id': record.employee_id.id,
				'employee_name': record.employee_id.name,
				'attendance_pin': record.employee_id.attendance_pin,
				'attendance_status': record.attendance_status,
				'checkin': record.checkin,
				'checkout': record.checkout,
				'total_time': record.total_time,
				'shift_id': record.shift_id.id if record.shift_id else False,
				'overlapping': overlapping,
			}

			if overlapping and record.date == yesterday_date:
				record_data.update({
					'last_checkin': last_checkin,
					'last_checkout': last_checkout,
				})

			# if overlapping:
			#     last_record = record.raw_attendance_ids[0] if record.raw_attendance_ids else None
			#     last_checkin = last_checkout = False
			#     if last_record:
			#         last_checkin = last_record.final_checkin
			#         last_checkout = last_record.final_checkout

			#         record_data.update({
			#             'last_checkin': last_checkin,
			#             'last_checkout': last_checkout,
			#         })

			if grouped_records['active_attendance'] is None:
				grouped_records['active_attendance'] = {
					'date': record.date.strftime('%Y-%m-%d'),
					'last_checkin': last_checkin,
					'last_checkout': last_checkout,
					**record_data
				}

			elif grouped_records['active_attendance']['log_attendance_id'] != record.id:
				grouped_records['monthly_datewise_attendance'][record.date.strftime('%Y-%m-%d')] = record_data
		
		return grouped_records



	@api.model
	def get_punch_details(self, attendance_details):
		"""API function for Get Punch Details"""
		employee_id = attendance_details.get('employee_id')
		log_attendance_id = attendance_details.get('log_attendance_id')

		punches = self.search([('id', '=', log_attendance_id), ('employee_id', '=', employee_id)], order='date')
		punch_details = []
		for line in punches.raw_attendance_ids:
			punch_details.append({
				'punch_attendance_id': line.id,
				'final_checkin': line.final_checkin,
				'final_checkout': line.final_checkout,
				'checkin_latitude': line.checkin_latitude,
				'checkout_latitude': line.checkout_latitude,
				'checkin_longitude': line.checkin_longitude,
				'checkout_longitude': line.checkout_longitude,
				'total_time': punches.total_time,
				'remarks': line.remarks
			})
		return punch_details


	def update_punch_details(self):
		"""API function for Update Punch Details"""

		for rec in self:
			first_checkin = False
			last_checkout = False

			"""Sort attendances based on final_checkin"""
			sorted_attendances = rec.raw_attendance_ids.sorted(key=lambda r: r.final_checkin)
			
			if sorted_attendances:
				first_checkin = sorted_attendances[0].final_checkin
				for i, attendance in enumerate(sorted_attendances):
					"""Check for final_checkout or fallback to the last available final_checkout"""
					if attendance.final_checkout:
						last_checkout = attendance.final_checkout
					elif i > 0 and sorted_attendances[i - 1].final_checkout:
						last_checkout = sorted_attendances[i - 1].final_checkout
						break

			if first_checkin:
				rec.checkin = first_checkin
				if last_checkout:
					total_hours = (last_checkout - first_checkin).total_seconds() / 3600.0
					rec.total_time = total_hours
					rec.checkout = last_checkout
				else:
					rec.checkout = False
					rec.total_time = 0.0
			else:
				rec.checkin = False
				rec.checkout = False
				rec.total_time = 0.0


	@api.model
	def create(self, vals):
		record = super(DailyAttendanceLogsWags, self).create(vals)
		return record

	
	def write(self, vals):
		result = super(DailyAttendanceLogsWags, self).write(vals)
		if any(key in vals for key in ['checkin']):
			self.update_attendance_status()
		return result







class AttendanceDatesWags(models.Model):
	_name = 'attendance.date.wags'
	_description = "Attendance Date Wags"
	_rec_name = 'date'

	date = fields.Date(string="Attendance Date")
	company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)