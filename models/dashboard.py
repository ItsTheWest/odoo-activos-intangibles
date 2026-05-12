from odoo import models, fields, api  # type: ignore


class ActivoIntangibleDashboard(models.TransientModel):
    """
    ARCHITECTURE NOTE:
    This is a 'TransientModel' (stored in RAM/Temporary table).
    We use it for the Dashboard because:
    1. It doesn't bloat the main database with persistent statistic records.
    2. It allows us to calculate 'Fresh' data every time the user opens the view.
    3. It provides a clean 'Form View' interface where we can inject custom HTML/SVG.
    """
    _name = 'activo.intangible.dashboard'
    _description = 'Dashboard de Estadísticas de Activos Intangibles'

    # -----------------------------------------------------------------------
    # KPI FIELDS (Key Performance Indicators)
    # These fields use 'default' lambdas to compute values on-the-fly when 
    # the record is initialized for the user.
    # -----------------------------------------------------------------------

    total_activos = fields.Integer(
        string="Total de Activos",
        default=lambda self: self._compute_total_activos(),
        help="Total count of all intangible assets in the system.",
        readonly=True,
    )
    activos_activos = fields.Integer(
        string="Activos Activos",
        default=lambda self: self._compute_por_estado('activo'),
        help="Count of assets currently in 'Active' state.",
        readonly=True,
    )
    activos_por_expirar = fields.Integer(
        string="Por Expirar",
        default=lambda self: self._compute_por_estado('por_expirar'),
        help="Assets that will reach their renewal date within the next 60 days.",
        readonly=True,
    )
    activos_expirados = fields.Integer(
        string="Expirados",
        default=lambda self: self._compute_por_estado('expirado'),
        help="Assets whose renewal date has already passed.",
        readonly=True,
    )
    activos_inactivos = fields.Integer(
        string="Inactivos",
        default=lambda self: self._compute_por_estado('inactivo'),
        help="Assets manually set to inactive.",
        readonly=True,
    )
    valoracion_total = fields.Monetary(
        string="Valoración Total",
        currency_field='currency_id',
        default=lambda self: self._compute_valoracion_total(),
        help="Sum of 'valor_contable' across all registered assets.",
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    # -----------------------------------------------------------------------
    # DYNAMIC SVG GRAPHS (The "WOW" Factor)
    # We use fields.Html to render raw SVG strings. This avoids the complexity
    # of Odoo's JS registry (OWL) while maintaining high performance.
    # -----------------------------------------------------------------------
    graph_estado_svg = fields.Html(string="Gráfico de Estados", compute="_compute_graphs")
    graph_tipo_svg = fields.Html(string="Gráfico de Tipos", compute="_compute_graphs")
    graph_vencimientos_svg = fields.Html(string="Línea de Tiempo", compute="_compute_graphs")

    @api.depends('total_activos')  # Dummy dependency to trigger computation
    def _compute_graphs(self):
        """
        Main computation engine for visualizations.
        1. Fetches all asset records once to optimize performance.
        2. Passes the recordset to specialized SVG generator methods.
        """
        activos = self.env['activo.intangible'].search([])
        
        for record in self:
            # We assign the raw SVG string to the HTML field.
            # Odoo's 'html' widget will render this directly in the browser.
            record.graph_estado_svg = self._generate_bar_chart(activos)
            record.graph_tipo_svg = self._generate_pie_chart(activos)
            record.graph_vencimientos_svg = self._generate_timeline_chart(activos)

    # -----------------------------------------------------------------------
    # DATA COMPUTATION HELPERS
    # These methods use Odoo's ORM (Object-Relational Mapping) to query the DB.
    # -----------------------------------------------------------------------

    def _compute_total_activos(self):
        """Returns the total number of records in the asset table."""
        return self.env['activo.intangible'].search_count([])

    def _compute_por_estado(self, estado):
        """Returns the number of assets filtered by a specific state."""
        return self.env['activo.intangible'].search_count([('state', '=', estado)])

    def _compute_valoracion_total(self):
        """
        Sums up the financial value of all assets.
        .mapped('field') is a shorthand to get a list of values from a recordset.
        """
        activos = self.env['activo.intangible'].search([])
        return sum(activos.mapped('valor_contable'))

    # -----------------------------------------------------------------------
    # SVG RENDERING ENGINE (The Math behind the visuals)
    # -----------------------------------------------------------------------

    def _generate_bar_chart(self, activos):
        """
        BAR CHART GENERATOR
        Logic: Calculate the height of each bar relative to the maximum value.
        - max_height: 150px
        - Formula: (current_value / max_value) * max_height
        """
        states = {
            'activo': {'label': 'Activo', 'color': '#27ae60', 'count': 0},
            'por_expirar': {'label': 'Por Expirar', 'color': '#e67e22', 'count': 0},
            'expirado': {'label': 'Expirado', 'color': '#c0392b', 'count': 0},
            'inactivo': {'label': 'Inactivo', 'color': '#2980b9', 'count': 0},
        }
        for a in activos:
            if a.state in states:
                states[a.state]['count'] += 1

        # Max val prevents division by zero and sets the chart scale
        max_val = max([s['count'] for s in states.values()] or [1])
        
        # ViewBox defines the internal coordinate system of the SVG
        svg = '<div class="text-center"><svg viewBox="0 0 400 200" style="max-height:250px; width:100%;">'
        x = 50
        for code, data in states.items():
            h = (data['count'] / max_val) * 150 if max_val > 0 else 0
            # SVG coordinates start at top-left (0,0). To draw bars from bottom-up,
            # we subtract height from the baseline (170).
            svg += f"""
                <rect x="{x}" y="{170 - h}" width="40" height="{h}" fill="{data['color']}" rx="4">
                    <title>{data['label']}: {data['count']}</title>
                </rect>
                <text x="{x + 20}" y="190" font-size="10" text-anchor="middle" fill="#666">{data['label']}</text>
                <text x="{x + 20}" y="{165 - h}" font-size="12" font-weight="bold" text-anchor="middle" fill="{data['color']}">{data['count']}</text>
            """
            x += 85
        svg += '</svg></div>'
        return svg

    def _generate_pie_chart(self, activos):
        """
        DONUT CHART GENERATOR
        Logic: Use SVG 'stroke-dasharray' to draw circle segments.
        - Radius: 70
        - Circumference: 2 * PI * Radius (~439.8)
        - Segment Length: (Count / Total) * Circumference
        """
        types = {}
        for a in activos:
            name = a.asset_type_id.name or 'Otros'
            types[name] = types.get(name, 0) + 1
        
        if not types:
            return '<div class="text-muted text-center p-5">Sin datos de tipos</div>'

        total = sum(types.values())
        colors = ['#1155cc', '#27ae60', '#f1c40f', '#e67e22', '#c0392b', '#8e44ad', '#2c3e50']
        svg = '<div class="text-center"><svg viewBox="0 0 400 220" style="max-height:250px; width:100%;">'
        
        # DRAW LEGEND (Text and Squares)
        ly = 30
        idx = 0
        for name, count in types.items():
            color = colors[idx % len(colors)]
            svg += f"""
                <rect x="250" y="{ly}" width="12" height="12" fill="{color}" rx="2"/>
                <text x="270" y="{ly + 10}" font-size="11" fill="#444">{name[:15]}... ({count})</text>
            """
            ly += 22
            idx += 1

        # DRAW DONUT (Mathematical circles)
        radius = 70
        circumference = 2 * 3.14159 * radius
        current_offset = 0
        idx = 0
        for name, count in types.items():
            color = colors[idx % len(colors)]
            dash = (count / total) * circumference
            # Stroke-dashoffset shifts the starting point of the dash
            svg += f"""
                <circle cx="100" cy="110" r="{radius}" fill="none" stroke="{color}" stroke-width="35" 
                        stroke-dasharray="{dash} {circumference - dash}" 
                        stroke-dashoffset="-{current_offset}" transform="rotate(-90 100 110)">
                    <title>{name}: {count}</title>
                </circle>
            """
            current_offset += dash
            idx += 1

        # Center text (Total count)
        svg += f'<text x="100" y="120" text-anchor="middle" font-size="28" font-weight="bold" fill="#333">{total}</text>'
        svg += f'<text x="100" y="140" text-anchor="middle" font-size="10" fill="#999">TOTAL</text>'
        svg += '</svg></div>'
        return svg

    def _generate_timeline_chart(self, activos):
        """
        TREND LINE CHART GENERATOR
        Logic: Connect (x,y) points with a <polyline>.
        - X axis: 6 months (Today + 30, 60, 90... days)
        - Y axis: Number of assets expiring in that month.
        """
        from datetime import datetime, timedelta
        
        # 1. Generate month names for the labels
        today = datetime.now()
        months = []
        for i in range(6):
            target_date = today + timedelta(days=i*30)
            months.append(target_date.strftime('%b'))
        
        # 2. Map assets to their expiration month
        counts = [0] * 6
        for a in activos:
            if a.renewal_date:
                v_date = fields.Date.from_string(a.renewal_date)
                if today.date() <= v_date:
                    diff_months = (v_date.year - today.year) * 12 + v_date.month - today.month
                    if 0 <= diff_months < 6:
                        counts[diff_months] += 1

        max_count = max(counts + [1])
        svg = '<div class="p-3"><svg viewBox="0 0 800 150" style="width:100%; height:120px;">'
        
        # 3. Draw baseline
        svg += '<line x1="50" y1="110" x2="750" y2="110" stroke="#eee" stroke-width="2"/>'
        
        x = 100
        points = []
        for i, val in enumerate(counts):
            h = (val / max_count) * 80
            y = 110 - h
            points.append(f"{x},{y}")
            
            # Label
            svg += f'<text x="{x}" y="130" text-anchor="middle" font-size="12" fill="#888">{months[i]}</text>'
            # Point
            svg += f'<circle cx="{x}" cy="{y}" r="5" fill="#1155cc"/>'
            svg += f'<text x="{x}" y="{y-10}" text-anchor="middle" font-size="14" font-weight="bold" fill="#1155cc">{val}</text>'
            x += 120
        
        # 4. Connect points with polyline
        if len(points) > 1:
            polyline_points = " ".join(points)
            svg += f'<polyline points="{polyline_points}" fill="none" stroke="#1155cc" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
            
        svg += '</svg></div>'
        return svg

    # -----------------------------------------------------------------------
    # NAVIGATION ACTIONS (Drill-down logic)
    # These return an Odoo Action dictionary to switch views.
    # -----------------------------------------------------------------------

    def action_ver_grafico(self):
        """Redirects to the native Odoo Graph view for State analysis."""
        return {
            'name': 'Análisis por Estado',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['state'], 'graph_mode': 'bar'},
            'target': 'current',
        }

    def action_ver_grafico_tipo(self):
        """Redirects to the native Odoo Graph view for Type analysis."""
        return {
            'name': 'Análisis por Tipo',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['asset_type_id'], 'graph_mode': 'pie'},
            'target': 'current',
        }

    def action_ver_pivot(self):
        """Redirects to the Pivot table for advanced data cross-referencing."""
        return {
            'name': 'Explorador de Datos (Pivot)',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'pivot,graph',
            'target': 'current',
        }

