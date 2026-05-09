from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class ActivoIntangibleType(models.Model):
    _name = 'activo.intangible.type'
    _description = 'Tipos de Activos Intangibles'

    name = fields.Char(string="Tipo de Activo", required=True)
    code = fields.Char(string="Código", help="Código interno del tipo de activo")
    lifespan_days = fields.Integer(string="Días de Vigencia", default=0, help="Días predeterminados para la fecha de renovación/caducidad")
    description = fields.Text(string="Descripción")


class ActivoIntangible(models.Model): 
    _name = 'activo.intangible'
    _description = 'tabla de activos intangibles'
    # mail.thread enables chatter/messaging on records.
    # mail.activity.mixin enables the "Schedule Activity" button and the activity system.
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="nombre", required=True, tracking=True)

    asset_type_id = fields.Many2one('activo.intangible.type', string="Tipo", required=True, tracking=True)

    registration_number = fields.Char(string="numero de registro")

    concession_date = fields.Date(string="fecha de concesion")

    renewal_date = fields.Date(string="fecha de renovacion/caducidad", tracking=True)

    state = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('expirado', 'Expirado')
    ], string="Estado", default="activo", tracking=True)

    responsible_id = fields.Many2one('hr.employee', string="responsable")
    expense_id = fields.Many2one('hr.expense', string="gastos")

    def action_inactivar(self):
        for record in self:
            record.state = 'inactivo'

    def action_renovar(self):
        for record in self:
            if not record.renewal_date:
                raise UserError("Error: No se puede activar el activo sin una Fecha de Renovación.")
            record.state = 'activo'

    @api.constrains('concession_date', 'renewal_date')
    def _check_dates(self):
        for record in self:
            if record.concession_date and record.renewal_date:
                if record.concession_date > record.renewal_date:
                    raise ValidationError("Error: La fecha de concesión no puede ser mayor a la fecha de renovación/caducidad.")

    @api.onchange('concession_date', 'renewal_date')
    def _onchange_dates(self):
        if self.concession_date and self.renewal_date:
            if self.concession_date > self.renewal_date:
                return {
                    'warning': {
                        'title': "Validación de Fechas",
                        'message': "La fecha de concesión no debería ser mayor a la fecha de renovación/caducidad. Por favor, verifique."
                    }
                }

    @api.onchange('asset_type_id', 'concession_date')
    def _onchange_asset_type_dates(self):
        if self.asset_type_id and self.asset_type_id.lifespan_days > 0 and self.concession_date:
            self.renewal_date = self.concession_date + timedelta(days=self.asset_type_id.lifespan_days)


    @api.model
    def _cron_check_vencement(self):
        """
        Scheduled action (cron) that runs nightly.
        1. Marks assets as 'expirado' if their renewal date has passed.
        """
        today = fields.Date.today()
        
        # 1. PROCESS EXPIRED ASSETS
        # Find assets that are still active but their date has already passed.
        expired_assets = self.search([
            ('state', '=', 'activo'),
            ('renewal_date', '<', today),
        ])
        for asset in expired_assets:
            asset.state = 'expirado'
            _logger.info("Cron [Activos Intangibles]: Asset '%s' (ID: %s) marked as EXPIRED.", asset.name, asset.id)

        if not expired_assets:
            _logger.info("Cron [Activos Intangibles]: No state transitions needed today.")
            return