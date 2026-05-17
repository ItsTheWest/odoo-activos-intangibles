# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore

# ==============================================================================
# CONFIGURATION MODEL: ActivoIntangibleType
# Defines the catalogue of intangible asset types (e.g., Patent, Trademark).
# Each type carries a default lifespan used to auto-calculate renewal dates.
# ==============================================================================

class ActivoIntangibleType(models.Model):
    _name = 'activo.intangible.type'
    _description = 'Tipos de Activos Intangibles'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Tipo de Activo", required=True)
    code = fields.Char(string="Código", help="Código interno del tipo de activo")
    lifespan_days = fields.Integer(
        string="Días de Vigencia",
        default=0,
        help="Días predeterminados para caducidad. Used to auto-fill renewal_date on asset creation.",
    )
    lifespan_display = fields.Char(
        string="Vigencia (Display)",
        compute="_compute_lifespan_display",
    )
    description = fields.Text(string="Descripción")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('lifespan_days')
    def _compute_lifespan_display(self):
        """Formats the lifespan into a human-readable 'X year(s) and Y day(s)' string."""
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

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_edit_type(self):
        """Opens the form view for the selected asset type in a modal window."""
        self.ensure_one()
        return {
            'name': 'Editar Tipo de Activo',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible.type',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
