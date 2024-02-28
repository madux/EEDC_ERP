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
                    var current_btn = $(ev.target);
                    var form = $('#msformidocs')[0];
                    var formData = new FormData(form);
                    console.log('formData is ==>', formData)
                    var DataItems = []
                    $(`div#col-sm-docu > input.docuClass`).each(function(){
                        var inputId = $(this).attr('id'); 
                        console.log($(this).attr('name'))
                        var list_item = {
                                        'DocumentId': inputId, 
                                        'DocumentVal': $(this).val(), 
                                }
                                 
                        DataItems.push(list_item)
                    })
                     
                    formData.append('DataItems', JSON.stringify(DataItems))
                    $.ajax({
                        type: "POST",
                        enctype: 'multipart/form-data',
                        url: "/document_data_process",
                        data: formData,
                        processData: false,
                        contentType: false,
                        cache: false,
                        timeout: 800000,
                    }).then(function(data) {
                        console.log(`Recieving response from server => ${JSON.stringify(data)} and ${data} + `)
                        window.location.href = `/portal-success`;
                        console.log("XMLREQUEST Successful");
                        // clearing form content
                        // $("#build_attachment")[0].reset();
                        $("#build_attachment").empty()
                    }).catch(function(err) {
                        console.log(err);
                        alert(err);
                    }).then(function() {
                        console.log(".")
                    })
            },

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
                        $('#build_attachment').empty()
                        alert(`Validation Error! ${data.message}`)
                    }else{
                        console.log(`data dynamic rendering ${data.data.applicant_documentation_checklist_ids}`);
                        $.each(data.data.applicant_documentation_checklist_ids, function(k, elm){
                            $(`#build_attachment`).append(
                                
                                `<div class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="text" data-name="Field">
                                    <div class="row s_col_no_resize s_col_no_bgcolor">
                                        <label class="col-4 col-sm-auto s_website_form_label" style="width: 200px" for="Docu-${elm.document_file_name}">
                                            <span class="s_website_form_label_content" >${elm.document_file_name}</span>
                                        </label>
                                        <div class="col-sm" id="col-sm-docu">
                                            <input type="file" class="form-control s_website_form_input docuClass" labelfor="Docu-${elm.document_file_name}" name="Docuname" id="${elm.document_file_id}" required="${elm.required}"/>
                                        </div>
                                    </div>
                                </div>
                                `
                            )
                        })
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