odoo.define('relatives_disclosure_form.form_js', function (require) {
    "use strict";

    $(document).ready(function () {
        console.log("Relatives Disclosure Form JS Loaded");
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

        // Ensure add-relative is bound once
        $(document).off('click', '#add-relative').on('click', '#add-relative', function () {
            var $container = $('#relatives-container');

            var $district = $('#template_district')
                .clone(false)
                .removeAttr('id')
                .show()
                .attr('name', 'relative_district[]')
                .addClass('form-control');
            $district.find('option:first').text('Select District');

            var $department = $('#template_department')
                .clone(false)
                .removeAttr('id')
                .show()
                .attr('name', 'relative_department[]')
                .addClass('form-control');
            $department.find('option:first').text('Select Department');

            var $row = $(
                `<div class="relative-row border rounded p-3 mb-3">
                    <div class="form-group">
                        <label>Relative Name</label>
                        <input type="text" name="relative_name[]" class="form-control" required placeholder="Enter Relative Name"/>
                    </div>
                    <div class="form-group">
                        <label>Relationship</label>
                        <select name="relationship[]" class="form-control" required>
                            <option value="">Select Relationship</option>
                            <option value="spouse">Spouse</option>
                            <option value="parent">Parent</option>
                            <option value="sibling">Sibling</option>
                            <option value="child">Child</option>
                            <option value="niece">Niece</option>
                            <option value="nephew">Nephew</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>District</label>
                    </div>
                    <div class="form-group">
                        <label>Department</label>
                    </div>
                    <div class="text-right">
                        <button type="button" class="btn btn-sm remove-relative" style="background-color:#dc3545; color:white;">Remove</button>
                    </div>
                </div>`
            );

            $row.find('.form-group').eq(2).append($district);
            $row.find('.form-group').eq(3).append($department);

            $container.append($row);

            $row.find('.remove-relative').on('click', function () {
                $row.remove();
            });
        });

        // Step navigation
        function setActiveStep(stepNumber) {
            $('.step-item').each(function () {
                const $item = $(this);
                const step = parseInt($item.data('step'));

                if (step === stepNumber) {
                    $item.addClass('active');
                    $item.html(`
                <div class="step-content">
                    <div class="step-number">${step}</div>
                    <div class="step-title">${step === 1 ? 'Staff Details' : step === 2 ? 'Relatives' : 'Complete'}</div>
                </div>
            `);
                } else {
                    $item.removeClass('active');
                    $item.html(`<div class="step-dot"></div>`);
                }
            });
        }



        $('#next-to-relatives').on('click', function (e) {
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

            setActiveStep(2);

            $('#details').removeClass('show active');
            $('#relatives').addClass('show active');
        });

        $('#prev-to-details').on('click', function (e) {
            setActiveStep(1);

            $('#relatives').removeClass('show active');
            $('#details').addClass('show active');
        });

        // Form validation on submit
        $('.relatives-disclosure-form').on('submit', function (e) {
            var errorMessages = [];
            $('#relatives').find('input, select, textarea').each(function () {
                var $field = $(this);
                if ($field.prop('required') && !$field.val()) {
                    errorMessages.push('Please complete all relative fields.');
                    $field.addClass('is-invalid');
                } else {
                    $field.removeClass('is-invalid');
                }
            });

            if (errorMessages.length > 0) {
                e.preventDefault();
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
