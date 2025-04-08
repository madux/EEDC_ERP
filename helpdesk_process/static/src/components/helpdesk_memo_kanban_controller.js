/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HelpdeskMemoDashboard } from "./helpdesk_memo_dashboard";

export class HelpdeskMemoKanbanController extends KanbanController {}

// Extend the components with our dashboard component
HelpdeskMemoKanbanController.components = {
    ...KanbanController.components,
    HelpdeskMemoDashboard,
};

// Set the template to our custom QWeb override
HelpdeskMemoKanbanController.template = "helpdesk_process.HelpdeskMemoKanbanView";

// Register the controller under a unique JS class name so that only the view with js_class="helpdeskMemoKanbanView" uses it
import { registry } from "@web/core/registry";
registry.category("view_controllers").add("helpdeskMemoKanbanView", HelpdeskMemoKanbanController);