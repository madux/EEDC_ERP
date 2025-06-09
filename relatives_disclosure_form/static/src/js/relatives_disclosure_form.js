odoo.define('relatives_disclosure_form.maiden_toggle', function(require){
    "use strict";
    
    // Simple function to initialize form behavior
    function initializeForm() {
        function toggleMaidenName() {
            var gender = document.getElementById('gender');
            var marital = document.getElementById('marital_status');
            var maidenGroup = document.getElementById('maiden_name_group');
            var maidenInput = maidenGroup ? maidenGroup.querySelector('input[name="maiden_name"]') : null;
            
            if (gender && marital && maidenGroup && maidenInput) {
                // Show maiden name for females who are married
                if (gender.value === 'female' && marital.value === 'married') {
                    maidenGroup.style.display = 'block';
                    maidenInput.required = true;
                } else {
                    maidenGroup.style.display = 'none';
                    maidenInput.required = false;
                    maidenInput.value = '';
                }
            }
        }

        function validateForm(e) {
            var errorMessages = [];
            var form = e.target;
            var errorDiv = document.getElementById('form-error-message');
            
            // Get all form elements
            var formElements = form.querySelectorAll('input, select, textarea');
            
            formElements.forEach(function(field) {
                // Check if field is visible and required
                var fieldStyle = window.getComputedStyle(field.closest('.form-group') || field);
                var isVisible = fieldStyle.display !== 'none';
                
                if (isVisible && field.required && !field.value.trim()) {
                    var label = '';
                    var labelElement = field.closest('.form-group');
                    if (labelElement) {
                        var labelTag = labelElement.querySelector('label');
                        label = labelTag ? labelTag.textContent : field.name;
                    } else {
                        label = field.name;
                    }
                    errorMessages.push('Please fill the "' + label + '" field.');
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            if (errorMessages.length > 0) {
                e.preventDefault();
                if (errorDiv) {
                    errorDiv.innerHTML = errorMessages.join('<br>');
                    errorDiv.style.display = 'block';
                    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            } else {
                if (errorDiv) {
                    errorDiv.style.display = 'none';
                }
            }
        }

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                setupEventListeners();
            });
        } else {
            setupEventListeners();
        }

        function setupEventListeners() {
            var genderField = document.getElementById('gender');
            var maritalField = document.getElementById('marital_status');
            var form = document.querySelector('.relatives-disclosure-form');

            if (genderField) {
                genderField.addEventListener('change', toggleMaidenName);
            }
            if (maritalField) {
                maritalField.addEventListener('change', toggleMaidenName);
            }
            if (form) {
                form.addEventListener('submit', validateForm);
            }

            // Initial toggle
            toggleMaidenName();
        }
    }

    // Initialize when the module is loaded
    initializeForm();

    // Return empty object to satisfy odoo.define
    return {};
});