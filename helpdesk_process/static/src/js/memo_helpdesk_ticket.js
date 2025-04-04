odoo.define('helpdesk_process.memo_helpdesk_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    let localStorage = window.localStorage;

    let trigger_date_function = function(dateElement, minDate=new Date(), maxDate=null){
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

    // let storeOldFieldsValue = function(){
    //     let storeFieldItem = {};
    //     $('input,textarea,select,select2').each(function(ev){
    //         var field_id = $(this);
    //         storeFieldItem[`${field_id.attr('id')}`] = field_id.val()
    //     });
    //     localStorage.setItem('oldValueStore', JSON.stringify(storeFieldItem))
    // }
     
    // let saveChangedFieldsValues = function(thiss){
    //     let leave_type_id = $("#leave_type_id")
    //     let leave_start_datex = $("#leave_start_datex")
    //     let leave_end_datex = $("#leave_end_datex")
    //     let leave_remaining = $("#leave_remaining")
    //     let leave_reliever_ids = $("#leave_reliever_ids")
    //     let description = $("#description")
    //     let record_id = $(".record_id").attr('id')

    //     // call a save route 
    //     thiss._rpc({
    //         route: '/save/data/',
    //         params: {
    //             'leave_type_id': leave_type_id.val(),
    //             'leave_start_date': leave_start_datex.val(),
    //             'leave_end_date': leave_end_datex.val(),
    //             // 'leave_remaining': leave_remaining,
    //             'leave_Reliever': leave_reliever_ids.val(),
    //             'description': description.val(),
    //             'memo_id': record_id,
    //         }
    //     }).then(function (data) {
    //         if(data.status){
    //             console.log('saving record data => ')
    //             $("#is_edit_mode").prop('checked', false);
    //         }else{
    //             alert(data.message);
    //         }
            
    //     }).guardedCatch(function (error) {
    //         let msg = error.message.message
    //         alert(`Unknown Error! ${msg}`)
    //     });
    // }

    trigger_date_function($('#deadline_date'));

    publicWidget.registry.MemoHelpdeskFormWidgets = publicWidget.Widget.extend({
        selector: '#memo-request-form',
        start: function(){
            return this._super.apply(this, arguments).then(function(){
                console.log("started helpdesk form request");
            });
        },
        willStart: function(){
            return this._super.apply(this, arguments).then(function(){
                console.log("...memo helpdesk willstart...")
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

            'click .submit_btn': function(ev){
                var list_of_fields = [];
                $('input,textarea,select,select2').filter('[required]:visible').each(function(ev){
                    var field = $(this); 
                    if (field.val() == ""){
                        field.addClass('is-invalid'); 
                        list_of_fields.push(field.attr('labelfor'));
                    }
                });
                if (list_of_fields.length > 0){
                    alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
                    return false;
                }else{
                    let $btn = $('.submit_btn');
                    let $btnHtml = $btn.html()
                    $btn.attr('disabled', 'disabled');
                    $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                    $.blockUI({
                        'message': '<h2 class="card-name">Please wait ...</h2>'
                    });
                    var form = $('#msform')[0];
                    // FormData object 
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
                    }).then(function(data) {
                        if (data.status == false){
                            alert(data.message)
                            return false;
                        }else{
                            // clearing form content
                            $("#msform")[0].reset();
                            console.log(`Recieving response from server => ${JSON.stringify(data)} and ${data} + `)
                            window.location.href = `/customer-ticket-success`;
                            $btn.attr('disabled', false);
                            $btn.html($btnHtml)
                            $.unblockUI()
                        }
                    }).catch(function(err) {
                        console.log(err);
                        alert(err);
                    }).then(function() {
                        console.log(".")
                    })

                }
            },
        },
    });
// return PortalRequestWidget;
});