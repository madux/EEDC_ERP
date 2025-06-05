odoo.define('relatives_disclosure_form.maiden_toggle', function(require){
    "use strict";
    $(document).ready(function () {
        function toggleMaidenName() {
            var gender = $('#gender').val();
            var marital = $('#marital_status').val();
            var maidenGroup = $('#maiden_name_group');
            if (gender === 'male' && marital === 'married') {
                maidenGroup.show();
            } else {
                maidenGroup.hide();
            }
        }
        $('#gender, #marital_status').on('change', toggleMaidenName);
        toggleMaidenName();
    });
});
