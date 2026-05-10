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
    lifespan_display = fields.Char(string="Vigencia (Display)", compute="_compute_lifespan_display")
    description = fields.Text(string="Descripción")

    @api.depends('lifespan_days')
    def _compute_lifespan_display(self):
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

    # ---------------------------------------------------------------
    # DIGITAL EVIDENCE — explicit Many2many to ir.attachment
    #
    # WHY explicit and not mail.thread's implicit attachment_ids?
    # mail.thread only wires attachments to the Chatter internally.
    # It does NOT expose 'attachment_ids' as a usable ORM field on
    # the model, so the many2many_binary widget would fail with
    # "Field does not exist" unless we declare it ourselves.
    #
    # This Many2many creates its own relation table
    # (activo_intangible_ir_attachment_rel) so files uploaded here
    # are explicitly linked to the asset record.
    # ---------------------------------------------------------------
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='activo_intangible_ir_attachment_rel',  # explicit table name avoids collisions
        column1='activo_id',
        column2='attachment_id',
        string="Evidencias Digitales",
    )

    document_count = fields.Integer(
        string="Documentos",
        compute="_compute_document_count",
        store=False,
    )

    @api.depends('attachment_ids')
    def _compute_document_count(self):
        """Derive count directly from the Many2many field — no extra SQL query."""
        for rec in self:
            rec.document_count = len(rec.attachment_ids)

    def write(self, vals):
        before_attachments = self.attachment_ids
        res = super(ActivoIntangible, self).write(vals)
        if 'attachment_ids' in vals:
            after_attachments = self.attachment_ids
            removed_attachments = before_attachments - after_attachments
            if removed_attachments:
                removed_attachments.sudo().unlink()
        return res

    def action_open_attachment_wizard(self):
        """Action to open the upload wizard for digital evidences."""
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
        for record in self:
            record.state = 'inactivo'

    def action_renovar(self):
        for record in self:
            if not record.renewal_date:
                raise UserError("Error: No se puede activar el activo sin una Fecha de Renovación.")
            if not record.attachment_ids:
                raise UserError("Error: No se puede activar el activo sin adjuntar al menos un documento de evidencia (contrato o licencia).")
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

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_modal(self):
        """Abre un modal (form target='new') para previsualizar el documento actual."""
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
        """Opens a confirmation wizard before permanently deleting the attachment."""
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

class ActivoAttachmentWizard(models.TransientModel):
    _name = 'activo.attachment.wizard'
    _description = 'Wizard para subir evidencias'

    activo_id = fields.Many2one('activo.intangible', string="Activo", required=True)
    wizard_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Nuevos Archivos"
    )

    def action_save_attachments(self):
        self.ensure_one()
        if self.wizard_attachment_ids:
            # Enlaza los nuevos archivos al campo Many2many real del activo
            self.activo_id.write({
                'attachment_ids': [(4, att.id) for att in self.wizard_attachment_ids]
            })
            # Actualiza el registro de Odoo para vincular lógicamente
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
        """Permanently deletes the attachment after user confirms."""
        self.ensure_one()
        if self.attachment_id:
            self.attachment_id.unlink()
        return {'type': 'ir.actions.act_window_close'}