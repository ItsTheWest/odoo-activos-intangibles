# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore

# ==============================================================================
# WIZARD: ActivoDeleteAttachmentWizard
# Presents a confirmation dialog before physically deleting an attachment
# from the system, preventing accidental data loss.
# ==============================================================================

class ActivoDeleteAttachmentWizard(models.TransientModel):
    _name = 'activo.delete.attachment.wizard'
    _description = 'Wizard de confirmación para eliminar evidencia'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    attachment_id = fields.Many2one('ir.attachment', string="Archivo", required=True)
    attachment_name = fields.Char(string="Nombre del archivo", readonly=True)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_confirm_delete(self):
        """Physically deletes the attachment after user confirmation."""
        self.ensure_one()
        if self.attachment_id:
            self.attachment_id.unlink()
        return {'type': 'ir.actions.act_window_close'}
