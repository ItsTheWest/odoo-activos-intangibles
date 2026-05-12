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
    # KPI Fields — all computed on creation via default=...
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

    # -----------------------------------------------------------------------
    # DYNAMIC SVG GRAPHS — Generated in Python for maximum compatibility
    # and "WOW" aesthetics without breaking the Owl lifecycle.
    # -----------------------------------------------------------------------
    graph_estado_svg = fields.Html(string="Gráfico de Estados", compute="_compute_graphs")
    graph_tipo_svg = fields.Html(string="Gráfico de Tipos", compute="_compute_graphs")
    graph_vencimientos_svg = fields.Html(string="Línea de Tiempo", compute="_compute_graphs")

    def _compute_graphs(self):
        """
        Computes the SVG HTML strings for the three main dashboard charts.
        This method searches all records in 'activo.intangible' and passes them
        to the specific rendering helper functions. It is triggered automatically
        by Odoo when the HTML fields are requested in the view.
        """
        activos = self.env['activo.intangible'].search([])
        
        for record in self:
            record.graph_estado_svg = self._generate_bar_chart(activos)
            record.graph_tipo_svg = self._generate_pie_chart(activos)
            record.graph_vencimientos_svg = self._generate_timeline_chart(activos)

    # -----------------------------------------------------------------------
    # Private helpers — called during default computation
    # -----------------------------------------------------------------------

    def _compute_total_activos(self):
        """Calculates the total number of intangible assets currently in the system."""
        return self.env['activo.intangible'].search_count([])

    def _compute_por_estado(self, estado):
        """
        Calculates the number of assets currently in a specific state.
        :param estado: String representing the state (e.g., 'activo', 'expirado').
        """
        return self.env['activo.intangible'].search_count([('state', '=', estado)])

    def _compute_valoracion_total(self):
        """
        Calculates the sum of the book value ('valor_contable') across all assets.
        This gives the total financial valuation of the intangible assets portfolio.
        """
        activos = self.env['activo.intangible'].search([])
        return sum(activos.mapped('valor_contable'))

    # -----------------------------------------------------------------------
    # SVG GENERATORS (Architect Level)
    # -----------------------------------------------------------------------

    def _generate_bar_chart(self, activos):
        """
        Generates a professional bar chart (in raw SVG format) to display the distribution 
        of assets across their different lifecycle states (Active, Expiring, Expired, Inactive).
        
        Logic:
        1. Initializes a dictionary with colors and labels for each state.
        2. Iterates over the assets to count occurrences of each state.
        3. Determines the maximum count to scale the bars correctly (max height is 150px).
        4. Constructs the SVG string with <rect> elements for the bars and <text> for labels.
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

        max_val = max([s['count'] for s in states.values()] or [1])
        svg = '<div class="text-center"><svg viewBox="0 0 400 200" style="max-height:250px; width:100%;">'
        x = 50
        for code, data in states.items():
            h = (data['count'] / max_val) * 150 if max_val > 0 else 0
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
        Generates an accurate donut (pie) chart in SVG format to display the composition 
        of assets grouped by their Asset Type ('asset_type_id').
        
        Logic:
        1. Groups assets by type and counts them.
        2. If no data exists, returns a placeholder div.
        3. Calculates the circumference of the SVG circle.
        4. Iterates through the groups, calculating the 'stroke-dasharray' (the length of the segment)
           and 'stroke-dashoffset' (where the segment starts) to draw the exact proportions.
        5. Adds a legend on the right side and the total count in the center of the donut.
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
        
        # Legend (Right side)
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

        # Real Donut calculation
        radius = 70
        circumference = 2 * 3.14159 * radius
        current_offset = 0
        idx = 0
        for name, count in types.items():
            color = colors[idx % len(colors)]
            dash = (count / total) * circumference
            # We use stroke-dasharray and stroke-dashoffset to draw segments
            svg += f"""
                <circle cx="100" cy="110" r="{radius}" fill="none" stroke="{color}" stroke-width="35" 
                        stroke-dasharray="{dash} {circumference - dash}" 
                        stroke-dashoffset="-{current_offset}" transform="rotate(-90 100 110)">
                    <title>{name}: {count}</title>
                </circle>
            """
            current_offset += dash
            idx += 1

        svg += f'<text x="100" y="120" text-anchor="middle" font-size="28" font-weight="bold" fill="#333">{total}</text>'
        svg += f'<text x="100" y="140" text-anchor="middle" font-size="10" fill="#999">TOTAL</text>'
        svg += '</svg></div>'
        return svg

    def _generate_timeline_chart(self, activos):
        """
        Generates a trend line chart predicting upcoming asset expirations for the next 6 months.
        
        Logic:
        1. Generates the names of the next 6 months starting from today.
        2. Iterates through all assets checking their 'fecha_vencimiento' (Expiration Date).
        3. If the date falls within the next 6 months, it increments the count for that specific month.
        4. Calculates the maximum count to scale the Y-axis points (max height is 80px).
        5. Draws the background baseline, then draws circles for each data point.
        6. Finally, connects the data points using an SVG <polyline> element.
        """
        from datetime import datetime, timedelta
        
        # Prepare 6 months map
        today = datetime.now()
        months = []
        for i in range(6):
            target_date = today + timedelta(days=i*30)
            months.append(target_date.strftime('%b'))
        
        # Count expirations per month
        counts = [0] * 6
        for a in activos:
            if a.fecha_vencimiento:
                # Simple check if date is in next 6 months
                v_date = fields.Date.from_string(a.fecha_vencimiento)
                if today.date() <= v_date:
                    diff_months = (v_date.year - today.year) * 12 + v_date.month - today.month
                    if 0 <= diff_months < 6:
                        counts[diff_months] += 1

        max_count = max(counts + [1])
        svg = '<div class="p-3"><svg viewBox="0 0 800 150" style="width:100%; height:120px;">'
        
        # Draw base line
        svg += '<line x1="50" y1="110" x2="750" y2="110" stroke="#eee" stroke-width="2"/>'
        
        x = 100
        points = []
        for i, val in enumerate(counts):
            h = (val / max_count) * 80
            y = 110 - h
            points.append(f"{x},{y}")
            
            # Month Label
            svg += f'<text x="{x}" y="130" text-anchor="middle" font-size="12" fill="#888">{months[i]}</text>'
            # Value Point
            svg += f'<circle cx="{x}" cy="{y}" r="5" fill="#1155cc"/>'
            svg += f'<text x="{x}" y="{y-10}" text-anchor="middle" font-size="14" font-weight="bold" fill="#1155cc">{val}</text>'
            
            x += 120
        
        # Draw connecting line
        if len(points) > 1:
            polyline_points = " ".join(points)
            svg += f'<polyline points="{polyline_points}" fill="none" stroke="#1155cc" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
            
        svg += '</svg></div>'
        return svg

    # -----------------------------------------------------------------------
    # Navigation actions — drill down to full Odoo Views
    # -----------------------------------------------------------------------

    def action_ver_grafico(self):
        """
        Action triggered by the "Ver completo" button in the States chart container.
        Redirects the user to the native Odoo graph view, grouped by 'state' as a bar chart.
        """
        return {
            'name': 'Análisis por Estado',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['state'], 'graph_mode': 'bar'},
            'target': 'current',
        }

    def action_ver_grafico_tipo(self):
        """
        Action triggered by the "Ver completo" button in the Types chart container.
        Redirects the user to the native Odoo graph view, grouped by 'asset_type_id' as a pie chart.
        """
        return {
            'name': 'Análisis por Tipo',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'graph,pivot',
            'context': {'graph_groupbys': ['asset_type_id'], 'graph_mode': 'pie'},
            'target': 'current',
        }

    def action_ver_pivot(self):
        """
        Action triggered by the "Explorar Datos" button in the Timeline container.
        Redirects the user to the native Odoo pivot view for deep data exploration.
        """
        return {
            'name': 'Explorador de Datos (Pivot)',
            'type': 'ir.actions.act_window',
            'res_model': 'activo.intangible',
            'view_mode': 'pivot,graph',
            'target': 'current',
        }
