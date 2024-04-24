odoo.define('maach_dashboard.dashboard_content', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  
    publicWidget.registry.MaachDashboard = publicWidget.Widget.extend({
        selector: '#dashboard-content',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("started form request")
                // var y_data_chart = JSON.parse($('#y_data_for_chart').text())
                // var x_data_chart = JSON.parse($('#x_data_for_chart').text())
                var y_data_chart = $('#y_data_for_chart').text()
                var x_data_chart = $('#x_data_for_chart').text()
                console.log('Y====> ', JSON.parse(y_data_chart).data)
                console.log('X====> ', JSON.parse(x_data_chart).data)

                var y_data_chart_array = JSON.parse(y_data_chart).data 
                var x_data_chart_array = JSON.parse(x_data_chart).data
                if (y_data_chart_array && x_data_chart_array){
                    var ctx = document.getElementById("chart-bars").getContext("2d");
                    new Chart(ctx, {
                        type: 'bar',
                        data: {
                        labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
                        //   labels: x_data_chart,
                        datasets: [{
                            label: "Sales",
                            tension: 0.4,
                            borderWidth: 0,
                            borderRadius: 4,
                            borderSkipped: false,
                            backgroundColor: "#fff",
                            data: [450, 200, 100, 220, 500, 800],
                            maxBarThickness: 10,
                            hoverBorderColor: "orange",
                            }, ],
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                            legend: {
                                display: false,
                            }
                            },
                            interaction: {
                            intersect: false,
                            mode: 'index',
                            },
                            scales: {
                                y: {
                                    grid: {
                                    drawBorder: false,
                                    display: false,
                                    drawOnChartArea: false,
                                    drawTicks: false,
                                    },
                                    ticks: {
                                    suggestedMin: 0,
                                    suggestedMax: 500,
                                    beginAtZero: true,
                                    padding: 15,
                                    font: {
                                        size: 14,
                                        family: "Open Sans",
                                        style: 'normal',
                                        lineHeight: 2
                                    },
                                    color: "#fff"
                                    },
                                },
                                x: {
                                    grid: {
                                    drawBorder: false,
                                    display: false,
                                    drawOnChartArea: false,
                                    drawTicks: false
                                    },
                                    ticks: {
                                    display: false
                                    },
                                },
                            },
                        },
                    });
                    var ctx2 = document.getElementById("chart-line").getContext("2d");
                    var gradientStroke1 = ctx2.createLinearGradient(0, 230, 0, 50);
                    gradientStroke1.addColorStop(1, 'rgba(203,12,159,0.2)');
                    gradientStroke1.addColorStop(0.2, 'rgba(72,72,176,0.0)');
                    gradientStroke1.addColorStop(0, 'rgba(203,12,159,0)'); //purple colors

                    var gradientStroke2 = ctx2.createLinearGradient(0, 230, 0, 50);

                    gradientStroke2.addColorStop(1, 'rgba(20,23,39,0.2)');
                    gradientStroke2.addColorStop(0.2, 'rgba(72,72,176,0.0)');
                    gradientStroke2.addColorStop(0, 'rgba(20,23,39,0)'); //purple colors

                    new Chart(ctx2, {
                    type: "line",
                    data: {
                        //   labels: ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        labels: x_data_chart_array,
                        datasets: [{
                            label: "Success Rate",
                            tension: 0.4,
                            borderWidth: 0,
                            pointRadius: 0,
                            borderColor: "#cb0c9f",
                            borderWidth: 3,
                            backgroundColor: gradientStroke1,
                            fill: true,
                            data: [50, 40, 300, 220, 500, 250, 400, 230, 500],
                            maxBarThickness: 6

                        },
                        // {
                        //     label: "Success Rate",
                        //     tension: 0.4,
                        //     borderWidth: 0,
                        //     pointRadius: 0,
                        //     borderColor: "#3A416F",
                        //     borderWidth: 3,
                        //     backgroundColor: gradientStroke2,
                        //     fill: true,
                        //     data: y_data_chart_array,
                        //     maxBarThickness: 6
                        // },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                        legend: {
                            display: false,
                        }
                        },
                        interaction: {
                        intersect: false,
                        mode: 'index',
                        },
                        scales: {
                        y: {
                            grid: {
                            drawBorder: false,
                            display: true,
                            drawOnChartArea: true,
                            drawTicks: false,
                            borderDash: [5, 5]
                            },
                            ticks: {
                            display: true,
                            padding: 10,
                            color: '#b2b9bf',
                            font: {
                                size: 11,
                                family: "Open Sans",
                                style: 'normal',
                                lineHeight: 2
                            },
                            }
                        },
                        x: {
                            grid: {
                            drawBorder: false,
                            display: false,
                            drawOnChartArea: false,
                            drawTicks: false,
                            borderDash: [5, 5]
                            },
                            ticks: {
                            display: true,
                            color: '#b2b9bf',
                            padding: 20,
                            font: {
                                size: 11,
                                family: "Open Sans",
                                style: 'normal',
                                lineHeight: 2
                            },
                            }
                        },
                        },
                    },
                    });
                }
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("united bosses.....")
            })
        },
        events: {
            'click .btn-close-success': function(ev){
                $('#successful_alert').hide()

            },
         },
    });

// return PortalRequestWidget;
});