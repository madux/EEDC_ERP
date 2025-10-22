odoo.define('sales_rep_dashboard.dashboard', function (require) {
    "use strict";

    const ajax = require('web.ajax');

    // ============================================================
    // STATE MANAGEMENT
    // ============================================================
    let state = {
        date_from: null,
        date_to: null,
        search: "",
        page: 1,
        page_size: 20,
        charts: { pipeline: null, topCustomers: null, forecast: null },
        currency_symbol: "₦",
    };

    // ============================================================
    // UTILITY HELPERS
    // ============================================================

    // Escape RegExp for highlight safety
    _.escapeRegExp = function (string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    };

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
            search: state.search || "",
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
        responsive: false,  
        maintainAspectRatio: false,
        animation: false,
        events: []  
    };

    function showChartEmptyState(id, message = "No data available") {
        const wrapper = document.querySelector(`#${id}`)?.parentElement;
        // only insert if the wrapper exists and we haven’t already inserted an empty state
        if (!wrapper || wrapper.querySelector(".chart-empty-state")) return;

        wrapper.innerHTML = `
            <div class="chart-empty-state">
                <i class="fa fa-chart-bar"></i>
                <p>${message}</p>
            </div>
        `;
    }

    function drawCharts(payload) {
        // Common options shared across charts
        const COMMON_CHART_OPTIONS = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 800,
                easing: "easeOutQuart",
            },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { family: "Inter, sans-serif", size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: "rgba(17, 24, 39, 0.9)",
                    titleFont: { size: 13, weight: "600" },
                    bodyFont: { size: 12 },
                    padding: 10,
                    displayColors: false,
                    cornerRadius: 8,
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: "#6b7280", font: { size: 11 } },
                },
                y: {
                    grid: { color: "rgba(0,0,0,0.05)", drawBorder: false },
                    ticks: {
                        color: "#9ca3af",
                        font: { size: 11 },
                        callback: (value) => value.toLocaleString(),
                    },
                },
            },
        };

        // ===== PIPELINE BY MONTH =====
        const pipeCanvas = document.getElementById("chart-pipeline");
        if (pipeCanvas) {
            const ctx = pipeCanvas.getContext("2d");
            const gradientBlue = ctx.createLinearGradient(0, 0, 0, 220);
            gradientBlue.addColorStop(0, "rgba(59,130,246,0.9)");
            gradientBlue.addColorStop(1, "rgba(59,130,246,0.2)");
            const gradientGreen = ctx.createLinearGradient(0, 0, 0, 220);
            gradientGreen.addColorStop(0, "rgba(16,185,129,0.9)");
            gradientGreen.addColorStop(1, "rgba(16,185,129,0.2)");

            // ✅ fixed logic
            const hasPipelineData =
                payload.pipeline.labels.length > 0 &&
                (payload.pipeline.quotations.some(v => v > 0) ||
                payload.pipeline.won.some(v => v > 0));

            if (!hasPipelineData) {
                showChartEmptyState("chart-pipeline", "No pipeline data found");
            } else {
                recreateChart("pipeline", "chart-pipeline", "bar", {
                    labels: payload.pipeline.labels,
                    datasets: [
                        {
                            label: "Quotations",
                            data: payload.pipeline.quotations,
                            backgroundColor: gradientBlue,
                            borderRadius: 6,
                            barPercentage: 0.45,
                        },
                        {
                            label: "Won",
                            data: payload.pipeline.won,
                            backgroundColor: gradientGreen,
                            borderRadius: 6,
                            barPercentage: 0.45,
                        },
                    ],
                }, COMMON_CHART_OPTIONS);
            }
        }

        // ===== TOP CUSTOMERS =====
        const topCanvas = document.getElementById("chart-top-customers");
        if (topCanvas) {
            const ctx = topCanvas.getContext("2d");
            const gradientOrange = ctx.createLinearGradient(0, 0, 0, 220);
            gradientOrange.addColorStop(0, "rgba(245,158,11,0.9)");
            gradientOrange.addColorStop(1, "rgba(245,158,11,0.2)");

            const hasTopCustomers =
                payload.top_customers.values.length > 0 &&
                payload.top_customers.values.some(v => v > 0);

            if (!hasTopCustomers) {
                showChartEmptyState("chart-top-customers", "No customer data available");
            } else {
                recreateChart("topCustomers", "chart-top-customers", "bar", {
                    labels: payload.top_customers.labels,
                    datasets: [
                        {
                            label: "Total Amount",
                            data: payload.top_customers.values,
                            backgroundColor: gradientOrange,
                            borderRadius: 6,
                            barPercentage: 0.55,
                        },
                    ],
                }, COMMON_CHART_OPTIONS);
            }
        }

        // ===== FORECAST (Smooth Line Chart) =====
        const forecastCanvas = document.getElementById("chart-forecast");
        if (forecastCanvas) {
            const ctx = forecastCanvas.getContext("2d");
            const gradientPurple = ctx.createLinearGradient(0, 0, 0, 220);
            gradientPurple.addColorStop(0, "rgba(168,85,247,0.5)");
            gradientPurple.addColorStop(1, "rgba(168,85,247,0.05)");

            const hasForecastData =
                payload.forecast_curve.values.length > 0 &&
                payload.forecast_curve.values.some(v => v > 0);

            if (!hasForecastData) {
                showChartEmptyState("chart-forecast", "No forecast data available");
            } else {
                recreateChart("forecast", "chart-forecast", "line", {
                    labels: payload.forecast_curve.labels,
                    datasets: [
                        {
                            label: "Forecast (Next 3 Months)",
                            data: payload.forecast_curve.values,
                            fill: true,
                            backgroundColor: gradientPurple,
                            borderColor: "#8b5cf6",
                            pointBackgroundColor: "#a855f7",
                            pointRadius: 4,
                            tension: 0.4,
                            borderWidth: 2.2,
                        },
                    ],
                }, COMMON_CHART_OPTIONS);
            }
        }
    }

    // ============================================================
    // TABLE & PAGINATION
    // ============================================================
    
    function fillTable(tbl) {
        const $tb = $("#srd-tbody").empty();
        
        if (tbl.rows.length === 0) {
            const searchText = state.search ? _.escape(state.search) : "";
            const customMessage = state.search
                ? `<p class="no-result-msg">No results found for "<strong>${searchText}</strong>".</p>`
                : `<p class="no-result-msg">There are no orders matching your criteria. Try adjusting your filters.</p>`;

            $tb.append(`
                <tr>
                    <td colspan="7" class="p-0">
                        <div class="table-empty-state">
                            <i class="fa fa-inbox"></i>
                            <h5>No orders found</h5>
                            ${customMessage}
                        </div>
                    </td>
                </tr>
            `);
        } else {
            tbl.rows.forEach(r => {
                function highlightMatch(text, query) {
                    if (!query) return _.escape(text || "");
                    const regex = new RegExp(`(${_.escapeRegExp(query)})`, "ig");
                    return _.escape(text || "").replace(regex, "<mark class='highlight'>$1</mark>");
                }

                tbl.rows.forEach(r => {
                    const orderName = highlightMatch(r.name, state.search);
                    const partnerName = highlightMatch(r.partner, state.search);
                    $tb.append(`
                        <tr>
                            <td><a href="#action=281&model=sale.order&id=${r.id}" class="order-link">${orderName}</a></td>
                            <td>${partnerName}</td>
                            <td>${pill(r.state)}</td>
                            <td>${_.escape(r.date_order || "")}</td>
                            <td class="text-end">${r.amount_untaxed?.toLocaleString()}</td>
                            <td class="text-end fw-semibold">${r.amount_total?.toLocaleString()}</td>
                            <td>${_.escape(r.validity_date || "—")}</td>
                        </tr>
                    `);
                });

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
                search: "",
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

        // Live search (debounced)
        let searchTimer;
        $("#srd-search").on("input", function () {
            clearTimeout(searchTimer);
            const value = $(this).val().trim();
            searchTimer = setTimeout(() => {
                state.search = value;
                state.page = 1;
                refresh();
            }, 400); 
        });

        // Toggle clear icon visibility
        $("#srd-search").on("input", function () {
            clearTimeout(searchTimer);
            const value = $(this).val().trim();
            $("#srd-clear-search").toggleClass("visible", !!value);
            searchTimer = setTimeout(() => {
                state.search = value;
                state.page = 1;
                refresh();
            }, 400);
        });
    
        // Clear search when clicking "×"
        $("#srd-clear-search").on("click", function () {
            $("#srd-search").val("");
            $(this).removeClass("visible");
            state.search = "";
            state.page = 1;
            refresh();
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