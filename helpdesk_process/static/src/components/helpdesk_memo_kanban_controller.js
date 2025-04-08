/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HelpdeskMemoDashboard } from "./helpdesk_memo_dashboard";

export class HelpdeskMemoKanbanController extends KanbanController {}

HelpdeskMemoKanbanController.components = {
    ...KanbanController.components,
    HelpdeskMemoDashboard,
};

// Use the QWeb template from the assets bundle.
HelpdeskMemoKanbanController.template = "helpdesk_process.HelpdeskMemoKanbanView";
