odoo.define('hr_cbt_portal_recruitment.documentation_request_form', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  
     
    publicWidget.registry.DocumentationRequestFormWidgets = publicWidget.Widget.extend({
        selector: '#documentation-request-form',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("documentation request started")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log(".....")
            })
        },
        
        events: {

            'click .button_doc_submit': function (ev) {
                // Get form
                var form = $('#msformidocs')[0];
                // FormData object 
                var formData = new FormData(form);
                var DataItems = []
                //append extra data to form
                formData.append('record_id', parseInt($('.record_id').attr('id')));
                let inputIdArray = [];
                $(`div#col-sm-docu > input.docuClass`).each(function(){
                    var inputId = $(this).attr('id'); 
                    console.log(`the game is  `, document.getElementById(inputId).files[0])
                    let inputfile = document.getElementById(inputId).files[0]
                    if (inputfile){
                        formData.append(inputId, inputfile);
                        inputIdArray.push(inputId)
                    }
                    
                });
                formData.append('counter_ids', JSON.stringify(inputIdArray));
                console.log(formData);
                var xmlRequest = $.ajax({
                    type: "POST",
                    enctype: 'multipart/form-data',
                    url: "/document-data-process",
                    data: formData,
                    processData: false,
                    contentType: false,
                    cache: false,
                    timeout: 800000,
                    beforeSend: function () {
                        console.log('trying to upload documentation ')
                    }
                });
                xmlRequest.done(function (data) {
                    let result = JSON.stringify(data);
                    console.log(`Recieving response from server => ${result.status} //// ${result}`)
                    // if (!result.status) {
                        // alert(`Validation Error:  ${result.message}`);
                        // return false;
                    // }else{
                    window.location.href = `/documentation-success`;
                    console.log("XMLREQUEST Successful");
                    // clearing form content
                    $("#msformidocs")[0].reset();
                    $("#build_attachment").empty()
                        
                    // }
                });
                xmlRequest.fail(function (jqXHR, textStatus) {
                    console.log(`Registration. TextStatus: ${textStatus}. Statuscode:  ${jqXHR.status}`);
                });
                xmlRequest.always(function () {
                    console.log("-*");

                })
            },

            // 'click .button_doc_submit': function (ev) {
            //         var current_btn = $(ev.target);
            //         var form = $('#msformidocs')[0];
            //         var formData = new FormData(form);
            //         let DataItems = []
            //         const localStorage = window.localStorage;
            //         localStorage.setItem('DataItems', "");

            //         // $.each($('input[type=file]'), (outer_index, input) => {
            //         //     // var inputId = input.attr('id') != undefined ? parseInt(input.attr('id')) : false; 
            //         //     let inputId = $(input).prop('attributes')['id'];
            //         //     console.log($(input).prop('attributes')['id'])
            //         //     var list_item = {
            //         //         'DocumentId': $(input).prop('attributes')['id'], 
            //         //         'DocumentVal': false, 
            //         //         'record_id': $('.record_id').attr('id'), 
            //         //     }
            //         //     $.each($(input).prop('files'), function (index, file) {
            //         //         list_item['DocumentVal'] = file
            //         //         console.log(file)
            //         //     });
            //         //     DataItems.push(list_item)
            //         // });
            //         // console.log(DataItems)
            //         $(`div#col-sm-docu > input.docuClass`).each(function(){
            //             // var inputId = $(this).attr('id') != undefined ? parseInt($(this).attr('id')) : '4443'; 
            //             var inputId = $(this).attr('id'); 
            //             console.log(`the game is  `, document.getElementById(inputId).files[0])
            //             let inputfile = document.getElementById(inputId).files[0]
            //             if (inputfile) {
            //                 var reader = new FileReader();
            //                 reader.readAsDataURL(inputfile);
            //                 reader.onload = function(e) 
            //                     {
            //                         let image_input = e.target.result;
            //                         let list_item = {
            //                             'DocumentId': inputId ? parseInt(inputId) : '', 
            //                             'DocumentVal': image_input,
            //                             'record_id': $('.record_id').attr('id'), 
            //                         }
            //                         DataItems.push(list_item)
            //                         localStorage.setItem('DataItems', JSON.stringify(DataItems));

            //                         // console.log('gush  ', image_input);
            //                     }
            //                 // var result = {'article': image_input}
                            
            //             // $.each($(this).prop('files'), function (index, file) {
            //             //         list_item['DocumentVal'] = JSON.stringify(file)
            //             //         console.log(`the files is  `, file)
            //             //     });
                                 
            //                 // DataItems.push(list_item)
            //             }
            //         });
            //         console.log(DataItems)
            //         formData.append('DataItems', $('input[type=file]')[0].files[0])
            //         formData.append('record_id', $('.record_id').attr('id'))
            //         console.log('formData is ==>', formData)
            //         // let data = JSON.parse(localStorage.getItem('DataItems'));
            //         /** DataItems = [{}, {}, {
            //             'DocumentId': '234',
            //             'DocumentVal': data, 
            //         }]*/
            //         // $.ajax({
            //         //     type: "POST",
            //         //     // dataType: 'json',
            //         //     enctype: 'multipart/form-data',
            //         //     url: "/document_data_process",
            //         //     data: {'res': 'image_input'}, //formData, //localStorage.getItem('DataItems'), // formData,//JSON.stringify(DataItems) , // { DataItems: DataItems, record_id : $('.record_id').attr('id')},
            //         //     processData: false,
            //         //     contentType: false,
            //         //     cache: false,
            //         //     timeout: 800000,
            //         // }).then(function(data) {

            //         //     console.log(`Recieving response from server => ${JSON.stringify(data)} and ${data} + `)
            //         //     // window.location.href = `/portal-success`;
            //         //     console.log("XMLREQUEST Successful");
            //         //     // clearing form content
            //         //     // $("#build_attachment")[0].reset();
            //         //     $("#build_attachment").empty()
            //         // }).catch(function(err) {
            //         //     console.log(err);
            //         //     alert(err);
            //         // }).then(function() {
            //         //     console.log(".")
            //         // })
            //         this._rpc({
            //             route: `/document_data_process`,
            //             params: {
            //                 'res': 'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkfff',
            //                 'record_id': $('.record_id').attr('id')
            //             },
            //         }).then(function (data) {
            //             if (!data.status) {
            //                 alert(`Validation Error! Nothing`)
            //             }else{
            //                 console.log("Successful and working")
            //             }
            //         }).guardedCatch(function (error) {
            //             let msg = error.message.message
            //             console.log(msg)
            //         });
            // },
            'click .start-documentation': function(ev){
                let targetElement = $(ev.target).attr('id');
                let record_id = $('.record_id').attr('id');
                console.log(`Displays the form element and build dynamic rendering ${targetElement}`);
                this._rpc({
                    route: `/get-applicant-document`,
                    params: {
                        'record_id': record_id,
                    },
                }).then(function (data) {
                    if (!data.status) {
                        $('#build_attachment').empty();
                        alert(`Validation Error! ${data.message}`)
                    }else{
                        if (data.data.applicant_documentation_checklist_ids.length > 0){
                            $.each(data.data.applicant_documentation_checklist_ids, function(k, elm){
                                $(`#build_attachment`).append(
                                    `<div class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="text" data-name="Field">
                                        <div class="row s_col_no_resize s_col_no_bgcolor">
                                            <label class="col-5 col-sm-5 s_website_form_label" style="min-width: 200px" for="Docu-${elm.document_file_name}">
                                                <span class="s_website_form_label_content" >${elm.document_file_name}</span>
                                            </label>
                                            <div class="col-4 col-sm-4" id="col-sm-docu">
                                                <input type="file" class="form-control s_website_form_input docuClass" labelfor="Docu-${elm.document_file_name}" name="Docuname" id="${elm.document_file_id}" required="${elm.required}"/>
                                            </div>
                                        </div>
                                        <div class="${$.inArray(elm.hr_comment, ['', 'Resubmitted']) !== -1  ? 'd-none': 'alert alert-danger'}" role="alert" style="font-size: 14px;">
                                            ${elm.hr_comment}<br/>
                                        </div>
                                    </div>
                                    `
                                )
                            })
                            $('.s_website_form_submit').addClass('text-center'); 
                            $('#s_website_form_submit_div').removeClass('d-none')
                            $(`#show-if-no-documentation`).addClass('d-none')
                            console.log("There is data to display")

                        }else{
                            console.log("There is no data to display")
                            $(`#show-if-no-documentation`).removeClass('d-none')
                            $(`#start_documentation_div`).addClass('d-none')
                            $('#s_website_form_submit_div').addClass('d-none')
                        }
                        $('#start_documentation_div').addClass('d-none')
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    console.log(msg)
                    $('#build_attachment').empty()
                    alert(`Unknown Error! ${msg}`)
                });
 
                 
            },
         },
         

    });
});