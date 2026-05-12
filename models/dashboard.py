from odoo import models, fields, api  # type: ignore


class ActivoIntangibleDashboard(models.TransientModel):
    """
    Transient model used exclusively to render the Statistics Dashboard.
    Computes all global KPIs at creation time from the activo.intangible records.
    This model is never stored; it only exists for the lifetime of the form view session.
    """
    _name = 'activo.intangible.dashboard'
    _description = 'Dashboard de Estadísticas de Activos Intangibles'

    # -----------------------------------------------------------------------
    # KPI Fields — all computed on creation via _default_*
    # Using defaults instead of @api.depends because this is a TransientModel
    # and no further updates are needed after initial load.
    # -----------------------------------------------------------------------

    total_activos = fields.Integer(
        string="Total de Activos",
        default=lambda self: self._compute_total_activos(),
        readonly=True,
    )
    activos_activos = fields.Integer(
        string="Activos Activos",
        default=lambda self: self._compute_por_estado('activo'),
        readonly=True,
    )
    activos_por_expirar = fields.Integer(
        string="Por Expirar",
        default=lambda self: self._compute_por_estado('por_expirar'),
        readonly=True,
    )
    activos_expirados = fields.Integer(
        string="Expirados",
        default=lambda self: self._compute_por_estado('expirado'),
        readonly=True,
    )
    activos_inactivos = fields.Integer(
        string="Inactivos",
        default=lambda self: self._compute_por_estado('inactivo'),
        readonly=True,
    )
    valoracion_total = fields.Monetary(
        string="Valoración Total",
        currency_field='currency_id',
        default=lambda self: self._compute_valoracion_total(),
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    # Holds all asset records so graph widgets can render inline inside the
    # dashboard form, displaying multiple chart types without leaving the page.
    activos_ids = fields.Many2many(
        comodel_name='activo.intangible',
        relation='activo_intangible_dashboard_rel',   # explicit table — no ORM collision
        column1='dashboard_id',
        column2='activo_id',
        string="Activos (Gráficos)",
        default=lambda self: self.env['activo.intangible'].search([]),
        readonly=True,
    )

    # -----------------------------------------------------------------------
    # Private helpers — called once during default computation
    # -----------------------------------------------------------------------

    def _compute_total_activos(self):
        return self.env['activo.intangible'].search_count([])

    def _compute_por_estado(self, estado):
        return self.env['activo.intangible'].search_count([('state', '=', estado)])

    def _compute_valoracion_total(self):
        activos = self.env['activo.intangible'].search([])
        return sum(activos.mapped('valor_contable'))

    # -----------------------------------------------------------------------
    # Navigation actions — open full-page views for deep-dive analysis
    # -----------------------------------------------------------------------

    def action_ver_grafico(self):
        """Opens full-page bar chart grouped by state."""
        return {
            'name': 'Estadísticas — Gráfico por Estado',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['state'], 'graph_mode': 'bar'},
            'target': 'current',
        }

    def action_ver_grafico_tipo(self):
        """Opens full-page pie chart grouped by asset type."""
        return {
            'name': 'Estadísticas — Gráfico por Tipo',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['asset_type_id'], 'graph_mode': 'pie'},
            'target': 'current',
        }

    def action_ver_pivot(self):
        """Opens full-page pivot table for Excel export."""
        return {
            'name': 'Estadísticas — Tabla Pivot',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'pivot,graph',
            'target': 'current',
        }
