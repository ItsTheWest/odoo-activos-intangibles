/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

/**
 * TIPO ACTIVO PIE CHART WIDGET
 * 
 * This component visualizes the composition of intangible assets by their type.
 * It uses Chart.js to render a doughnut chart for a premium, modern look.
 * Data is fetched in real-time from the 'activo.intangible' model.
 */

// Categorical color palette for different asset types
const COLORS = [
    "#27ae60", "#2980b9", "#8e44ad", "#f39c12", "#d35400",
    "#16a085", "#2c3e50", "#c0392b", "#7f8c8d", "#2ecc71"
];

class TipoActivoPieChart extends Component {
    static template = "gestion_activos_intangibles.TipoActivoPieChart";

    setup() {
        this.orm       = useService("orm");
        this.action    = useService("action");
        this.canvasRef = useRef("pieCanvas");
        this._chart    = null;
        this._data     = [];

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._fetchData();
        });

        onMounted(() => {
            this._renderChart();
        });

        onWillUnmount(() => {
            if (this._chart) {
                this._chart.destroy();
                this._chart = null;
            }
        });
    }

    // ─── Data Layer ───────────────────────────────────────────────────────────

    async _fetchData() {
        const groups = await this.orm.call(
            "activo.intangible",
            "read_group",
            [],
            {
                domain:  [],
                fields:  ["asset_type_id"],
                groupby: ["asset_type_id"],
                lazy:    false,
            }
        );

        console.debug("[TipoActivoPieChart] read_group response:", groups);

        this._data = (groups || []).map((g, index) => {
            // asset_type_id usually comes as [id, "Name"] or false
            const typeId = Array.isArray(g.asset_type_id) ? g.asset_type_id[0] : g.asset_type_id;
            const typeLabel = Array.isArray(g.asset_type_id) 
                ? g.asset_type_id[1] 
                : (g.asset_type_id || "Sin Tipo");
                
            return {
                id:    typeId,
                label: typeLabel,
                count: g.__count || 0,
                color: COLORS[index % COLORS.length],
            };
        });
    }

    // ─── Rendering Layer ──────────────────────────────────────────────────────

    _renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas || this._data.length === 0) return;

        if (this._chart) {
            this._chart.destroy();
        }

        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels:   this._data.map((d) => d.label),
                datasets: [{
                    data:            this._data.map((d) => d.count),
                    backgroundColor: this._data.map((d) => d.color),
                    borderWidth:     2,
                    borderColor:     "#ffffff",
                    hoverOffset:     10,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                cutout:              "70%", // Makes it a sleek doughnut
                onHover: (event, chartElement) => {
                    // Update canvas cursor to show the segments are interactive and clickable.
                    const target = event.chart?.canvas || event.native?.target;
                    if (target) {
                        target.style.cursor = chartElement.length ? "pointer" : "default";
                    }
                },
                onClick: (event, elements) => {
                    if (elements && elements.length > 0) {
                        const index = elements[0].index;
                        this._onPieClick(index);
                    }
                },
                plugins: {
                    legend: {
                        position: "right",
                        labels: {
                            usePointStyle: true,
                            padding:       15,
                            font:          { size: 12 },
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((ctx.raw / total) * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.raw} (${percentage}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    /**
     * Interactivity Handler: When a pie segment representing a specific asset type
     * is clicked, redirect to the intangible asset list view pre-filtered by that type.
     *
     * @param {Number} index - The index of the clicked segment
     */
    _onPieClick(index) {
        const item = this._data[index];
        if (!item) return;

        this.action.doAction({
            name: `Activos: ${item.label}`,
            type: "ir.actions.act_window",
            res_model: "activo.intangible",
            views: [[false, "list"], [false, "form"]],
            domain: [["asset_type_id", "=", item.id]],
            target: "current",
        });
    }
}

// Register as a standalone view widget
registry.category("view_widgets").add("tipo_activo_pie_chart", {
    component: TipoActivoPieChart,
});
