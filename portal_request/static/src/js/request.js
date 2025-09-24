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
    const setEmployeedata = [];
    let alert_modal = $('#portal_request_alert_modal');
    let modal_message = $('#display_modal_message');
    if ($("#msform")[0] !== undefined){
        $("#msform")[0].reset();
    }

    const NonItemRequest = [
        'server_access', 
        'Payment',
        'leave_request',
        'employee_update'

    ];

    
    const ItemRequest = [
        'material_request', 
        'Procurement',
        'vehicle_request',
        'leave_request',
        'cash_advance',
        'soe',
    ];

    const productRequiredItems = [
        'material_request', 
        'Procurement',
        'vehicle_request',
    ];
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

    function setRecordStatus(targetElementId, setStatus){
        if(targetElementId !== ''){   
            let setState = setStatus
            this._rpc({
                route: `/my/request-state`,
                params: {
                    'type': setState,
                    'id': targetElementId
                },
            }).then(function (data) {
                if (!data.status) {
                    alert(`Validation Error! ${data.message}`)
                }else{
                    console.log('updating record to draft => '+ JSON.stringify(data))
                }
            }).guardedCatch(function (error) {
                let msg = error.message.message
                alert(`Unknown Error! ${msg}`)
            });
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

    function validateLineItems(DataItems){
        let memo_type_with_line = ['payment_request', 'Payment', 'material_request', 'soe', 'vehicle_request', 'procurement_request', 'employee_update', 'cash_advance'];
        // if the memo type in memo_type_with_line
        var selectRequestOption = $('#selectRequestOption'); 
        if ($.inArray(selectRequestOption.val(), memo_type_with_line) !== -1 && DataItems.length < 1){
            alert(`Validation: Please ensure Request line items are added`)
            return false;
        }else{
            return true;
        }
    }

    function displaytableProps(memo_type){
        // Hiding labels of the product row
        if(memo_type == 'vehicle_request'){
            $('#distance_from').removeClass('d-none');
            $('#distance_to').removeClass('d-none');
            $('#distance_from_th').removeClass('d-none');
            $('#distance_to_th').removeClass('d-none');

            $('#req_qty_label').addClass('d-none');
            $('#unit_price_label').addClass('d-none');
            $('#unit_sub_total').addClass('d-none');
            $('#sub_total_line').addClass('d-none');

            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');
            $('#note_label').addClass('d-none');

            $('#req_qty_label_th').addClass('d-none');
            $('#unit_price_label_th').addClass('d-none');
            $('#sub_total_amount_th').addClass('d-none');
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');
            $('#note_label_th').addClass('d-none');
        }
        // else if ($.inArray(memo_type, ['Payment']) !== -1){
        //     $('#used_qty_for_soe').addClass('d-none');
        //     $('#used_amount_for_soe').addClass('d-none');
        // }
        else if ($.inArray(memo_type, ['soe']) !== -1){
            $('#used_qty_for_soe_th').removeClass('d-none');
            $('#used_amount_for_soe_th').removeClass('d-none');
            $('#retirement_sub_total_th').removeClass('d-none');
            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');

            $('#used_qty_for_soe').removeClass('d-none');
            $('#used_amount_for_soe').removeClass('d-none');
            $('#retirement_sub_total').removeClass('d-none');

            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');
            
            $('#note_label_th').removeClass('d-none');
        }
        else if ($.inArray(memo_type, ['cash_advance']) !== -1){
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');

            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');

            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');

            $('#note_label_th').removeClass('d-none');
        }
        else if ($.inArray(memo_type, ['material_request']) !== -1){
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#distance_from').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#req_qty_label_th').removeClass('d-none');
            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');

            $('#unit_price_label').addClass('d-none');
            $('#unit_sub_total').addClass('d-none');
            $('#sub_total_line').addClass('d-none');

            $('#unit_price_label_th').addClass('d-none');
            $('#sub_total_amount_th').addClass('d-none');

            $('#note_label_th').removeClass('d-none');
        }else{
            $('#distance_from').addClass('d-none');
            $('#distance_to').addClass('d-none');
            $('#distance_from_th').addClass('d-none');
            $('#distance_to_th').addClass('d-none');
            $('#req_qty_label').removeClass('d-none');
            $('#unit_price_label').removeClass('d-none');
            $('#unit_sub_total').removeClass('d-none');
            $('#sub_total_line').removeClass('d-none');
            $('#used_qty_for_soe').addClass('d-none');
            $('#used_amount_for_soe').addClass('d-none');
            $('#retirement_sub_total').addClass('d-none');
            $('#used_qty_for_soe_th').addClass('d-none');
            $('#used_amount_for_soe_th').addClass('d-none');
            $('#retirement_sub_total_th').addClass('d-none');

            $('#note_label').removeClass('d-none');
            $('#req_qty_label_th').removeClass('d-none');
            $('#unit_price_label_th').removeClass('d-none');
            $('#sub_total_amount_th').removeClass('d-none');
            $('#note_label_th').removeClass('d-none');
        }
    }

    function buildProductTable(data, memo_type, require='', hidden='d-none', readon=''){
        $.each(data, function (k, elm) {
            if (elm) {
                var lastRow_count = getOrAssignRowNumber()
                console.log(`Building product table ${k} ${elm}`)
                $(`#tbody_product`).append(
                    `<tr class="heading prod_row" id="${elm.id}" name="prod_row" row_count=${lastRow_count}>
                        <th width="5%">
                            <span>
                                <input type="checkbox" readonly="readonly" class="productchecked" checked="" id="${elm.id}" name="${elm.qty}" code="${elm.request_line_id}"/>
                            </span>
                        </th>
                        <th width="20%">
                            <span id=${elm.id}>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" disabled="true" class="form-control productitemrow d-none" name="product_item_id" value=${elm.id} labelfor="Product Name - ${elm.name}"/>
                                <input id="${elm.id}" special_id="${lastRow_count}" readonly="readonly" disabled="true" class="form-control productitemrowx" name="product_item_idx" value=${elm.name} labelfor="Product Name - ${elm.name}"/>
                            </span>
                        </th>
                        <th width="10%">
                            <input type="textarea" placeholder="Start typing" name="description" readonly="readonly" disabled="true" id="desc-${lastRow_count}" desc_elm="" value="${elm.description}" class="DescFor form-control" labelfor="Note"/> 
                        </th>
                        <th width="5%">
                            <input type="number" pattern="[0-9\s]" min="1" productinput="productreqQty" name="${elm.qty}" id="${elm.id}" value="${elm.qty}" readonly="readonly" disabled="true" required="required" class="productinput form-control" labelfor="Request Quantity"/> 
                        </th>
                        <th width="10%">
                            <input type="number" name="amount_total" id="${elm.id}" value="${elm.amount_total}" readonly="readonly" disabled="true" amount_total="${elm.amount_total}" required="${memo_type == 'soe' ? '': 'required'}" class="productAmt form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Unit Amount"/> 
                        </th>
                        
                        <th width="10%">
                            <input type="text" name="sub_total_line" id="sub_total_line" value="${elm.sub_total_amount}" sub_total="${elm.sub_total_amount}" required="${require}" readonly="readonly" disabled="true" class="productSubTotal form-control ${hidden}" labelfor="unit_sub_total"/> 
                        </th>

                        <th width="10%">
                            <input type="text" name="usedqty" id="${elm.id-lastRow_count}" value="${elm.used_qty}" usedqty="${elm.used_qty}" required="${require}" class="productUsedQty form-control ${hidden}" labelfor="Used Quantity"/> 
                        </th>
                        <th width="10%">
                            <input type="text" name="usedAmount" id="${elm.used_amount-lastRow_count}" value="${elm.used_amount}" usedAmount="${elm.used_qty}" required="${memo_type == 'soe' ? 'required': ''}" class="productUsedAmt form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor=" Used Amount"/> 
                        </th>
                        <th width="10%" id="retirement_sub_total_th">
                            <input type="number" value="${elm.sub_total_amount}" name="retireSubTotal" id="${elm.sub_total_amount-lastRow_count}" main_name = "retireSubTotal" class="retireSubTotal${lastRow_count} form-control ${memo_type == 'soe' ? '': 'd-none'}}" labelfor="Retire Subtotal" readonly="true" disabled="true"/> 
                        </th>
                        <th width="45%">
                            <input type="textarea" name="note_area" id="${lastRow_count}" note_elm="" class="Notefor form-control ${hidden}" labelfor="Note"/> 
                        </th>
                        <th width="5%">
                            <a id="${lastRow_count}" remove_id="${lastRow_count}" name="${elm.id}" href="#" class="remove_field fa fa-trash-o p-3 ${memo_type == 'soe' ? 'd-none': ''}"></a>
                        </th>
                    </tr>`
                    
                )
                // ${memo_type=="cash_advance" || memo_type=="soe" ? 1: 0}
                // TriggerProductField(lastRow_count);
                // $(`input[special_id='${lastRow_count}'`).attr('readonly', true);
                setProductdata.push(elm.id)
            } else {
                console.log('-')
            }
        });
    }

    function buildProductRow(memo_type){ 
        // for new request: building each line of item 
        let lastRow_count = getOrAssignRowNumber()
        // console.log("what is memo type ==", memo_type)
        // console.log(`lastrowcount ${lastRow_count}`)
        $(`#tbody_product`).append(
            `<tr class="heading prod_row" name="prod_row" row_count=${lastRow_count}>
                <th width="5%">
                    <span>
                        <input type="checkbox" class="productchecked" code=""/>
                    </span>
                </th>
                <th width="25%">
                    <span>
                        <input special_id="${lastRow_count}" class="form-control productitemrow" name="product_item_id" required="${memo_type == 'cash_advance' ? '': 'required'}" labelfor="Product Name"/>
                    </span>
                </th>
                <th width="20%">
                    <textarea placeholder="Start typing" name="description" id="${lastRow_count}" desc_elm="" required="${memo_type == 'cash_advance' ? 'required': ''}" class="DescFor form-control" labelfor="Description"/> 
                </th>
                <th width="10%" id="req_qty_label_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none': ''}">
                    <input type="number" pattern="[0-9\s]" productinput="productreqQty" class="productinput form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none': ''} QTY${lastRow_count}" required="${$.inArray(memo_type, ['vehicle_request']) == 2 ? '': 'required'}" labelfor="Requested Quantity" min="1" row_count="${lastRow_count}"/>
                </th>
                <th width="15%" id="unit_price_label_th" class="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none': ''}">
                    <input type="number" value="1" name="amount_total" id="amount_totalx-${lastRow_count}-id" required="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? '': 'required'}" class="productAmt form-control ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none': ''} AmounTotal${lastRow_count}" labelfor="Unit Price" row_count="${lastRow_count}"/> 
                </th>
                <th width="15%" id="sub_total_amount_th" class="sub_total_amount ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none': ''}">
                    <input type="number" value="0" name="sub_total_amount" id="sub_amount_totalx-${lastRow_count}-id" main_name = "sub_total_amount" required="${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? '': 'required'}" class="sub_total_amount form-control ${$.inArray(memo_type, ['soe', 'material_request', 'vehicle_request']) !== -1 ? 'd-none': ''} SUBTOTAL${lastRow_count}" labelfor="Subtotal" readonly="true" disabled="true"/> 
                </th>
                <th width="5%" id="used_qty_for_soe_th" class="${memo_type == 'soe' ? '': 'd-none'}"> 
                    <input type="text" name="usedQty-${lastRow_count}" id="usedQty-${lastRow_count}-id" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '': 'readonly'}" class="productUsedQty form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Used Quantity"/> 
                </th>
                <th width="10%" id="used_amount_for_soe_th" class="${memo_type == 'soe' ? '': 'd-none'}">
                    <input type="number" name="UsedAmount" id="amounttUsed-${lastRow_count}" used_amount="UsedAmount-${lastRow_count}" required="${memo_type == 'soe' ? 'required': ''}" readonly="${memo_type == 'soe' ? '': 'readonly'}" class="productSoe form-control ${memo_type == 'soe' ? '': 'd-none'}" labelfor="Used Amount"/> 
                </th>
                
                <th width="10%" id="note_label_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none': ''}">
                    <textarea rows="2" name="note_area" id="${lastRow_count}" note_elm="" class="Notefor form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? 'd-none': ''}" labelfor="Note"/> 
                </th>
                 
                <th width="10% id="distance_from_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '': 'd-none'}">
                    <textarea placeholder="Start typing" name="distance_from" id="${lastRow_count}" desc_elm="" required="${memo_type == 'vehicle_request' ? 'required': ''}" class="DistanceFrom form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '': 'd-none'}" labelfor="Distance From"/> 
                </th>
                <th width="10%" id="distance_to_th" class="${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '': 'd-none'}">
                    <textarea placeholder="Start typing" name="distance_to" id="${lastRow_count}" desc_elm="" required="${memo_type == 'vehicle_request' ? 'required': ''}" class="Distanceto form-control ${$.inArray(memo_type, ['vehicle_request']) !== -1 ? '': 'd-none'}" labelfor="Distance To"/> 
                </th>

                <th width="5%">
                    <a id="${lastRow_count}" remove_id="${lastRow_count}" href="#" class="remove_field fa fa-trash-o p-3"></a>
                </th>
            </tr>`
        )
        TriggerProductField(lastRow_count)
        $('textarea').autoResize();
        scrollTable(); // used to scroll to the next level when add a line
    }

    function buildEmployeeRow(memo_type){ 
        // used to build employee lines for promotion and transfers
        let lastRow_count = getOrAssignRowNumber(memo_type)
        // console.log("what is memo type ==", memo_type)
        // console.log(`lastrowcount ${lastRow_count}`)
        $(`#tbody_employee`).append(
            `<tr class="heading employee_row" name="employee_row" row_count=${lastRow_count}>
                <th width="5%">
                    <span>
                        <input type="checkbox" class="employeechecked" code=""/>
                    </span>
                </th>
                <th width="35%">
                    <span>
                        <input employee_line_id="" employee_special_id="${lastRow_count}" class="form-control employeeitemrow" name="employee_item_id" required="required" labelfor="Employee Name"/>
                    </span>
                </th>
                <th width="20%">
                    <span>
                        <input department_line_id="" department_special_id="${lastRow_count}" class="form-control" name="department_item_id" required="required" labelfor="Department Name"/>
                    </span>
                </th>

                <th width="20%">
                    <span>
                        <input role_line_id="" role_special_id="${lastRow_count}" class="form-control" name="role_item_id" required="required" labelfor="Role"/>
                    </span>
                </th>
                <th width="20%">
                    <span>
                        <input district_line_id="" district_special_id="${lastRow_count}" class="form-control districtitemrow" name="district_item_id" required="required" labelfor="District"/>
                    </span>
                </th>  
                <th width="5%">
                    <a href="#" id="" employee_remove_id="${lastRow_count}" class="employee_remove_field fa fa-trash-o p-3"></a>
                </th>
            </tr>`
        )
        TriggerEmployeeData(lastRow_count)
        // $('textarea').autoResize();
        scrollTable(); // used to scroll to the next level when add a line
    }

    localStorage.setItem('SelectedProductItems', "[]")

    function getSelectedProductItems(){
        let products = JSON.parse(localStorage.getItem('SelectedProductItems'));
        // console.log("Products store is ", products)
        return products
    }

    var formatCurrency = function(value) {
        if (value) {
            return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")

        }
    }

    function getAmountQtyProcess(objVal, attrs, targetEv) {
        let result = 0
        // console.log(`val res ${objVal}`)

        if(attrs == targetEv){
            // console.log(`element attributes ${attrs}`)
            result = Number(objVal)
            // console.log(`what is result ${result}`)
            return result;
        }
        return result;
      }
 
    var compute_total_amount = function(targetEv){
        // targetEv: amount_total or usedAmount
        // GOES THROUGH EACH TR >TABLE ROW, LOOP AGAIN TO GET THE ...
        // request quantity and total amount and give the result of subtotal 
        // used qty and used amount and give the total of retirement subtotal 
        var targetEv = $('#selectRequestOption').val() == "soe" ? "usedAmount" : "amount_total"
        var total = 0
        $(`#tbody_product > tr.prod_row`).each(function(){
            var row_co = $(this).attr('row_count')
            var amount = 0
            var qty = 0
            var amt = false
            var r_amt = false
            var rt_amt = false
            var r_qty = false
            var subtotal = false
            $(`tr[row_count=${row_co}]`).closest(":has(input)").find('input').each(
                function(){
                    if($(this).attr('name') == targetEv){
                        amount = Number($(this).val())
                    }
                    if($(this).attr('productinput') == 'productreqQty'){
                        qty = Number($(this).val())
                    }
                    if($(this).attr('name') == 'usedqty'){
                        r_qty = Number($(this).val())
                    }
                    if($(this).attr('name') == 'usedAmount'){
                        r_amt = Number($(this).val())
                    }
                    amt = amount * qty
                    rt_amt = r_amt * r_qty
                }
            )
            total += amt
            $(`.SUBTOTAL${row_co}`).val(amt)
            $(`.SUBTOTAL${row_co}`).addClass('is-invalid', true);
            $(`.retireSubTotal${row_co}`).val(rt_amt)
        })
        var amount = formatCurrency(total)
        $('#all_total_amount').text(`${amount != undefined ? amount : 0.0}`)
    }

    function getOrAssignRowNumber(memo_type=false){
        var lastRow_count = 0
        // $(`#tbody_product > tr.prod_row > th > input.productitemrow`)[0].each(
        var lastElement = memo_type !== 'employee_update' ? $(`#tbody_product > tr.prod_row > th > span > input.productitemrow`) : $(`#tbody_employee > tr.employee_row > th > span > input.employeeitemrow`) 
        if (lastElement){
            let special_id = memo_type !== 'employee_update' ? lastElement.last().attr('special_id') : lastElement.last().attr('employee_special_id');
            lastRow_count = special_id ? parseInt(special_id) + 1 : lastRow_count + 1
        }else {
            lastRow_count + 1
        }
         
        return lastRow_count
    }

    $.fn.autoResize = function(){
        let r = e => {
          e.style.height = '';
          e.style.width = '';
          e.style.height = e.scrollHeight + 'px'
          e.style.width = e.scrollWidth + 'px'
        };
        return this.each((i,e) => {
          e.style.overflow = 'hidden';
          r(e);
          $(e).bind('input', e => {
            r(e.target);
          })
        })
      };
      $('textarea').autoResize();
     
    var scrollTable = function(){
        var i = 1;
        if (i < $(`#tbody_product tr`).length) {
            let position = $(`#tbody_product tr:eq(${i})`).offset().top;
            $('#attachment_table').stop().animate({
              scrollTop: $('#attachment_table').scrollTop() + position
            }, 300);
            i++
          } else {
            i = 0
          }
        // $('#attachment_table').stop().animate({
        //     scrollTop: '+=60px' // 40px can be the height of a row
        // }, 200);
    }

    function TriggerEmployeeData(lastRow_count){
        $(`input[employee_special_id='${lastRow_count}'`).select2({
            ajax: {
              url: '/portal-request-employee',
              dataType: 'json',
              delay: 250,
              data: function (term, page) {
                return {
                  q: term, //search term
                  employeeItems: JSON.stringify(setEmployeedata), 
                  request_type: 'employee', 
                  page_limit: 10, // page size
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                // console.log(data);
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a employee',
            allowClear: false,
          });
        
          $(`input[department_special_id='${lastRow_count}'`).select2({
            ajax: {
              url: '/portal-request-employee',
              dataType: 'json',
              delay: 250,
              data: function (term, page) {
                return {
                  q: term, //search term
                  request_type: 'department', 
                  page_limit: 10, // page size
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                // console.log(data);
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a department',
            allowClear: false,
          });

          $(`input[role_special_id='${lastRow_count}'`).select2({
            ajax: {
              url: '/portal-request-employee',
              dataType: 'json',
              delay: 250,
              data: function (term, page) {
                return {
                  q: term, //search term
                  request_type: 'role', 
                  page_limit: 10, // page size
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                // console.log(data);
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a job role',
            allowClear: false,
          });

          $(`input[district_special_id='${lastRow_count}'`).select2({
            ajax: {
              url: '/portal-request-employee',
              dataType: 'json',
              delay: 250,
              data: function (term, page) {
                return {
                  q: term, //search term
                  request_type: 'district', 
                  page_limit: 10, // page size
                  page: page, // page number
                };
              },
              results: function (data, page) {
                var more = (page * 30) < data.total;
                // console.log(data);
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 1,
            multiple: false,
            placeholder: 'Search for a district',
            allowClear: false,
          });
    }

    function TriggerProductField(lastRow_count){
        // PRODUCTSEARCH
        $(`input[special_id='${lastRow_count}']`).select2({
            ajax: {
              url: '/portal-request-product',
              dataType: 'json',
              delay: 30,
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
                // console.log(data);
                // localStorage.setItem('productStorage', JSON.stringify(data.results))
                return {results: data.results, more: more};
              },
              cache: true
            },
            minimumInputLength: 2,
            multiple: false,
            placeholder: 'Search for a Products',
            allowClear: true,
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

    $('#leave_reliever').select2({
        ajax: {
            url: '/portal-request-employee-reliever',
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
        minimumInputLength: 3,
        multiple: false,
        placeholder: 'Search for a reliever',
        allowClear: true,
    });

    $('#inputFollowers').select2({
        ajax: {
            url: '/portal-request-employee-reliever',
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
        minimumInputLength: 3,
        multiple: true,
        placeholder: 'Search for followers',
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
                        let message = `Validation Error! ${data.message}`
                        // console.log("not Passed for leave, ", message)
                        // alert(message); 
                        // return false
                        modal_message.text(message)
                        alert_modal.modal('show');

                    }else{
                        console.log("--")
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
    }

    function displayNonLeaveElement() {
        $('#leave_section').addClass('d-none');
        $('#leave_section2').addClass('d-none');
        $('#leave_start_date').attr("required", false);
        $('#leave_end_datex').attr("required", false);
        $('#leave_reliever').attr('required', false);
        $('#leave_reliever').val('');
        $('#leave_type_id').attr('required', false);
        $('#product_form_div').addClass('d-none');
        $('#product_ids').addClass('d-none');
        $('#product_ids').attr("required", false); 
        $('#divEmployeeData').addClass('d-none');
        $('#selectEmployeedata').attr("required", false); 
        $('#employee_item_form_div').addClass('d-none');
        }
    
    function makefieldsReadonly(readable=true){
            if (readable){
                $('#employed_id').attr("readonly", true); 
                $('#phone_number').attr("readonly", true); 
                $('#email_from').attr("readonly", true); 
            }else{
                $('#employed_id').attr("readonly", false); 
                $('#phone_number').attr("readonly", false); 
                $('#email_from').attr("readonly", false); 
            }
        }
 
    $('#leave_start_date').datepicker('destroy').datepicker({
        onSelect: function (ev) {
            $('#leave_start_date').trigger('blur')
        },
        dateFormat: 'mm/dd/yy',
        changeMonth: true,
        changeYear: true,
        yearRange: '2023:2050',
        maxDate: null,
        minDate: new Date(),
        // Disable Saturday (6) & Sunday (0)
        beforeShowDay: function (date) {
            var day = date.getDay();
            return [(day != 0 && day != 6), ''];
        }
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
            // Disable Saturday (6) & Sunday (0)
            beforeShowDay: function (date) {
                var day = date.getDay();
                return [(day != 0 && day != 6), ''];
            }
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

                $('#request_end_date').datepicker('destroy').datepicker({
                    onSelect: function (ev) {
                        $('#request_end_date').trigger('blur')
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
                console.log("ERP event has started")
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
                var link = product_elm.closest(":has(input.productinput)").find('input.productinput');
                var remove_link = product_elm.closest(":has(a.remove_field)").find('a.remove_field');
                link.attr('id', product_val);
                remove_link.attr('id', product_val);
                setProductdata.push(parseInt(product_val));
                // console.log('sele ==> ', setProductdata) 
            },

            'change .employeeitemrow': function(ev){
                let employee_elm = $(ev.target);
                let employee_val = employee_elm.val();
                var link = employee_elm.closest(":has(input.employeeinput)").find('input.employeeinput');
                var remove_link = employee_elm.closest(":has(a.employee_remove_field)").find('a.employee_remove_field');
                link.attr('id', employee_val);
                remove_link.attr('id', employee_val);
                setEmployeedata.push(parseInt(employee_val));
            },
            'click .remove_field': function(ev){
                let elm = $(ev.target);
                let elm_remove_id = elm.attr('remove_id'); 
                elm.closest(":has(tr.prod_row)").find('tr.prod_row').each(function(ev){
                    if($(this).attr('row_count') == elm_remove_id){
                        let remove_element_id = elm.attr('id'); 
                        setProductdata.splice(setProductdata.indexOf(remove_element_id),1)
                        // console.log(`See it ${$.inArray(remove_element_id, setProductdata)}}`)
                        // console.log('SEE PRD ', setProductdata)
                        $(this).remove();
                        compute_total_amount();
                    }
                });
            }, 

            'click .employee_remove_field': function(ev){
                let elm = $(ev.target);
                let elm_remove_id = elm.attr('employee_remove_id'); 
                elm.closest(":has(tr.employee_row)").find('tr.employee_row').each(function(ev){
                    if($(this).attr('row_count') == elm_remove_id){
                        let remove_element_id = elm.attr('id'); 
                        setEmployeedata.splice(setEmployeedata.indexOf(remove_element_id),1)
                        $(this).remove();
                    }
                });
            },
 
            'change .productAmt': function(ev){
                //computation of the total unit price
                compute_total_amount();
                // compute_sub_total($(this).attr('row_count'), $(this).val());
            },
            'change .productUsedAmt': function(ev){
                //computation of the total productUsedQty unit price
                compute_total_amount();
            },

            'change .productUsedQty': function(ev){
                //computation of the total productUsedQty unit price
                compute_total_amount();
            },

            // $('#inactivelist').change(function () {
            //     alert('changed');
            //  });

            'change .otherChangeOption': function(ev){
                if ($(ev.target).is(':checked')){
                    $('#div_other_system_details').removeClass('d-none');
                    $('#other_system_details').attr('required', true);
                    // $('#other_system_details').addClass("is-invalid");
                }
                else {
                    $('#div_other_system_details').addClass('d-none');
                    $('#other_system_details').attr('required', false);
                    $('#other_system_details').val('');
                    // $('#other_system_details').addClass("is-valid");
                }
            },

            'change .productinput': function(ev){
                // assigning the property: name of quantity field as the quantity selected
                let qty_elm = $(ev.target);
                let productinput_rowcount = qty_elm.attr('row_count');
                $(`.SUBTOTAL${productinput_rowcount}`).val('')
                $(`.AmounTotal${productinput_rowcount}`).val('')
                $(`.SUBTOTAL${productinput_rowcount}`).removeClass('is-invalid', true);

                let selectedproductQty = qty_elm.val(); 
                let request_type = $("#selectRequestOption").val()
                // console.log('THE REQUEST TYPE IS ==> ', request_type)
                if ($.inArray(request_type, productRequiredItems) !== -1){
                    // console.log('THE REQUEST TYPE IS 2222 ==> ', request_type)
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
                            compute_total_amount();
                            $('#TargetSourceLocation').val(data.location_id)
                        }
                    })
                }
            },

            'blur input[name=staff_id]': function(ev){
                let staff_num = $(ev.target).val();
                if(staff_num !== ''){  
                    var self = this;
                    this._rpc({
                        route: `/check_staffid`, ///${staff_num}`,
                        params: {
                            //'type': type
                            'staff_num': staff_num
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
                        route: `/get/leave-allocation`, ///${leave_id}/${staff_num}`,
                        params: {
                            'staff_num': staff_num.trim(),
                            'leave_id': leave_id
                        },
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
                            $("#leave_remain").text(number_of_days_display)
                        }
                    }).guardedCatch(function (error) {
                        let msg = error.message.message
                        console.log(msg)
                        alert(`Unknown Error! ${msg}`)
                    });
                }
            },  

            'blur input[name=leave_start_datex]': function(ev){
                if ($('#leave_type_id').val() == ""){
                    let message = `Validation Error! Please ensure to select Leave type`
                    $('#leave_start_datex').val('');
                    $('#leave_end_datex').val('');
                    modal_message.text(message)
                    alert_modal.modal('show');

                }
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
                    alert(`You only have ${leaveRemaining} number of leave remaining 
                        for this leave type. Please Ensure the date range is within the available 
                        day allocated for you.`)
                    return true
                }
                else{
                    $('#leave_end_datex').attr('required', false);
                    $('#leave_end_datex').attr('required', false);
                    endDate.removeClass('is-invalid').addClass('is-valid');
                    $('#leave_taken').text(Difference_In_Days)
                }
                checkOverlappingLeaveDate(this)
            }, 

            'change #leave_reliever': function(ev){
            // 'blur input[name=leave_reliever]': function(ev){
                let leave_reliever = $('#leave_reliever');
                let start_date = $('#leave_start_date');
                if (!start_date.val() && leave_reliever.val() !== ""){
                    $('#leave_reliever').val('').trigger('change');
                    let message = `Validation Error! Please provide leave start date`
                    modal_message.text(message)
                    alert_modal.modal('show');
                }
                else{
					console.log("THE TODLE POL")
					if ($('#selectRequestOption').val() == "leave_request" && leave_reliever.val() !== ""){
						this._rpc({
							route: `/check-employee-still-onleave`,
							params: {
								'employee_id': leave_reliever.val(),
								'start_date': $('#leave_start_date').val(),
								'end_date': $('#leave_end_datex').val(),
							},
						}).then(function (data) { 
							if (!data.status) {
                                $('#leave_reliever').val('0').trigger('change');
								leave_reliever.addClass('is-invalid', true);
								let message = `Validation Error! ${data.message}`
								console.log("Employee has leave already", message)
								modal_message.text(message)
								alert_modal.modal('show');
							}else{
								console.log("---")
							}
						}).guardedCatch(function (error) {
							let msg = error.message.message
							console.log(msg)
							leave_reliever.val('')
							let message = `Unknown Error! ${msg}`
							modal_message.text(message)
							alert_modal.modal('show');
							return false;
						});
					}
                }
            }, 
            
            'change select[name=selectRequestOption]': function(ev){
                let selectedTarget = $(ev.target).val();
                $('#existing_ref_label').text("Existing Ref #");
                $('#div_existing_order').addClass('d-none');
                clearAllElement();
                let self = this;
                // checkConfiguredStages(this, selectedTarget);
                let staff_num = $('#staff_id').val();
                this._rpc({
                    route: `/check-configured-stage`,
                    params: {
                        'staff_num': staff_num,
                        'request_option': selectedTarget,
                    },
                }).then(function (data) {
                    console.log('checking if stage is configured => '+ JSON.stringify(data))
                    if (!data.status) {
                        $('#selectRequestOption').val('')
                        // alert(`Validation Error! ${data.message}`)
                        let message = `Validation Error! ${data.message}`
                        modal_message.text(message)
                        alert_modal.modal('show');
                    }
                    else{
                         // set the value of selected option to the hidden field
                        let sro = $('#selectRequestOption option:selected')[0].getAttribute("id");
                        $('#selectedRequestOptionId').val(Number(sro));
                        // $('#selectConfigOptionId').val(Number(sro));
                        if(selectedTarget == "leave_request"){
                            console.log('Yes leave is selected')
                            $('#leave_section').removeClass('d-none');
                            $('#leave_section2').removeClass('d-none');
                            $('#leave_start_date').attr('required', true);
                            $('#leave_type_id').attr('required', true);
                            $('#leave_end_datex').attr('required', true);
                            $('#leave_reliever').attr('required', true);
                            $('#product_form_div').addClass('d-none');
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            let main = $('#leave_reliever').prop('required');
				            console.log('WHAT IS LEAVE RELIEVER', main)

                        }
                        else if(selectedTarget == "server_access"){
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').removeClass('d-none');
                            $('#div_system_requirement').removeClass('d-none');
                            $('#request_end_date').removeClass('d-none');
                            $('#request_end_date').attr('required', true);
                            $('#labelDescription').text('Resource Details (IP Adress/Server Name/Database');
                            $('#div_justification_reason').removeClass('d-none');
                            $('#justification_reason').attr('required', true);
                            // $('#justification_reason').addClass("is-valid");
                            $('#justification_reason').removeClass("d-none");
                            console.log("server request selected == ", selectedTarget);
                            displayNonLeaveElement()
                        }
                        else if(selectedTarget == 'employee_update'){
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').addClass('d-none');
                            $('#div_system_requirement').addClass('d-none');
                            $('#request_end_date').addClass('d-none');
                            $('#request_end_date').attr('required', false);
                            $('#labelDescription').text('Description');
                            $('#div_justification_reason').addClass('d-none');
                            $('#justification_reason').attr('required', false);
                            $('#divEmployeeData').removeClass('d-none');
                            $('#selectEmployeedata').attr('required', true);
                            $('#employee_item_form_div').removeClass('d-none');
                            
                        }
                        // else if($.inArray(selectedTarget, ["Payment", "cash_advance"])){
                        else if(selectedTarget == "Payment"){
                            $('#amount_section').removeClass('d-none');
                            $('#amount_fig').attr("required", true);
                            console.log("request selected== ", selectedTarget);
                            displayNonLeaveElement()
                        }
                        // else if(selectedTarget == "cash_advance" || selectedTarget == "soe"){
                        else if(selectedTarget == "cash_advance"){
                            var staff_num = $('#staff_id').val();
                            self._rpc({
                                route: `/check-cash-retirement`,
                                params: {
                                    'staff_num': staff_num,
                                    'request_type': selectedTarget,
                                },
                            }).then(function (data) {
                                console.log('retrieved cash advance data => '+ JSON.stringify(data))
                                if (!data.status) {
                                    $(ev.target).val('');
                                    $("#amount_fig").val('')
                                    $('#amount_section').addClass('d-none');
                                    $('#product_form_div').addClass('d-none');
                                    $('.add_item').addClass('d-none')
                                    alert(`Validation Error! ${data.message}`)
                                }else{
                                    // $('#amount_section').removeClass('d-none');
                                    // $('#amount_fig').attr("required", false);
                                    console.log("request selected== ", selectedTarget);
                                    displayNonLeaveElement()
                                    $('#product_form_div').removeClass('d-none');
                                    $('.add_item').removeClass('d-none');
                                }
                            }).guardedCatch(function (error) {
                                let msg = error.message.message
                                console.log(msg)
                                $("#amount_fig").val('')
                                $('#amount_section').addClass('d-none');
                                $('#product_form_div').addClass('d-none');
                                alert(`Unknown Error! ${msg}`)
                            }); 
                        }
                        else if(selectedTarget == "soe"){
                            // $('#amount_section').removeClass('d-none');
                            // $('#amount_fig').attr("required", true); 
                            displayNonLeaveElement()
                            $('.add_item').addClass('d-none')
                            $('#product_form_div').removeClass('d-none'); 
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
                        }
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    console.log(msg)
                    $("#selectRequestOption").val('')
                    alert(`Unknown Error! ${msg}`)
                });
            },

            'change select[name=selectConfigOption]': function(ev){
                // let selectedTarget = $(ev.target).val();
                let selectedTarget = $(ev.target);
                let sro = $('#selectConfigOption option:selected')[0]
                $('#existing_ref_label').text("Existing Ref #");
                $('#div_existing_order').addClass('d-none');
                clearAllElement();
                let self = this;
                // checkConfiguredStages(this, selectedTarget);
                let staff_num = $('#staff_id').val();
                this._rpc({
                    route: `/check-configured-stage`,
                    params: {
                        'staff_num': staff_num,
                        'request_config_option': selectedTarget.val(),
                    },
                }).then(function (data) {
                    console.log('checking if stage is configured => '+ JSON.stringify(data))
                    if (!data.status) {
                        $('#selectConfigOption').val('')
                        // alert(`Validation Error! ${data.message}`)
                        let message = `Validation Error! ${data.message}`
                        modal_message.text(message)
                        alert_modal.modal('show');
                    }
                    else{
                         // set the value of selected option to the hidden field
                        let memo_config_id = sro.getAttribute("id");
                        let memo_type_id = sro.getAttribute("memo_key_id");
                        let memo_type_key = sro.getAttribute("memo_type_key");
                        $('#selectConfigOptionId').val(Number(memo_config_id));
                        $('#selectedRequestOptionId').val(Number(memo_type_id));
                        $('#selectRequestOption').val(memo_type_key);

                        if(memo_type_key == "leave_request"){
                            console.log('Yes leave is selected')
                            $('#leave_section').removeClass('d-none');
                            $('#leave_section2').removeClass('d-none');
                            $('#leave_start_date').attr('required', true);
                            $('#leave_type_id').attr('required', true);
                            $('#leave_end_datex').attr('required', true);
                            $('#product_form_div').addClass('d-none');
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                        }
                        else if(memo_type_key == "server_access"){
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').removeClass('d-none');
                            $('#div_system_requirement').removeClass('d-none');
                            $('#request_end_date').removeClass('d-none');
                            $('#request_end_date').attr('required', true);
                            $('#labelDescription').text('Resource Details (IP Adress/Server Name/Database');
                            $('#div_justification_reason').removeClass('d-none');
                            $('#justification_reason').attr('required', true);
                            // $('#justification_reason').addClass("is-valid");
                            $('#justification_reason').removeClass("d-none");
                            console.log("server request selected == ", memo_type_key);
                            displayNonLeaveElement()
                        }
                        else if(memo_type_key == 'employee_update'){
                            $('#amount_section').addClass('d-none');
                            $('#amount_fig').attr("required", false);
                            $('#product_form_div').addClass('d-none');
                            $('#label_end_date').addClass('d-none');
                            $('#div_system_requirement').addClass('d-none');
                            $('#request_end_date').addClass('d-none');
                            $('#request_end_date').attr('required', false);
                            $('#labelDescription').text('Description');
                            $('#div_justification_reason').addClass('d-none');
                            $('#justification_reason').attr('required', false);
                            $('#divEmployeeData').removeClass('d-none');
                            $('#selectEmployeedata').attr('required', true);
                            $('#employee_item_form_div').removeClass('d-none');
                            
                        }
                        // else if($.inArray(selectedTarget, ["Payment", "cash_advance"])){
                        else if(memo_type_key == "Payment"){
                            // $('#amount_section').removeClass('d-none');
                            // $('#amount_fig').attr("required", true);
                           
                            console.log("request selected== ", memo_type_key);
                            displayNonLeaveElement()
                             $('#PaymentcashAdvanceDiv').removeClass('d-none');
                            $('#PaymentcashAdvanceLabel').removeClass('d-none');
                            $('#product_form_div').removeClass('d-none');
                            $('.add_item').removeClass('d-none');
                        }
                        // else if(selectedTarget == "cash_advance" || selectedTarget == "soe"){
                        else if(memo_type_key == "cash_advance"){
                            var staff_num = $('#staff_id').val();
                            self._rpc({
                                route: `/check-cash-retirement`,
                                params: {
                                    'staff_num': staff_num,
                                    'request_type': memo_type_key,
                                },
                            }).then(function (data) {
                                console.log('retrieved cash advance data => '+ JSON.stringify(data))
                                if (!data.status) {
                                    $(ev.target).val('');
                                    $("#amount_fig").val('')
                                    $('#amount_section').addClass('d-none');
                                    $('#product_form_div').addClass('d-none');
                                    $('.add_item').addClass('d-none')
                                    alert(`Validation Error! ${data.message}`)
                                }else{
                                    // $('#amount_section').removeClass('d-none');
                                    // $('#amount_fig').attr("required", false);
                                    console.log("request selected== ", selectedTarget);
                                    displayNonLeaveElement()
                                    $('#product_form_div').removeClass('d-none');
                                    $('.add_item').removeClass('d-none');
                                }
                            }).guardedCatch(function (error) {
                                let msg = error.message.message
                                console.log(msg)
                                $("#amount_fig").val('')
                                $('#amount_section').addClass('d-none');
                                $('#product_form_div').addClass('d-none');
                                alert(`Unknown Error! ${msg}`)
                            }); 
                        }
                        else if(memo_type_key == "soe"){
                            // $('#amount_section').removeClass('d-none');
                            // $('#amount_fig').attr("required", true); 
                            displayNonLeaveElement()
                            $('.add_item').addClass('d-none')
                            $('#product_form_div').removeClass('d-none'); 
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
                        }
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    console.log(msg)
                    $("#selectConfigOptionId").val('')
                    $("#selectedRequestOptionId").val('')
                    $("#selectRequestOption").val('')
                    alert(`Unknown Error! ${msg}`)
                });
            },

            'blur input[name=existing_order]': function(ev){
                let existing_order = $(ev.target).val();
                var selectRequestOption = $('#selectRequestOption');
                var selectConfigOptionId = $('#selectConfigOptionId');
                if(!selectConfigOptionId.val()){
                    alert('You must provide Request option!')
                    return false;
                }
                // if(!selectRequestOption.val()){
                //     alert('Request option type not selected!')
                //     return false;
                // }
                // if(existing_order !== '' && $('#staff_id').val() !== "" && $('#selectRequestOption').val() !== ""){  
                if(existing_order !== '' && $('#staff_id').val() !== ""){
                    var self = this;
                    var staff_num = $('#staff_id').val();
                    console.log(`THIS IS MY TEST ${staff_num} -- ${existing_order} --- ${selectRequestOption.val()}`)
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
                        console.log('retrieved existing_order link => '+ data.link)

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
                            alert(`Validation Error!${data.message}`)
                            if (data.link){
                                // window.location.href = data.link
                                window.open(data.link, '_blank');
                            }
                        }else{
                            var employee_name = data.data.name;
                            var email = data.data.work_email;
                            var phone = data.data.phone;   
                            var subject = data.data.subject; 
                            var description = data.data.description; 
                            // var district_id = data.data.district_id; 
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
                            // $("#selectDistrict").val(district_id).trigger('change')
                            $("#request_status").val(state)
                            $("#amount_fig").val(formatCurrency(amount))
                            $('#amount_fig').attr("readonly", false); 
                            $("#request_date").val(request_date).trigger('change')
                            // building product items
                            if(state == "Draft"){
                                let product_val = [];
                                $.each(product_ids, function(k, elm){
                                    product_val.push(elm.id)
                                }) 
                                buildProductTable(product_ids, selectRequestOption.val());
                            }
                            if(selectRequestOption.val() == "soe"){
                                makefieldsReadonly(true);
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
                // ensure that normal request such as server request, leave request and payment request
                // does not show product item div elements
                if ($.inArray($("#selectRequestOption").val(), ItemRequest) !== -1){
                    $('#product_form_div').removeClass('d-none'); 
                }
                else{
                    $('#product_form_div').addClass('d-none');
                }
            },

            'click .add_item_btn': function(ev){
                    ev.preventDefault();
                    $(ev.target).val()
                    var selectRequestOption = $('#selectRequestOption');
                    if (selectRequestOption.val() !== "employee_update"){
                        console.log("Building product row with form data=> ", setProductdata)
                        buildProductRow(selectRequestOption.val());
                        displaytableProps(selectRequestOption.val()); // hide some artifacts before building products lines
                    }
                    else{
                        console.log("Building Employee row with form data=> ", setEmployeedata)
                        buildEmployeeRow(selectRequestOption.val())
                    }
                },
            'click .search_panel_btn': function(ev){
                console.log("the search")
                var get_search_query = $("#search_input_panel").val()
                window.location.href = `/my/requests/param/${get_search_query}`
            },

            'click .set_state_draft': function(ev){
                console.log("drafting")
                let targetElement = $(ev.target).attr('id');
                setRecordStatus(targetElement, 'submit');
            },

            'click .resend_request': function(ev){
                console.log("Resending")
                let targetElement = $(ev.target).attr('id');
                setRecordStatus(targetElement, 'Sent');
            },

            'click .button_req_submit': function (ev) {
                //// main event starts
                var list_of_fields = [];
                //ensure leave reliever is added 
                if($('#selectRequestOption').val() == "leave_request" && $('#leave_reliever').val() == ''){
                    modal_message.text("Please ensure to add a reliever")
                    alert_modal.modal('show');
                    return false;
                }
                $('input,textarea,select').filter('[required]:visible').each(function(ev){
                    var field = $(this); 
                    if (field.val() == ""){
                        field.addClass('is-invalid');
                        console.log($(this).attr('labelfor'));
                        list_of_fields.push(field.attr('labelfor'));
                    }
                });
                if (list_of_fields.length > 0){
                    // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
                    // alert(`Validation: Please ensure the following fields are filled.. ${list_of_fields}`)
                    let message = `Validation: Please ensure the following fields are filled.. ${list_of_fields}`
                    modal_message.text(message)
                    alert_modal.modal('show');
                    return false;
                }else{
                    

                    var current_btn = $(ev.target);
                    var form = $('#msform')[0];
                    // FormData object 
                    var formData = new FormData(form);
                    console.log('formData is ==>', formData)
                    var DataItems = []
                    // $(`#tbody_product > tr.prod_row > th > input.productinput`).each(
                    //     function(){
                    //         let id = $(this).attr('id');
                    //         let qty = $(this).val();
                    //         if(setProductdata.includes(parseInt(id))){
                    //             let prod_data = {
                    //                 'product_id': id, 
                    //                 'qty': qty,
                    //             } 
                    //             DataItems.push(prod_data)
                    //         }
                    //     }
                    // )
                    let selectRequestOptionValue = $('#selectRequestOption').val()
                    if(selectRequestOptionValue != 'employee_update'){
                        $(`#tbody_product > tr.prod_row`).each(function(){
                            var row_co = $(this).attr('row_count') 
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
                                'request_line_id': '',
                                'distance_from': '',
                                'distance_to': '',
                            }
                            // input[type='text'], input[type='number']
                            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                                function(){
                                    if($(this).attr('name') == "product_item_id"){
                                        console.log($(this).val())
                                        list_item['product_id'] = $(this).val()
                                    }
                                    if($(this).attr('name') === "description"){
                                        list_item['description'] = $(this).val()
                                    }
                                    if($(this).attr('productinput') == "productreqQty"){
                                        console.log($(this).val())
                                        list_item['qty'] = $(this).val()
                                    }
                                
                                    if($(this).attr('name') == "amount_total"){
                                        console.log($(this).val())
                                        list_item['amount_total'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "usedqty"){
                                        console.log($(this).val())
                                        list_item['used_qty'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "usedAmount"){
                                        console.log($(this).val())
                                        list_item['used_amount'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "note_area"){
                                        console.log($(this).val())
                                        list_item['note'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "distance_from"){
                                        console.log($(this).val())
                                        list_item['distance_from'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "distance_to"){
                                        console.log($(this).val())
                                        list_item['distance_to'] = $(this).val()
                                    }
                                    if($(this).attr('class') == "productchecked"){
                                        console.log($(this).val())
                                        // list_item['line_checked'] = $(this).val()
                                        list_item['line_checked'] = $(this).is(':checked') ? 'on' : 'off' 
                                        list_item['request_line_id'] = $(this).attr('code')
                                        list_item['code'] = $(this).attr('code')
                                    }
                                }
                            )
                            DataItems.push(list_item)
                        })
                    }
                    else {
                        // #tbody_employee > tr.employee_row > th > span > input.employeeitemrow
                        $(`#tbody_employee > tr.employee_row`).each(function(){
                            var row_co = $(this).attr('row_count') 
                            var list_item = {
                                    'employee_transfer_id': '', 
                                    'employee_id': '',
                                    'current_dept_id': '',
                                    'transfer_dept': '',
                                    'new_role': '',
                                    'new_district': '',
                            }
                            $(`tr[row_count=${row_co}]`).closest(":has(input, textarea)").find('input,textarea').each(
                                function(){
                                    if($(this).attr('name') == "employee_item_id"){
                                        console.log($(this).val())
                                        list_item['employee_id'] = $(this).val()
                                    }
                                    if($(this).attr('name') === "department_item_id"){
                                        list_item['transfer_dept'] = $(this).val()
                                    }
                                    if($(this).attr('name') == "role_item_id"){
                                        console.log($(this).val())
                                        list_item['new_role'] = $(this).val()
                                    }
                                
                                    if($(this).attr('name') == "district_item_id"){
                                        console.log($(this).val())
                                        list_item['new_district'] = $(this).val()
                                    }
                                }
                            )
                            DataItems.push(list_item)
                        })
                    } 
                    if (!validateLineItems(DataItems)){
                        return false
                    }
                    else{
                       
                        formData.append('DataItems', JSON.stringify(DataItems))
                        formData.append('inputFollowers', $('#inputFollowers').select2('data'))
                        console.log("sssXMLREQUEST Successful====", DataItems);
                        let $btn = $('.button_req_submit');
                        let $btnHtml = $btn.html()
                        $btn.attr('disabled', 'disabled');
                        $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
                        $.blockUI({
                            'message': '<h2 class="card-name">Please wait ...</h2>'
                        });
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
                            if (data.status == false){
                                alert(data.message)
                                return false;
                            }else{
                                // // clearing form content
                                $("#msform")[0].reset();
                                $("#tbody_product").empty()
                                $("#tbody_employee").empty()
                                console.log(`Recieving response from server => ${JSON.stringify(data)} and ${data} + `)
                                window.location.href = `/portal-success`;
                                $btn.attr('disabled', false);
                                $btn.html($btnHtml)
                                $.unblockUI()
                                console.log("XMLREQUEST Successful====", DataItems);
                            }
                        }).catch(function(err) {
                            console.log(err);
                            alert(err);
                        }).then(function() {
                            console.log(".")
                        })
                    }
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
        $('#request_end_date').val('');
        $('#labelDescription').text('Description');
        $('#label_end_date').addClass('d-none');
        $('#div_system_requirement').addClass('d-none');
        $('#request_end_date').addClass('d-none');
        $('#request_end_date').attr('required', false);
        $('#existing_order').val('');
        $('#request_status').val('');
        $('#product_ids').val('').trigger('change');
        $('#product_form_div').addClass('d-none');
        $('#tbody_product').empty();
        $('#otherChangeOption').prop('checked', false);
        $('#hardwareOption').prop('checked', false);
        $('#versionUpgrade').prop('checked', false);
        $('#ids_on_os_and_db').prop('checked', false);
        $('#osChange').prop('checked', false);
        $('#databaseChange').prop('checked', false);
        $('#datapatch').prop('checked', false);
        $('#enhancement').prop('checked', false);
        $('#applicationChange').prop('checked', false);
        $('#div_other_system_details').addClass('d-none');
        $('#other_system_details').attr('required', false);
        $('#other_system_details').val('');
        // $('#other_system_details').addClass("is-valid");
        $('#div_justification_reason').addClass('d-none');
        $('#justification_reason').attr('required', false);
        $('#justification_reason').val('');

        $('#PaymentcashAdvanceDiv').addClass('d-none');
        $('#PaymentcashAdvanceLabel').addClass('d-none');
        $('#PaymentcashAdvance').val('');
        // $('#justification_reason').addClass("is-valid");
    }
    var form = $('#msform')[0];
// return PortalRequestWidget;
});