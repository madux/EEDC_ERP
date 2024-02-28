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
            'click .start-documentation': function(ev){
                let targetElement = $(ev.target).attr('id');
                let record_id = $('#record_id').attr('id');
                console.log(`Displays the form element and build dynamic rendering ${targetElement}`);
                $('#build_attachment').empty()
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
                         
                    }
                }).guardedCatch(function (error) {
                    let msg = error.message.message
                    console.log(msg)
                    $("#existing_order").val('')
                    alert(`Unknown Error! ${msg}`)
                });

                $(`#tbody_employee`).append(
                    `<label class="col-4 col-sm-auto s_website_form_label" style="width: 200px" for="Docu-${documentName}">
                    <span class="s_website_form_label_content" >${documentName}</span>
                </label>
                
                <div class="col-sm">
                    <input type="file" class="form-control s_website_form_input" labelfor="${documentName}" name="${documentName}" id="${documentName}" required="${required}" multiple="1"/>
                </div>`
                )


                 
            },
         },
         

    });
});