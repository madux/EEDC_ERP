odoo.define('portal_request.portal_employee_dashboards', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t; 

    let navigateTo = function(screenId) {
        $('.page-section').removeClass('active');   // remove active from all
        $('#' + screenId).addClass('active'); // add to target
        }

    let navigateBack = function(screenId) {
        $('.page-section').removeClass('active');   // remove active from all
        $('#' + screenId).addClass('active'); // add to target
        }

    publicWidget.registry.EmployeeDashboardWidgets = publicWidget.Widget.extend({
        selector: '#portal-dashboard-form',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("Employee dashboard")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("loading Employee dashboard.....")
            })
        },
        events: {
            'click #app-icon': function(ev){
                console.log("App icoon clicked.....")
                navigateTo('website-app-section')  
            },

            'click #navigateBack': function(ev){
                navigateBack('portal-dashboard-content')  
            },

         },
         

    });

// return PortalRequestWidget;
});