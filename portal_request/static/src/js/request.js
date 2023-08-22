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
    
    function showAlertDialog(title, msg) {
        // Load the XML templates
        ajax.loadAsset('portal_request.portal_request', 'xml', '/portal_request/static/src/xml/partials.xml', {}, qweb).then(
            function (qweb) {
            // Templates loaded, you can now use them
                var wizard = qweb.render('portal_request.alert_dialogs', {
                    'msg': msg || _t('Message Body'),
                    'title': title || _t('Title')
                });
                wizard.appendTo($('body')).modal({
                    'keyboard': true
                });
            })
    }

    function buildProductTable(data){
        // data: data.data.assessor_ids
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
                        <th width="60%">
                            <span id=${elm.id}>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" class="form-control productitemrow" name="product_item_id" value=${elm.name}/>
                            </span>
                        </th>
                        <th width="20%">
                            <input type="text" name="${elm.qty}" id="${elm.id}" value="${elm.qty}" required="required" class="productinput form-control"/> 
                        </th>
                         
                        <th width="15%">
                            <a id="${lastRow_count}" remove_id="${lastRow_count}" name="${elm.id}" href="#" class="remove_field btn btn-primary btn-sm"> Remove </a>
                        </th>
                    </tr>`
                )
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

    function buildProductRow(){
        let lastRow_count = getOrAssignRowNumber()
        console.log(`lastrowcount ${lastRow_count}`)
        $(`#tbody_product`).append(
            `<tr class="heading prod_row" name="prod_row" row_count=${lastRow_count}>
                <th width="5%">
                    <span>
                        <input type="checkbox" class="productchecked"/>
                    </span>
                </th>
                <th width="60%">
                    <span>
                        <input special_id="${lastRow_count}" class="form-control productitemrow" name="product_item_id"/>
                    </span>
                </th>
                <th width="20%">
                    <input type="text" class="productinput form-control" required="required"/>
                </th>
                <th width="15%">
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
        // let SPECIAL_ID = $(`input[special_id=${lastRow_count}]`)
        // console.log('THE SPECIAL ID', SPECIAL_ID)
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

    function displayNonLeaveElement() {
        $('#leave_section').addClass('d-none');
        $('#leave_start_date').attr("required", false);
        $('#leave_end_date').attr("required", false);
        $('#product_form_div').addClass('d-none');
        $('#product_ids').addClass('d-none');
        $('#product_ids').attr("required", false);
        // $('.product_section').addClass('d-none');
        }

    function validate_empty_required_fields(){
        let list_of_fields = [];
        $('input,textarea,select').filter('[required]:visible').each(function(ev){
            // console.log($(this).val())
            let field = $(this); 
            if (field.val() == ""){
                field.addClass('is-invalid')
                console.log($(this).val())
                list_of_fields.push(field.text())
            }
            
        })
        if (length.list_of_fields > 0){
            alert('Validation: Please ensure the following fields are filled.. ', list_of_fields)
            return false 
        }
    }

    publicWidget.registry.PortalRequestWidgets = publicWidget.Widget.extend({
        selector: '#portal-request',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                $('.datepicker').datepicker('destroy').datepicker({
                    onSelect: function (ev) {
                        $('.datepicker').trigger('blur')
                    },
                    dateFormat: 'mm/dd/yy',
                    changeMonth: true,
                    changeYear: true,
                    yearRange: '2022:2050',
                    maxDate: "+0d"
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
            // 'blur input, select, textarea': function (ev) {
            //     let input = $(ev.target)
            //     if (input.is(":required") && input.val() !== '') {
            //         input.removeClass('is-invalid').addClass('is-valid')
            //     } else if (input.is(":required") && input.val() == '') {
            //         input.addClass('is-invalid')
            //     }
            // }, 

            'change .productitemrow': function(ev){
                let product_elm = $(ev.target);
                // let productStorage = JSON.parse(localStorage.getItem('productStorage'));
                // console.log('PRODUCT STORAGE ==> ', productStorage);
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
                qty_elm.attr('name', selectedproductQty);
                qty_elm.attr('value', selectedproductQty);
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
            'change select[name=selectRequestOption]': function(ev){
                let selectedTarget = $(ev.target).val();
                clearAllElement();
                if(selectedTarget == "leave_request"){
                    $('#leave_section').removeClass('d-none');
                    $('#leave_start_date').attr('required', true);
                    $('#leave_end_date').attr('required', true);
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
                else if(selectedTarget == "cash_advance"){
                    $('#amount_section').removeClass('d-none');
                    $('#amount_fig').attr("required", true);
                    console.log("request selected== ", selectedTarget);
                    displayNonLeaveElement()
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
                if(!$('#selectRequestOption').val()){
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
                                $("#product_ids").val(product_val).trigger('change');
                                buildProductTable(product_ids);
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
                    console.log("Building product row with form data=> ", setProductdata)
                    buildProductRow()
                }, 
            'click .button_req_submit': function (ev) {
                validate_empty_required_fields()
                var current_btn = $(ev.target);
                console.log('BUTTONMSZ is ==>', current_btn.text())

                var form = $('#msform')[0];
                // FormData object 
                var formData = new FormData(form);
                console.log('formData is ==>', formData)
                var productItems = []
                $(`#tbody_product > tr.prod_row > th > input.productinput`).each(
                    function(){
                        let id = $(this).attr('id');
                        let qty = $(this).val();
                        if(setProductdata.includes(parseInt(id))){
                            let prod_data = {'product_id': id, 'qty': qty}
                            productItems.push(prod_data)
                        }
                        
                    }
                )
                console.log('formData productitem is ==>', productItems)
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