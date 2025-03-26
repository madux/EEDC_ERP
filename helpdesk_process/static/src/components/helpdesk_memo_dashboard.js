/** @odoo-module **/

import { session } from "@web/session";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class HelpdeskMemoDashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            dashboardValues: null,
        });
        console.log("HelpdeskMemoDashboard loaded")

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        // Call your Python method to fetch aggregated stats
        this.state.dashboardValues = await this.orm.call(
            "memo.model",
            "retrieve_dashboard",
            [],
            { context: session.user_context },
        );
    }

    // If you have any click actions
    async onActionClicked(ev) {
        // your logic
    }

    formatFloat(value, options = {}) {
        return formatFloat(value, options);
    }
    formatTime(value, options = {}) {
        return formatFloatTime(value, options);
    }
}

HelpdeskMemoDashboard.template = "helpdesk_process.HelpdeskMemoDashboard";