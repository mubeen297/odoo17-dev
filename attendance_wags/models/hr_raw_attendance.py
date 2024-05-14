# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime , timedelta


class RawAttendanceWags(models.Model):
	_name = 'raw.attendance.wags'
	_description = "Raw Attendance Wags"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_rec_name = 'employee_id'
	_order = "create_date desc, id desc"
	

	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	employee_id = fields.Many2one('hr.employee.wags',string="Employee", tracking=True)
	user_id = fields.Many2one('res.users',string="User", tracking=True)
	mac_address = fields.Char(string="Mac Address", tracking=True)
	date_wags = fields.Datetime(string="DateTime", tracking=True)
	department_id = fields.Many2one('hr.department.wags',string="Department", tracking=True)
	shift_id= fields.Many2one('shifts.attendance',string="Shift", tracking=True)
	date = fields.Date(string='Date',store=True, tracking=True, default=fields.Date.today())
	actual_attendance_id = fields.Many2one('daily.attendance.logs.wags', tracking=True)
	daily_attendance_id = fields.Many2one('daily.attendance.logs.wags', tracking=True)
	checkin = fields.Datetime(string="Actual Check In", tracking=True)
	requested_checkin = fields.Datetime(string="Requested Check In", tracking=True)
	final_checkin = fields.Datetime(string="Final Check In", tracking=True)
	checkin_latitude = fields.Char(string='Checkin Latitude', tracking=True)
	checkin_longitude = fields.Char(string='Checkin Longitude', tracking=True)
	checkout = fields.Datetime(string="Actual Check Out", tracking=True)
	requested_checkout = fields.Datetime(string="Requested Check Out", tracking=True)
	final_checkout = fields.Datetime(string="Final Check Out", tracking=True)
	checkout_latitude = fields.Char(string='Checkout Latitude', tracking=True)
	checkout_longitude = fields.Char(string='Checkout Longitude', tracking=True)
	remarks = fields.Char(string='Remarks', tracking=True)
	manager_remarks = fields.Char(string='Manager Remarks', tracking=True)
	employee_image_name = fields.Char(tracking=True)
	employee_image = fields.Binary(string='Image', tracking=True)
	create_uid = fields.Many2one('res.users',string="Created By", tracking=True, readonly=True)
	create_date = fields.Datetime('Created On', tracking=True, readonly=True)
	state = fields.Selection([
		('no_change', 'No Change'),
		('change_request', 'Change Request'),
		('approved', 'Approved'),
		('rejected', 'Rejected'),
	], string='Status', readonly=True, default='no_change', tracking=True)


	def action_no_change(self):
		self.state = "no_change"

	def action_change_request(self):
		if self.state == "no_change":
			self.state = "change_request"

	def action_approve(self):
		if self.state == "change_request":
			if self.requested_checkin:
				self.final_checkin = self.requested_checkin
			if self.requested_checkout:
				self.final_checkout = self.requested_checkout

			self.state = "approved"

	def action_reject(self):
		self.state = "rejected"


	# @api.model
	# def create_update_raw_attendance(self, attendance_data):
	#   user_id = attendance_data.get('user_id')
	#   datetime = attendance_data.get('datetime')
	#   latitude = attendance_data.get('latitude')
	#   longitude = attendance_data.get('longitude')
	#   mac_address = attendance_data.get('mac_address')

	#   existing_records = self.search([('user_id', '=', user_id)], order='id desc', limit=1)
	#   if existing_records and existing_records.checkin and not existing_records.checkout:
	#       existing_records.write({
	#           'checkout': datetime,
	#           'final_checkout': datetime,
	#           'checkout_latitude': latitude,
	#           'checkout_longitude': longitude
	#       })
	#       return {'id': existing_records.id, 'message': 'Attendance Updated'}
	#   else:
	#       new_record = self.create({
	#           'user_id': user_id,
	#           'checkin': datetime,
	#           'final_checkin': datetime,
	#           'checkin_latitude': latitude,
	#           'checkin_longitude': longitude,
	#           'mac_address': mac_address
	#       })
	#       return {'id': new_record.id, 'message': 'Attendance Created.'}
	#   return False


	# @api.model
	# def get_module_version(self):
	# 	module = self.env['ir.module.module'].sudo().search([('name', '=', 'attendance_wags')])
	# 	return module.installed_version if module else False


	@api.model
	def create_update_raw_attendance(self, attendance_data):
		employee_id = attendance_data.get('employee_id')
		department_id = attendance_data.get('department_id')
		user_id = attendance_data.get('user_id')
		log_attendance_id = attendance_data.get('log_attendance_id')
		datetime = attendance_data.get('datetime')
		latitude = attendance_data.get('latitude')
		longitude = attendance_data.get('longitude')
		mac_address = attendance_data.get('mac_address')

		existing_records = self.search([('employee_id', '=', employee_id), ('daily_attendance_id', '=', log_attendance_id)])
		if existing_records:
			for record in existing_records:
				if record.checkin and not record.checkout:
					record.write({
						'checkout': datetime,
						'final_checkout': datetime,
						'checkout_latitude': latitude,
						'checkout_longitude': longitude
					})
					return {'punch_attendance_id': record.id, 'message': 'Attendance Updated'}
				else:
					new_record = self.create({
						'employee_id': employee_id,
						'department_id': department_id,
						'user_id': user_id if user_id else False,
						'daily_attendance_id': log_attendance_id,
						'checkin': datetime,
						'final_checkin': datetime,
						'checkin_latitude': latitude,
						'checkin_longitude': longitude,
						'mac_address': mac_address
					})
					return {'punch_attendance_id': new_record.id, 'message': 'Attendance Created.'}

		else:
			new_record = self.create({
				'employee_id': employee_id,
				'department_id': department_id,
				'user_id': user_id if user_id else False,
				'daily_attendance_id': log_attendance_id,
				'checkin': datetime,
				'final_checkin': datetime,
				'checkin_latitude': latitude,
				'checkin_longitude': longitude,
				'mac_address': mac_address
			})
			return {'punch_attendance_id': new_record.id, 'message': 'Attendance Created.'}
		return False




	@api.model
	def get_user_attendance(self, employee_id):
		
		thirty_days_ago = datetime.now() - timedelta(days=30)
		
		attendances = self.search_read([
			('employee_id', '=', employee_id),
			('create_date', '>=', thirty_days_ago),
			('create_date', '<=', datetime.now())
		], fields=[
			'employee_id', 'user_id', 'mac_address', 'department_id',
			'checkin', 'requested_checkin', 'final_checkin',
			'checkin_latitude', 'checkin_longitude', 'checkout',
			'requested_checkout', 'final_checkout', 'checkout_latitude',
			'checkout_longitude'
		], order='create_date')
		
		return attendances


	@api.model
	def update_requested_time(self, requested_data):
		
		punch_attendance_id = requested_data.get('punch_attendance_id')
		existing_record = self.search([('id', '=', punch_attendance_id)])
		remarks = requested_data.get('remarks', '')
		
		if existing_record:
			if 'requested_checkin' in requested_data and existing_record.checkin:
				existing_record.requested_checkin = requested_data['requested_checkin']
				existing_record.state = 'change_request'
			
			if 'requested_checkout' in requested_data:
				existing_record.requested_checkout = requested_data['requested_checkout']
				existing_record.state = 'change_request'
			
			# new_remarks = requested_data.get('remarks', '')
			# existing_remarks = existing_record.remarks or ''
			
			# if existing_remarks:
			# 	existing_remarks += ', ' + new_remarks
			# else:
			# 	existing_remarks = new_remarks
			
			existing_record.remarks = remarks
			
			return True
		
		return False


	# @api.model
	# def get_change_request_details(self, employee_id):
		
	# 	details = self.search_read([
	# 		('employee_id', '=', employee_id),
	# 		('state', '!=', 'no_change')
	# 	], fields=[
	# 		'employee_id', 'user_id', 'state', 'remarks', 'daily_attendance_id.date',
	# 		'checkin', 'requested_checkin', 'final_checkin', 'checkin_longitude', 'checkin_latitude', 
	# 		'checkout', 'requested_checkout', 'final_checkout', 'checkout_longitude', 'checkout_latitude'
	# 	], order='create_date')
		
	# 	return details


	@api.model
	def get_change_request_details(self, employee_id):
	    change_request_records = self.search([
	        ('employee_id', '=', employee_id),
	        ('state', '!=', 'no_change')
	    ], order='create_date')

	    details = [{
	        'employee_id': record.employee_id.id,
	        'user_id': record.user_id.id,
	        'state': record.state,
	        'remarks': record.remarks,
	        'manager_remarks': record.manager_remarks,
	        'create_date': record.create_date,
	        'date': record.daily_attendance_id.date if record.daily_attendance_id else None,
	        'checkin': record.checkin,
	        'requested_checkin': record.requested_checkin,
	        'final_checkin': record.final_checkin,
	        'checkin_longitude': record.checkin_longitude,
	        'checkin_latitude': record.checkin_latitude,
	        'checkout': record.checkout,
	        'requested_checkout': record.requested_checkout,
	        'final_checkout': record.final_checkout,
	        'checkout_longitude': record.checkout_longitude,
	        'checkout_latitude': record.checkout_latitude,
	    } for record in change_request_records]

	    return details



	@api.model
	def manager_wise_change_requests(self, manager_id):
		"""API function for Manager wise Change Request Deatils"""
		punch_details = []
		employees = self.env['hr.employee.wags'].search([('manager_id', '=', manager_id)])
		for employee in employees:
			punches = self.env['raw.attendance.wags'].search([('employee_id', '=', employee.id), ('state', '!=', 'no_change')], order='create_date')
			for punch in punches:
				punch_details.append({
					'punch_attendance_id': punch.id,
					'employee_id': employee.id,
					'employee_name': employee.name,
					'date': punch.daily_attendance_id.date if punch.daily_attendance_id else None,
					'remarks': punch.remarks,
					'manager_remarks': punch.manager_remarks,
					'state': punch.state,
					'checkin': punch.checkin,
					'requested_checkin': punch.requested_checkin,
					'final_checkin': punch.final_checkin,
	        		'checkin_latitude': punch.checkin_latitude,
					'checkin_longitude': punch.checkin_longitude,
					'checkout': punch.checkout,
					'requested_checkout': punch.requested_checkout,
					'final_checkout': punch.final_checkout,
	        		'checkout_latitude': punch.checkout_latitude,
					'checkout_longitude': punch.checkout_longitude,
				})
		return punch_details


	@api.model
	def update_request_status(self, vals):
		"""API function for Update Request Status"""
		punch_attendance_id = vals.get('punch_attendance_id')
		manager_remarks = vals.get('manager_remarks', '')
		state = vals.get('state', '')
		existing_record = self.search([('id', '=', punch_attendance_id)])
		
		if existing_record:
			if existing_record.state == "change_request" and state == "approved":
				if existing_record.requested_checkin:
					existing_record.final_checkin = existing_record.requested_checkin
				if existing_record.requested_checkout:
					existing_record.final_checkout = existing_record.requested_checkout
			existing_record.manager_remarks = manager_remarks
			existing_record.state = state

			return True
		return False
		



	def get_employee_details(self):
		if self.user_id:
			employee = self.env['hr.employee.wags'].search([('user_id', '=', self.user_id.id)])
			if employee:
				self.write({
					'employee_id': employee.id,
					# 'employee_image': employee.image_1920,
					'department_id': employee.department_id.id if employee.department_id else False
				})


	@api.model
	def create(self,vals):
		rec= super(RawAttendanceWags, self).create(vals)
		# rec.get_employee_details()
		return rec


	# def unlink(self):
	#   raise ValidationError("Sorry, Deletion of record is not allowed..!")


	# def LinkingRawAttendence(self):
	#     dbName = self._cr.dbname
	#     if dbName != "Isb_Feed_Live_DB":
	#         if self.date_wags and self.employee_id:
	#             recorded = self.env['actual.attendance'].search([('employee_id.id','=',self.employee_id.id),('effective_start_date','<=',self.date_wags),('effective_end_date','>=',self.date_wags)])
	#             if recorded:
	#                 for line in reversed(recorded):
	#                     self.actual_attendance_id = line.id
	#                     line.update_checkin_and_checkout()
	#                     break