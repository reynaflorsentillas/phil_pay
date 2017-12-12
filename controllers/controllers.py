# -*- coding: utf-8 -*-
from odoo import http

# class PhilPay(http.Controller):
#     @http.route('/phil_pay/phil_pay/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/phil_pay/phil_pay/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('phil_pay.listing', {
#             'root': '/phil_pay/phil_pay',
#             'objects': http.request.env['phil_pay.phil_pay'].search([]),
#         })

#     @http.route('/phil_pay/phil_pay/objects/<model("phil_pay.phil_pay"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('phil_pay.object', {
#             'object': obj
#         })