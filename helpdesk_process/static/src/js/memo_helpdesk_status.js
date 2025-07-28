odoo.define('helpdesk_process', function (require) {
    "use strict";

    require('web.dom_ready');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    let localStorage = window.localStorage;

    let renderCustomerTicketStatus = function (data, current_stage_id, close_stage_id) {
        $('#status_display').empty();
        $('#status_display_div').removeClass('d-none');

        let circle_count = 1;
        let current_stage_reached = false;

        $.each(data, function (key, val) {
            let circle_class = 'step';
            let icon = circle_count;

            if (val.id === current_stage_id) {
                circle_class += ' current';
                icon = `<span class="icon">⏳</span>`;
                current_stage_reached = true;
            } else if (!current_stage_reached) {
                circle_class += ' completed';
                icon = `<span class="icon">✓</span>`;
            } else {
                circle_class += ' upcoming';
                icon = `<span class="icon">○</span>`;
            }

            const stageLabel = `<span class="stage-badge">${val.name.toUpperCase()}</span>`;
            const date = `<div class="stage-date">Thursday, 07-01</div>`;
            const description = val.description ? `<div class="description">${val.description}</div>` : '';

            $('#status_display').append(`
                <div class="${circle_class}">
                    <div class="circle">${icon}</div>
                    <div class="label">
                        ${stageLabel}
                        ${date}
                        ${description}
                    </div>
                </div>
            `);

            circle_count += 1;
        });
    }

    
    publicWidget.registry.MemoHelpdeskCustomerTicketsFormWidgets = publicWidget.Widget.extend({
        selector: '.CustomerStatusDashboard',
        start: function () {
            return this._super.apply(this, arguments).then(function () {
                console.log("started Customer status");
            });
        },
        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                console.log("...started Customer status 2")
            })
        },
        events: {
            'blur input, select, textarea': function (ev) {
                let input = $(ev.target)
                if (input.is(":required") && input.val() !== '') {
                    input.removeClass('is-invalid').addClass('is-valid')
                } else if (input.is(":required") && input.val() == '') {
                    input.addClass('is-invalid')
                }
            },

            'click .submit_btn': function (ev) {
                let target = $('#customer_info');
                console.log(`The value of customer info is ${target.val()}`)
                // Make an api call
                this._rpc({
                    route: `/get-customer-ticket`,
                    params: {
                        'ticket_no': target.val() // e.g REF00921, 
                    },
                }).then(function (data) {
                    if (data.status) {
                        console.log('Customer tickets providing => ' + JSON.stringify(data));
                        target.val('');
                        renderCustomerTicketStatus(data.data, data.current_stage_id, data.close_stage_id)
                    } else {
                        target.val('');
                        alert(data.message);
                    }

                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

        },
    });
});