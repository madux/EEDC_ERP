odoo.define('sales_rep_dashboard.dashboard', function (require) {
    "use strict";

    const ajax = require('web.ajax');
    let state = {
        date_from: null,
        date_to: null,
        page: 1,
        page_size: 20,
        charts: { pipeline: null, topCustomers: null, forecast: null },
        currency_symbol: "₦", // default fallback
    };

    // ------------------------------------------------------------
    // UTILITY HELPERS
    // ------------------------------------------------------------

    function fmtMoney(v, cur) {
        if (v == null) return "-";
        try {
            return new Intl.NumberFormat(undefined, { style: "currency", currency: cur || "USD" }).format(v);
        } catch (e) {
            return (cur || "") + " " + v.toFixed(2);
        }
    }

    function pill(state) {
        const map = {
            draft: "Quotation", sent: "Quotation Sent", sale: "Sales Order",
            done: "Done", cancel: "Cancelled"
        };
        const label = map[state] || state;
        const classes = {
            draft: "bg-secondary", sent: "bg-info", sale: "bg-success",
            done: "bg-success", cancel: "bg-danger"
        }[state] || "bg-light text-dark";
        return `<span class="badge ${classes} rounded-pill">${_.escape(label)}</span>`;
    }

    // ------------------------------------------------------------
    // DATA FETCHING
    // ------------------------------------------------------------

    async function fetchData() {
        const payload = {
            date_from: state.date_from,
            date_to: state.date_to,
            page: state.page,
            page_size: state.page_size,
        };
        const res = await ajax.jsonRpc("/sales_rep_dashboard/data", "call", payload);
        if (res.currency_symbol) state.currency_symbol = res.currency_symbol;
        return res;
    }

    // ------------------------------------------------------------
    // KPI DISPLAY + ANIMATION
    // ------------------------------------------------------------

    function setKPIs(kpis) {
        animateKPI("kpi-quotations", kpis.quotations);
        animateKPI("kpi-won", kpis.sales_won);
        animateKPI("kpi-customers", kpis.customers);
        animateKPI("kpi-total-won", kpis.total_won);
        animateKPI("kpi-forecast", kpis.forecast);

        $("#kpi-quotations-change").text("+8% from yesterday").addClass("text-success");
        $("#kpi-won-change").text("+5% from yesterday").addClass("text-success");
        $("#kpi-customers-change").text("+1.2% from yesterday").addClass("text-success");
        $("#kpi-total-won-change").text("-0.8% from yesterday").addClass("text-danger");
        $("#kpi-forecast-change").text("+0.5% from yesterday").addClass("text-success");
    }

    // --- Enhanced KPI animation (handles ₦, $, €, decimals, etc.)
    function animateKPI(id, newValue, duration = 1000) {
        const el = document.getElementById(id);
        if (!el) return;

        const text = el.innerText.trim();
        const currencySymbol = state.currency_symbol || "";
        const current = parseFloat(text.replace(/[^0-9.-]+/g, "")) || 0;
        const target = parseFloat(newValue) || 0;

        if (current === target) {
            el.innerText = currencySymbol
                ? `${currencySymbol}${target.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
                : target.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
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
                ? `${currencySymbol}${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
                : value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
            el.innerText = formatted;
            if (count >= steps) clearInterval(timer);
        }, stepTime);
    }

    // ------------------------------------------------------------
    // CHARTS
    // ------------------------------------------------------------

    function ensureChart(canvasId, type, data, options) {
        const ctx = document.getElementById(canvasId).getContext("2d");
        return new Chart(ctx, { type, data, options });
    }

    // function drawCharts(payload) {
    //     function getGradient(ctx, color1, color2) {
    //         const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    //         gradient.addColorStop(0, color1);
    //         gradient.addColorStop(1, color2);
    //         return gradient;
    //     }

    //     // Pipeline
    //     if (state.charts.pipeline) state.charts.pipeline.destroy();
    //     state.charts.pipeline = ensureChart("chart-pipeline", "bar", {
    //         labels: payload.pipeline.labels,
    //         datasets: [
    //             { label: "Quotations", data: payload.pipeline.quotations },
    //             { label: "Won", data: payload.pipeline.won },
    //         ],
    //     }, { responsive: true, maintainAspectRatio: false });

    //     // Top customers
    //     if (state.charts.topCustomers) state.charts.topCustomers.destroy();
    //     state.charts.topCustomers = ensureChart("chart-top-customers", "bar", {
    //         labels: payload.top_customers.labels,
    //         datasets: [{ label: "Total", data: payload.top_customers.values }],
    //     }, { responsive: true, maintainAspectRatio: false });

    //     // Forecast chart
    //     const ctxF = document.getElementById("chart-forecast").getContext("2d");
    //     const gradientF = getGradient(ctxF, "rgba(168,85,247,0.4)", "rgba(236,72,153,0.1)");
    //     if (state.charts.forecast) state.charts.forecast.destroy();

    //     state.charts.forecast = new Chart(ctxF, {
    //         type: "line",
    //         data: {
    //             labels: payload.forecast_curve.labels,
    //             datasets: [{
    //                 label: "Forecast",
    //                 data: payload.forecast_curve.values,
    //                 borderColor: "#a855f7",
    //                 backgroundColor: gradientF,
    //                 fill: true,
    //                 tension: 0.4,
    //                 borderWidth: 2,
    //             }],
    //         },
    //         options: {
    //             responsive: true,
    //             maintainAspectRatio: false,
    //             scales: { x: { type: "time", time: { unit: "month" } }, y: { beginAtZero: true } },
    //         },
    //     });
    // }

    function drawCharts(payload) {
        // Reusable helper for safe chart re-creation
        console.log("Redrawing charts once...");

        function recreateChart(key, id, type, data, options) {
            if (state.charts[key]) {
                state.charts[key].destroy();
                state.charts[key] = null;
            }
            const canvas = document.getElementById(id);
            if (!canvas) return;
            const ctx = canvas.getContext("2d");
            state.charts[key] = new Chart(ctx, { type, data, options });
        }

        // Gradient helper
        function getGradient(ctx, color1, color2) {
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, color1);
            gradient.addColorStop(1, color2);
            return gradient;
        }

        // --- Pipeline (Quotations vs Won)
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
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // prevents continuous redraw
            plugins: { legend: { position: "bottom" } },
        });

        // --- Top Customers
        recreateChart("topCustomers", "chart-top-customers", "bar", {
            labels: payload.top_customers.labels,
            datasets: [{
                label: "Total",
                data: payload.top_customers.values,
                backgroundColor: "#f59e0b",
            }],
        }, {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
        });

        // --- Forecast Chart
        const ctxF = document.getElementById("chart-forecast").getContext("2d");
        const gradientF = getGradient(ctxF, "rgba(168,85,247,0.4)", "rgba(236,72,153,0.1)");
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
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { title: { display: true, text: "Month" } },
                y: { beginAtZero: true, title: { display: true, text: "Amount" } },
            },
            plugins: { legend: { display: false } },
        });
    }


    // ------------------------------------------------------------
    // TABLE + PAGINATION
    // ------------------------------------------------------------

    function fillTable(tbl) {
        const $tb = $("#srd-tbody").empty();
        tbl.rows.forEach(r => {
            $tb.append(`
                <tr>
                    <td><a href="#action=281&model=sale.order&id=${r.id}" class="text-decoration-none">${_.escape(r.name)}</a></td>
                    <td>${_.escape(r.partner || "")}</td>
                    <td>${pill(r.state)}</td>
                    <td>${_.escape(r.date_order || "")}</td>
                    <td class="text-end">${r.amount_untaxed?.toLocaleString()}</td>
                    <td class="text-end">${r.amount_total?.toLocaleString()}</td>
                    <td>${_.escape(r.validity_date || "")}</td>
                </tr>
            `);
        });
        const start = (tbl.page - 1) * tbl.page_size + 1;
        const end = Math.min(tbl.page * tbl.page_size, tbl.total);
        $("#srd-pager-info").text(`${start}-${end} of ${tbl.total}`);
        $("#srd-prev").prop("disabled", tbl.page <= 1);
        $("#srd-next").prop("disabled", end >= tbl.total);
    }

    // ------------------------------------------------------------
    // CORE REFRESH LOGIC
    // ------------------------------------------------------------

    async function refresh() {
        const data = await fetchData();
        setKPIs(data.kpis);
        drawCharts(data);
        fillTable(data.table);
        // $(".sales-rep-dashboard canvas").hide().fadeIn(800);
        $(".sales-rep-dashboard canvas").css("opacity", 1);

    }

    // ------------------------------------------------------------
    // EVENT BINDINGS
    // ------------------------------------------------------------

    function bindEvents() {
        $("#srd-apply").on("click", function () {
            state.date_from = $("#srd-date-from").val() || null;
            state.date_to = $("#srd-date-to").val() || null;
            state.page = 1;
            refresh();
        });

        $("#srd-reset").on("click", function () {
            $("#srd-date-from, #srd-date-to, #srd-search").val("");
            state = Object.assign(state, { date_from: null, date_to: null, page: 1 });
            refresh();
        });

        $("#srd-prev").on("click", function () {
            if (state.page > 1) { state.page--; refresh(); }
        });

        $("#srd-next").on("click", function () {
            state.page++; refresh();
        });

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

    // ------------------------------------------------------------
    // INITIALIZATION
    // ------------------------------------------------------------

    $(document).ready(function () {
        if (!$(".sales-rep-dashboard").length) return;
        bindEvents();
        refresh();
    });
});
