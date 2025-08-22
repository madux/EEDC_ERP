/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const rfqNotifyAndRefresh = {
    async execute(action, options, env) {
        const actionService = env.services.action;
        const notificationService = env.services.notification;
        
        notificationService.add(action.params.message || 'Success', {
            title: action.params.title || 'Info',
            type: action.params.type || 'success',
            sticky: action.params.sticky || false,
        });
        
        const context = action.context || {};
        const currentModel = context.default_memo_id ? 'rfq.upload.wizard' : null;
        const activeId = context.active_id;
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (currentModel && activeId) {
            return actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'rfq.upload.wizard',
                view_mode: 'form',
                target: 'new',
                context: { default_memo_id: context.default_memo_id },
            });
        }
        
        return Promise.resolve();
    }
};

registry.category("actions").add("rfq_upload.rfq_notify_and_refresh", rfqNotifyAndRefresh);