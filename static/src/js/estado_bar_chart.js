/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

// ─── Why orm.call instead of orm.readGroup? ──────────────────────────────────
// The 'orm' service in Odoo 17 does not have a method named 'readGroup' (it has
// 'webReadGroup' and 'call'). We use 'this.orm.call' to directly invoke the 
// Python 'read_group' method, which is the most reliable approach.
// ─────────────────────────────────────────────────────────────────────────────

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
         * Calls Python's read_group() via orm.call.
         *
         * KEY: When lazy=false, Odoo returns the record count in '__count',
         * NOT in 'state_count'. Using the wrong key was the root cause of
         * bars rendering at height 0.
         */
        const groups = await this.orm.call(
            "activo.intangible",
            "read_group",
            [],
            {
                domain:  [],
                fields:  ["state"],
                groupby: ["state"],
                lazy:    false,
            }
        );

        // Debug: log the raw response so the data shape is always inspectable.
        console.debug("[EstadoBarChart] read_group response:", groups);

        this._data = (groups || []).map((g) => {
            // 'g.state' is the raw selection key (string), e.g. "activo".
            // '__count' holds the number of records in this group.
            const stateKey = g.state || "";
            return {
                label: STATE_META[stateKey]?.label || stateKey,
                count: g.__count || 0,
                color: STATE_META[stateKey]?.color || "#95a5a6",
            };
        });
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
