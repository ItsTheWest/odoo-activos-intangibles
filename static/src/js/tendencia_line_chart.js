/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

class TendenciaLineChart extends Component {
    static template = "gestion_activos_intangibles.TendenciaLineChart";

    setup() {
        this.orm       = useService("orm");
        this.action    = useService("action");
        this.canvasRef = useRef("lineCanvas");
        this._chart    = null;
        this._data     = { labels: [], data: [] };

        onWillStart(async () => {
            // Load Chart.js
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

    async _fetchData() {
        // Fetch historical data from Python model
        const result = await this.orm.call(
            "activo.intangible",
            "get_historical_valuation_data",
            []
        );

        console.debug("[TendenciaLineChart] fetched data:", result);
        this._data = result || { labels: [], data: [] };
    }

    _renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        if (this._chart) {
            this._chart.destroy();
        }

        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas, {
            type: "line",
            data: {
                labels: this._data.labels,
                datasets: [{
                    label: 'Valoración ($)',
                    data: this._data.data,
                    borderColor: '#2d9b5e',
                    backgroundColor: 'rgba(45, 155, 94, 0.1)',
                    borderWidth: 3,
                    pointBackgroundColor: '#2d9b5e',
                    pointRadius: 4,
                    fill: true,
                    tension: 0.3
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onHover: (event, chartElement) => {
                    // Update canvas cursor to show the line points are interactive and clickable.
                    const target = event.chart?.canvas || event.native?.target;
                    if (target) {
                        target.style.cursor = chartElement.length ? "pointer" : "default";
                    }
                },
                onClick: (event, elements) => {
                    if (elements && elements.length > 0) {
                        const index = elements[0].index;
                        this._onLineClick(index);
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` $${ctx.raw.toLocaleString()}`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#888",
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: { color: "#f4f6f9" },
                    },
                    x: {
                        ticks: { color: "#555" },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    /**
     * Interactivity Handler: When a point on the line chart is clicked,
     * redirect to the intangible asset list view pre-filtered to show only
     * the assets that existed (acquired/conceded) at or before the end of
     * the clicked month.
     *
     * @param {Number} index - The index of the clicked point (0 to 11)
     */
    _onLineClick(index) {
        const today = new Date();
        // 11 represents the current month (index 11).
        const monthsAgo = 11 - index;
        const targetDate = new Date(today.getFullYear(), today.getMonth() - monthsAgo, 1);
        
        const year = targetDate.getFullYear();
        const month = targetDate.getMonth();
        
        // Find last day of the clicked month
        const lastDay = new Date(year, month + 1, 0);
        const lastDayStr = lastDay.toISOString().split("T")[0];
        
        const label = this._data.labels[index] || "";
        
        this.action.doAction({
            name: `Portafolio Histórico: ${label}`,
            type: "ir.actions.act_window",
            res_model: "activo.intangible",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["state", "!=", "inactivo"],
                "|",
                ["concession_date", "<=", lastDayStr],
                "&",
                ["concession_date", "=", false],
                ["create_date", "<=", lastDayStr]
            ],
            target: "current",
        });
    }
}

// Register as a standalone view widget
registry.category("view_widgets").add("tendencia_line_chart", {
    component: TendenciaLineChart,
});
