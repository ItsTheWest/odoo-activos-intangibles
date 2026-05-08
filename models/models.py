from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
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
            if not record.renewal_date:
                raise UserError("Error: No se puede activar el activo sin una Fecha de Renovación.")
            if record.renewal_date <= fields.Date.today():
                raise UserError(f"Error: La fecha de renovación ({record.renewal_date}) ya ha pasado. Por favor, actualice la fecha antes de activar.")
            record.state = 'activo'

    @api.constrains('concession_date', 'renewal_date')
    def _check_dates(self):
        for record in self:
            if record.concession_date and record.renewal_date:
                if record.concession_date > record.renewal_date:
                    raise ValidationError("Error: La fecha de concesión no puede ser mayor a la fecha de renovación/caducidad.")
            if record.renewal_date and record.renewal_date <= fields.Date.today():
                record.state = 'expirado'

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


    @api.model
    def _cron_check_vencement(self):
        """
        Scheduled action (cron) that runs nightly.
        1. Marks assets as 'expirado' if their renewal date has passed.
        2. Marks assets as 'en renovacion' if they expire in 30 days or less and creates an activity.
        """
        today = fields.Date.today()
        alert_limit = today + timedelta(days=30)
        
        # 1. PROCESS EXPIRED ASSETS
        # Find assets that are still active or in renovation but their date has already passed.
        expired_assets = self.search([
            ('state', 'in', ['activo', 'en renovacion']),
            ('renewal_date', '<', today),
        ])
        for asset in expired_assets:
            asset.state = 'expirado'
            _logger.info("Cron [Activos Intangibles]: Asset '%s' (ID: %s) marked as EXPIRED.", asset.name, asset.id)

        # 2. PROCESS ASSETS NEAR EXPIRATION (30 Days)
        # We only process 'activo' assets to avoid re-triggering for those already 'en renovacion'.
        near_expiry_assets = self.search([
            ('state', '=', 'activo'),
            ('renewal_date', '!=', False),
            ('renewal_date', '<=', alert_limit),
            ('renewal_date', '>=', today),
        ])

        if not near_expiry_assets and not expired_assets:
            _logger.info("Cron [Activos Intangibles]: No state transitions needed today.")
            return

        activity_type = self.env.ref('mail.mail_activity_data_todo')

        for asset in near_expiry_assets:
            # Change state
            asset.state = 'en renovacion'

            # Determine the user to notify
            user_id = (
                asset.responsible_id.user_id.id
                if asset.responsible_id and asset.responsible_id.user_id
                else self.env.company.partner_id.user_ids[:1].id
            )

            if user_id:
                asset.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=f"⚠️ Vencimiento próximo: {asset.name}",
                    note=(
                        f"El activo intangible <b>{asset.name}</b> "
                        f"(Tipo: {dict(asset._fields['asset_type'].selection).get(asset.asset_type)}) "
                        f"vence el <b>{asset.renewal_date.strftime('%d/%m/%Y')}</b>. "
                        f"El sistema ha cambiado su estado a <b>En renovación</b> automáticamente."
                    ),
                    user_id=user_id,
                )
                _logger.info("Cron [Activos Intangibles]: Asset '%s' (ID: %s) transitioned to 'en renovacion' and notified.", asset.name, asset.id)
            else:
                _logger.warning("Cron [Activos Intangibles]: Asset '%s' (ID: %s) has no responsible user to notify.", asset.name, asset.id)