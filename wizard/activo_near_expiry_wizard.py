# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore

# ==============================================================================
# WIZARD: ActivoNearExpiryWizard
# Triggered when an asset is created or activated with a renewal_date
# within the next 60 days. Forces explicit user confirmation to prevent
# accidental registration of soon-to-expire assets without awareness.
# ==============================================================================

class ActivoNearExpiryWizard(models.TransientModel):
    _name = 'activo.near.expiry.wizard'
    _description = 'Confirmación de activo próximo a vencer'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Nombre del Activo", readonly=True)
    renewal_date = fields.Date(string="Fecha de Renovación", readonly=True)
    days_left = fields.Integer(string="Días Restantes", readonly=True)
    pending_vals_json = fields.Text(string="Datos Pendientes", readonly=True)

    activo_id = fields.Many2one('activo.intangible', string="Activo Existente")
    action_type = fields.Selection([
        ('create', 'Creación'),
        ('activate', 'Activación')
    ], string="Tipo de Acción", default='create')

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """
        Confirms the pending action:
          - 'create'  : Creates the asset using the serialized pending values.
          - 'activate': Updates the existing asset's state to 'por_expirar'.
        """
        self.ensure_one()

        if self.action_type == 'create':
            import ast
            vals = ast.literal_eval(self.pending_vals_json)
            self.env['activo.intangible'].with_context(skip_near_expiry_check=True).create(vals)

        elif self.action_type == 'activate' and self.activo_id:
            self.activo_id.state = 'por_expirar'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Activos Intangibles',
            'res_model': 'activo.intangible',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_cancel(self):
        """Closes the wizard without performing any action."""
        return {'type': 'ir.actions.act_window_close'}
