from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ActivoIntangible(models.Model):
    _name = 'activo.intangible'
    _description = 'tabla de activos intangibles'
    # mail.thread enables chatter/messaging on records.
    # mail.activity.mixin enables the "Schedule Activity" button and the activity system.
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="nombre", required=True, tracking=True)

    asset_type = fields.Selection([
        ('software', 'Software'),
        ('hardware', 'Hardware'),
        ('licencia', 'Licencia'),
        ('marca', 'Marca'),
        ('patente', 'Patente'),
        ('copyright', 'Copyright'),
    ], string="Tipo", required=True, default="software", tracking=True)

    registration_number = fields.Char(string="numero de registro")

    concession_date = fields.Date(string="fecha de concesion")

    renewal_date = fields.Date(string="fecha de renovacion/caducidad", tracking=True)

    state = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('en renovacion', 'En renovacion'),
        ('expirado', 'Expirado')
    ], string="Estado", default="activo", tracking=True)

    responsible_id = fields.Many2one('hr.employee', string="responsable")
    expense_id = fields.Many2one('hr.expense', string="gastos")

    def action_inactivar(self):
        for record in self:
            record.state = 'inactivo'

    def action_renovar(self):
        for record in self:
            record.state = 'activo'