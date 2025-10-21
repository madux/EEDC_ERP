odoo.define('sales_rep_dashboard.dashboard', function (require) {
    "use strict";

    const ajax = require('web.ajax');

    // ============================================================
    // STATE MANAGEMENT
    // ============================================================
    let state = {
        date_from: null,
        date_to: null,
        page: 1,
        page_size: 20,
        charts: { pipeline: null, topCustomers: null, forecast: null },
        currency_symbol: "₦",
    };

    // ============================================================
    // UTILITY HELPERS
    // ============================================================
    function fmtMoney(v, cur) {
        if (v == null) return "-";
        try {
            return new Intl.NumberFormat(undefined, { 
                style: "currency", 
                currency: cur || "USD" 
            }).format(v);
        } catch (e) {
            return (cur || "") + " " + v.toFixed(2);
        }
    }

    function pill(state) {
        const map = {
            draft: "Quotation", 
            sent: "Quotation Sent", 
            sale: "Sales Order",
            done: "Done", 
            cancel: "Cancelled"
        };
        const label = map[state] || state;
        const classes = {
            draft: "bg-secondary", 
            sent: "bg-info", 
            sale: "bg-success",
            done: "bg-success", 
            cancel: "bg-danger"
        }[state] || "bg-light text-dark";
        
        return `<span class="badge ${classes} rounded-pill">${_.escape(label)}</span>`;
    }

    // ============================================================
    // DATA FETCHING
    // ============================================================
    
    async function fetchData() {
        const payload = {
            date_from: state.date_from,
            date_to: state.date_to,
            page: state.page,
            page_size: state.page_size,
        };
        const res = await ajax.jsonRpc("/sales_rep_dashboard/data", "call", payload);
        if (res.currency_symbol) {
            state.currency_symbol = res.currency_symbol;
        }
        return res;
    }

    // ============================================================
    // KPI DISPLAY & ANIMATION
    // ============================================================
    
    function setKPIs(kpis) {
        animateKPI("kpi-quotations", kpis.quotations);
        animateKPI("kpi-won", kpis.sales_won);
        animateKPI("kpi-customers", kpis.customers);
        animateKPI("kpi-total-won", kpis.total_won);
        animateKPI("kpi-forecast", kpis.forecast);

        // Update change indicators (you can calculate real percentages from backend)
        $("#kpi-quotations-change").text("+8% from yesterday").addClass("text-success");
        $("#kpi-won-change").text("+5% from yesterday").addClass("text-success");
        $("#kpi-customers-change").text("+1.2% from yesterday").addClass("text-success");
        $("#kpi-total-won-change").text("-0.8% from yesterday").addClass("text-danger");
        $("#kpi-forecast-change").text("+0.5% from yesterday").addClass("text-success");
    }

    function animateKPI(id, newValue, duration = 1000) {
        const el = document.getElementById(id);
        if (!el) return;

        const text = el.innerText.trim();
        const currencySymbol = state.currency_symbol || "";
        const current = parseFloat(text.replace(/[^0-9.-]+/g, "")) || 0;
        const target = parseFloat(newValue) || 0;

        if (current === target) {
            el.innerText = currencySymbol
                ? `${currencySymbol}${target.toLocaleString(undefined, { 
                    minimumFractionDigits: 0, 
                    maximumFractionDigits: 2 
                })}`
                : target.toLocaleString(undefined, { 
                    minimumFractionDigits: 0, 
                    maximumFractionDigits: 2 
                });
            return;
        }

        const diff = target - current;
        const steps = 30;
        const stepTime = duration / steps;
        let count = 0;

        const timer = setInterval(() => {
            count++;
            const value = current + (diff * count) / steps;
            const formatted = currencySymbol
                ? `${currencySymbol}${value.toLocaleString(undefined, { 
                    minimumFractionDigits: 0, 
                    maximumFractionDigits: 2 
                })}`
                : value.toLocaleString(undefined, { 
                    minimumFractionDigits: 0, 
                    maximumFractionDigits: 2 
                });
            el.innerText = formatted;
            
            if (count >= steps) {
                clearInterval(timer);
            }
        }, stepTime);
    }

    // ============================================================
    // CHART RENDERING
    // ============================================================
    
    function getGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    }

    function recreateChart(key, id, type, data, options) {
        // Destroy existing chart if present
        if (state.charts[key]) {
            state.charts[key].destroy();
            state.charts[key] = null;
        }

        const canvas = document.getElementById(id);
        if (!canvas) {
            console.error("Canvas not found:", id);
            return;
        }

        // Set explicit dimensions to prevent resize issues
        const parent = canvas.parentElement;
        if (parent) {
            canvas.width = parent.clientWidth;
            canvas.height = 220;
        }

        const ctx = canvas.getContext("2d");
        state.charts[key] = new Chart(ctx, { type, data, options });
    }

    const COMMON_CHART_OPTIONS = {
        responsive: false,  // Disable responsive to stop resize observer
        maintainAspectRatio: false,
        animation: false,
        events: []  // Disable all events to prevent interactions that trigger redraws
    };

    function drawCharts(payload) {
        // Pipeline Chart (Bar Chart: Quotations vs Won)
        recreateChart("pipeline", "chart-pipeline", "bar", {
            labels: payload.pipeline.labels,
            datasets: [
                {
                    label: "Quotations",
                    data: payload.pipeline.quotations,
                    backgroundColor: "#3b82f6",
                },
                {
                    label: "Won",
                    data: payload.pipeline.won,
                    backgroundColor: "#22c55e",
                },
            ],
        }, {
            ...COMMON_CHART_OPTIONS,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        generateLabels: function(chart) {
                            return Chart.defaults.plugins.legend.labels.generateLabels(chart);
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'category',
                    grid: { display: true }
                },
                y: {
                    type: 'linear',
                    min: 0,
                    max: 1000,
                    ticks: {
                        stepSize: 200,
                        callback: function(value) {
                            return value;
                        }
                    },
                    grid: { display: true }
                }
            }
        });

        // Top Customers Chart (Bar Chart)
        recreateChart("topCustomers", "chart-top-customers", "bar", {
            labels: payload.top_customers.labels.length > 0
                ? payload.top_customers.labels
                : ["No Data"],
            datasets: [{
                label: "Total",
                data: payload.top_customers.values.length > 0
                    ? payload.top_customers.values
                    : [0],
                backgroundColor: "#f59e0b",
            }],
        }, {
            ...COMMON_CHART_OPTIONS,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    type: 'category',
                    grid: { display: true }
                },
                y: {
                    type: 'linear',
                    min: 0,
                    max: 1000,
                    ticks: {
                        stepSize: 200,
                        callback: function(value) {
                            return value;
                        }
                    },
                    grid: { display: true }
                }
            }
        });

        // Forecast Chart (Line Chart)
        const ctxF = document.getElementById("chart-forecast");
        if (!ctxF) {
            console.error("Forecast canvas not found!");
            return;
        }

        // Set explicit dimensions
        const parentF = ctxF.parentElement;
        if (parentF) {
            ctxF.width = parentF.clientWidth;
            ctxF.height = 220;
        }

        const gradientF = getGradient(
            ctxF.getContext("2d"),
            "rgba(168,85,247,0.4)",
            "rgba(236,72,153,0.1)"
        );

        recreateChart("forecast", "chart-forecast", "line", {
            labels: payload.forecast_curve.labels,
            datasets: [{
                label: "Forecast",
                data: payload.forecast_curve.values,
                borderColor: "#a855f7",
                backgroundColor: gradientF,
                fill: true,
                tension: 0.4,
                borderWidth: 2,
            }],
        }, {
            ...COMMON_CHART_OPTIONS,
            scales: {
                x: {
                    type: 'category',
                    title: { display: true, text: "Month" },
                    grid: { display: true }
                },
                y: {
                    type: 'linear',
                    min: 0,
                    max: 1000,
                    title: { display: true, text: "Amount" },
                    ticks: {
                        stepSize: 200,
                        callback: function(value) {
                            return value;
                        }
                    },
                    grid: { display: true }
                }
            },
            plugins: {
                legend: { display: false }
            }
        });
    }

    // ============================================================
    // TABLE & PAGINATION
    // ============================================================
    
    function fillTable(tbl) {
        const $tb = $("#srd-tbody").empty();
        
        if (tbl.rows.length === 0) {
            // Show empty state
            $tb.append(`
                <tr>
                    <td colspan="7" class="p-0">
                        <div class="table-empty-state">
                            <i class="fa fa-inbox"></i>
                            <h5>No orders found</h5>
                            <p>There are no orders matching your criteria. Try adjusting your filters.</p>
                        </div>
                    </td>
                </tr>
            `);
        } else {
            tbl.rows.forEach(r => {
                $tb.append(`
                    <tr>
                        <td><a href="#action=281&model=sale.order&id=${r.id}" class="order-link">${_.escape(r.name)}</a></td>
                        <td>${_.escape(r.partner || "")}</td>
                        <td>${pill(r.state)}</td>
                        <td>${_.escape(r.date_order || "")}</td>
                        <td class="text-end">${r.amount_untaxed?.toLocaleString()}</td>
                        <td class="text-end fw-semibold">${r.amount_total?.toLocaleString()}</td>
                        <td>${_.escape(r.validity_date || "—")}</td>
                    </tr>
                `);
            });
        }

        // Update pagination info
        const start = (tbl.page - 1) * tbl.page_size + 1;
        const end = Math.min(tbl.page * tbl.page_size, tbl.total);
        $("#srd-pager-info").text(`Showing ${start}-${end} of ${tbl.total}`);
        
        // Update pagination button states
        $("#srd-prev").prop("disabled", tbl.page <= 1);
        $("#srd-next").prop("disabled", end >= tbl.total);
    }

    // ============================================================
    // CORE REFRESH LOGIC
    // ============================================================
    
    async function refresh() {
        const data = await fetchData();
        setKPIs(data.kpis);
        drawCharts(data);
        fillTable(data.table);
        $(".sales-rep-dashboard canvas").css("opacity", 1);
    }

    // ============================================================
    // EVENT BINDINGS
    // ============================================================
    
    function bindEvents() {
        // Apply date filter
        $("#srd-apply").on("click", function () {
            state.date_from = $("#srd-date-from").val() || null;
            state.date_to = $("#srd-date-to").val() || null;
            state.page = 1;
            refresh();
        });

        // Reset filters
        $("#srd-reset").on("click", function () {
            $("#srd-date-from, #srd-date-to, #srd-search").val("");
            state = Object.assign(state, { 
                date_from: null, 
                date_to: null, 
                page: 1 
            });
            refresh();
        });

        // Previous page
        $("#srd-prev").on("click", function () {
            if (state.page > 1) {
                state.page--;
                refresh();
            }
        });

        // Next page
        $("#srd-next").on("click", function () {
            state.page++;
            refresh();
        });

        // Export to CSV
        $("#srd-export").on("click", function () {
            const data = $("#srd-tbody tr").map(function () {
                const cells = $(this).find("td").map((_, td) => $(td).text().trim()).get();
                return [cells];
            }).get();

            const csv = ["Order,Customer,Status,Date,Untaxed,Total,Forecast"]
                .concat(data.map(row => row.join(","))).join("\n");

            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = "sales_report.csv";
            link.click();
        });
    }

    // ============================================================
    // INITIALIZATION
    // ============================================================
    
    $(document).ready(function () {
        if (!$(".sales-rep-dashboard").length) return;
        bindEvents();
        refresh();
    });
});