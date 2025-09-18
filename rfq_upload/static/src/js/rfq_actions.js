odoo.define('rfq_upload.notification_refresh', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var NotificationRefreshAction = AbstractAction.extend({
        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.action = action;
        },

        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            var params = this.action.params || {};

            // Use the reliable displayNotification method directly.
            // This is the correct way to show a notification from a legacy AbstractAction.
            this.displayNotification({
                title: params.title || 'Notification',
                message: params.message || '',
                type: params.type || 'info', // 'success', 'warning', 'danger', 'info'
                sticky: params.sticky || false
            });

            // Wait a moment for the user to see the notification, then refresh the wizard
            setTimeout(function() {
                self.do_action({
                    'type': 'ir.actions.act_window',
                    'res_model': params.res_model,
                    'res_id': params.res_id,
                    'view_mode': 'form',
                    'target': 'new',
                    'views': [[false, 'form']]
                });
            }, 800); // 800ms delay
        }
    });

    core.action_registry.add('rfq_notification_refresh', NotificationRefreshAction);

    return NotificationRefreshAction;
});