/** @odoo-module **/

import { session } from "@web/session";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

/**
 * Dashboard component for memo.model
 * (Adapted from your example).
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
     * Adjust as needed for your use-case.
     */
    async onActionClicked(ev) {
        const actionElement = ev.currentTarget;
        const actionRef = actionElement.getAttribute("name");
        const title = actionElement.dataset.actionTitle || actionElement.getAttribute("title");
        const searchViewRef = actionElement.getAttribute("search_view_ref");
        const buttonContext = actionElement.getAttribute("context") || "";

        // Example: If the name includes "memo.model", do something special.
        if (actionRef.includes("memo.model")) {
            return await this.actionService.doActionButton({
                resModel: "memo.model",
                name: "create_action",
                args: JSON.stringify([actionRef, title, searchViewRef]),
                context: "",
                buttonContext,
                type: "object",
            });
        } else {
            // Otherwise do a simpler call
            return this.actionService.doActionButton({
                resModel: "memo.model",
                name: actionRef,
                context: "",
                buttonContext,
                type: "object",
            });
        }
    }

    /**
     * Fetch the dashboard data from the server.
     * Expects a method `retrieve_dashboard` on `memo.model`.
     */
    async _fetchData() {
        this.state.dashboardValues = await this.orm.call(
            "memo.model",
            "retrieve_dashboard",  // Implement this in your Python model if needed
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

// Register the template name for Owl
HelpdeskMemoDashboard.template = "helpdesk_process.HelpdeskMemoDashboard";
