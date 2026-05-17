# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore

# ==============================================================================
# WIZARD: ActivoAttachmentWizard
# Handles uploading and linking multiple digital evidence files to an asset.
# ==============================================================================

class ActivoAttachmentWizard(models.TransientModel):
    _name = 'activo.attachment.wizard'
    _description = 'Wizard para subir evidencias'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    activo_id = fields.Many2one('activo.intangible', string="Activo", required=True)
    wizard_attachment_ids = fields.Many2many('ir.attachment', string="Nuevos Archivos")

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_save_attachments(self):
        """Links uploaded files to the asset and updates their res_model/res_id for proper ownership."""
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
