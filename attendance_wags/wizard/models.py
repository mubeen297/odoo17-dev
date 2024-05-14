from odoo import fields, models, api
from datetime import datetime, timedelta


class StockImmediateTransferWizard(models.TransientModel):
    _name = 'daily.attendance.logs.wizard'
    _description = 'Daily Attendance Logs Wizard'

    date = fields.Date(string="Date")
    year = fields.Integer(string='Year')

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.year = self.date.year

    def create_daily_logs(self):
        active_employees = self.env['hr.employee.wags'].search([('active', '=', True)])

        for employee in active_employees:
            employee.create_daily_logs(year=self.year)

        return {'type': 'ir.actions.act_window_close'}

