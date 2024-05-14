from odoo import models, fields, api
# from zklib import zklib
# from zklib import zkconst
# from zk import ZK, const
from datetime import date, datetime, timedelta

class MachineInfoWags(models.Model):
	_name = 'machine.info'
	_description = "Machine Info Wags"
	
	db = fields.Char(string='Data Base')
	odooLogin = fields.Char(string='Login')
	odooPasswd = fields.Char(string='password')
	product_ids=fields.One2many('machine.info.tree','partner_id')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

	def updateAttendanceAll_not_web(self):

		dbName = self._cr.dbname
		if dbName == self.db:
			machine_list=self.env['machine.info'].search([])
			for x in machine_list.product_ids:
				if not x.status=="no":
					if x.status_web==True:
						ip=x.ip
						port=x.port
						zk = ZK(ip, port=int(port), timeout=10)
						connect = zk.connect()
						connect.disable_device()
						attendances = connect.get_attendance()
						self.odooLogin = attendances
						info = []
						for attendance in attendances:
							data = {
							'user_id' :attendance.user_id,
							'Timestamp' : str(attendance.timestamp - timedelta(minutes=300)),
							'Real_Timestamp' : str(attendance.timestamp),
							'Status' : attendance.status
							}
							info.append(data)
						create_attend = []
						count = 1
						for record in reversed(info):
							real_date=record['Real_Timestamp'].split(' ')
							user_id_name=record['user_id']
							machine_date=record['Real_Timestamp']
							date_time=record['Timestamp']
							employee_id_raw =self.env['hr.employee.wags'].search([('emp_code','=',user_id_name)])
							raw_attendance=self.env['raw.attendance.wags'].search([('employee_id','=',employee_id_raw.id),('date_wags','=',date_time),('name','=',ip)])
							

							if not raw_attendance:
								print ("create attendance")
								self.env['raw.attendance.wags'].create({
												'employee_id': employee_id_raw.id,
												'department': employee_id_raw.department_id.id,
												# 'shift_id': employee_id_raw.schedule.id,
												'attendance_date': machine_date,
												'name': ip,
												'date': real_date[0],
												'time': real_date[1],
												'date_wags': date_time,
										})
							else:
								count +=1
								if count == 100:
									break



class MachineInfoErrorWags(models.Model):
	_name = 'machine.info.tree'
	_description = "Machine Info Tree Wags"

	ip = fields.Char(string='IP')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	des = fields.Char(string='Location')
	port= fields.Integer(string='Port')
	status = fields.Selection([('yes','Active'),('no','InActive')],default='yes')
	status_web = fields.Boolean()
	machine_no = fields.Selection([('bio1','Machine 1'),('bio2','Machine 2'),('bio3','Machine 3'),('bio4','Machine 4')])
	partner_id=fields.Many2one('machine.info')