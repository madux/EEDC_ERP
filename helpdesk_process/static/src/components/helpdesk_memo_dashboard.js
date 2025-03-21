/** @odoo-module **/

import { session } from "@web/session";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

/**
 * Dashboard component for memo.model
 */
export class HelpdeskMemoDashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            dashboardValues: null,
        });

        onWillStart(this.onWillStart);
    }

    /**
     * Fetches the dashboard data on load.
     */
    async onWillStart() {
        await this._fetchData();
    }

    /**
     * Example click handler for custom actions.
     */
    async onActionClicked(ev) {
        const actionElement = ev.currentTarget;
        const actionRef = actionElement.getAttribute("name");
        const title = actionElement.dataset.actionTitle || actionElement.getAttribute("title");
        const searchViewRef = actionElement.getAttribute("search_view_ref");
        const buttonContext = actionElement.getAttribute("context") || "";

        // You can adapt this logic as needed
        return this.actionService.doActionButton({
            resModel: "memo.model",
            name: actionRef,
            context: "",
            buttonContext,
            type: "object",
        });
    }

    /**
     * Fetch the dashboard data from the server.
     * Expects a method `retrieve_dashboard` on `memo.model`.
     */
    async _fetchData() {
        this.state.dashboardValues = await this.orm.call(
            "memo.model",
            "retrieve_dashboard",
            [],
            { context: session.user_context },
        );
    }

    // Utility formatters
    formatFloat(value, options = {}) {
        return formatFloat(value, options);
    }
    formatTime(value, options = {}) {
        return formatFloatTime(value, options);
    }
    parseInteger(value) {
        return parseInt(value, 10);
    }
}

// IMPORTANT: Template name must match the QWeb template's t-name
HelpdeskMemoDashboard.template = "helpdesk_process.HelpdeskMemoDashboard";
