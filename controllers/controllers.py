# from odoo import http


# class GestionActivosIntangibles(http.Controller):
#     @http.route('/gestion_activos_intangibles/gestion_activos_intangibles', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/gestion_activos_intangibles/gestion_activos_intangibles/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('gestion_activos_intangibles.listing', {
#             'root': '/gestion_activos_intangibles/gestion_activos_intangibles',
#             'objects': http.request.env['gestion_activos_intangibles.gestion_activos_intangibles'].search([]),
#         })

#     @http.route('/gestion_activos_intangibles/gestion_activos_intangibles/objects/<model("gestion_activos_intangibles.gestion_activos_intangibles"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('gestion_activos_intangibles.object', {
#             'object': obj
#         })

