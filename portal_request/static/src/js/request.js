// import publicWidget from "web.public.widget";
// import { qweb } from "web.core";
// import { utils } from "web.utils";
// import { ajax } from "web.ajax";

// const PortalRequestWidget = publicWidget.registry.PortalRequest;

odoo.define('portal_request.portal_request', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;
    const setProductdata = [];
    let alert_modal = $('#portal_request_alert_modal');
    let modal_message = $('#display_modal_message');

    function getSelectedProductItem(valueName){
        // use to compile id no of the checked options for assessors and moderators
        let Items = [];
        $(`input[value=${valueName}]`).each(
            function(){
                let id = $(this).attr('id');
                Items.push(id);
            }
        )
        return Items;

    }
    function formatToDatePicker(date_str) {
        //split 1988-01-23 00:00:00 and return datepicker format 01/31/2021
        if (date_str !== '') {
            // let date = date_str.split(" ")[0]
            let data = date_str.split("-")
            if (data.length > 0) return `${data[2]}/${data[1]}/${data[0]}`;
        }
    }

    // var FormateDateToMMDDYYYY = function(dateObject) {
    //     var d = new Date(dateObject);
    //     var day = d.getDate();
    //     var month = d.getMonth() + 1;
    //     var year = d.getFullYear();
    //     if (day < 10) {
    //         day = "0" + day;
    //     }
    //     if (month < 10) {
    //         month = "0" + month;
    //     }
    //     var date = month + "/" + day + "/" + year; 
    //     return date;
    // };
 
    // function showAlertDialog(title, msg) {
    //     // Load the XML templates
    //     ajax.loadAsset('portal_request.portal_request', 'xml', '/portal_request/static/src/xml/partials.xml', {}, qweb).then(
    //         function (qweb) {
    //         // Templates loaded, you can now use them
    //             var wizard = qweb.render('portal_request.alert_dialogs', {
    //                 'msg': msg || _t('Message Body'),
    //                 'title': title || _t('Title')
    //             });
    //             wizard.appendTo($('body')).modal({
    //                 'keyboard': true
    //             });
    //         })
    // }

    function buildProductTable(data, memo_type, require='0', hidden='d-none', readon='0'){
        $.each(data, function (k, elm) {

            if (elm) {
                var lastRow_count = getOrAssignRowNumber()
                console.log(`Building product table ${k} ${elm}`)
                $(`#tbody_product`).append(
                    `<tr class="heading prod_row" id="${elm.id}" name="prod_row" row_count=${lastRow_count}>
                        <th width="5%">
                            <span>
                                <input type="checkbox" readonly="readonly" class="productchecked" checked="checked" id="${elm.id}" name="${elm.qty}"/>
                            </span>
                        </th>
                        <th width="40%">
                            <span id=${elm.id}>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" required="${memo_type == 'cash_advance' ? '': 'required'}" class="form-control productitemrow" name="product_item_id" value=${elm.name} labelfor="Product Line - ${elm.name}"/>
                            </span>
                        </th>
                        <th width="10%">
                            <input type="textarea" placeholder="Start typing" name="description" readonly="readonly" id="desc-${lastRow_count}" desc_elm="" value="${elm.description}" class="DescFor form-control" labelfor="Note"/> 
                        </th>
                        <th width="5%">
                            <input type="text" productinput="productreqQty" name="${elm.qty}" id="${elm.id}" value="${elm.qty}" required="required" class="productinput form-control" labelfor="Product Line - ${elm.name} Quantity"/> 
                        </th>
                        
                        <th width="10%">
                            <input type="number" name="amount_total" id="${elm.id}" value="${elm.amount_total}" amount_total="${elm.amount_total}" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '0': 'readonly'}" class="productAmt form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Amount Total"/> 
                        </th>
                        <th width="5%">
                            <input type="text" name="usedqty" id="${elm.id-lastRow_count}" value="${elm.used_qty}" usedqty="${elm.used_qty}" required="${require}" readonly="${readon}" class="productUsedQty form-control ${hidden}" labelfor="Product Line - ${elm.name}: Used Quantity"/> 
                        </th>
                        <th width="10%">
                            <input type="text" name="usedAmount" id="${elm.used_amount-lastRow_count}" value="${elm.used_amount}" usedAmount="${elm.used_qty}" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '0': 'readonly'}" class="productUsedAmt form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Product Line - ${elm.name}: Used Amount"/> 
                        </th>
                        <th width="10%">
                            <input type="textarea" name="note_area" id="${lastRow_count}" note_elm="" required="${memo_type == 'soe' || memo_type == 'cash_advance' ? 'required': ''}" class="Notefor form-control ${hidden}" labelfor="Note"/> 
                        </th>
                        <th width="5%">
                            <a id="${lastRow_count}" remove_id="${lastRow_count}" name="${elm.id}" href="#" class="remove_field btn btn-primary btn-sm"> Remove </a>
                        </th>
                    </tr>`
                )
                // ${memo_type=="cash_advance" || memo_type=="soe" ? 1: 0}
                // TriggerProductField(lastRow_count);
                // $(`input[special_id='${lastRow_count}'`).attr('readonly', true);
                setProductdata.push(elm.id)
            } else {
                console.log('No product items found')
            }
        });
    }

    function getOrAssignRowNumber(){
        var lastRow_count = 0
        // $(`#tbody_product > tr.prod_row > th > input.productitemrow`)[0].each(
        var lastElement = $(`#tbody_product > tr.prod_row > th > span > input.productitemrow`)
        if (lastElement){
            let special_id = lastElement.last().attr('special_id');
            console.log("Last element found is, ", lastElement)
            lastRow_count = special_id ? parseInt(special_id) + 1 : lastRow_count + 1
        }else {
            lastRow_count + 1
        }
         
        return lastRow_count
    }

    function buildProductRow(memo_type){
        let lastRow_count = getOrAssignRowNumber()
        console.log(`lastrowcount ${lastRow_count}`)
        $(`#tbody_product`).append(
            `<tr class="heading prod_row" name="prod_row" row_count=${lastRow_count}>
                <th width="5%">
                    <span>
                        <input type="checkbox" class="productchecked"/>
                    </span>
                </th>
                <th width="40%">
                    <span>
                        <input special_id="${lastRow_count}" class="form-control productitemrow" name="product_item_id" required="${memo_type == 'cash_advance' ? '': 'required'}" labelfor="Product Line"/>
                    </span>
                </th>
                <th width="10%">
                    <input type="textarea" placeholder="Start typing" name="description" id="${lastRow_count}" desc_elm="" required="${memo_type == 'cash_advance' ? 'required': ''}" class="DescFor form-control" labelfor="Note"/> 
                </th>
                <th width="5%">
                    <input type="text" productinput="productreqQty" class="productinput form-control" required="required" labelfor="Product Line - Quantity"/>
                </th>
                <th width="10%">
                    <input type="number" name="amount_total" id="amountt-${lastRow_count}" amount_total="Amount-${lastRow_count}" required="${memo_type == 'cash_advance' ? 'required': ''}" readonly="${memo_type == 'cash_advance' ? '0': 'readonly'}" class="productAmt form-control" labelfor="Amount Total"/> 
                </th>
                <th width="5%">
                    <input type="text" name="usedQty-${lastRow_count}" id="usedQty-${lastRow_count}-id" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '0': 'readonly'}" class="productUsedQty form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Product Line -: Used Quantity"/> 
                </th>
                <th width="10%">
                    <input type="number" name="UsedAmount-${lastRow_count}" id="amounttUsed-${lastRow_count}" amount_total="UsedAmount-${lastRow_count}" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '0': 'readonly'}" class="productAmt form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Amount Total"/> 
                </th>
                <th width="10%">
                    <input type="textarea" name="note_area" id="${lastRow_count}" note_elm="" required="${memo_type == 'soe' || memo_type == 'cash_advance' ? 'required': ''}" class="Notefor form-control" labelfor="Note"/> 
                </th>
                
                <th width="5%">
                    <a href="#" id="" remove_id="${lastRow_count}" class="remove_field btn btn-primary btn-sm"> Remove </a>
                </th>
            </tr>`
        )
        TriggerProductField(lastRow_count)
    }
    localStorage.setItem('SelectedProductItems', "[]")

    function getSelectedProductItems(){
        let products = JSON.parse(localStorage.getItem('SelectedProductItems'));
        console.log("Products store is ", products)
        return products
    }

    function TriggerProductField(lastRow_count){
        $(`input[special_id='${lastRow_count}'`).select2({
            ajax: {
              url: '/portal-request-product',
              dataType: 'json',
              delay: 250,
              data: function (term, page) {
                return {
                  q: term, //search term
                  productItems: JSON.stringify(setProductdata), //getSelectedProductItems(),
                  request_type: $('#selectRequestOption').val(), //getSelectedProductItems(),
                  page_limit: 10, // page size
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                console.log(data);
                // localStorage.setItem('productStorage', JSON.stringify(data.results))
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a Products',
            allowClear: false,
          });
    }

    $('#product_ids').select2({
    ajax: {
        url: '/portal-request-product',
        dataType: 'json',
        delay: 250,
        data: function (term, page) {
        return {
            q: term, //search term
            page_limit: 10, // page size
            page: page, // page number
        };
        },
        results: function (data, page) {
        var more = (page * 30) < data.total;
        return {results: data.results, more: more};
        },
        cache: true
    },
    minimumInputLength: 1,
    multiple: true,
    placeholder: 'Search for a Products',
    allowClear: true,
    });

    let checkOverlappingLeaveDate = function(thiis){
        var message = ""
        if ($('#selectRequestOption').val() === "leave_request"){
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
                        message = `Validation Error! ${data.message}`
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
            // else{
            //     message = "[Staff ID, leave start date and end date] Must all be provided";
            //     modal_message.text(message)
            //     alert_modal.modal('show');
            //     return false;
            // }
        } 
    }

    function displayNonLeaveElement() {
        console.log("Leave set to false")
        $('#leave_section').addClass('d-none');
        $('#leave_start_date').attr("required", false);
        $('#leave_end_datex').attr("required", false);
        $('#product_form_div').addClass('d-none');
        $('#product_ids').addClass('d-none');
        $('#product_ids').attr("required", false);
        // $('.product_section').addClass('d-none');
        }

    // function validate_empty_required_fields(){
    //     var list_of_fields = [];
    //     $('input,textarea,select').filter('[required]:visible').each(function(ev){
    //         var field = $(this); 
    //         if (field.val() == ""){
    //             field.addClass('is-invalid');
    //             console.log($(this).attr('labelfor'));
    //             list_of_fields.push(field.attr('labelfor'));
    //         } 
    //     });
    //     if (list_of_fields.length > 0){
    //         return true
    //     }else{
    //         return false
    //     }
    // }
    $('#leave_start_date').datepicker('destroy').datepicker({
        onSelect: function (ev) {
            $('#leave_start_date').trigger('blur')
        },
        dateFormat: 'mm/dd/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '2023:2050',
        maxDate: null,
        minDate: new Date()
    });
    
    var triggerEndDate = function(minDate, maxDate){
        $('#leave_end_datex').datepicker('destroy').datepicker({
            onSelect: function (ev) {
                $('#leave_end_datex').trigger('blur')
            },
            dateFormat: 'mm/dd/yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2023:2050',
            maxDate: maxDate,
            minDate: minDate, //new Date()
        });
    }
    
    publicWidget.registry.PortalRequestWidgets = publicWidget.Widget.extend({
        selector: '#portal-request',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                $('#request_date').datepicker('destroy').datepicker({
                    onSelect: function (ev) {
                        $('#request_date').trigger('blur')
                    },
                    dateFormat: 'mm/dd/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '2022:2050',
                    maxDate: null,
                    minDate: new Date()
                });
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("All events start")
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

            'change .productitemrow': function(ev){
                let product_elm = $(ev.target);
                let product_val = product_elm.val();
                console.log('Product value ==', product_val)
                // let selectedproductId = product_val.split('-')[1] 
                // console.log('Product value selected ==', selectedproductId)
                var link = product_elm.closest(":has(input.productinput)").find('input.productinput');
                var remove_link = product_elm.closest(":has(a.remove_field)").find('a.remove_field');
                link.attr('id', product_val);
                remove_link.attr('id', product_val);
                setProductdata.push(parseInt(product_val));
                console.log('sele ==> ', setProductdata)
                // let product_data = JSON.parse(localStorage.getItem('SelectedProductItems'));
                // product_data.append(product_val);
                // localStorage.setItem('SelectedProductItems', JSON.stringify(product_data))
                // let name="${elm.qty}" id="${elm.id}" value="${elm.qty}"
            },
            'click .remove_field': function(ev){
                let elm = $(ev.target);
                let elm_remove_id = elm.attr('remove_id'); 
                elm.closest(":has(tr.prod_row)").find('tr.prod_row').each(function(ev){
                    if($(this).attr('row_count') == elm_remove_id){
                        let remove_element_id = elm.attr('id');
                        // remove product id from the productData list
                        console.log("Remove element id == ", remove_element_id)
                        console.log('SEE PRODUCT DATA ', setProductdata)

                        // setProductdata.splice(remove_element_id)
                        setProductdata.splice(setProductdata.indexOf(remove_element_id),1)
                        console.log(`See it ${$.inArray(remove_element_id, setProductdata)}}`)
                        console.log('SEE PRD ', setProductdata)
                        $(this).remove();
                    }
                });
            }, 
            'change .productinput': function(ev){
                // assigning the property: name of quantity field as the quantity selected
                let qty_elm = $(ev.target);
                let selectedproductQty = qty_elm.val(); 
                this._rpc({
                    route: `/check-quantity`,
                    params:{
                        'product_id': qty_elm.attr('id'),
                        'qty': selectedproductQty,
                        'district': $("#selectDistrict").val(),
                        'request_type': $("#selectRequestOption").val()
                    }
                }).then(function(data){
                        if(!data.status){
                            qty_elm.attr('required', true);
                            qty_elm.val("");
                            qty_elm.addClass("is-invalid");
                            alert_modal.modal('show');
                            modal_message.text(data.message)
                        }else{
                            qty_elm.attr('required', false);
                            qty_elm.removeClass("is-invalid");
                            qty_elm.attr('name', selectedproductQty);
                            qty_elm.attr('value', selectedproductQty);
                        }
                })
            },

            'blur input[name=staff_id]': function(ev){
                let staff_num = $(ev.target).val();
                if(staff_num !== ''){  
                    var self = this;
                    this._rpc({
                        route: `/check_staffid/${staff_num}`,
                        params: {
                            //'type': type
                        },
                    }).then(function (data) {
                        console.log('retrieved staff data => '+ JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#employed_id").val('')
                            $("#phone_number").val('')
                            $("#email_from").val('')
                            alert(`Validation Error! ${data.message}`)
                        }else{
                            var employee_name = data.data.name;
                            var email = data.data.work_email;
                            var phone = data.data.phone; 
                            
                            $("#employed_id").val(employee_name);
                            $("#phone_number").val(phone)
                            $("#email_from").val(email)
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            },
            'change select[name=leave_type_id]': function(ev){
                let leave_id = $(ev.target).val();
                let staff_num = $('#staff_id').val();
                if(staff_num !== '' && leave_id !== ''){  
                    var self = this;
                    this._rpc({
                        route: `/get/leave-allocation/${leave_id}/${staff_num}`,
                        // params: {
                        //     'type': type
                        // },
                    }).then(function (data) {
                        console.log('retrieved staff leave data => '+ JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#leave_start_date").val('')//.trigger('change')
                            $("#leave_end_datex").val('')//.trigger('change')
                            $("#leave_remaining").val('')
                            alert(`Validation Error! ${data.message}`)
                        }else{
                            var number_of_days_display = data.data.number_of_days_display; 
                            console.log(number_of_days_display)
                            $("#leave_remaining").val(number_of_days_display)
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            }, 

            'blur input[name=leave_start_datex]': function(ev){
                let leave_remaining = $('#leave_remaining').val(); 
                let start_date = $(ev.target);
                let remain_days = leave_remaining !== undefined ? parseInt($('#leave_remaining').val()) : 1
                var selectStartLeaveDate = new Date(start_date.val());
                var endDate = new Date($('#leave_start_date').val()).getTime() + (1 * 24 * 60 * 60 * 1000);
                var maxDate = endDate + (21 * 24 * 60 * 60 * 1000)
                var st = `0${new Date(endDate).getMonth() + 1}/${new Date(endDate).getDate()}/${new Date(endDate).getFullYear()}`
                var end = `0${new Date(maxDate).getMonth() + 1}/${new Date(maxDate).getDate()}/${new Date(maxDate).getFullYear()}`
                triggerEndDate(st, end) 
            },
            'blur input[name=leave_end_datex]': function(ev){
                let leaveRemaining = $('#leave_remaining').val();
                console.log(`leaveRemaining IS : ${leaveRemaining}`)
                let start_date = $('#leave_start_date');
                let endDate = $(ev.target);
                var date1 = new Date(start_date.val());
                var date2 = new Date(endDate.val());
                var Difference_In_Time = date2.getTime() - date1.getTime();
                var Difference_In_Days = Difference_In_Time / (1000 * 3600 * 24);
                console.log(`Difference_In_Days IS : ${Difference_In_Days}`)
                if (Difference_In_Days > parseInt(leaveRemaining)){
                    $('#leave_end_datex').val("");
                    $('#leave_end_datex').attr('required', true);
                    alert(`You only have ${leaveRemaining} number of leave remaining for this leave type. Please Ensure the date range is within the available day allocated for you.`)
                    return true
                }
                else{
                    $('#leave_end_datex').attr('required', false);
                }
                checkOverlappingLeaveDate(this)
            },

            'change select[name=selectRequestOption]': function(ev){
                let selectedTarget = $(ev.target).val();
                $('#existing_ref_label').text("Existing Ref #");
                clearAllElement();
                if(selectedTarget == "leave_request"){
                    $('#leave_section').removeClass('d-none');
                    $('#leave_start_date').attr('required', true);
                    $('#leave_end_datex').attr('required', true);
                    $('#product_form_div').addClass('d-none');
                    // $('#product_ids').addClass('d-none');
                    // $('#product_ids').attr('required', false);
                    $('#amount_section').addClass('d-none');
                    $('#amount_fig').attr("required", false);
                }
                // else if($.inArray(selectedTarget, ["payment_request", "cash_advance"])){
                else if(selectedTarget == "payment_request"){
                    $('#amount_section').removeClass('d-none');
                    $('#amount_fig').attr("required", true);
                    console.log("request selected== ", selectedTarget);
                    displayNonLeaveElement()
                }
                // else if(selectedTarget == "cash_advance" || selectedTarget == "soe"){
                else if(selectedTarget == "cash_advance"){
                    $('#amount_section').removeClass('d-none');
                    $('#amount_fig').attr("required", true);
                    console.log("request selected== ", selectedTarget);
                    displayNonLeaveElement()
                    $('#product_form_div').removeClass('d-none');
                }

                else if(selectedTarget == "soe"){
                    $('#amount_section').removeClass('d-none');
                    $('#amount_fig').attr("required", true); 
                    displayNonLeaveElement()
                    $('#product_form_div').removeClass('d-none');
                    let existing_order = $(ev.target).val();
                    let selectTypeRequest = $('#selectTypeRequest');

                    if ($('#selectTypeRequest').val() == "new"){
                        if ($('#staff_id').val() == ""){
                            selectedTarget.val('').trigger('change')
                            alert("Please enter staff ID");
                        }
                        else{
                            $('#existing_order').attr('required', true);
                            $('#div_existing_order').removeClass('d-none');
                            $('#existing_ref_label').text("Cash Advance Ref #");
                            }
                    }
                }
                 
                else{
                    $('#amount_section').addClass('d-none');
                    $('#amount_fig').attr("required", false);
                    console.log("request selected");
                    displayNonLeaveElement();
                    $('#product_form_div').removeClass('d-none');
                    // $('.product_section').removeClass('d-none');
                    // $('#product_ids').attr('required', true);
                } 
            },

            'blur input[name=existing_order]': function(ev){
                let existing_order = $(ev.target).val();
                var selectRequestOption = $('#selectRequestOption');
                if(!selectRequestOption.val()){
                    alert('You must provide Request option!')
                    return false;
                }
                // if(existing_order !== '' && $('#staff_id').val() !== "" && $('#selectRequestOption').val() !== ""){  
                if(existing_order !== '' && $('#staff_id').val() !== ""){
                    var self = this;
                    var staff_num = $('#staff_id').val();
                    this._rpc({
                        route: `/check_order`,
                        params: {
                            'staff_num': staff_num,
                            'existing_order': existing_order,
                            'request_type': selectRequestOption.val(),
                        },
                    }).then(function (data) {
                        console.log('retrieved existing_order data => '+ JSON.stringify(data))
                        if (!data.status) {
                            $(ev.target).val('')
                            $("#existing_order").val('')
                            $("#phone_number").val('')
                            $("#email_from").val('')
                            $("#employee_id").val('')
                            $("#subject").val('')
                            $("#description").val('')
                            $("#amount_fig").val('')
                            $("#selectDistrict").val('')
                            $("#product_ids").val('').trigger('change')
                            $("#tbody_product").empty();
                            alert(`Validation Error! ${data.message}`)
                        }else{
                            var employee_name = data.data.name;
                            var email = data.data.work_email;
                            var phone = data.data.phone;   
                            var subject = data.data.subject; 
                            var description = data.data.description; 
                            var district_id = data.data.district_id; 
                            var request_date = data.data.request_date; 
                            var amount = data.data.amount; 
                            var state = data.data.state; 
                            var product_ids = data.data.product_ids; 
                            $("#phone_number").val(phone)
                            $("#email_from").val(email)
                            $("#employee_id").val(employee_name)
                            $("#subject").val(subject)
                            // $("#description").val(description)
                            $("#description").attr('required', false)
                            // $("#description").removeClass('required', false)
                            $("#selectDistrict").val(district_id).trigger('change')
                            $("#request_status").val(state)
                            $("#amount_fig").val(amount)
                            // $("#request_date").val(formatToDatePicker(request_date))
                            $("#request_date").val(request_date).trigger('change')
                            // let product_val = $('input[name="product_ids"]').val();
                            // building product items
                            if(state == "Draft"){
                                let product_val = [];
                                $.each(product_ids, function(k, elm){
                                    product_val.push(elm.id)
                                })
                                // $("#product_ids").val(product_val).trigger('change');
                                buildProductTable(product_ids, selectRequestOption.val());
                            }
                            if(selectRequestOption.val() == "soe"){
                                buildProductTable(product_ids, "soe", "required", "", "");
                            }
                            if(selectRequestOption.val() == "cash_advance"){
                                // make cash advance field required and displayed
                                buildProductTable(product_ids, "cash_advance", "", "", "readonly");
                            }  
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        $("#existing_order").val('')
                        alert(`Unknown Error! ${msg}`)
                    });
                }else{
                    alert("[Staff ID, Request option, Existing Ref # ] Must all be provideds")
                }
            },
            'change select[name=selectTypeRequest]': function(){
                // if new request type; hide existing order else reveal it
                let existing_order = $('#existing_order');
                let selectTypeRequest = $('#selectTypeRequest');
                clearAllElement();
                if (selectTypeRequest.val() == "new"){
                    console.log("hiding existing order")
                    existing_order.attr('required', false);
                    existing_order.val('')
                    $('#div_existing_order').addClass('d-none');
                }else if(selectTypeRequest.val() == "existing"){
                    if ($('#staff_id').val() == ""){
                        selectTypeRequest.val('')
                        alert("Please enter staff ID")
                    }
                    else{
                        existing_order.attr('required', true);
                        $('#div_existing_order').removeClass('d-none');
                        }
                }
                $('#product_form_div').removeClass('d-none');
            },

            'click .add_item_btn': function(ev){
                    ev.preventDefault();
                    $(ev.target).val()
                    var selectRequestOption = $('#selectRequestOption');
                    console.log("Building product row with form data=> ", setProductdata)
                    buildProductRow(selectRequestOption.val())
                },
            'click .search_panel_btn': function(ev){
                console.log("the search")
                var get_search_query = $("#search_input_panel").val()
                window.location.href = `/my/requests/param/${get_search_query}`
            },

            'click .button_req_submit': function (ev) {
                //// main event starts
                var list_of_fields = [];
                $('input,textarea,select').filter('[required]:visible').each(function(ev){
                    var field = $(this); 
                    if (field.val() == ""){
                        field.addClass('is-invalid');
                        console.log($(this).attr('labelfor'));
                        list_of_fields.push(field.attr('labelfor'));
                    }
                });
                if (list_of_fields.length > 0){
                    alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
                    return false;
                }else{
                    var current_btn = $(ev.target);
                    console.log('BUTTONMSZ is ==>', current_btn.text())
                    var form = $('#msform')[0];
                    // FormData object 
                    var formData = new FormData(form);
                    console.log('formData is ==>', formData)
                    var productItems = []
                    // $(`#tbody_product > tr.prod_row > th > input.productinput`).each(
                    //     function(){
                    //         let id = $(this).attr('id');
                    //         let qty = $(this).val();
                    //         if(setProductdata.includes(parseInt(id))){
                    //             let prod_data = {
                    //                 'product_id': id, 
                    //                 'qty': qty,
                    //             } 
                    //             productItems.push(prod_data)
                    //         }
                    //     }
                    // )
                    $(`#tbody_product > tr.prod_row > th > span > input`).each(
                        function(){
                            let product_id = $(this).attr('name') == "product_item_id" ? $(this).attr('id') : null;
                            let description = $(this).attr('name') == "description" ? $(this).attr('value') : null;
                            let request_qty = $(this).attr('productinput') == "productreqQty" ? $(this).attr('value') : null;
                            let amount_total = $(this).attr('name') == "amount_total" ? $(this).attr('value') : null;
                            let usedqty = $(this).attr('name') == "usedqty" ? $(this).attr('value') : null;
                            let usedAmount = $(this).attr('name') == "usedAmount" ? $(this).attr('value') : null;
                            let note_area = $(this).attr('name') == "note_area" ? $(this).attr('value') : null;
                            if(setProductdata.includes(parseInt(id))){
                                let prod_data = {
                                    'product_id': product_id, 
                                    'description': description,
                                    'qty': request_qty,
                                    'amount_total': amount_total,
                                    'used_qty': usedqty,
                                    'used_amount': usedAmount,
                                    'note': note_area,
                                } 
                                productItems.push(prod_data)
                            }
                        }
                    )
                    formData.append('productItems', JSON.stringify(productItems))
                    $.ajax({
                        type: "POST",
                        enctype: 'multipart/form-data',
                        url: "/portal_data_process",
                        data: formData,
                        processData: false,
                        contentType: false,
                        cache: false,
                        timeout: 800000,
                    }).then(function(data) {
                        console.log(`Recieving response from server => ${JSON.stringify(data)} and ${data} + `)
                        window.location.href = `/portal-success`;
                        console.log("XMLREQUEST Successful");
                    }).catch(function(err) {
                        console.log(err);
                        alert(err);
                    }).then(function() {
                        console.log("ANYTING")
                    })
                }
            }
         }

    });

    function clearAllElement(){ 
        // $('#phone_number').val('')
        // $('#email_from').val('')
        $('#subject').val('')
        $('#description').val('')
        $('#amount_fig').val('');
        $('#request_date').val('');
        $('#existing_order').val('');
        $('#request_status').val('');
        $('#product_ids').val('').trigger('change');
        $('#product_form_div').addClass('d-none');
        $('#tbody_product').empty();

    }

    var form = $('#msform')[0];
// return PortalRequestWidget;
});