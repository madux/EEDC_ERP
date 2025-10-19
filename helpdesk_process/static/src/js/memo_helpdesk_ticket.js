odoo.define('helpdesk_process.memo_helpdesk_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    let localStorage = window.localStorage;

    let trigger_date_function = function (dateElement, minDate = new Date(), maxDate = null) {
        dateElement.datepicker('destroy').datepicker({
            onSelect: function (ev) {
                dateElement.trigger('blur')
            },
            dateFormat: 'mm/dd/yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2024:2050',
            maxDate: maxDate,
            minDate: minDate
        });
    }

    function buildMemoConfigOption(data) {
        console.log("Request config build loading")
        let select = $("#helpdesk_memo_config_id").empty();
        select.append($('<option>', { value: '', text: 'Please select' }));
        $.each(data, function (index, item) {
            if (item) {
                console.log(`Building memo table ${index} ${item}`)
                select.append(
                    `
                    <option value="${item.id}">
                        <span>${item.name}</span>
                    </option>
                    `
                )
            } else {
                console.log('No helpdesk config items found')
            }
        });
    }

    function toggleMeterFields() {
        var val = $('#meter_type').val();
        console.log('Meter type selected:', val);
        
        if (val === 'prepaid') {
            $('.meter_no_field').show();
            $('.account_no_field').hide();
            // Make meter_no required, account_no not required
            $('#meter_no').prop('required', true);
            $('#account_no').prop('required', false);
        } else if (val === 'postpaid') {
            $('.meter_no_field').hide();
            $('.account_no_field').show();
            // Make account_no required, meter_no not required
            $('#account_no').prop('required', true);
            $('#meter_no').prop('required', false);
        } else {
            // For direct source or no selection, hide both
            $('.meter_no_field').hide();
            $('.account_no_field').hide();
            $('#meter_no').prop('required', false);
            $('#account_no').prop('required', false);
        }
    }

    trigger_date_function($('#deadline_date'));

    publicWidget.registry.MemoHelpdeskFormWidgets = publicWidget.Widget.extend({
        selector: '#memo-request-form',
        
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // Initialize meter field toggle
                toggleMeterFields();
                
                // Bind the change event
                self.$('#meter_type').on('change', toggleMeterFields);
                
                console.log("Helpdesk form widget started; meter toggle bound");
                console.log("started helpdesk form request");
            });
        },

        willStart: function () {
            return this._super.apply(this, arguments).then(function () {
                console.log("...memo helpdesk willstart...")
            })
        },

        events: {
            'blur input, select, textarea': function (ev) {
                let input = $(ev.target);
                if (input.is('input[type="tel"]')) {
                    let phone = input.val().replace(/\s+/g, '');
                    // Regex for Nigerian mobile numbers
                    let regex = /^(0[789]\d{9}|\+234[789]\d{9})$/;
                    if (!regex.test(phone)) {
                        input.addClass('is-invalid');
                    } else {
                        input.removeClass('is-invalid').addClass('is-valid');
                    }
                } else if (input.attr('name') === 'meter_no') {
                    let meterNo = input.val().replace(/\s+/g, '');
                    // Regex for EEDC meter numbers
                    let regex = /^[0-9]{11}$/;
                    if (!regex.test(meterNo)) {
                        input.addClass('is-invalid');
                    } else {
                        input.removeClass('is-invalid').addClass('is-valid');
                    }
                } else if (input.attr('name') === 'account_no') {
                    let accountNo = input.val().replace(/\s+/g, '');
                    // Add validation for account number if needed
                    // For now, just check if it's not empty when required
                    if (input.prop('required') && accountNo === '') {
                        input.addClass('is-invalid');
                    } else {
                        input.removeClass('is-invalid').addClass('is-valid');
                    }
                }
            },

            'change select[name=helpdesk_category_id]': function (ev) {
                let value = $(ev.target).val();
                if (!value) {
                    alert('You must provide category option!')
                    return false;
                };
                if (value !== '') {
                    var self = this;
                    this._rpc({
                        route: `/get-helpdesk-config`,
                        params: {
                            'category_id': value,
                        },
                    }).then(function (data) {
                        console.log('retrieved helpdesk memo category data => ' + JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#helpdesk_memo_config_id").val('')
                            alert(`Validation Error! ${data.message}`)
                        } else {
                            let memo_config_ids = data.data.memo_config_ids
                            buildMemoConfigOption(memo_config_ids);
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        $("#helpdesk_category_id").val('')
                        alert(`Unknown Error! ${msg}`)
                    });
                } else {
                    alert("Category Must all be provided")
                }
            },

            'click .submit_btn': function (ev) {
                var list_of_fields = [];
                $('input,textarea,select,select2').filter('[required]:visible').each(function (ev) {
                    var field = $(this);
                    if (field.val() == "") {
                        field.addClass('is-invalid');
                        list_of_fields.push(field.attr('labelfor'));
                    }
                });
                if (list_of_fields.length > 0) {
                    alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
                    return false;
                } else {
                    let $btn = $('.submit_btn');
                    let $btnHtml = $btn.html()
                    $btn.attr('disabled', 'disabled');
                    $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                    $.blockUI({
                        'message': '<h2 class="card-name">Please wait ...</h2>'
                    });
                    var form = $('#msform')[0];
                    var formData = new FormData(form);
                    console.log('formData is ==>', formData)
                    $.ajax({
                        type: "POST",
                        enctype: 'multipart/form-data',
                        url: "/customer/ticket/submission",
                        data: formData,
                        processData: false,
                        contentType: false,
                        cache: false,
                        timeout: 800000,
                    }).then(function (data) {
                        if (data.status == false) {
                            alert(data.message)
                            return false;
                        } else {
                            $("#msform")[0].reset();
                            console.log(`Receiving response from server => ${JSON.stringify(data)} and ${data} + `)
                            window.location.href = `/customer-ticket-success`;
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                        }
                    }).catch(function (err) {
                        console.log(err);
                        alert(err);
                    }).then(function () {
                        console.log(".")
                    })
                }
            },
        },
    });
});