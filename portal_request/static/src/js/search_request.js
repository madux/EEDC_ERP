odoo.define('portal_request.search_request', function (require) {
    "use strict";

    require('web.dom_ready');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var qweb = core.qweb;
    var _t = core._t;  
    

    publicWidget.registry.SearchRequestWidgets = publicWidget.Widget.extend({
        selector: '#search_request_section',
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                console.log("started search request")
               
            });

        },
        willStart: function(){
            var self = this; 
            return this._super.apply(this, arguments).then(function(){
                console.log("All events start")
                
            })
        },
        events: {
            'click .search_panel_btn': function(ev){
                console.log("the search")
                var get_search_query = $("#search_input_panel").val();
                $("#search_input_panel").val("");
                window.location.href = `/my/requests/param/${get_search_query}`
            },

            'click #app-icon': function(ev){
                console.log("App icoon at search clicked.....")
                document.getElementById("website-app-section").classList.add("active");
                // navigateTo('website-app-section')  
                // $('#website-app-section').removeClass('d-none')
                
				// document.getElementById("website-app-section").style.width = "100px";
				// document.getElementById("website-app-section").style.height = "100px";
            },

            'click #navigateBack': function(ev){
                console.log("Back page click to remove search clicked.....")
                document.getElementById("website-app-section").classList.remove("active");

                // navigateTo('website-app-section')  
				// document.getElementById("website-app-section").style.width = "0px";
				// document.getElementById("website-app-section").style.height = "0px";
            },
         }

    });

// return PortalRequestWidget;
});