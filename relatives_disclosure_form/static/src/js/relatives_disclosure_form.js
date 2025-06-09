odoo.define('relatives_disclosure_form.maiden_toggle', function(require){
    "use strict";
    
    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    
    publicWidget.registry.RelativesDisclosureForm = publicWidget.Widget.extend({
        selector: '.relatives-disclosure-form',
        events: {
            'change #gender, #marital_status': '_onGenderMaritalChange',
            'submit': '_onFormSubmit',
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._toggleMaidenName();
            });
        },

        /**
         * Toggle maiden name field based on gender and marital status
         * @private
         */
        _toggleMaidenName: function () {
            var gender = this.$('#gender').val();
            var marital = this.$('#marital_status').val();
            var maidenGroup = this.$('#maiden_name_group');
            var maidenInput = maidenGroup.find('input[name="maiden_name"]');
            
            if (gender === 'male' && marital === 'married') {
                maidenGroup.show();
                maidenInput.prop('required', true);
            } else {
                maidenGroup.hide();
                maidenInput.prop('required', false);
                maidenInput.val('');
            }
        },

        /**
         * Handle gender/marital status change
         * @private
         */
        _onGenderMaritalChange: function () {
            this._toggleMaidenName();
        },

        /**
         * Handle form submission with validation
         * @private
         */
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
                e.preventDefault(); // Stop form from submitting
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