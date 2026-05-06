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

    @api.model
    def _cron_check_vencement(self):
        """
        Scheduled action (cron) that runs nightly.
        Finds all 'activo' assets whose renewal_date is exactly 30 days from today
        and creates a 'To Do' activity to alert the responsible user.
        """
        # Calculate the exact date that is 30 days from now.
        alert_date = fields.Date.today() + timedelta(days=30)

        # Search only for assets that are active AND have a renewal date in 30 days.
        # This prevents duplicate alerts for already processed or inactive assets.
        expiring_assets = self.search([
            ('state', '=', 'activo'),
            ('renewal_date', '=', alert_date),
        ])

        if not expiring_assets:
            _logger.info("Cron [Activos Intangibles]: No assets expiring in 30 days. No alerts created.")
            return

        # Retrieve the "To Do" activity type, which is standard in all Odoo installations.
        activity_type = self.env.ref('mail.mail_activity_data_todo')

        for asset in expiring_assets:
            # Determine the user to notify.
            # Priority: the employee's linked user > the current company admin user.
            user_id = (
                asset.responsible_id.user_id.id
                if asset.responsible_id and asset.responsible_id.user_id
                else self.env.company.partner_id.user_ids[:1].id
            )

            if not user_id:
                _logger.warning(
                    "Cron [Activos Intangibles]: Asset '%s' (ID: %s) has no responsible user. Skipping.",
                    asset.name, asset.id
                )
                continue

            asset.activity_schedule(
                activity_type_id=activity_type.id,
                summary=f"⚠️ Vencimiento próximo: {asset.name}",
                note=(
                    f"El activo intangible <b>{asset.name}</b> "
                    f"(Tipo: {dict(asset._fields['asset_type'].selection).get(asset.asset_type)}) "
                    f"vence el <b>{asset.renewal_date.strftime('%d/%m/%Y')}</b>. "
                    f"Por favor, inicie el proceso de renovación a la brevedad."
                ),
                user_id=user_id,
            )
            _logger.info(
                "Cron [Activos Intangibles]: Activity created for asset '%s' (ID: %s), expiring on %s.",
                asset.name, asset.id, asset.renewal_date
            )