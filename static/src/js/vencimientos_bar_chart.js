/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

// ─────────────────────────────────────────────────────────────────────────────
// VENCIMIENTOS BAR CHART WIDGET
// Displays how many intangible assets expire in each of the next 6 months.
// Uses orm.call("read_group") so it follows the same proven pattern as
// EstadoBarChart — direct Python RPC, no custom @api.model method needed.
// ─────────────────────────────────────────────────────────────────────────────

// Month abbreviation lookup (Spanish UI, as per project language policy).
const MONTH_NAMES_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
];

class VencimientosBarChart extends Component {
    static template = "gestion_activos_intangibles.VencimientosBarChart";

    setup() {
        this.orm       = useService("orm");
        this.action    = useService("action");
        this.canvasRef = useRef("vencimientosCanvas");
        this._chart    = null;
        this._data     = { labels: [], data: [] };

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
        /**
         * Build a 6-month window starting from today.
         * We query assets whose renewal_date falls within [today, +6 months],
         * grouped by the month of renewal_date.
         *
         * Odoo's read_group with groupby:["renewal_date:month"] returns one
         * bucket per month present in the data. We then merge those buckets
         * into a dense 6-slot array (months with 0 expiries still show up).
         */
        const today  = new Date();
        const future = new Date(today);
        future.setMonth(future.getMonth() + 6);

        // ISO date strings: "YYYY-MM-DD"
        const todayStr  = today.toISOString().split("T")[0];
        const futureStr = future.toISOString().split("T")[0];

        const groups = await this.orm.call(
            "activo.intangible",
            "read_group",
            [],
            {
                domain:  [
                    ["renewal_date", ">=", todayStr],
                    ["renewal_date", "<=", futureStr],
                    ["state", "!=", "inactivo"],
                ],
                fields:  ["renewal_date"],
                groupby: ["renewal_date:month"],
                lazy:    false,
            }
        );

        console.debug("[VencimientosBarChart] read_group response:", groups);

        // Build a dense lookup: "YYYY-MM" -> count
        const countByMonth = {};
        (groups || []).forEach((g) => {
            // Odoo returns the group key as a date string like "01/05/2026 00:00:00"
            // or a parsed value. We extract year-month from the __range or the key.
            const raw = g["renewal_date:month"];  // e.g. "05/2026" or a date object
            if (!raw) return;

            // Parse different possible formats Odoo may return.
            let year, month;
            if (typeof raw === "string") {
                // Formats observed: "MM/YYYY" or "YYYY-MM-DD"
                const parts = raw.split("/");
                if (parts.length === 2) {
                    // "MM/YYYY"
                    month = parseInt(parts[0], 10) - 1;  // 0-indexed
                    year  = parseInt(parts[1], 10);
                } else {
                    const d = new Date(raw);
                    year  = d.getFullYear();
                    month = d.getMonth();
                }
            } else {
                const d = new Date(raw);
                year  = d.getFullYear();
                month = d.getMonth();
            }

            const key = `${year}-${String(month + 1).padStart(2, "0")}`;
            countByMonth[key] = (countByMonth[key] || 0) + (g.__count || 0);
        });

        // Build the 6-slot dense array.
        const labels = [];
        const data   = [];
        for (let i = 0; i < 6; i++) {
            const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
            labels.push(`${MONTH_NAMES_ES[d.getMonth()]} ${d.getFullYear()}`);
            data.push(countByMonth[key] || 0);
        }

        this._data = { labels, data };
    }

    // ─── Rendering Layer ──────────────────────────────────────────────────────

    _renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        if (this._chart) {
            this._chart.destroy();
        }

        // Color scale: first month is lightest info blue, last is darkest.
        const barColors = [
            "#b3d9f5", "#7ebfe8", "#4da6db", "#2980b9", "#1f638f", "#164a6b"
        ];

        // eslint-disable-next-line no-undef
        this._chart = new Chart(canvas, {
            type: "bar",
            data: {
                labels:   this._data.labels,
                datasets: [{
                    label:           "Vencimientos",
                    data:            this._data.data,
                    backgroundColor: barColors,
                    borderColor:     barColors.map(c => c),
                    borderWidth:     0,
                    borderRadius:    8,
                    barPercentage:   0.60,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                onHover: (event, chartElement) => {
                    // Update canvas cursor to show the bars are interactive and clickable.
                    const target = event.chart?.canvas || event.native?.target;
                    if (target) {
                        target.style.cursor = chartElement.length ? "pointer" : "default";
                    }
                },
                onClick: (event, elements) => {
                    if (elements && elements.length > 0) {
                        const index = elements[0].index;
                        this._onBarClick(index);
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) =>
                                ` ${ctx.raw} activo${ctx.raw !== 1 ? "s" : ""} por vencer`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color:    "#888",
                            callback: (v) => Number.isInteger(v) ? v : null,
                        },
                        grid: { color: "#f4f6f9" },
                    },
                    x: {
                        ticks: { color: "#555" },
                        grid:  { display: false },
                    },
                },
            },
        });
    }

    /**
     * Interactivity Handler: When a bar representing a specific month is clicked,
     * it triggers a standard Odoo window action to redirect to the intangible asset
     * list view, pre-filtered for active assets expiring in that specific month.
     *
     * @param {Number} index - The index of the clicked bar (0 to 5)
     */
    _onBarClick(index) {
        const today = new Date();
        const targetDate = new Date(today.getFullYear(), today.getMonth() + index, 1);
        
        const year = targetDate.getFullYear();
        const month = targetDate.getMonth();
        
        // Compute precise date boundaries for the selected month (start / end)
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        
        const firstDayStr = firstDay.toISOString().split("T")[0];
        const lastDayStr = lastDay.toISOString().split("T")[0];
        
        this.action.doAction({
            name: `Vencimientos: ${MONTH_NAMES_ES[month]} ${year}`,
            type: "ir.actions.act_window",
            res_model: "activo.intangible",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["renewal_date", ">=", firstDayStr],
                ["renewal_date", "<=", lastDayStr],
                ["state", "!=", "inactivo"]
            ],
            target: "current",
        });
    }
}

// Register as a standalone view widget — used via <widget name="vencimientos_bar_chart"/>
registry.category("view_widgets").add("vencimientos_bar_chart", {
    component: VencimientosBarChart,
});
