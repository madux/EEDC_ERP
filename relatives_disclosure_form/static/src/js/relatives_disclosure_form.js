odoo.define('relatives_disclosure_form.maiden_toggle', function(require){
    "use strict";
    $(document).ready(function () {
        function toggleMaidenName() {
            var gender = $('#gender').val();
            var marital = $('#marital_status').val();
            var maidenGroup = $('#maiden_name_group');
            var maidenInput = maidenGroup.find('input[name="maiden_name"]');
            if (gender === 'male' && marital === 'married') {
                maidenGroup.show();
                maidenInput.prop('required', true);
            } else {
                maidenGroup.hide();
                maidenInput.prop('required', false);
                maidenInput.val('');
            }
        }
        $('#gender, #marital_status').on('change', toggleMaidenName);
        toggleMaidenName();
        console.log("Michael 1")

        // Custom validation on submit
        $('.relatives-disclosure-form').on('submit', function(e){
            var errorMessages = [];
            var $form = $(this);

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

            // You can also check for special rules (e.g., signature file only certain extensions, etc.)

            if (errorMessages.length > 0) {
                e.preventDefault(); // Stop form from submitting
                $('#form-error-message').html(errorMessages.join('<br>')).show();
                $('html, body').animate({
                    scrollTop: $('#form-error-message').offset().top - 100
                }, 300);
            } else {
                $('#form-error-message').hide();
            }
        });
    });
});

