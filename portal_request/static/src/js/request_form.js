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
    let divRefuseCommentMessage = $('.div_refuse_comment_message');
    let modalfooter4cancel = $('#modalfooter4cancel');
    let refuseCommentMessage = $('#refuse_comment_message');

    // hiding the components until options is indicated
    divRefuseCommentMessage.hide()
    modalfooter4cancel.hide()
    refuseCommentMessage.attr('required', false)

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
                divRefuseCommentMessage.show();
                modalfooter4cancel.hide();
                refuseCommentMessage.attr('required', true);
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