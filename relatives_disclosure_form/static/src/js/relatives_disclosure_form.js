odoo.define('relatives_disclosure_form.form_js', function (require) {
    "use strict";
    $(document).ready(function () {
        // Maiden name show/hide logic
        // function toggleMaidenName() {
        //     var gender = $('#gender').val();
        //     var marital = $('#marital_status').val();
        //     var maidenGroup = $('#maiden_name_group');
        //     var maidenInput = maidenGroup.find('input[name="maiden_name"]');
        //     if (gender === 'female' && marital === 'married') {
        //         maidenGroup.show();
        //         maidenInput.prop('required', true);
        //     } else {
        //         maidenGroup.hide();
        //         maidenInput.prop('required', false);
        //         maidenInput.val('');
        //     }
        // }
        // $('#gender, #marital_status').on('change', toggleMaidenName);
        // toggleMaidenName();

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

        // Step navigation
        $('#next-to-relatives').on('click', function (e) {
            // Validate required fields in the "details" tab first
            var valid = true;
            var errorMessages = [];
            $('#details').find('input, select, textarea').each(function () {
                var $field = $(this);
                if ($field.prop('required') && !$field.val()) {
                    valid = false;
                    var label = $field.closest('.form-group').find('label').text() || $field.attr('name');
                    errorMessages.push('Please fill the "' + label + '" field.');
                    $field.addClass('is-invalid');
                } else {
                    $field.removeClass('is-invalid');
                }
            });
            if (!valid) {
                $('#form-error-message').html(errorMessages.join('<br>')).show();
                $('html, body').animate({
                    scrollTop: $('#form-error-message').offset().top - 100
                }, 300);
                return;
            } else {
                $('#form-error-message').hide();
            }

            // Move to relatives tab
            $('#details-tab').removeClass('active');
            $('#relatives-tab').addClass('active');
            $('#details').removeClass('show active');
            $('#relatives').addClass('show active');
        });

        $('#prev-to-details').on('click', function (e) {
            // Move back to details tab
            $('#relatives-tab').removeClass('active');
            $('#details-tab').addClass('active');
            $('#relatives').removeClass('show active');
            $('#details').addClass('show active');
        });

        // Custom validation on submit (on relatives tab)
        $('.relatives-disclosure-form').on('submit', function (e) {
            var errorMessages = [];
            var $form = $(this);

            // Only validate fields in the relatives tab for submission
            $('#relatives').find('input, select, textarea').each(function () {
                var $field = $(this);
                if ($field.prop('required') && !$field.val()) {
                    var label = $field.closest('.relative-row').find('input[name="relative_name[]"]').val() || $field.attr('name');
                    errorMessages.push('Please complete all relative fields.');
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
