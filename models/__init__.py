# -*- coding: utf-8 -*-
# Import order is critical for Odoo's registry:
#   1. activo_intangible_type   -> must be first; ActivoIntangible references it via Many2one.
#   2. activo_intangible        -> main model, depends on the type catalogue above.
#   3. ir_attachment_inherit    -> extends a base model; no internal dependencies.
#   4. dashboard                -> read-only reporting model; loaded last.
from . import activo_intangible_type
from . import activo_intangible
from . import ir_attachment_inherit
from . import dashboard
