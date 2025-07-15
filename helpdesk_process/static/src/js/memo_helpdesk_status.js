odoo.define('helpdesk_process.memo_customer_status_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    let localStorage = window.localStorage;

    let renderCustomerTicketStatus = function(data, current_stage_id, close_stage_id){
        //  loop through all data to render dynamic records
        $(`#status_display`).empty();
        $('#status_display_div').removeClass('d-none');
        console.log("Displaying status with data", data);
        let circle_count = 1
        $.each(data, function (key, val) {
            console.log(`what is key ${val.id} current_stage_id ${current_stage_id} close_stage_id ${close_stage_id}`);

            let circle_class = ""
            if (val.id == current_stage_id){
                circle_class = 'step current'
            }else if (val.id == close_stage_id){
                circle_class = 'step completed'
            }else {
                circle_class = 'step'
            }
            console.log(`what is attr: ${circle_class} ==> ${val.id} current_stage_id ${current_stage_id} close_stage_id ${close_stage_id}`);
            $(`#status_display`).append(
                `
                <div class="${circle_class}">
                    <div class="circle">${circle_count}</div>
                    <div class="label">${val.name}</div>
                </div>
                `
            )
            circle_count += 1
            }
        );
        
    }
    publicWidget.registry.MemoHelpdeskCustomerTicketsFormWidgets = publicWidget.Widget.extend({
        selector: '.CustomerStatusDashboard',
        start: function(){
            return this._super.apply(this, arguments).then(function(){
                console.log("started Customer status");
            });
        },
        willStart: function(){
            return this._super.apply(this, arguments).then(function(){
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

            'click .submit_btn': function(ev){
                let target = $('#customer_info');
                console.log(`The value of customer info is ${target.val()}`)
                // Make an api call
                this._rpc({
                    route: `/get-customer-ticket`,
                    params: {
                        'ticket_no': target.val() // e.g REF00921, 
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('Customer tickets providing => '+ JSON.stringify(data));
                        target.val('');
                        renderCustomerTicketStatus(data.data, data.current_stage_id, data.close_stage_id)
                    }else{
                        target.val('');
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

            // 'click .submit_btn': function(ev){
            //     var list_of_fields = [];
            //     $('input,textarea,select,select2').filter('[required]:visible').each(function(ev){
            //         var field = $(this); 
            //         if (field.val() == ""){
            //             field.addClass('is-invalid'); 
            //             list_of_fields.push(field.attr('labelfor'));
            //         }
            //     });
            //     if (list_of_fields.length > 0){
            //         alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
            //         return false;
            //     }else{
            //         let $btn = $('.submit_btn');
            //         let $btnHtml = $btn.html()
            //         $btn.attr('disabled', 'disabled');
            //         $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
            //         $.blockUI({
            //             'message': '<h2 class="card-name">Please wait ...</h2>'
            //         });
            //         // var form = $('#msform')[0];
            //         // // FormData object 
            //         // var formData = new FormData(form);
            //         // console.log('formData is ==>', formData)
            //         $.ajax({
            //             url: "/customer/tickets",
            //             type: "GET",
            //             beforeSend: function () {
            //                 console.log("Logining.... ");
            //             },
            //           })
            //             .then(function (data) {
            //                 console.log(`Logining data.... ${data}`);
            //             //   self._handleResponse(data);
            //             })
            //             .fail(function (jxhr, textStatus) {
            //               // console.error('Request For Helpdesk Tickets Failed ' + textStatus);
            //               console.log("Request For Helpdesk Tickets Failed " + textStatus);
            //             })
            //             .then(function () {
            //                 console.log("Logining data 222.... ");
            //             });
            //     }
            // },
        },
    });
// return PortalRequestWidget;
});