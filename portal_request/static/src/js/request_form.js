odoo.define('portal_request.portal_request_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  

    let alert_modal = $('#portal_request_alert_modal');
    let successful_alert = $('#successful_alert');
    let modal_message = $('#display_modal_message');
    let divRefuseCommentMessage = $('#div_refuse_comment_message');
    let modalfooter4cancel = $('#modalfooter4cancel');
    let refuseCommentMessage = $('#refuse_comment_message');
    $('input[name=is_edit_mode]').prop('checked', false);

    // hiding the components until options is indicated
    divRefuseCommentMessage.hide()
    modalfooter4cancel.hide()
    refuseCommentMessage.attr('required', false);
    let localStorage = window.localStorage;

    let checkOverlappingLeaveDate = function(thiis){
        var message = ""
        var staff_num = $('#staff_id').val();
        if(staff_num !== "" && $('#leave_start_date').val() !== '' && $('#leave_end_datex').val() !== ""){
            thiis._rpc({
                route: `/check-overlapping-leave`,
                params: {
                    'data': {
                        'staff_num': staff_num,
                        'start_date': $('#leave_start_date').val(),
                        'end_date': $('#leave_end_datex').val(),
                    }
                },
            }).then(function (data) { 
                if (!data.status) {
                    $("#leave_start_date").val('')
                    $("#leave_end_datex").val('') //.trigger('change')
                    $('#leave_start_date').attr('required', true);
                    $('#leave_start_date').addClass('is-invalid', true);
                    let message = `Validation Error! ${data.message}`
                    console.log("not Passed for leave, ", message)
                    // alert(message); 
                    // return false
                    modal_message.text(message)
                    alert_modal.modal('show');

                }else{
                    console.log("Passed for leave")
                }
            }).guardedCatch(function (error) {
                let msg = error.message.message
                console.log(msg)
                $("#leave_end_datex").val('')
                message = `Unknown Error! ${msg}`
                modal_message.text(message)
                alert_modal.modal('show');
                return false;
            });
        } 
    }

    let trigger_date_function = function(dateElement, minDate=new Date(), maxDate=null){
        dateElement.datepicker('destroy').datepicker({
            onSelect: function (ev) {
                dateElement.trigger('blur')
            },
            dateFormat: 'mm/dd/yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2023:2050',
            maxDate: maxDate,
            minDate: minDate,
            // Disable Saturday (6) & Sunday (0)
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            }
        });
    }

    let saveChangedFieldsValues = function(thiss){
        let leave_type_id = $("#leave_type_id")
        let leave_start_datex = $("#leave_start_datex")
        let leave_end_datex = $("#leave_end_datex")
        let leave_remaining = $("#leave_remaining")
        let leave_reliever_ids = $("#leave_reliever_ids")
        let description = $("#description")
        let record_id = $(".record_id").attr('id')
        checkEditableRequiredFields()
        // call a save route 
        thiss._rpc({
            route: '/save/data/',
            params: {
                'leave_type_id': leave_type_id.val(),
                'leave_start_date': leave_start_datex.val(),
                'leave_end_date': leave_end_datex.val(),
                // 'leave_remaining': leave_remaining,
                'leave_Reliever': leave_reliever_ids.val(),
                'description': description.val(),
                'memo_id': record_id,
            }
        }).then(function (data) {
            if(data.status){
                console.log('saving record data => ')
                $("#is_edit_mode").prop('checked', false);
            }else{
                alert(data.message);
            }
            
        }).guardedCatch(function (error) {
            let msg = error.message.message
            alert(`Unknown Error! ${msg}`)
        });
    }

    let storeOldFieldsValue = function(){
        let storeFieldItem = {};
        $('input,textarea,select,select2,span').each(function(ev){
            var field_id = $(this);
            var tagName = field_id.prop("tagName").toLowerCase();
            if (tagName == 'span'){
                storeFieldItem[`${field_id.attr('field_name')}`] = field_id.text()
            }
            else{
                storeFieldItem[`${field_id.attr('field_name')}`] = field_id.val()
            }
        });
        localStorage.setItem('oldValueStore', JSON.stringify(storeFieldItem))
    }

    let discardRestoreOldFieldsValue = function(){
        let stored = localStorage.getItem('oldValueStore');
        if (!stored) return; // nothing stored yet
        
        let oldValues = JSON.parse(stored); 
        $('input, textarea, select, select2, span').each(function(){
            let field = $(this);
            let fieldName = field.attr('field_name');
            if (!fieldName) return; // skip if no field_name

            let tagName = field.prop("tagName").toLowerCase();
            let oldValue = oldValues[fieldName];

            if (oldValue !== undefined) {
                if (tagName === 'span') {
                    // display field
                    field.text(oldValue);

                } else if (tagName === 'input') {
                    let type = field.attr('type');
                    if (type === 'checkbox') {
                        field.prop('checked', oldValue === true || oldValue === "true");
                    } else if (type === 'radio') {
                        // restore radio by value match
                        if (field.val() == oldValue) {
                            field.prop('checked', true);
                        }
                    } else {
                        // text, number, hidden, etc.
                        field.val(oldValue);
                    }

                } else if (tagName === 'select') {
                    field.val(oldValue);
                    // handle select2 if applied
                    if (field.hasClass("select2-hidden-accessible")) {
                        field.trigger('change.select2');
                    } else {
                        field.trigger('change');
                    }

                } else if (tagName === 'textarea') {
                    field.val(oldValue);
                }
            }
        });
    };

    let makeWritableFieldsEditable = function(){
        console.log('All writable fields are now readable to edit');
        // store values of old records in localstorage ==> oldValueStore
        // check if the status of the record is not the first stage. 
        //consider putting this in the controller
        // 1. Set all the fields not readonly,
        // set is_edit_mode checkbox to true
        storeOldFieldsValue();
        // $('input,textarea,select,select2').filter('[readonly]:visible').each(function(ev){
        $('input,textarea,select,select2').each(function(ev){
            var field = $(this); 
            if (field.prop('readonly')) {
                field.prop('readonly', false);
            }
            if (field.prop('disabled')) {
                field.prop('disabled', false);
            }
            if (field.prop('required')) {
                field.prop('required', true);
            }

            $('input[name=is_edit_mode]').prop('checked', true);
            trigger_date_function($('#leave_start_datex'))
            trigger_date_function($('#leave_end_datex'))
            // open the description text for editting
            // $('#description').prop('contenteditable', true)
            // trigger leave date
        });

    }

    let resetModificationProps=function(){
        let save = $('#save');
        let edit = $('#editbtn');
        let back = $('#previous')
        let discard = $('#discardbtn')
        let resend_request = $('.resend_request')
        save.addClass('d-none');
        discard.addClass('d-none');
        edit.removeClass('d-none');
        back.removeClass('d-none');
        resend_request.removeClass('d-none');
        // saveChangedFieldsValues();
    }

    let checkEditableRequiredFields = function () {
        let lf = [];
        const excluded = ['message'];
        // $('input[required], textarea[required], select[required]')
        //     .filter(':visible:not([disabled]):not([readonly])')
        // $('input,textarea,select,select2').filter('[required]:visible')
        $('input[required], textarea[required], select[required]').filter(':visible:not([disabled])')
        .each(function () {
                let field = $(this);
                console.log('show me fields to edit', field);
                if (field.val() == "" || field.val().trim() === "") {
                    field.addClass('is-invalid');
                    // Prefer labelfor, fallback to name or id
                    let label =  field.attr('labelfor') || field.attr('name') || field.attr('id') 
                    console.log(`All edited fields in forms ${label}`);
                    lf.push(label);
                } else {
                    field.removeClass('is-invalid'); // cleanup if corrected
                }
            }); 
        let fields_to_exclude = ['message', 'product_item_id']
        let filtered_fields = lf.filter(item => $.inArray(item, fields_to_exclude) === -1);
        if (filtered_fields.length > 0) {
            // let lf_no_message = lf.filter(item => item !== 'message')
            console.log(`length of fields not filled  ${filtered_fields}`);
            let message = `Validation: Please ensure the following fields are filled:\n - ${filtered_fields.join("\n - ")}`;
            return filtered_fields;
        } 
        else{
            return false;
        }
    };

     var formatCurrency = function(value) {
        if (value) {
            return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")

        }
    }

    // var compute_total_amount = function(){
    //     let total = 0;

    //     $('.sub_total_amount').each(function () {
    //     let text = $(this).text().trim();
    //     let value = parseFloat(text.replace(/,/g, '')); // remove commas and convert to number

    //     if (!isNaN(value)) {
    //         total += value;
    //     }

    //     console.log(`Subtotal item: ${value}`);
    //     });
    //     console.log(`Total subtotal amount: ${total}`); 
    //     var amount = formatCurrency(total)
    //     $('#all_total_amount').text(amount)

    //     // $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
    // }
    var compute_total_amount = function(){
        var total = 0
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_co = $(this).attr('row_count')
            var amount = 0
            var qty = 0
            var amt = false
            var subtotal = false
            let top_m = $(this)
            $(`tr[row_count=${row_co}]`).closest(":has(input)").find('input').each(
                
                function(){
                    // if($(this).attr('main_name') == 'sub_total_amount'){
                    //     let qty_val = Number($(this).val())
                    //     console.log(`what is subtotal qty ${qty_val} gggg ${$(this).text()}`)
                    //     qty = qty_val
                    // }
                    if($(this).attr('main_name') == 'quantity_available'){
                        let qty_val = Number($(this).val())
                        console.log(`what is subtotal qty ${qty_val}`)
                        qty = qty_val
                    }
                    if($(this).attr('main_name') == 'amount_total'){
                        amt = Number($(this).val())
                        console.log(`what is subtotal qty ${amt}`)

                    } 
                }
            )
            console.log(`what is subtotal and qty ${qty} / ${amt}`)
            let qt = qty * amt
            total += qt
        })
        var amount = formatCurrency(total)
        $('#all_total_amount').text(amount)
        console.log(`what is subtotal final amount ${total}`)

        // $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
    }

    // let checkEditableRequiredFields = function(){
    //     var list_of_fields = [];
    //     $('input,textarea,select,select2').filter('[required]:visible').each(function(ev){
    //         var field = $(this); 
    //         if (field.val() == ""){
    //             field.addClass('is-invalid');
    //             console.log(`All edited fields in forms ${$(this).attr('labelfor')}`);
    //             list_of_fields.push(field.attr('labelfor'));
    //         }
    //     });
    //     if (list_of_fields.length > 0){
    //         // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
    //         // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
    //         let message = `Validation: Please ensure the following fields are filled.. ${list_of_fields}`
    //         modal_message.text(message)
    //         alert_modal.modal('show');
    //         return false;
    //     }
    // }

    let makeAllFieldsReadonly = function(){
        $('input, select, textarea, select2').each(function(ev){
            $(this).prop('disabled', true) 
        })
    }
    let saveProductitem = function(){
        let DataItems = []
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_co = $(this).attr('row_count') 
            console.log('rrrooowsssss', row_co)
            var list_item = {
                'product_id': '', 
                'description': '',
                'qty': '',
                'amount_total': '',
                'used_qty': '',
                'used_amount': '',
                'note': '',
                'line_checked': false,
                'code': 'mef00981',
                'request_line_id': $(this).attr('id'),
                'distance_from': '',
                'distance_to': '',
            }
            // input[type='text'], input[type='number']
            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                function(){
                    if($(this).attr('name') == "product_item_id"){
                        console.log('HERE NA MY FIELD VALUE ', $(this).val())
                        list_item['product_id'] = $(this).val()
                    }
                    if($(this).attr('name') == "product_item_description"){
                        console.log($(this).val())
                        list_item['description'] = $(this).val()
                    }
                    if($(this).attr('main_name') === "quantity_available"){
                        list_item['qty'] = $(this).val()
                    } 
                    if($(this).attr('main_name') == "amount_total"){
                        console.log($(this).val())
                        list_item['amount_total'] = $(this).val()
                    }
                    
                }
            )
            DataItems.push(list_item)
        })
        return DataItems;
    }
    publicWidget.registry.PortalRequestFormWidgets = publicWidget.Widget.extend({
        selector: '#portal-request-form',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("started form request")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log(".....")
            })
        },

        _onSubmitSearch: function (ev) {
            ev.preventDefault();
            let query = this.$('#search_input_panel').val() || '';
            console.log("Custom search for:", query);
            // Example: redirect to controller
            window.location = `/my/requests/param/${query}`;
        },
        events: {
            'submit': '_onSubmitSearch',
            'click .editbtn': function(ev){
                console.log("EDIT MODE ACTIVATED")
                // hide editbtn 
                // display save and discard option
                // enable all fields to be writtable 
                let edit = $(ev.target);
                let save = $('#save');
                let back = $('#previous')
                let discard = $('#discardbtn')
                let resend_request = $('.resend_request')

                edit.addClass('d-none');
                resend_request.addClass('d-none');
                back.addClass('d-none');
                save.removeClass('d-none');
                discard.removeClass('d-none');
                makeWritableFieldsEditable();
            },

            'click #save': function(ev){
                // hide save btn 
                // hide discard button
                // disable all fields to be readonly 
                let cef = checkEditableRequiredFields()
                if (cef){
                    alert(cef);
                    return false;
                }
                resetModificationProps()
                // let save = $(ev.target);
                // let edit = $('#editbtn');
                // let back = $('#previous')
                // let discard = $('#discardbtn')
                // let resend_request = $('.resend_request')

                // edit.removeClass('d-none');
                // back.removeClass('d-none');
                // resend_request.removeClass('d-none');
                // save.addClass('d-none');
                // discard.addClass('d-none');
                // // saveChangedFieldsValues();

                let leave_type_id = $("#leave_type_id")
                let leave_start_datex = $("#leave_start_datex")
                let leave_end_datex = $("#leave_end_datex")
                let leave_remaining = $("#leave_remaining")
                let leave_reliever_ids = $("#leave_reliever_ids")
                let description = $("#description")
                let payment_reference_form = $("#payment_reference_form")
                let record_id = $(".record_id").attr('id')
                console.log('saving record data => 1', saveProductitem())
                // call a save route 
                
                this._rpc({
                    route: `/save/data`,
                    params: {
                        'leave_type_id': leave_type_id.val(),
                        'leave_start_date': leave_start_datex.val(),
                        'leave_end_date': leave_end_datex.val(),
                        'leave_Reliever': leave_reliever_ids.val(),
                        'leave_Reliever': leave_reliever_ids.val(),
                        'description': description.val(),
                        'memo_id': record_id,
                        'payment_reference': payment_reference_form.val(),
                        'Dataitem': saveProductitem()
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('return saved record data => ')
                        $("#is_edit_mode").prop('checked', false);
                        // lock all fields 
                        makeAllFieldsReadonly();
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

            'click #discardbtn': function(ev){
                discardRestoreOldFieldsValue();
                $("#is_edit_mode").prop('checked', false);
                // lock all fields 
                makeAllFieldsReadonly();
                resetModificationProps();
            },

            'change .AmountTots': function(ev){
                // assigning the property: name of quantity field as the quantity selected
                let qty_elm = $(ev.target);
                console.log("WE ARE HERE TO GET TARGET", qty_elm)

                let productinput_id = qty_elm.attr('id');
                console.log("WE ARE HERE TO GET TARGET", productinput_id)

                // $(`.SUBTOTAL${productinput_id}`).val();
                let unit_price = qty_elm.val()
                let unit = $(`.QTY${productinput_id}`)
                if (unit.val() < -1){
                    alert('Unit must be greater than 0');
                    unit_price.val('');
                    qty_elm.addClass('is-invalid', true);
                    unit.addClass('is-invalid', true);
                console.log("WE ARE HERE TO GET TARGET 1", qty_elm)

                }else{
                    let subtotal = $(`.SUBTOTAL${productinput_id}`)

                    let result = unit.val() * unit_price 
                    subtotal.val(result);
                    subtotal.text(result);
                    $(`.AMTTOTAL${productinput_id}`).removeClass('is-invalid', true);
                    unit.removeClass('is-invalid', true);
                compute_total_amount();

                }

                
            },

            'blur input[name=leave_start_datex]': function(ev){
                if ($('#leave_type_id').val() == ""){
                    let message = `Validation Error! Please ensure to select Leave type`
                    $('#leave_start_datex').val('');
                    $('#leave_end_datex').val('');
                    alert(message);
                    return false;
                }
                let leave_remaining = $('#leave_remaining').val(); 
                let start_date = $(ev.target);
                let remain_days = leave_remaining !== undefined ? parseInt($('#leave_remaining').val()) : 1
                var selectStartLeaveDate = new Date(start_date.val());
                var endDate = new Date($('#leave_start_datex').val()).getTime() + (1 * 24 * 60 * 60 * 1000);
                var maxDate = endDate + (21 * 24 * 60 * 60 * 1000)
                var prefixendDate = new Date(endDate).getMonth() + 1 
                var prefixmaxDate = new Date(maxDate).getMonth() + 1
                var join1 = prefixendDate.length == 1 ? `0${prefixendDate}` : prefixendDate;
                var join2 = prefixmaxDate.length == 1 ? `0${prefixmaxDate}` : prefixmaxDate;
                var st = `${join1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
                var end = `${join2}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`
                console.log(`what is start and end date ${st} ${end}`)
                trigger_date_function($('#leave_end_datex'), st, end)
            },
            'blur input[name=leave_end_datex]': function(ev){
                let leaveRemaining = $('#leave_remaining').val();
                console.log(`leaveRemaining IS : ${leaveRemaining}`)
                let start_date = $('#leave_start_datex');
                let endDate = $(ev.target);
                var date1 = new Date(start_date.val());
                var date2 = new Date(endDate.val());
                var Difference_In_Time = date2.getTime() - date1.getTime();
                var Difference_In_Days = Difference_In_Time / (1000 * 3600 * 24);
                console.log(`Difference_In_Days IS : ${Difference_In_Days}`)
                if (parseInt(leaveRemaining) > 0 && Difference_In_Days > parseInt(leaveRemaining)){
                    $('#leave_end_datex').val("");
                    $('#leave_end_datex').attr('required', true);
                    alert(`You only have ${leaveRemaining} number of leave remaining for this leave type. Please Ensure the date range is within the available day allocated for you.`)
                    return true;
                }
                else{
                    $('#leave_end_datex').attr('required', false);
                    endDate.removeClass('is-invalid').addClass('is-valid');
                    $('#leave_taken').text(Difference_In_Days + ` Day(s)`)

                }
                checkOverlappingLeaveDate(this)
            }, 
			'change #leave_reliever_ids': function(ev){
            // 'blur input[name=leave_reliever]': function(ev){
                let leave_reliever = $('#leave_reliever_ids');
                let start_date = $('#leave_start_datex');
                if (!start_date.val() && leave_reliever.val() !== ""){
                    leave_reliever.val('').trigger('change');
                    let message = `Validation Error! Please provide leave start date, reliever`
                    alert(message);
                    return false;
                }
                else{
					if (leave_reliever.val() !== ""){
						this._rpc({
							route: `/check-employee-still-onleave`,
							params: {
								'employee_id': leave_reliever.val(),
								'start_date': $('#leave_start_datex').val(),
								'end_date': $('#leave_end_datex').val(),
							},
						}).then(function (data) { 
							if (!data.status) {
                                leave_reliever.val('').trigger('change');
								leave_reliever.addClass('is-invalid', true);
								let message = `Validation Error! ${data.message}`
								alert(message);
                                // return false;
							}else{
								console.log("---")
							}
						}).guardedCatch(function (error) {
							let msg = error.message.message
							console.log(msg)
							leave_reliever.val('')
							let message = `Unknown Error! ${msg}`
							alert(message);
							return false;
						});
					}
                }
            },

            'change select[name=leave_type_id]': function(ev){
                let leave_id = $(ev.target).val();
                let staff_num = $('#staff_id').text();
                if(staff_num !== '' && leave_id !== ''){  
                    var self = this;
                    this._rpc({
                        route: `/get/leave-allocation`, ///${leave_id}/${staff_num}`,
                        params: {
                            'staff_num': staff_num.trim(),
                            'leave_id': leave_id
                        },
                    }).then(function (data) {
                        console.log('retrieved staff leave data => '+ JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#leave_start_datex").val('')//.trigger('change')
                            $("#leave_end_datex").val('')//.trigger('change')
                            $("#leave_remaining").val('')
                            $("#leave_remain").text('0')
                            $("#leave_reliever").val('')

                            alert(`Validation Error! ${data.message}`)
                        }else{
                            var number_of_days_display = data.data.number_of_days_display; 
                            console.log(number_of_days_display)
                            $("#leave_remaining").val(number_of_days_display)
                            $("#leave_remain").text(number_of_days_display)
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            }, 

            'click .supervisor_comment_button': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_comment_button');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Resending ...</h2>'
                });
                console.log(`supervisor comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'supervisor_comment': $('#supervisor_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': ''
                    },
                }).then(function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    if(data.status){
                        console.log('updating record data => '+ JSON.stringify(data))
                        $('#supervisor_comment_message').val('');
                        alert(data.message);
                        let targetElementid = $('.record_id').attr('id');
                        window.location.href = `/my/request/view/${targetElementid}`
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_comment_button': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_comment_button');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Refusing ...</h2>'
                });
                console.log(`refusal comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'manager_comment': $('#refuse_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': 'Refuse'
                    },
                }).then(function (data) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    if(data.status){
                        console.log('updating manager comment record data => '+ JSON.stringify(data))
                        $('#refuse_comment_message').val('');
                        $('#refuse_comment_message').attr('required', false);
                        $('#portal_request_cancel_modal').hide()
                        $('#successful_alert').show()
                        window.location.href = `/my/request/view/${$('.record_id').attr('id')}`
                        // alert(data.message);
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_request_btn': function(ev){
                let targetElement = $(ev.target).attr('id');
                let $btn = $('.refuse_request_btn');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Refusing ...</h2>'
                });
                this._rpc({
                    route: `/user/approver`,
                    params: {
                        'memo_id': $('.record_id').attr('id'),
                    },
                }).then(function (data) {
                    console.log('updating manager comment record data => '+ JSON.stringify(data))
                    
                    if(!data.status){
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        modal_message.text(data.message)
                        alert_modal.modal('show');
                    }else{
                        if (data.warning){
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                            alert(data.message);
                        }
                        else{
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                            divRefuseCommentMessage.show();
                            modalfooter4cancel.hide();
                            refuseCommentMessage.attr('required', true);
                        }
                    }
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            }, 
            'click .btn-close-success': function(ev){
                $('#successful_alert').hide()

            },

            'click .resend_request': function(ev){
                let targetElementid = $('.record_id').attr('id');
                let $btn = $('.resend_request');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Resending ...</h2>'
                });
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'Resend',
                        'memo_id': $('.record_id').attr('id')
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('updating resending status => '+ JSON.stringify(data))
                        // $('#successful_alert').show()
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        alert(data.message);
                        window.location.href = `/my/request/view/${$('.record_id').attr('id')}`
                    }else{
                        alert(data.message);
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

            'click .approve_request': function(ev){
                let targetElementId = $('.record_id').attr('id');
                let $btn = $('.approve_request');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Approving ...</h2>'
                });
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'Approve',
                        'memo_id': targetElementId
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('updating Approval status => '+ JSON.stringify(data))
                        // $('#successful_alert').show()
                        alert(data.message);
                        $('#div_supervisor_comment_message').addClass('d-none');
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        window.location.href = `/my/request/view/${targetElementId}`
                    }else{
                        
                        alert(data.message);
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                        if (data.link){
                            // window.location.href = data.link
                            window.open( data.link, '_blank');
                        }
                        // return false;
                    }
                    
                }).guardedCatch(function (error) {
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .cancel_btn': function(ev){
                $('#refuse_comment_message').val('');
                $('#refuse_comment_message').attr('required', false);
                divRefuseCommentMessage.hide();
                modalfooter4cancel.show()
            }, 

            'click .cancel_modal_btn': function(ev){
                let targetElementid = $('.record_id').attr('id');
                let $btn = $('.cancel_modal_btn');
                let $btnHtml = $btn.html()
                $btn.attr('disabled', 'disabled');
                $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                $.blockUI({
                    'message': '<h2 class="card-name">Cancelling ...</h2>'
                });
                this._rpc({
                    route: `/my/request/update`,
                    params: {
                        'status': 'cancel',
                        'memo_id': targetElementid
                    },
                }).then(function (data) { 
                    if(data.status){
                        console.log('updating cancelled status => '+ JSON.stringify(data))
                        // $('#successful_alert').show()
                        alert(data.message);
                        window.location.href = `/my/request/view/${targetElementid}`
                        $btn.attr('disabled', false);
                        $btn.html($btnHtml)
                        $.unblockUI()
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                    $btn.attr('disabled', false);
                    $btn.html($btnHtml)
                    $.unblockUI()
                    alert(data.message);
                });
            },
         },
         

    });

// return PortalRequestWidget;
});