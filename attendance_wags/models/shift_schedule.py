# -*- coding: utf-8 -*-
# import placeholder
from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError
import datetime
from datetime import date , datetime , timedelta
import calendar
import datetime as dt
from dateutil.relativedelta import relativedelta
from odoo import exceptions, _
import getpass
import psycopg2 as pg
import re


class ActualAttendance_ext(models.Model):
    _name = 'actual.attendance'
    _description = "Actual Attendance Wags"
    _rec_name = 'rec_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee.wags', string="Employee")
    shift_link = fields.Many2one('shifts.attendance',string="Shift Link")
    card_no = fields.Char(string='Employee ID')
    date = fields.Date(string="Date")
    shift = fields.Char(string="Effective Shift for the day")
    shift_id = fields.Integer(string="Shift ID")
    standard_working_hour = fields.Float(string="Standard Working Hours")
    intime = fields.Selection([
        ('lin', 'Late In'),
        # ('ein', 'Early In'),
        ('-', ' - '),
        ],default='-', string="In Time")
    total_late_in_time = fields.Float(string="Total Total Late In Time")
    total_late_time = fields.Float(string="Total Late Time")
    short_leave_adjusted_time = fields.Float(string="Short leave Adjusted Time")
    outtime = fields.Selection([
        ('lout', 'Late Out'),
        ('eout', 'Early Out'),
        ('-', ' - '),
        ],default='-', string="Out Time")
    total_early_out_time = fields.Float(string="Total Early Out Time")
    start_date = fields.Datetime(string="Shift Start Date")
    end_date = fields.Datetime(string="Shift End Date")
    end_date_overtime = fields.Datetime(string="End Date Overtime")
    start_shift = fields.Float(string="Start Shift Time")
    end_shift = fields.Float(string="End Shift Time")
    effective_start_date = fields.Datetime(string="Effective Start Date")
    effective_end_date = fields.Datetime(string="Effective End Date")
    leave_id = fields.Integer(string="Leave ID")
    leave_id_bool = fields.Boolean(string="Leave ID Bool")  

    checkin_dt = fields.Datetime(string="Checkin DT")
    checkout_dt = fields.Datetime(string="Checkout DT")
    checkin = fields.Float(string="Check In")
    checkout = fields.Float(string="Check Out")
    total_time = fields.Float(string="Total Time")
    half_day_deduction = fields.Boolean(string="half_day_deduction")
    total_eraly_out_time = fields.Float(string="Total Early Out Time")
    todaystatus = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_leave', 'Half Leave'),
        ('leave', 'Leave'),
        ('cpl', 'CPL'),
        ('half_cpl', 'CPL HALF'),
        ('holiday', 'Holiday'),
        ('sick_leaves', 'Sick Leaves'),
        ('annual_leaves', 'Annual Leaves'),
        ('special_leave', 'Special leave'),
        ('casual_leaves', 'Casual Leaves'),
        ('marriage_leaves', 'Marriage Leaves'),
        ('short_leave', 'Short leave'),
        ('work_from_home', 'Work From Home'),
        ('gazetted_holiday', 'Gazetted Holiday'),
        ], string="Status Today")
    defaultstatus = fields.Selection([
        ('holiday', 'Holiday'),
        ('gazetted_holiday', 'Gazetted Holiday'),
        ], string="Default Status")
    start_hours = fields.Float(string="Start Overtime")
    end_hours = fields.Float(string="End Overtime")
    total_hours = fields.Float(string="Total Overtime")
    overtime = fields.Boolean(string="Overtime")
    is_overlap_shift = fields.Boolean(string= "Is Overlap Shift" ,tracking=True)
    rec_name = fields.Char("Rec Name")
    raw_attendance_tree = fields.One2many('raw.attendance.wags', 'actual_attendance_id')

    
    @api.onchange('employee_id')
    def _get_code(self):
        pass
        # self.card_no = self.employee_id.emp_code

    def onchange_shift(self):
        self.rec_name = str(self.employee_id.name) + " " + str(self.date)

    def create(self, vals):
        new_record = super(ActualAttendance_ext, self).create(vals)
        new_record.onchange_shift()
        return new_record

    def fetch_attendance(self):
        actual_attend = self.env['actual.attendance'].search([('id','=',self.id)])

        if actual_attend:
            attendance = self.env['raw.attendance.wags'].search([('date_wags','>=',actual_attend.effective_start_date),('date_wags','<=',actual_attend.effective_end_date),('attendance_done','=',False),('employee_id','=',self.employee_id.id)])
            if attendance:
                for rawt_attend in attendance:
                    rawt_attend.actual_attendance_id = actual_attend.id
                    rawt_attend.attendance_done = True

                actual_attend.update_checkin_and_checkout()

    def set_shift(self):
        

        if not self.shift_link:
            self.shift_link = self.employee_id.schedule.id
        

        self.is_overlap_shift = self.shift_link.is_overlap_shift
        if self.shift_link:
            shift_start_date = str(self.date)+' '+self.shift_link.name[:5]  
            shift_end_date = str(self.date)+' '+self.shift_link.name[-5:]
            date_time_start = dt.datetime.strptime(shift_start_date, '%Y-%m-%d %H:%M')
            date_time_end = dt.datetime.strptime(shift_end_date, '%Y-%m-%d %H:%M')

            self.start_date = date_time_start - relativedelta(hours=5)
            self.end_date = date_time_end - relativedelta(hours=5)

            if self.is_overlap_shift == False:
                effective_start_date = str(self.date) +' '+ "00:00:00"
                effective_end_date = str(self.date) +' '+ "23:59:59"
                self.effective_start_date =  dt.datetime.strptime(effective_start_date, '%Y-%m-%d %H:%M:%S') - relativedelta(hours=5)
                self.effective_end_date =  dt.datetime.strptime(effective_end_date, '%Y-%m-%d %H:%M:%S') - relativedelta(hours=5)
            
            else:
                self.effective_start_date =  date_time_start - relativedelta(hours=10)
                self.effective_end_date =  date_time_end


            self.standard_working_hour = self.shift_link.shift_hours


    

    def update_checkin_and_checkout(self):
        if self.shift_link and self.effective_start_date and self.effective_end_date and self.date:
            attendance_date = []
            self.checkin_dt = False
            self.checkout_dt = False
            self.checkout = False
            self.checkin = 0
            self.checkout = 0
            self.total_time = 0
            if self.raw_attendance_tree:
                for x in self.raw_attendance_tree:
                    if x.date_wags: 
                        attendance_date.append(x)

                attendance_date = sorted(attendance_date, key=lambda x: x.date_wags)
                if attendance_date:
                    checkin_dt = attendance_date[0]
                    self.checkin_dt = checkin_dt.date_wags
                    if self.todaystatus not in ["gazetted_holiday","holiday"]:
                        if self.checkin_dt:
                            self.todaystatus = "present"
                    
                    start_time_var =  attendance_date[0].server_date.time()
                    start_time_float = start_time_var.hour+start_time_var.minute/60.0
                    self.checkin = start_time_float
                

                    self.total_late_in_time = 0
                    self.intime = '-'
                    if self.checkin_dt > self.start_date:
                        self.intime = 'lin'
                        difference = relativedelta(self.start_date, self.checkin_dt)
                        hours = difference.hours
                        minutes = difference.minutes
                        total_minutes = ((hours * 60) + minutes)
                        total_hours =  float(total_minutes) / 60.00
                        self.total_late_in_time =  abs(total_hours)
                    else:
                        self.intime = '-'

                    ##########################(Out Time)############### 
                    
                    self.checkout = 0.0
                    self.total_hours = 0.0
                    self.total_time = 0.0
                    self.outtime = '-'

                    if len(attendance_date) > 1:
                        checkout_dt =  attendance_date[-1]
                        self.checkout_dt =  checkout_dt.date_wags
                        date_time_end_var = attendance_date[-1].server_date
                        end_time_var =  date_time_end_var.time()
                        end_time_float = end_time_var.hour+end_time_var.minute/60.0
                        self.checkout =  end_time_float


                      
                        self.outtime = '-'
                        if self.end_date > self.checkout_dt:
                            self.outtime = 'eout'
                            difference = relativedelta(self.checkout_dt, self.end_date)
                            hours = difference.hours
                            minutes = difference.minutes
                            total_minutes = ((hours * 60) + minutes)
                            total_hours =  float(total_minutes) / 60.00
                            self.total_eraly_out_time =  abs(total_hours)



                        if self.checkin_dt and self.checkout_dt:
                            time1 = self.checkin_dt
                            time2 = self.checkout_dt

                            if self.is_overlap_shift == False:
                                difference = relativedelta(time1, time2)
                                hours = difference.hours
                                minutes = difference.minutes
                                total_minutes = ((hours * 60) + minutes)
                                total_hours =  float(total_minutes) / 60.00
                                self.total_time =  abs(total_hours)
                            else:
                                difference = relativedelta(time2, time1)
                                hours = difference.hours
                                minutes = difference.minutes
                                total_minutes = ((hours * 60) + minutes)
                                total_hours =  float(total_minutes) / 60.00
                                self.total_time =  total_hours

        if self.todaystatus not in ["gazetted_holiday","holiday"]:
            self.holiday_status()

    def holiday_status(self):
        holiday = self.env['holidays.tree'].search([('date','=',self.date),('holidays_attendance_id.stages','=','validated')])
        if holiday:
            for h in holiday:
                if h.holidays_attendance_id:        
                    if holiday.remarks == 'Sunday Holiday':
                        self.todaystatus = "holiday"
                    else:
                        self.todaystatus = "gazetted_holiday"




    def attend_get(self):
        #added a check here so the function of cron job only runs on the given db
        dbName = self._cr.dbname
        if dbName != "Isb_Feed_Live_DB": 
            attend_dates = self.env['dates.attendance'].search([])
            lastdate = attend_dates[-1]
            
            lastdate = lastdate.date
            
            self.CreateDateWiseRecords(lastdate)

    def CreateDateWiseRecords(self,lastdate):
        today_date = datetime.today().strftime('%Y-%m-%d')
        today = datetime.strptime(today_date, "%Y-%m-%d")
        print (today)
        print (lastdate)
        if lastdate < today:
            print ('check 1')
            while (lastdate < today):

                lastdate = lastdate + timedelta(days=1)
                
                create_date = self.env['dates.attendance'].create({
                    'date': lastdate,
                })
                
                employees = self.env['hr.employee.wags'].search([('active','=',True)])
                
                date = lastdate
                for employee in employees:
                    print (employee.name)
                    if employee.schedule:
                        actual = self.env['actual.attendance'].search([('date','=',date),('employee_id','=',employee.id)])
                        if not actual:
                            create_date = actual.create({
                                'employee_id': employee.id,
                                'card_no': employee.employee_code,
                                'date': date,
                                'todaystatus': 'absent',
                                'shift_link': employee.schedule.id,
                            })
                            create_date.set_shift()
                            create_date.holiday_status()


               
        
    def LinkingRawAttendence(self):
        dbName = self._cr.dbname
        if dbName != "Isb_Feed_Live_DB":
            current_date = fields.date.today()
            date = (current_date - relativedelta(days=31))

            all_unmark = self.env['raw.attendance.wags'].search([('attendance_done','=',False),('employee_id','!=',False),('date','>=',date)])
            actual_attendance_list = []
            for x in all_unmark:
                if x.date_wags:
                    recorded = self.env['actual.attendance'].search([('employee_id.id','=',x.employee_id.id),('effective_start_date','<=',x.date_wags),('effective_end_date','>=',x.date_wags)])
                    if recorded:
                        for line in recorded:
                            # if line.todaystatus != "holiday":
                            x.attendance_done = True
                            x.actual_attendance_id = line.id
                            if line not in actual_attendance_list:
                                actual_attendance_list.append(line)


            for record  in actual_attendance_list:
                record.update_checkin_and_checkout()


class InheritedEmployeeWags(models.Model):
    _inherit = 'hr.employee.wags'

    holidays_attendace = fields.Many2one('holidays.attendance',string="Holiday Attendance")


class AttendanceHolidays_ext(models.Model):
    _name = 'holidays.attendance'
    _description = "Holidays Attendance"
    _rec_name = 'year_day'

    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)

    year = fields.Integer(string="Year")
    holidays_tree = fields.One2many("holidays.tree","holidays_attendance_id")
    stages = fields.Selection([
        ('draft',' Draft'),
        ('validated','Validate'),
        ('done','Done'),
        ],default="draft",copy=False)
    default_holiday = fields.Boolean(string="Default Holiday",default=False)
    days = fields.Many2many('week.days.wags',string="Days")
    year_day = fields.Char()
    description = fields.Text(string="Description")

    def draft(self):
        if self.stages == 'validated':
            self.stages = "draft"

    # @api.constrains('default_holiday')
    # def check_unique_default_holiday(self):
    #     # Check if any other user has default_holiday=True
    #     if self.default_holiday:
    #         existing_records = self.search([('default_holiday', '=', True), ('id', '!=', self.id)])
    #         if existing_records:
    #             raise exceptions.ValidationError("Only one user can have Default Holiday set to True.")

    def validate(self):
        if self.stages == 'draft':
            self.year_day = f"{self.year} - {self.description}"
            self.stages = "validated"

    def done(self):
        if self.stages == 'validated':
            self.stages = "done"

    def get_holidays(self):
        items = []
        day_names = self.days.mapped('name')
        previous_days = self.env['holidays.tree'].search([('day','in',day_names)])
        if previous_days:
            for prev_holiday in previous_days:
                prev_holiday.unlink()
        if self.holidays_tree:
            self.holidays_tree.unlink()
        for d in self.other_holidays(self.year):
            create_holiday = self.env['holidays.tree'].create({
                'date' : d,
                'day' : d.strftime('%A'),
                'remarks' : f"{d.strftime('%A')} Holiday",
                'holidays_attendance_id' : self.id
            })
            """ d.strftime('%A') is used to get weekday from date """
        """ year_day is the rec name build by concatinating first 3 char of every weekday with year """
        day_name = [day[:3] for day in day_names]
        # self.year_day = f"{self.year}-{','.join(day_name)}"
    def other_holidays(self,attr):
        """ This function is used to generate holidays for selected days defined in many2many field """
        year = attr
        for rec in self.days:
            d = date(year,1,1)
            difference = int(rec.no) - d.weekday()
            if difference < 0:
                difference += 7
            d += timedelta(days = difference)
            while d.year == year:
                yield d
                d += timedelta(days = 7)



    def get_sundays(self):
        year = self.year
        items = []
        
        for x in self.holidays_tree:
            items.append(x.date)
        prv_sunday_sat=self.env['holidays.tree'].search([('day','=',['Sunday'])])
        
        for r in  prv_sunday_sat:
            r.unlink()

        for d in self.allsundays(year):
            if d not in items:
                create_holiday = self.env['holidays.tree'].create({
                    'date' : d,
                    'day' : 'Sunday',
                    'remarks' : 'Sunday Holiday',
                    'holidays_attendance_id' : self.id
                })
        
        # for dt in self.allsaturday(year):
        #     if dt not in items:
        #         create_holiday = self.env['holidays.tree'].create({
        #             'date' : dt,
        #             'day' : 'Saturday',
        #             'remarks' : 'Saturday Holiday',
        #             'holidays_attendance_id' : self.id
        #         })

    def allsundays(self,attr):
        year = attr
        d = date(year, 1, 1)
        d += timedelta(days = 6 - d.weekday())
        while d.year == year:
            yield d
            d += timedelta(days = 7)
    def allsaturday(self,attr):
        year = attr
        d = date(year, 1, 1)
        d += timedelta(days = 5 - d.weekday())

        while d.year == year:
            yield d

            d += timedelta(days = 7)

    def unlink(self):
        # raise ValidationError('Cannot Delete Record')   
        super(AttendanceHolidays_ext, self).unlink()


class AttendanceHolidaysTree(models.Model):
    _name = 'holidays.tree'
    _description = "Holidays Tree Wags"
    _rec_name = 'day'


    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)

    date = fields.Date(string="Date")
    day = fields.Char(string="Day")
    remarks = fields.Char(string="Remarks")
    holidays_attendance_id = fields.Many2one("holidays.attendance")

    @api.onchange('date')
    def _onchange_times(self):
        if self.date:
            now = datetime.strptime(str(self.date), "%Y-%m-%d").date()
            self.day = calendar.day_name[now.weekday()]


class AttendanceShifts_ext(models.Model):
    _name = 'shifts.attendance'
    _description = "Shifts Attendance Wags"
    _rec_name = 'rec_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    

    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)

    intime = fields.Float(string="In Time",tracking=True)
    outtime = fields.Float(string="Out Time",tracking=True)
    lavi_time = fields.Float(string="Lavi Time" , default=1,tracking=True)
    shift_hours = fields.Float(string="Shift Hours",tracking=True)
    shift_half_houre = fields.Float(string="Shift half Hours",tracking=True)
    check_out_lavi_time = fields.Char(string="Check Out Lavi Time",tracking=True)
    name = fields.Char(string="Shift",tracking=True)
    shift_name = fields.Char(string="Shift Name",tracking=True)
    rec_name = fields.Char(string="Rec Name",tracking=True)
    main = fields.Boolean(string="Main")
    is_management = fields.Boolean(string="Is Management ?",tracking=True)
    is_universal = fields.Boolean(string="Is Universal ?",tracking=True)
    is_8_hour_shift = fields.Boolean(string="Is 8 Hour Shift ?",tracking=True)
    active = fields.Boolean(string="Active",tracking=True, default=True)
    is_overlap_shift = fields.Boolean(string= "Is Overlap Shift" ,tracking=True)
    rec_name = fields.Char(string='Rec Name')

    @api.onchange('intime','outtime','shift_name')
    def _onchange_times(self):
        intime = self._FloattoTime(self.intime)
        outtime = self._FloattoTime(self.outtime)

        self.name = '%s - %s' %(intime,outtime)
        self.rec_name = '%s - %s' %(self.name,self.shift_name)


    def _FloattoTime(self, floatTime):
        intime = '{0:02.0f}:{1:02.0f}'.format(*divmod(floatTime*60,60))
        intime_01 = datetime.strptime(intime, "%H:%M")
        intime_02 = str(intime_01).replace(':', ' ', 2)
        intime_03 = intime_02.split(" ")
        intime_04 = '%s:%s' %(intime_03[1],intime_03[2])
        return intime_04


class AttendanceDates(models.Model):
    _name = 'dates.attendance'
    _description = "Dates Attendance Wags"
    _rec_name = 'date'

    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)
    
    date = fields.Datetime(string="Attendance Date")


class Employee_wags_ext(models.Model):
    _inherit = 'hr.employee.wags'

    schedule = fields.Many2one('shifts.attendance')



class WeekDays(models.Model):
    _name = 'week.days.wags'
    _description = "Week Days"

    name = fields.Char(string="Day")
    no = fields.Integer(string="Number")
