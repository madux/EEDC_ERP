odoo.define('eedc_addons.emp_transfer', function (require) {
    "use strict";
    var core = require('web.core');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');

    FormController.include({
        _onFieldChanged: function (event) {
            this._super.apply(this, arguments);
            if (event.data.changes.transfer_type) {
                // Update visibility of columns based on transfer_type
                this.renderer.updateState();
            }
        },
    });
});
