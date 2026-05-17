# -*- coding: utf-8 -*-
from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

# ==============================================================================
# MAIN MODEL: ActivoIntangible
# Handles the full lifecycle of an intangible asset:
#   - Field declarations
#   - Computed fields (risk level, calendar color, document count)
#   - ORM overrides (create/write)
#   - Business action buttons
#   - Cron job for expiry checking
# ==============================================================================

class ActivoIntangible(models.Model):
    _name = 'activo.intangible'
    _description = 'Gestión de Activos Intangibles'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Nombre", required=True, tracking=True)
    asset_type_id = fields.Many2one('activo.intangible.type', string="Tipo", required=True, tracking=True)
    registration_number = fields.Char(string="Número de Registro")
    concession_date = fields.Date(string="Fecha de Concesión")
    renewal_date = fields.Date(string="Fecha de Renovación/Caducidad", tracking=True)

    state = fields.Selection([
        ('inactivo', 'Inactivo'),
        ('activo', 'Activo'),
        ('por_expirar', 'Por Expirar'),
        ('expirado', 'Expirado'),
    ], string='Estado', default='activo', required=True, tracking=True)

    nivel_riesgo = fields.Selection([
        ('bajo', 'Bajo Riesgo'),
        ('medio', 'Riesgo Medio'),
        ('alto', 'Alto Riesgo'),
    ], string='Nivel de Riesgo', compute='_compute_nivel_riesgo', inverse='_inverse_nivel_riesgo', store=True, tracking=True)

    responsible_id = fields.Many2one('hr.employee', string="Responsable")
    expense_id = fields.Many2one('hr.expense', string="Gastos de Mantenimiento")
    invoice_id = fields.Many2one('account.move', string="Factura de Origen")

    valor_contable = fields.Monetary(
        string="Valor Contable",
        currency_field='currency_id',
        tracking=True,
        help="Valor contable actual del activo intangible (para reportes financieros).",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
    )

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='activo_intangible_ir_attachment_rel',
        column1='activo_id',
        column2='attachment_id',
        string="Evidencias Digitales",
    )

    calendar_color = fields.Integer(
        string='Color en Calendario',
        compute='_compute_calendar_color',
        store=True,
    )

    document_count = fields.Integer(
        string="Documentos",
        compute="_compute_document_count",
        store=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('state')
    def _compute_calendar_color(self):
        """Assigns a calendar color based on the asset state."""
        for record in self:
            if record.state == 'activo':
                record.calendar_color = 10  # Green
            elif record.state == 'expirado':
                record.calendar_color = 1   # Red
            elif record.state == 'inactivo':
                record.calendar_color = 4   # Light blue
            elif record.state == 'por_expirar':
                record.calendar_color = 2   # Orange
            else:
                record.calendar_color = 0   # Default

    @api.depends('state', 'valor_contable')
    def _compute_nivel_riesgo(self):
        """
        Automatically calculates the risk level of the asset.

        Business Rules:
          - ALTO  : Expired asset, OR expiring soon with valor_contable > 1100.
          - MEDIO : Expiring soon with valor_contable <= 1100.
          - BAJO  : Active or inactive (no imminent threat).
        """
        for rec in self:
            if rec.state == 'expirado':
                rec.nivel_riesgo = 'alto'
            elif rec.state == 'por_expirar':
                if rec.valor_contable and rec.valor_contable > 1100:
                    rec.nivel_riesgo = 'alto'
                else:
                    rec.nivel_riesgo = 'medio'
            else:
                rec.nivel_riesgo = 'bajo'

    def _inverse_nivel_riesgo(self):
        """Syncs the asset state when a card is dragged in the Risk Kanban view."""
        for rec in self:
            if rec.nivel_riesgo == 'alto':
                if rec.state not in ['expirado', 'por_expirar']:
                    rec.state = 'expirado'
            elif rec.nivel_riesgo == 'medio':
                if rec.state != 'por_expirar':
                    rec.state = 'por_expirar'
            elif rec.nivel_riesgo == 'bajo':
                if rec.state not in ['activo', 'inactivo']:
                    rec.state = 'activo'

    @api.depends('attachment_ids')
    def _compute_document_count(self):
        """Calculates the number of attached documents."""
        for rec in self:
            rec.document_count = len(rec.attachment_ids)

    @api.model
    def get_historical_valuation_data(self):
        """
        Returns the cumulative growth of the portfolio valuation over the last 12 months.
        Used by the OWL Line Chart widget.
        """
        from dateutil.relativedelta import relativedelta

        today = fields.Date.today()

        # Generate a list of the last 12 months (first day of each month)
        months_list = []
        for i in range(11, -1, -1):
            first_day = today - relativedelta(months=i, day=1)
            months_list.append(first_day)

        activos = self.search([('state', '!=', 'inactivo')])

        labels = [m.strftime('%b %Y') for m in months_list]
        data = []

        for m_first_day in months_list:
            next_month_start = m_first_day + relativedelta(months=1)
            val_sum = 0.0
            for a in activos:
                # Prioritize concession_date; fallback to create_date
                asset_date = a.concession_date or (a.create_date and a.create_date.date())
                if asset_date and asset_date < next_month_start:
                    val_sum += a.valor_contable or 0.0
            data.append(val_sum)

        return {
            'labels': labels,
            'data': data,
        }

    # -------------------------------------------------------------------------
    # ORM OVERRIDES
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Overrides creation to auto-assign state based on renewal_date."""
        today = fields.Date.today()
        for vals in vals_list:
            if vals.get('renewal_date'):
                rd = fields.Date.to_date(vals['renewal_date'])
                if rd < today:
                    vals['state'] = 'expirado'
                elif rd <= today + timedelta(days=60):
                    vals['state'] = 'por_expirar'
        return super(ActivoIntangible, self).create(vals_list)

    def write(self, vals):
        """Overrides update to manage physical deletion of removed attachments."""
        before_attachments = self.attachment_ids
        res = super(ActivoIntangible, self).write(vals)

        if 'attachment_ids' in vals:
            after_attachments = self.attachment_ids
            removed_attachments = before_attachments - after_attachments
            if removed_attachments:
                removed_attachments.sudo().unlink()

        return res

    # -------------------------------------------------------------------------
    # ONCHANGE & CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('concession_date', 'renewal_date')
    def _check_dates(self):
        """Ensures that the concession date is not later than the renewal date."""
        for record in self:
            if record.concession_date and record.renewal_date:
                if record.concession_date > record.renewal_date:
                    raise ValidationError("Error: La fecha de concesión no puede ser mayor a la fecha de renovación/caducidad.")

    @api.onchange('concession_date', 'renewal_date')
    def _onchange_dates(self):
        """Real-time date validation and expiry proximity alert."""
        if self.concession_date and self.renewal_date:
            if self.concession_date > self.renewal_date:
                return {
                    'warning': {
                        'title': "Validación de Fechas",
                        'message': "La fecha de concesión no debería ser mayor a la fecha de renovación/caducidad. Por favor, verifique."
                    }
                }

        if self.renewal_date:
            today = fields.Date.today()
            days_left = (self.renewal_date - today).days
            if 0 < days_left <= 60:
                return {
                    'warning': {
                        'title': '⚠️ Activo Próximo a Vencer',
                        'message': (
                            f'La fecha de renovación está a solo {days_left} día(s). '
                            'Este activo quedará en estado "Por Expirar" automáticamente. '
                            'Asegúrese de que la fecha es correcta antes de guardar.'
                        ),
                    }
                }

    @api.onchange('asset_type_id', 'concession_date')
    def _onchange_asset_type_dates(self):
        """Auto-fills renewal_date based on asset type lifespan, only if not already set."""
        if self.asset_type_id and self.asset_type_id.lifespan_days > 0 and self.concession_date:
            if not self.renewal_date:
                self.renewal_date = self.concession_date + timedelta(days=self.asset_type_id.lifespan_days)

    # -------------------------------------------------------------------------
    # ACTION METHODS (View Buttons)
    # -------------------------------------------------------------------------
    def action_open_attachment_wizard(self):
        """Opens the wizard to upload digital evidence."""
        self.ensure_one()
        return {
            'name': 'Adjuntar Archivos',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.attachment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_activo_id': self.id,
            }
        }

    def action_inactivar(self):
        """Sets the asset to inactive state."""
        for record in self:
            record.state = 'inactivo'

    def action_renovar(self):
        """Reactivates an asset by evaluating its renewal date."""
        self.ensure_one()
        if not self.renewal_date:
            raise UserError("Error: No se puede activar el activo sin una Fecha de Renovación.")

        today = fields.Date.today()
        if self.renewal_date < today:
            self.state = 'expirado'
        elif self.renewal_date <= today + timedelta(days=60):
            days_left = (self.renewal_date - today).days
            wizard = self.env['activo.near.expiry.wizard'].create({
                'name': self.name,
                'renewal_date': self.renewal_date,
                'days_left': days_left,
                'activo_id': self.id,
                'action_type': 'activate',
            })
            return {
                'name': '⚠️ Confirmar Activación Próxima a Vencer',
                'type': 'ir.actions.act_window',
                'res_model': 'activo.near.expiry.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            self.state = 'activo'

    def action_check_near_expiry(self):
        """
        Invoked by the 'Verify and Save' button when creating a new record.
        If the renewal date is ≤ 60 days away, raises the confirmation wizard.
        """
        self.ensure_one()
        today = fields.Date.today()

        if not self.renewal_date or self.id:
            return {'type': 'ir.actions.act_window_close'}

        days_left = (self.renewal_date - today).days
        if 0 < days_left <= 60:
            wizard = self.env['activo.near.expiry.wizard'].create({
                'name': self.name,
                'renewal_date': self.renewal_date,
                'days_left': days_left,
                'pending_vals_json': str({
                    'name': self.name,
                    'asset_type_id': self.asset_type_id.id,
                    'registration_number': self.registration_number,
                    'concession_date': str(self.concession_date) if self.concession_date else False,
                    'renewal_date': str(self.renewal_date),
                    'responsible_id': self.responsible_id.id if self.responsible_id else False,
                    'state': 'por_expirar',
                }),
            })
            return {
                'name': '⚠️ Confirmar Activo Próximo a Vencer',
                'type': 'ir.actions.act_window',
                'res_model': 'activo.near.expiry.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

        return {'type': 'ir.actions.act_window_close'}

    # -------------------------------------------------------------------------
    # CRON JOBS
    # -------------------------------------------------------------------------
    @api.model
    def _cron_check_vencement(self):
        """
        Nightly scheduled task that evaluates assets:
          1. Marks as 'expirado' if the renewal date has passed.
          2. Marks as 'por_expirar' if ≤ 60 days remain.
        """
        today = fields.Date.today()
        sixty_days = today + timedelta(days=60)

        expired_assets = self.search([
            ('state', 'in', ['activo', 'por_expirar']),
            ('renewal_date', '<', today),
        ])
        for asset in expired_assets:
            asset.state = 'expirado'
            _logger.info("Cron [Activos Intangibles]: Asset '%s' (ID: %s) marked as EXPIRED.", asset.name, asset.id)

        expiring_assets = self.search([
            ('state', '=', 'activo'),
            ('renewal_date', '>=', today),
            ('renewal_date', '<=', sixty_days),
        ])
        for asset in expiring_assets:
            asset.state = 'por_expirar'
            _logger.info("Cron [Activos Intangibles]: Asset '%s' (ID: %s) marked as EXPIRING SOON.", asset.name, asset.id)
