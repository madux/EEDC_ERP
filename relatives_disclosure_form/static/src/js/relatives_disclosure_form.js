odoo.define('relatives_disclosure_form.form_js', function (require) {
    "use strict";
    $(document).ready(function () {
        // Maiden name show/hide logic
        function toggleMaidenName() {
            var gender = $('#gender').val();
            var marital = $('#marital_status').val();
            var maidenGroup = $('#maiden_name_group');
            var maidenInput = maidenGroup.find('input[name="maiden_name"]');
            if (gender === 'female' && marital === 'married') {
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

        // Add relative row logic
        $('#add-relative').on('click', function () {
            var $container = $('#relatives-container');
            var $district = $('#template_district').clone().removeAttr('id').show().attr('name', 'relative_district[]').addClass('form-control d-inline-block w-auto mx-1');
            var $department = $('#template_department').clone().removeAttr('id').show().attr('name', 'relative_department[]').addClass('form-control d-inline-block w-auto mx-1');
            var $row = $(`
                <div class="relative-row mb-2">
                    <input type="text" name="relative_name[]" placeholder="Relative Name" required class="form-control d-inline-block w-auto mx-1"/>
                    <select name="relationship[]" required class="form-control d-inline-block w-auto mx-1">
                        <option value="">Relationship</option>
                        <option value="spouse">Spouse</option>
                        <option value="parent">Parent</option>
                        <option value="sibling">Sibling</option>
                        <option value="child">Child</option>
                        <option value="niece">Niece</option>
                        <option value="nephew">Nephew</option>
                        <option value="other">Other</option>
                    </select>
                </div>
            `);
            $row.append($district);
            $row.append($department);
            $row.append('<button type="button" class="btn btn-danger btn-sm remove-relative mx-1">Remove</button>');
            $container.append($row);
            $row.find('.remove-relative').on('click', function () {
                $row.remove();
            });
        });

        // Custom validation
        $('.relatives-disclosure-form').on('submit', function (e) {
            var errorMessages = [];
            var $form = $(this);

            // Check all visible required fields
            $form.find('input, select, textarea').each(function () {
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
