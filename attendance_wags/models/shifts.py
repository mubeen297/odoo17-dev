from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError
from datetime import date , datetime , timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz


class AttendanceShiftWags(models.Model):
	_name = 'attendance.shift.wags'
	_description = "Attendance Shift Wags"
	_rec_name = 'rec_name'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	

	rec_name = fields.Char(string="Reference", tracking=True)
	name = fields.Char(string="Shift", tracking=True)
	shift_name = fields.Char(string="Shift Name", tracking=True)
	date = fields.Date(string="Date", tracking=True, default=fields.Date.today())
	intime = fields.Float(string="In Time", tracking=True)
	outtime = fields.Float(string="Out Time", tracking=True)
	working_hours = fields.Float(string="Working Hours", tracking=True)
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	lavy_in = fields.Float(string="Lavi In",tracking=True)
	lavy_out = fields.Float(string="Lavi Out",tracking=True)
	overlapping = fields.Boolean(string="Overlapping", tracking=True)


	@api.constrains('intime', 'outtime')
	def _check_time_range(self):
		for record in self:
			if record.intime < 0 or record.intime > 24 or record.outtime < 0 or record.outtime > 24:
				raise ValidationError("In Time and Out Time must be between 0 and 24 hours.")


	@api.onchange('intime', 'outtime', 'shift_name')
	def _calculate_working_hours(self):
		for record in self:
			if record.intime and record.outtime:
				server_tz = self.env.user.tz or 'UTC'
				server_tz_obj = timezone(server_tz)
				intime_dt = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=record.intime)
				outtime_dt = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=record.outtime)
				intime_dt_tz = server_tz_obj.localize(intime_dt, is_dst=None)
				outtime_dt_tz = server_tz_obj.localize(outtime_dt, is_dst=None)

				time_difference = (outtime_dt_tz - intime_dt_tz).seconds / 3600.0
				record.working_hours = time_difference if time_difference >= 0 else 24 + time_difference
				record.name = '%.2f - %.2f' % (record.intime, record.outtime)
				record.rec_name = '%.2f - %.2f - %s' % (record.intime, record.outtime, record.shift_name)
			else:
				record.working_hours = 0.0


class HREmployeeWagsExt(models.Model):
	_inherit = 'hr.employee.wags'

	shift_ids = fields.Many2many('attendance.shift.wags', string='Shifts', tracking=True)



	@api.model
	def get_employee_details(self, user_id):
		employees = self.search([('user_id', '=', user_id)])
		employee_details = []
		for employee in employees:
			category_details = [{'id': category.id, 'name': category.name} for category in employee.category_ids]
			
			attendance_log = self.env['daily.attendance.logs.wags'].search([
				('date', '=', date.today()),
				('employee_id', '=', employee.id),
			], limit=1)
			
			shift_id = attendance_log.shift_id.id if attendance_log else False
			working_hours = attendance_log.shift_id.working_hours if attendance_log else 0.0

			employee_details.append({
				'id': employee.id,
				'name': employee.name,
				'image_1920': employee.image_1920,
				'category_ids': category_details,
				'employee_code': employee.employee_code,
				'company_id': employee.company_id.id,
				'company_name': employee.company_id.name,
				'work_email': employee.work_email,
				'mobile_phone': employee.mobile_phone,
				'emergency_name': employee.emergency_name,
				'emergency_relation': employee.emergency_relation,
				'emergency_cell_number': employee.emergency_cell_number,
				'passport_id': employee.passport_id,
				'passport_issue_date': employee.passport_issue_date,
				'passport_expiry_date': employee.passport_expiry_date,
				'joining_date': employee.joining_date,
				'no_of_years': employee.no_of_years,
				'nationality_type': employee.nationality_type,
				'country_id': employee.country_id.id,
				'country_name': employee.country_id.name,
				'visa_no': employee.visa_no,
				'visa_expiry': employee.visa_expiry,
				'identification_id': employee.identification_id,
				'id_issue_date': employee.id_issue_date,
				'id_expiry_date': employee.id_expiry_date,
				'bank_id': employee.bank_name.id,
				'bank_name': employee.bank_name.name,
				'bank_account': employee.bank_account,
				'gender': employee.gender,
				'marital': employee.marital,
				'birthday': employee.birthday,
				'place_of_birth': employee.place_of_birth,
				'department_id': employee.department_id.id,
				'department_name': employee.department_id.name,
				'job_id': employee.job_id.id,
				'job_name': employee.job_id.name,
				'company_location_id': employee.company_location.id,
				'company_location_name': employee.company_location.name,
				'is_manager': employee.is_manager,
				'manager_id': employee.manager_id.id,
				'manager_name': employee.manager_id.name,
				'wage': employee.wage,
				'shift_id': shift_id,
				'shift_name': attendance_log.shift_id.name if attendance_log else False,
				'working_hours': working_hours,
			})
		return employee_details


	@api.model
	def manager_wise_employees(self, manager_id):
		employees_list = []
		employees = self.env['hr.employee.wags'].search([('manager_id', '=', manager_id)])
		for employee in employees:

			attendance_log = self.env['daily.attendance.logs.wags'].search([
				('date', '=', date.today()),
				('employee_id', '=', employee.id),
			], limit=1)
			
			shift_id = attendance_log.shift_id.id if attendance_log else False
			working_hours = attendance_log.shift_id.working_hours if attendance_log else 0.0

			employee_data = {
				'employee_id': employee.id,
				'employee_name': employee.name,
				'shift_id': shift_id,
				'shift_name': attendance_log.shift_id.name if attendance_log else False,
				'working_hours': working_hours
			}
			employees_list.append(employee_data)

		return employees_list



	# def create_daily_logs(self , year=None):
	#   local_tz = self.env.user.tz
	#   if year:
	#       start_date = datetime(year, 1, 1).date()
	#       end_date = datetime(year, 12, 31).date()
	#   else:
	#       today = datetime.now(pytz.timezone(local_tz)).date()
	#       start_date = datetime(today.year, 1, 1).date()
	#       end_date = datetime(today.year, 12, 31).date()
	#   existing_logs = self.env['daily.attendance.logs.wags'].search([
	#       ('date', '>=', start_date),
	#       ('date', '<=', end_date),
	#       ('employee_id', '=', self.id),
	#   ])

	#   existing_dates = set(log.date for log in existing_logs)
	#   date_iterator = start_date
	#   while date_iterator <= end_date:
	#       if date_iterator not in existing_dates:
	#           print ('.      ')
	#           print ('.      ')
	#           print ('.      ')
	#           print ('.      ')
	#           print (self.name)
	#           print ('create log ')
	#           self.env['daily.attendance.logs.wags'].create({
	#               'employee_id': self.id,
	#               'user_id': self.user_id.id if self.user_id else False,
	#               'date': date_iterator,
	#           })

	#       date_iterator += timedelta(days=1)



	def create_daily_logs(self, year=None, batch_size=2000):
		local_tz = self.env.user.tz
		
		if year:
			start_date = datetime(year, 1, 1).date()
			end_date = datetime(year, 12, 31).date()
		else:
			today = datetime.now(pytz.timezone(local_tz)).date()
			start_date = datetime(today.year, 1, 1).date()
			end_date = datetime(today.year, 12, 31).date()
		
		existing_logs = self.env['daily.attendance.logs.wags'].search([
			('date', '>=', start_date),
			('date', '<=', end_date),
			('employee_id', '=', self.id),
		])

		existing_dates = set(log.date for log in existing_logs)
		dates_to_create = []
		
		date_iterator = start_date
		while date_iterator <= end_date:
			if date_iterator not in existing_dates:
				dates_to_create.append({
					'employee_id': self.id,
					'user_id': self.user_id.id if self.user_id else False,
					'date': date_iterator,
				})
			
			if len(dates_to_create) >= batch_size:
				self.env['daily.attendance.logs.wags'].create(dates_to_create)
				dates_to_create = []
			
			date_iterator += timedelta(days=1)
		
		# Create remaining records if any
		if dates_to_create:
			self.env['daily.attendance.logs.wags'].create(dates_to_create)



	@api.model
	def create(self, vals):
		result = super(HREmployeeWagsExt, self).create(vals)
		result.create_daily_logs()
		return result
