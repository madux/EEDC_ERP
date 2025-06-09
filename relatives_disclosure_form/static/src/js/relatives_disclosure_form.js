odoo.define('relatives_disclosure_form.maiden_toggle', function(require){
    "use strict";
    
    var core = require('web.core');
    var publicWidget = require('web.public.widget');

    publicWidget.registry.RelativesDisclosureForm = publicWidget.Widget.extend({
        selector: '.relatives-disclosure-form',
        events: {
            'change #gender': '_onGenderMaritalChange',
            'change #marital_status': '_onGenderMaritalChange',
            'submit': '_onFormSubmit',
        },

        start: function () {
            this._toggleMaidenName();
            return this._super.apply(this, arguments);
        },

        _toggleMaidenName: function () {
            var gender = this.$('#gender').val();
            var marital = this.$('#marital_status').val();
            var maidenGroup = this.$('#maiden_name_group');
            var maidenInput = maidenGroup.find('input[name="maiden_name"]');
            
            // Show maiden name for females who are married
            if (gender === 'female' && marital === 'married') {
                maidenGroup.show();
                maidenInput.prop('required', true);
            } else {
                maidenGroup.hide();
                maidenInput.prop('required', false);
                maidenInput.val('');
            }
        },

        _onGenderMaritalChange: function () {
            this._toggleMaidenName();
        },

        _onFormSubmit: function (e) {
            var errorMessages = [];
            var $form = this.$el;

            // Check all visible required fields
            $form.find('input, select, textarea').each(function(){
                var $field = $(this);
                if ($field.is(':visible') && $field.prop('required') && !$field.val()) {
                    var label = $field.closest('.form-group').find('label').text() || $field.attr('name');
                    errorMessages.push('Please fill the "' + label + '" field.');
                    $field.addClass('is-invalid');
                } else {
                    $field.removeClass('is-invalid');
                }
            });

            if (errorMessages.length > 0) {
                e.preventDefault();
                this.$('#form-error-message').html(errorMessages.join('<br>')).show();
                $('html, body').animate({
                    scrollTop: this.$('#form-error-message').offset().top - 100
                }, 300);
            } else {
                this.$('#form-error-message').hide();
            }
        },
    });

    return publicWidget.registry.RelativesDisclosureForm;
});