/** Sales Rep Dashboard frontend logic (Odoo 16 backend). */
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
        $("#kpi-quotations").text(kpis.quotations);
        $("#kpi-won").text(kpis.sales_won);
        $("#kpi-customers").text(kpis.customers);
        $("#kpi-total-won").text(kpis.total_won.toLocaleString());
        $("#kpi-forecast").text(kpis.forecast.toLocaleString());
    }

    function ensureChart(canvasId, type, data, options) {
        const ctx = document.getElementById(canvasId).getContext("2d");
        const c = new Chart(ctx, { type, data, options });
        return c;
    }

    function drawCharts(payload) {
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

        // Forecast curve
        if (state.charts.forecast) state.charts.forecast.destroy();
        state.charts.forecast = ensureChart("chart-forecast", "line", {
            labels: payload.forecast_curve.labels,
            datasets: [{ label: "Forecast", data: payload.forecast_curve.values, fill: false }],
        }, { responsive: true, maintainAspectRatio: false });
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
});
