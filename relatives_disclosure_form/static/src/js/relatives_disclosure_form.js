odoo.define('relatives_disclosure_form.form_js', function (require) {
    "use strict";

    $(document).ready(function () {
        console.log("Relatives Disclosure Form JS Loaded");

        // Staff number validation - SINGLE handler
        $('#staff_number').on('blur', function () {
            const staff_num = $(this).val().trim();
            if (!staff_num) return;

            $.ajax({
                type: 'POST',
                url: '/check_staffid',
                contentType: 'application/json',
                data: JSON.stringify({ staff_num: staff_num }),
                success: function (response) {
                    if (response.status) {
                        $('#staff_name')
                            .val(response.data.name)
                            .prop('readonly', true)
                            .removeClass('is-invalid')
                            .addClass('is-valid');
                        $('#staff_number')
                            .removeClass('is-invalid')
                            .addClass('is-valid');
                    } else {
                        $('#staff_name')
                            .val('')
                            .prop('readonly', false)
                            .removeClass('is-valid')
                            .addClass('is-invalid')
                            .attr('placeholder', 'Enter your name manually');
                        $('#staff_number')
                            .addClass('is-invalid')
                            .removeClass('is-valid');
                        alert(response.message);
                    }
                },
                error: function (xhr, status, error) {
                    console.error('AJAX Error:', error);
                    $('#staff_name')
                        .val('')
                        .prop('readonly', false)
                        .removeClass('is-valid')
                        .addClass('is-invalid')
                        .attr('placeholder', 'Enter your name manually');
                    $('#staff_number')
                        .addClass('is-invalid')
                        .removeClass('is-valid');
                    alert("Connection error. Try again.");
                }
            });
        });


        $('#state_of_origin').on('change', function () {
            const rawValue = $(this).val();
            const state_id = parseInt(rawValue);
            console.log("Raw state value:", rawValue, "| Parsed:", state_id);

            // Clear LGA dropdown first
            $('#lga').html('<option value="">Select LGA</option>');

            if (!state_id || isNaN(state_id)) {
                console.warn("No valid state ID selected");
                return;
            }

            $.ajax({
                type: 'POST',
                url: '/get_lgas_by_state',
                contentType: 'application/json',
                data: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {
                        state_id: state_id
                    },
                    id: new Date().getTime()
                }),
                success: function (response) {
                    console.log("LGA Response:", response);
                    let result = response.result || response;
                    let options = '<option value="">Select LGA</option>';

                    if (Array.isArray(result) && result.length > 0) {
                        result.forEach(function (lga) {
                            options += `<option value="${lga.id}">${lga.name}</option>`;
                        });
                    } else {
                        console.warn("No LGAs found for selected state");
                        options += '<option value="">No LGAs available</option>';
                    }

                    $('#lga').html(options);
                },
                error: function (xhr, status, error) {
                    console.error("AJAX Error loading LGAs:", error);
                    console.error("Response:", xhr.responseText);
                    alert("Failed to load LGAs. Please try again.");
                    $('#lga').html('<option value="">Select LGA</option>');
                }
            });
        });

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

        // Add relative functionality
        $(document).off('click', '#add-relative').on('click', '#add-relative', function () {
            var $container = $('#relatives-container');

            var $district = $('#template_district')
                .clone(false)
                .removeAttr('id')
                .show()
                .attr('name', 'relative_district[]')
                .attr('required', true)
                .addClass('form-control');
            $district.find('option:first').text('Select District');

            var $department = $('#template_department')
                .clone(false)
                .removeAttr('id')
                .show()
                .attr('name', 'relative_department[]')
                .attr('required', true)
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

        // Next button validation
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
                $('html, body').animate({
                    scrollTop: $('.is-invalid').first().offset().top - 100
                }, 300);
                return;
            }

            setActiveStep(2);
            $('#details').removeClass('show active');
            $('#relatives').addClass('show active');
        });

        // Previous button
        $('#prev-to-details').on('click', function (e) {
            setActiveStep(1);
            $('#relatives').removeClass('show active');
            $('#details').addClass('show active');
        });

        // Field-level blur validation
        $('.relatives-disclosure-form').on('blur', 'input, select, textarea', function () {
            var $field = $(this);

            if (!$field.prop('required')) return;

            var value = $field.val().trim();

            // Generic rule: required field must not be empty
            if (value === '') {
                $field.addClass('is-invalid').removeClass('is-valid');
            } else {
                $field.removeClass('is-invalid').addClass('is-valid');
            }

            if ($field.attr('name') === 'employee_id') {
                if (!/^[A-Za-z\s]+$/.test(value)) {
                    $field.addClass('is-invalid').removeClass('is-valid');
                }
            }
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
                $('html, body').animate({
                    scrollTop: $('.is-invalid').first().offset().top - 100
                }, 300);
            }
        });
    });
});