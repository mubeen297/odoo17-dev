# -*- coding: utf-8 -*-
{
    'name': "Attendance Wags",

    'summary': """
        Attendance Wags """,

    'description': """
        Attendance Wags
    """,

    'author': "wags.sa",
    'website': "https://wags.sa",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'sequence': '-100',
    'version': '0.1',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base', 'base_access_rights', 'hr_employee_wags','leaves_managment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_raw_attendance.xml',
        'views/daily_attendance_logs.xml',
        # 'views/schedulers.xml',
        'views/shifts.xml',
        # 'views/machine_info.xml',
        # 'views/change_shift_req.xml',
        'wizard/views.xml',
        'views/menus.xml',
        'views/record_rules.xml',
        'views/shift_schedule.xml',
        
    ],
}
