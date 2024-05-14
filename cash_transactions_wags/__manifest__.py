# -*- coding: utf-8 -*-
{
    'name': "Cash Transactions",

    'summary': "Cash Transactions",

    'description': """
        Long description of module's purpose
    """,

    'author': "wags.sa",
    'website': "https://wags.sa",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',
    'license': 'LGPL-3',
    
    # any module necessary for this one to work correctly
    'depends': ['base', 'base_access_rights', 'mail', 'pos_wags'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'data/data.xml',
        'views/views.xml',
        'views/record_rules.xml',
    ],
}
