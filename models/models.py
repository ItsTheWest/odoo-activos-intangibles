# from odoo import models, fields, api


# class gestion_activos_intangibles(models.Model):
#     _name = 'gestion_activos_intangibles.gestion_activos_intangibles'
#     _description = 'gestion_activos_intangibles.gestion_activos_intangibles'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

