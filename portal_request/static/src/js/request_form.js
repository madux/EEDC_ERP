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
        $('input,textarea,select,select2').each(function(ev){
            var field_id = $(this);
            storeFieldItem[`${field_id.attr('id')}`] = field_id.val()
        });
        localStorage.setItem('oldValueStore', JSON.stringify(storeFieldItem))
    }

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
            field.prop('readonly', false);
            field.prop('disabled', false);
            field.prop('required', true);
            $('input[name=is_edit_mode]').prop('checked', true);
            trigger_date_function($('#leave_start_datex'))
            trigger_date_function($('#leave_end_datex'))
            // open the description text for editting
            // $('#description').prop('contenteditable', true)
            // trigger leave date
            
        });

    }

    let checkEditableRequiredFields = function () {
        let lf = [];
        const excluded = ['message'];
        $('input[required], textarea[required], select[required]')
            .filter(':visible:not([disabled]):not([readonly])')
        // $('input,textarea,select,select2').filter('[required]:visible')
            .each(function () {
                let field = $(this);
                console.log('show me fields to edit', field);
                
                if (!field.val() || field.val().trim() === "") {
                    field.addClass('is-invalid');

                    // Prefer labelfor, fallback to name or id
                    let label =  field.attr('labelfor') || field.attr('name') || field.attr('id') 
                   
                    console.log(`All edited fields in forms ${label}`);
                    lf.push(label);
                } else {
                    field.removeClass('is-invalid'); // cleanup if corrected
                }
            });
        // let arr = arr.filter(item => item !== 'message');
        // if (arr.length > 0) {
        if (lf.filter(item => item !== 'message').length > 0) {
            let lf_no_message = lf.filter(item => item !== 'message')
            console.log(`length of fields not filled  ${lf_no_message}`);
            let message = `Validation: Please ensure the following fields are filled:\n - ${lf_no_message.join("\n - ")}`;
            return lf_no_message;
        }
        else{
            return false;
        }
    };

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

    let lockFieldsFunction = function(){
        $('input, select, textarea, select2').each(function(ev){
            $(this).prop('disabled', true) 
        })
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
        events: {
            'click .editbtn': function(ev){
                console.log("EDIT MODE ACTIVATED")
                // hide editbtn 
                // display save and discard option
                // enable all fields to be writtable 
                let edit = $(ev.target);
                let save = $('#save');
                let back = $('#previous')
                let discard = $('#discard')
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
                let save = $(ev.target);
                let edit = $('#editbtn');
                let back = $('#previous')
                let discard = $('#discard')
                let resend_request = $('.resend_request')

                edit.removeClass('d-none');
                back.removeClass('d-none');
                resend_request.removeClass('d-none');
                save.addClass('d-none');
                discard.addClass('d-none');
                // saveChangedFieldsValues();

                let leave_type_id = $("#leave_type_id")
                let leave_start_datex = $("#leave_start_datex")
                let leave_end_datex = $("#leave_end_datex")
                let leave_remaining = $("#leave_remaining")
                let leave_reliever_ids = $("#leave_reliever_ids")
                let description = $("#description")
                let record_id = $(".record_id").attr('id')
                console.log('saving record data => 1')
                // call a save route 
                
                this._rpc({
                    route: `/save/data`,
                    params: {
                        'leave_type_id': leave_type_id.val(),
                        'leave_start_date': leave_start_datex.val(),
                        'leave_end_date': leave_end_datex.val(),
                        'leave_Reliever': leave_reliever_ids.val(),
                        'description': description.val(),
                        'memo_id': record_id,
                    },
                }).then(function (data) {
                    if(data.status){
                        console.log('return saved record data => ')
                        $("#is_edit_mode").prop('checked', false);
                        // lock all fields 
                        lockFieldsFunction();
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
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
                console.log(`supervisor comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'supervisor_comment': $('#supervisor_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': ''
                    },
                }).then(function (data) {
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
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_comment_button': function(ev){
                let targetElement = $(ev.target).attr('id');
                console.log(`refusal comment clicked ${targetElement}`)
                this._rpc({
                    route: `/update/data`,
                    params: {
                        'manager_comment': $('#refuse_comment_message').val(),
                        'memo_id': $('.record_id').attr('id'),
                        'status': 'Refuse'
                    },
                }).then(function (data) {
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
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
            'click .refuse_request_btn': function(ev){
                let targetElement = $(ev.target).attr('id');
                this._rpc({
                    route: `/user/approver`,
                    params: {
                        'memo_id': $('.record_id').attr('id'),
                    },
                }).then(function (data) {
                    console.log('updating manager comment record data => '+ JSON.stringify(data))
                    if(!data.status){
                        modal_message.text(data.message)
                        alert_modal.modal('show');
                    }else{
                        divRefuseCommentMessage.show();
                        modalfooter4cancel.hide();
                        refuseCommentMessage.attr('required', true);
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            }, 
            'click .btn-close-success': function(ev){
                $('#successful_alert').hide()

            },

            'click .resend_request': function(ev){
                let targetElementid = $('.record_id').attr('id');
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
                        alert(data.message);
                        window.location.href = `/my/request/view/${$('.record_id').attr('id')}`
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },

            'click .approve_request': function(ev){
                let targetElementId = $('.record_id').attr('id');
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
                        window.location.href = `/my/request/view/${targetElementId}`
                    }else{
                        alert(data.message);
                        return false;
                    }
                    
                }).guardedCatch(function (error) {
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
                    }else{
                        alert(data.message);
                    }
                    
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    alert(`Unknown Error! ${msg}`)
                });
            },
         },
         

    });

// return PortalRequestWidget;
});