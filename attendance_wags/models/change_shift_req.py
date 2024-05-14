    # -*- coding: utf-8 -*-
# import placeholder
from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError, UserError
import datetime
from datetime import datetime
import datetime as dt
from odoo import exceptions, _
import getpass
import psycopg2 as pg
import re

class ChangeShiftRequestExt(models.Model):
    _name = 'shift.change'
    _description = "Shift Change Wags"
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    emp_code = fields.Char(string='Employee Id',tracking=True,required=True,)
    employee_id = fields.Many2one('hr.employee.wags',string="Employee Name")
    # related="employee_id.parent_id"
    manager_id = fields.Many2one('hr.employee.wags',string="Manager")
    current_shift_id= fields.Many2one('shifts.attendance',string="Previous Shift",readonly=True, )
    from_date= fields.Date(string='From Date')
    to_date= fields.Date(string='To Date')
    reason= fields.Char(string='Reason')
    requested_shift_id= fields.Many2one('shifts.attendance',string="Requested Shift",tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approve',' Approved By Manager'),
        ('validate', 'Validate'),
        ],default='draft' ,tracking=True)
    

    def draft(self):
        self.state = "draft"
        actual_attendnace = self.env['actual.attendance'].search([('date','>=',self.from_date),('date','<=',self.to_date),('employee_id','=',self.employee_id.id)])
        if actual_attendnace:
            for actual in actual_attendnace:
                actual.shift_link = self.current_shift_id.id
                actual.set_shift()

    def manager_approve(self):
        self.state = "manager_approve"

    def validate(self):
        self.state = "validate"
        actual_attendnace = self.env['actual.attendance'].search([('date','>=',self.from_date),('date','<=',self.to_date),('employee_id','=',self.employee_id.id)])
        if actual_attendnace:
            for actual in actual_attendnace:
                actual.shift_link = self.requested_shift_id.id
                actual.set_shift()

    # def write(self, vals):
        

    #     before = self.write_date
    #     rec = super(ChangeShiftRequest, self).write(vals)
    #     after = self.write_date
        # if before != after:
            # self.payrol_batch_created_check()
        # return rec

    def create(self, vals):
        new_record = super(ChangeShiftRequest, self).create(vals)
        # new_record.payrol_batch_created_check()
        return new_record

    # def payrol_batch_created_check(self):
    #     user = self.env['res.users'].search([('id','=',self._uid)])
    #     if not user.hr_user:
    #         payroll_from = self.env['hr.payslip.run'].sudo().search_count([('date_start','<=',self.from_date),('date_end','>=',self.from_date),('batch_status','!=','draft')])
    #         if payroll_from:
    #             raise ValidationError("You are not eligible for this request because payroll has been closed, please contact to HR.")
    #         payroll_to = self.env['hr.payslip.run'].sudo().search_count([('date_start','<=',self.to_date),('date_end','>=',self.to_date),('batch_status','!=','draft')])
    #         if payroll_to:
    #             raise ValidationError("You are not eligible for this request because payroll has been closed, please contact to HR.")


    @api.constrains('from_date', 'to_date', 'employee_id')
    def _check_dates(self):
    
        for check in self:
            # Starting date must be prior to the ending date
            from_date = check.from_date
            to_date = check.to_date
            if to_date < from_date:
                raise ValidationError('The ending date must not be prior to the starting date.')


            domain = [
                ('id', '!=', check.id),
                ('employee_id', '=', check.employee_id.id),
                '|', '|',
                '&', ('from_date', '<=', check.from_date), ('to_date', '>=', check.from_date),
                '&', ('from_date', '<=', check.to_date), ('to_date', '>=', check.to_date),
                '&', ('from_date', '<=', check.from_date), ('to_date', '>=', check.to_date),
            ]

            if self.search_count(domain) > 0:
                raise ValidationError("Date overlaps for already existing Employee.")

        

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.emp_code =self.employee_id.emp_code
            self.current_shift_id =self.employee_id.schedule.id
        else:
            self.emp_code =None
            self.current_shift_id = None


    @api.onchange('emp_code')
    def _onchange_emp_code(self):
        if self.emp_code:
            employee_id = self.env['hr.employee.wags'].search([('emp_code','=',self.emp_code)],limit=1)
            if employee_id:
                self.employee_id =employee_id.id
                self.current_shift_id =employee_id.schedule.id
    
                # self.claim_type=False
        
        else:
            self.employee_id =None
            self.current_shift_id = None



