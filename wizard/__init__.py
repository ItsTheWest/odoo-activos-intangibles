# -*- coding: utf-8 -*-
# Import order matters: configuration models first, then main model,
# then base model extensions. This avoids forward-reference issues
# during the Odoo registry initialization.
from . import activo_attachment_wizard
from . import activo_delete_wizard
from . import activo_near_expiry_wizard
