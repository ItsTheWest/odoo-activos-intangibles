# -*- coding: utf-8 -*-
from odoo import models  # type: ignore

# ==============================================================================
# BASE MODEL EXTENSION: IrAttachment
# Extends Odoo's native attachment model to support:
#   - In-app document preview modal.
#   - Confirmation wizard before physical deletion.
# ==============================================================================

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_modal(self):
        """Opens a modal to preview the current document."""
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
        """Opens the deletion confirmation wizard for the selected attachment."""
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
