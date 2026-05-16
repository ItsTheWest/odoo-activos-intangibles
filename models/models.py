# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

# ==============================================================================
# PART 1: MAIN MODELS
# ==============================================================================

class ActivoIntangible(models.Model): 
    _name = 'activo.intangible'
    _description = 'Gestión de Activos Intangibles'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # 1.1 FIELDS
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
    # 1.2 COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('state')
    def _compute_calendar_color(self):
        """Asigna un color en el calendario según el estado del activo."""
        for record in self:
            if record.state == 'activo':
                record.calendar_color = 10  # Verde
            elif record.state == 'expirado':
                record.calendar_color = 1   # Rojo
            elif record.state == 'inactivo':
                record.calendar_color = 4   # Azul claro
            elif record.state == 'por_expirar':
                record.calendar_color = 2   # Naranja
            else:
                record.calendar_color = 0   # Por defecto

    @api.depends('attachment_ids')
    def _compute_document_count(self):
        """Calcula el número de documentos adjuntos."""
        for rec in self:
            rec.document_count = len(rec.attachment_ids)

    # -------------------------------------------------------------------------
    # 1.3 ORM OVERRIDES (Create & Write)
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe la creación para auto-asignar estado basado en la fecha."""
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
        """Sobrescribe la actualización para gestionar adjuntos."""
        # 1. Ejecutar el guardado estándar
        before_attachments = self.attachment_ids
        res = super(ActivoIntangible, self).write(vals)
        
        # 2. Eliminar físicamente los adjuntos si fueron removidos del registro
        if 'attachment_ids' in vals:
            after_attachments = self.attachment_ids
            removed_attachments = before_attachments - after_attachments
            if removed_attachments:
                removed_attachments.sudo().unlink()
                
        return res

    # -------------------------------------------------------------------------
    # 1.4 ONCHANGE & CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('concession_date', 'renewal_date')
    def _check_dates(self):
        """Asegura que la fecha de concesión no sea posterior a la de renovación."""
        for record in self:
            if record.concession_date and record.renewal_date:
                if record.concession_date > record.renewal_date:
                    raise ValidationError("Error: La fecha de concesión no puede ser mayor a la fecha de renovación/caducidad.")

    @api.onchange('concession_date', 'renewal_date')
    def _onchange_dates(self):
        """Validación en tiempo real de fechas y alerta de proximidad de expiración."""
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
        """Autocompleta la fecha de renovación basada en la vigencia del tipo de activo, solo si no hay una fecha establecida."""
        if self.asset_type_id and self.asset_type_id.lifespan_days > 0 and self.concession_date:
            if not self.renewal_date:
                self.renewal_date = self.concession_date + timedelta(days=self.asset_type_id.lifespan_days)

    # -------------------------------------------------------------------------
    # 1.5 ACTION METHODS (Botones de Vista)
    # -------------------------------------------------------------------------
    def action_open_attachment_wizard(self):
        """Abre el wizard para subir evidencias digitales."""
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
        """Pasa el activo a estado inactivo."""
        for record in self:
            record.state = 'inactivo'

    def action_renovar(self):
        """Reactiva un activo evaluando su fecha de renovación."""
        self.ensure_one()
        if not self.renewal_date:
            raise UserError("Error: No se puede activar el activo sin una Fecha de Renovación.")
        
        today = fields.Date.today()
        if self.renewal_date < today:
            self.state = 'expirado'
        elif self.renewal_date <= today + timedelta(days=60):
            # En lugar de solo cambiar el estado, levanta el modal de aviso
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
        Invocado por el botón 'Verificar y Guardar' al crear un nuevo registro.
        Si la fecha de renovación es ≤ 60 días, levanta el wizard de confirmación.
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
    # 1.6 CRON JOBS
    # -------------------------------------------------------------------------
    @api.model
    def _cron_check_vencement(self):
        """
        Tarea programada nocturna que evalúa los activos:
        1. Marca como 'expirado' si la fecha pasó.
        2. Marca como 'por_expirar' si restan ≤ 60 días.
        """
        today = fields.Date.today()
        sixty_days = today + timedelta(days=60)
        
        expired_assets = self.search([
            ('state', 'in', ['activo', 'por_expirar']),
            ('renewal_date', '<', today),
        ])
        for asset in expired_assets:
            asset.state = 'expirado'
            _logger.info("Cron [Activos Intangibles]: Activo '%s' (ID: %s) marcado como EXPIRADO.", asset.name, asset.id)

        expiring_assets = self.search([
            ('state', '=', 'activo'),
            ('renewal_date', '>=', today),
            ('renewal_date', '<=', sixty_days),
        ])
        for asset in expiring_assets:
            asset.state = 'por_expirar'
            _logger.info("Cron [Activos Intangibles]: Activo '%s' (ID: %s) marcado como POR EXPIRAR.", asset.name, asset.id)


# ==============================================================================
# PART 2: CONFIGURATION MODELS
# ==============================================================================

class ActivoIntangibleType(models.Model):
    _name = 'activo.intangible.type'
    _description = 'Tipos de Activos Intangibles'

    name = fields.Char(string="Tipo de Activo", required=True)
    code = fields.Char(string="Código", help="Código interno del tipo de activo")
    lifespan_days = fields.Integer(string="Días de Vigencia", default=0, help="Días predeterminados para caducidad")
    lifespan_display = fields.Char(string="Vigencia (Display)", compute="_compute_lifespan_display")
    description = fields.Text(string="Descripción")

    @api.depends('lifespan_days')
    def _compute_lifespan_display(self):
        """Formatea la vigencia en años y días."""
        for rec in self:
            if rec.lifespan_days >= 365:
                years = rec.lifespan_days // 365
                remainder = rec.lifespan_days % 365
                if remainder == 0:
                    rec.lifespan_display = f"{years} año{'s' if years > 1 else ''}"
                else:
                    rec.lifespan_display = f"{years} año{'s' if years > 1 else ''} y {remainder} día{'s' if remainder > 1 else ''}"
            else:
                rec.lifespan_display = f"{rec.lifespan_days} día{'s' if rec.lifespan_days != 1 else ''}"

    def action_edit_type(self):
        self.ensure_one()
        return {
            'name': 'Editar Tipo de Activo',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible.type',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


# ==============================================================================
# PART 3: EXTENSIONS
# ==============================================================================

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_modal(self):
        """Abre un modal para previsualizar el documento actual."""
        self.ensure_one()
        return {
            'name': 'Vista Previa del Documento',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('gestion_activos_intangibles.view_attachment_preview_form').id,
            'target': 'new',
        }

    def action_delete_attachment_confirm(self):
        """Abre wizard de confirmación de eliminación."""
        self.ensure_one()
        return {
            'name': 'Confirmar Eliminación',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.delete.attachment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attachment_id': self.id,
                'default_attachment_name': self.name,
            },
        }


# ==============================================================================
# PART 4: WIZARDS
# ==============================================================================

class ActivoAttachmentWizard(models.TransientModel):
    _name = 'activo.attachment.wizard'
    _description = 'Wizard para subir evidencias'

    activo_id = fields.Many2one('activo.intangible', string="Activo", required=True)
    wizard_attachment_ids = fields.Many2many('ir.attachment', string="Nuevos Archivos")

    def action_save_attachments(self):
        """Vincula los archivos subidos al activo."""
        self.ensure_one()
        if self.wizard_attachment_ids:
            self.activo_id.write({
                'attachment_ids': [(4, att.id) for att in self.wizard_attachment_ids]
            })
            for att in self.wizard_attachment_ids:
                att.write({
                    'res_model': 'activo.intangible',
                    'res_id': self.activo_id.id,
                })
        return {'type': 'ir.actions.act_window_close'}


class ActivoDeleteAttachmentWizard(models.TransientModel):
    _name = 'activo.delete.attachment.wizard'
    _description = 'Wizard de confirmación para eliminar evidencia'

    attachment_id = fields.Many2one('ir.attachment', string="Archivo", required=True)
    attachment_name = fields.Char(string="Nombre del archivo", readonly=True)

    def action_confirm_delete(self):
        """Elimina el archivo tras confirmar."""
        self.ensure_one()
        if self.attachment_id:
            self.attachment_id.unlink()
        return {'type': 'ir.actions.act_window_close'}


class ActivoNearExpiryWizard(models.TransientModel):
    """
    WIZARD: Confirmación de activo próximo a vencer.
    Se activa si la fecha de renovación es ≤ 60 días al crear o al activar.
    """
    _name = 'activo.near.expiry.wizard'
    _description = 'Confirmación de activo próximo a vencer'

    name = fields.Char(string="Nombre del Activo", readonly=True)
    renewal_date = fields.Date(string="Fecha de Renovación", readonly=True)
    days_left = fields.Integer(string="Días Restantes", readonly=True)
    pending_vals_json = fields.Text(string="Datos Pendientes", readonly=True)
    
    activo_id = fields.Many2one('activo.intangible', string="Activo Existente")
    action_type = fields.Selection([
        ('create', 'Creación'),
        ('activate', 'Activación')
    ], string="Tipo de Acción", default='create')

    def action_confirm(self):
        """Confirma la acción (crear el activo o cambiar su estado a por_expirar)."""
        self.ensure_one()
        
        if self.action_type == 'create':
            import ast
            vals = ast.literal_eval(self.pending_vals_json)
            self.env['activo.intangible'].with_context(skip_near_expiry_check=True).create(vals)
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Activos Intangibles',
            'res_model': 'activo.intangible',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}