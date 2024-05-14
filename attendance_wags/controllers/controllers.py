# -*- coding: utf-8 -*-
# from odoo import http


# class TaskManagement(http.Controller):
#     @http.route('/manufacturing_order/manufacturing_order/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/manufacturing_order/manufacturing_order/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('manufacturing_order.listing', {
#             'root': '/manufacturing_order/manufacturing_order',
#             'objects': http.request.env['manufacturing_order.manufacturing_order'].search([]),
#         })

#     @http.route('/manufacturing_order/manufacturing_order/objects/<model("manufacturing_order.manufacturing_order"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('manufacturing_order.object', {
#             'object': obj
#         })
