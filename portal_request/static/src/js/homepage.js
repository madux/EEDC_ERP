odoo.define('portal_request.portal_homepage', function (require) {
    "use strict";

    // require('web.dom_ready');
    // var utils = require('web.utils');
    // var ajax = require('web.ajax');
    // var publicWidget = require('web.public.widget');
    // var core = require('web.core');
    // var qweb = core.qweb;
    // var _t = core._t;  

    // publicWidget.registry.ExtendedHomePage = publicWidget.Widget.extend({
    //     selector: '.o_website_homepage',  // homepage root selector
    //     start: function () {
    //         // Call parent start
    //         this._super.apply(this, arguments);

    //         console.log("🚀 Extended homepage loaded!");

    //         // Example: add a custom message under homepage banner
    //         const msg = $("<div class='alert alert-info mt-3'>Welcome to my extended homepage!</div>");
    //         this.$el.append(msg);

    //         return this;
    //     },
    // });

    $( document ).ready(function() {

        let setMode = function(isLight) {
            const $dashboard = $('.dashboard');
            const $btn = $('#switchModeBtn');
            if (isLight) {
                $dashboard.addClass('light-mode');
                $btn.text('Switch to Dark Mode');
                localStorage.setItem('mode', 'light');
                $('#back-icon').attr('fill', 'black');
                $('#myProfile').attr('color', 'black');
                $('#switchModeBtn1').attr('color', 'black');
            } else {
                $dashboard.removeClass('light-mode');
                $btn.text('Switch to Light Mode');
                localStorage.setItem('mode', 'dark');
                 $('#back-icon').attr('fill', 'white');
                $('#myprofile').attr('color', 'white');
                $('#switchModeBtn1').attr('color', 'white');

            }
        };
        $('#switchModeBtn').click(function () {
            const savedMode = localStorage.getItem('mode');
            setMode(savedMode === 'light');
            const isLight = !$('.dashboard').hasClass('light-mode');
            setMode(isLight);
            console.log('Clicked dark mode', localStorage.getItem('mode'))
        });
    })
});