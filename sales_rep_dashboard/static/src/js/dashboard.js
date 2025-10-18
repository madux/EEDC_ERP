odoo.define('sales_rep_dashboard.dashboard', function (require) {
    "use strict";
    const ajax = require('web.ajax');

    let state = {
        date_from: null,
        date_to: null,
        page: 1,
        page_size: 20,
        charts: {
            pipeline: null,
            topCustomers: null,
            forecast: null,
        },
    };

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
            draft: "Quotation",
            sent: "Quotation Sent",
            sale: "Sales Order",
            done: "Done",
            cancel: "Cancelled",
        };
        const label = map[state] || state;
        const classes = {
            draft: "bg-secondary",
            sent: "bg-info",
            sale: "bg-success",
            done: "bg-success",
            cancel: "bg-danger",
        }[state] || "bg-light text-dark";
        return `<span class="badge ${classes} rounded-pill">${_.escape(label)}</span>`;
    }

    async function fetchData() {
        const payload = {
            date_from: state.date_from,
            date_to: state.date_to,
            page: state.page,
            page_size: state.page_size,
        };
        return ajax.jsonRpc("/sales_rep_dashboard/data", "call", payload);
    }

    function setKPIs(kpis) {
        animateCountUp("kpi-quotations", kpis.quotations);
        animateCountUp("kpi-won", kpis.sales_won);
        animateCountUp("kpi-customers", kpis.customers);
        animateCountUp("kpi-total-won", kpis.total_won);
        animateCountUp("kpi-forecast", kpis.forecast);

        // Example dummy change values (you can compute real data later)
        $("#kpi-quotations-change").text("+8% from yesterday").addClass("text-success");
        $("#kpi-won-change").text("+5% from yesterday").addClass("text-success");
        $("#kpi-customers-change").text("+1.2% from yesterday").addClass("text-success");
        $("#kpi-total-won-change").text("-0.8% from yesterday").addClass("text-danger");
        $("#kpi-forecast-change").text("+0.5% from yesterday").addClass("text-success");

    }


    function animateCountUp(element, target, duration = 1000) {
        const el = document.getElementById(element);
        const start = parseFloat(el.textContent.replace(/,/g, "")) || 0;
        const end = target;
        const range = end - start;
        const increment = end > start ? 1 : -1;
        const stepTime = Math.abs(Math.floor(duration / range));
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            el.textContent = current.toLocaleString();
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                el.textContent = end.toLocaleString();
                clearInterval(timer);
            }
        }, Math.max(stepTime, 20));
    }


    function ensureChart(canvasId, type, data, options) {
        const ctx = document.getElementById(canvasId).getContext("2d");
        const c = new Chart(ctx, { type, data, options });
        return c;
    }

    function drawCharts(payload) {

        function getGradient(ctx, color1, color2) {
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, color1);
            gradient.addColorStop(1, color2);
            return gradient;
        }

        // Pipeline
        if (state.charts.pipeline) state.charts.pipeline.destroy();
        state.charts.pipeline = ensureChart("chart-pipeline", "bar", {
            labels: payload.pipeline.labels,
            datasets: [
                { label: "Quotations", data: payload.pipeline.quotations },
                { label: "Won", data: payload.pipeline.won },
            ],
        }, {
            responsive: true,
            maintainAspectRatio: false,
        });

        // Top customers
        if (state.charts.topCustomers) state.charts.topCustomers.destroy();
        state.charts.topCustomers = ensureChart("chart-top-customers", "horizontalBar", {
            labels: payload.top_customers.labels,
            datasets: [{ label: "Total", data: payload.top_customers.values }],
        }, { responsive: true, maintainAspectRatio: false });

        const ctxF = document.getElementById("chart-forecast").getContext("2d");
        const gradientF = getGradient(ctxF, "rgba(168,85,247,0.4)", "rgba(236,72,153,0.1)");

        state.charts.forecast = new Chart(ctxF, {
            type: "line",
            data: {
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
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: "time", time: { unit: "month" } },
                    y: { beginAtZero: true },
                },
            },
        });

    }

    function fillTable(tbl) {
        const $tb = $("#srd-tbody");
        $tb.empty();
        tbl.rows.forEach(r => {
            const row = `
                <tr>
                    <td><a href="#action=281&model=sale.order&id=${r.id}" class="text-decoration-none">${_.escape(r.name)}</a></td>
                    <td>${_.escape(r.partner || "")}</td>
                    <td>${pill(r.state)}</td>
                    <td>${_.escape(r.date_order || "")}</td>
                    <td class="text-end">${r.amount_untaxed?.toLocaleString()}</td>
                    <td class="text-end">${r.amount_total?.toLocaleString()}</td>
                    <td>${_.escape(r.validity_date || "")}</td>
                </tr>
            `;
            $tb.append(row);
        });
        const start = (tbl.page - 1) * tbl.page_size + 1;
        const end = Math.min(tbl.page * tbl.page_size, tbl.total);
        $("#srd-pager-info").text(`${start}-${end} of ${tbl.total}`);
        $("#srd-prev").prop("disabled", tbl.page <= 1);
        $("#srd-next").prop("disabled", end >= tbl.total);
    }

    async function refresh() {
        const data = await fetchData();
        setKPIs(data.kpis);
        drawCharts(data);
        fillTable(data.table);
        $(".sales-rep-dashboard canvas").hide().fadeIn(800);
    }

    function bindEvents() {
        $("#srd-apply").on("click", function () {
            state.date_from = $("#srd-date-from").val() || null;
            state.date_to = $("#srd-date-to").val() || null;
            state.page = 1;
            refresh();
        });
        $("#srd-reset").on("click", function () {
            $("#srd-date-from").val("");
            $("#srd-date-to").val("");
            $("#srd-search").val("");
            state = Object.assign(state, { date_from: null, date_to: null, page: 1 });
            refresh();
        });
        $("#srd-prev").on("click", function () {
            if (state.page > 1) { state.page--; refresh(); }
        });
        $("#srd-next").on("click", function () {
            state.page++; refresh();
        });
    }

    // Boot
    $(document).ready(function () {
        if (!$(".sales-rep-dashboard").length) return;
        bindEvents();
        refresh();
    });

    // Export
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

});
