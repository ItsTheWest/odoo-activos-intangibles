/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

// ─────────────────────────────────────────────────────────────────────────────
// ESTADO BAR CHART WIDGET
// Standalone OWL component registered in 'view_widgets'.
// Fetches live data from activo.intangible via orm.readGroup and renders a
// Chart.js bar chart — no Python SVG generation needed.
// ─────────────────────────────────────────────────────────────────────────────

const STATE_META = {
    activo:      { label: "Activo",      color: "#27ae60" },
    por_expirar: { label: "Por Expirar", color: "#e67e22" },
    expirado:    { label: "Expirado",    color: "#c0392b" },
    inactivo:    { label: "Inactivo",    color: "#2980b9" },
};

class EstadoBarChart extends Component {
    static template = "gestion_activos_intangibles.EstadoBarChart";

    setup() {
        this.orm       = useService("orm");
        this.canvasRef = useRef("barCanvas");
        this._chart    = null;
        this._data     = [];

        onWillStart(async () => {
            // Correct path for Odoo 17: /web/static/lib/Chart/Chart.js
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._fetchData();
        });

        onMounted(() => {
            this._renderChart();
        });

        onWillUnmount(() => {
            // Destroy chart instance to prevent canvas/memory leaks.
            if (this._chart) {
                this._chart.destroy();
                this._chart = null;
            }
        });
    }

    // ─── Data Layer ───────────────────────────────────────────────────────────

    async _fetchData() {
        /**
         * readGroup(model, domain, fields, groupby)
         * Returns one object per group with:
         *   - state: the state value
         *   - state_count: number of records in that group
         */
        const groups = await this.orm.readGroup(
            "activo.intangible",
            [],
            ["state"],
            ["state"]
        );

        this._data = (groups || []).map((g) => ({
            label: STATE_META[g.state]?.label || g.state,
            count: g.state_count || 0,
            color: STATE_META[g.state]?.color || "#95a5a6",
        }));
    }

    // ─── Rendering Layer ──────────────────────────────────────────────────────

    _renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        // Destroy previous instance if component is reused.
        if (this._chart) {
            this._chart.destroy();
        }

        // Chart is available as a global from the loaded UMD bundle.
        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas, {
            type: "bar",
            data: {
                labels:   this._data.map((d) => d.label),
                datasets: [{
                    data:            this._data.map((d) => d.count),
                    backgroundColor: this._data.map((d) => d.color),
                    borderRadius:    8,
                    barPercentage:   0.55,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                ` ${ctx.raw} activo${ctx.raw !== 1 ? "s" : ""}`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, color: "#888" },
                        grid:  { color: "#f4f6f9" },
                    },
                    x: {
                        ticks: { color: "#555" },
                        grid:  { display: false },
                    },
                },
            },
        });
    }
}

// Register as a standalone view widget — used via <widget name="estado_bar_chart"/>
registry.category("view_widgets").add("estado_bar_chart", {
    component: EstadoBarChart,
});
