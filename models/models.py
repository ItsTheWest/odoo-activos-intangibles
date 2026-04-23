from odoo import models, fields

class ActivoIntangible(models.Model):
    _name = 'activo.intangible'
    _description = 'tabla de activos intangibles'

    name = fields.Char(string="nombre", required=True)

    asset_type = fields.Selection([
        ('software', 'Software'),
        ('hardware', 'Hardware'),
        ('licencia', 'Licencia'),
        ('marca', 'Marca'),
        ('patente', 'Patente'),
        ('copyright', 'Copyright'),
    ], string="Tipo", required=True, default="software")

    registration_number = fields.Char(string="numero de registro")

    concession_date = fields.Date(string="fecha de concesion")
    
    renewal_date = fields.Date(string="fecha de renovacion/caducidad")

    state = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('en renovacion', 'En renovacion'),
        ('expirado', 'Expirado')
    ], string="Estado", default="activo")
    responsible_id = fields.Many2one('hr.employee', string="responsable")
    expense_id = fields.Many2one('hr.expense', string="gastos") 

    
    