/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
console.log("tree view Loading the sidebar widget")

export class CustomListRendererCallover extends ListRenderer {
    setup() {
        super.setup();
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;
        // this.action = useService("action");
        this.userService = this.env.services.user;
        console.log("Callover loading")
    } 


    async createNewExpenditures() {
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: "Expenditures",
            res_model: "memo.model",
            view_mode: "form",
            domain: [["is_internal_transfer", "=", true]],
            context: { default_is_internal_transfer: true },
            views: [[false, "form"]],
            // views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async openPaymentMandate(ev) {
        ev.preventDefault();

        await this.env.services.action.doAction(
            "maach_payment_schedule.action_ma_payment_schedule",
            {
                target: "current",
            }
        );
    }
    async openPaymentRequest(ev) {
        ev.preventDefault();

        await this.env.services.action.doAction(
            "plateau_addons.internal_memo_model_mda_action",
            {
                target: "current",
            }
        );
    }
    async openExpenditures(ev) {
        ev.preventDefault();

        await this.env.services.action.doAction(
            "plateau_addons.internal_memo_model_internal_mda_action",
            {
                target: "current",
            }
        );
    }
}
// CustomListRenderer.components = { ...ExpenseDashboardListRenderer.components, ExpenseDashboard};
CustomListRendererCallover.template = "account_callover.CustomListRendererCallover";

export const CustomDashboardListViewCallover = {
    ...listView,
    Renderer: CustomListRendererCallover,
};
registry.category("views").add("memo_dashboard_listCallover", CustomDashboardListViewCallover);


// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { ListController } from "@web/views/list/list_controller";
// import { listView } from "@web/views/list/list_view";
// import { useEffect, useState, onMounted, onWillUpdateProps} from "@odoo/owl";
// import { ListRenderer } from "@web/views/list/list_renderer";

// export class AccountCalloverListController extends ListRenderer {
//     setup() {
//         super.setup();
//         this.orm = useService("orm");
//         this.state = useState({
//             stats: {
//                 total: 0,
//                 budget_balance: 0,
//             },
//         });

//         useEffect(
//             () => {
//                 this.loadStats();
//             },
//             () => [JSON.stringify(this.model.root.domain)]
//         );
//     }

//     _resolveCurrentModel() {
//         return (
//             this._resolveAction().res_model ||
//             this.props?.list?.resModel ||           // Odoo 17
//             this.props?.list?.config?.resModel ||   // Odoo 16
//             ""
//         );
//     }

//     _resolveCurrentModelName() {
//         return (
//             this.props.list?.resModel
//         ).trim(); 
//     }

//     get isReportCalloverView() {
//         const name = this._resolveCurrentModelName();
//         console.log("isReportCalloverView — name:", name);
//         return name === "account.callover";
//     }

//     // async loadStats() {
//     //     const domain = this.model.root.domain || [];
//     //     const groups = await this.orm.readGroup(
//     //         this.props.resModel,
//     //         domain,
//     //         ["total:sum", "budget_balance:sum"],
//     //         []
//     //     );
//     //     const data = groups[0] || {};
//     //     this.state.stats.total = data.total || 0;
//     //     this.state.stats.budget_balance = data.budget_balance || 0;
//     // }

//     formatAmount(value) {
//         return new Intl.NumberFormat(undefined, {
//             minimumFractionDigits: 2,
//             maximumFractionDigits: 2,
//         }).format(value || 0);
//     }
// }

// AccountCalloverListController.template = "account_callover.CustomListRenderer";

// export const accountCalloverListViewRenderer = {
//     ...listView,
//     Renderer: AccountCalloverListController,
// };

// registry.category("views").add("account_callover_list", accountCalloverListViewRenderer);
