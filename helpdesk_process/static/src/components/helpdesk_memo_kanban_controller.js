/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HelpdeskMemoDashboard } from "./helpdesk_memo_dashboard";

export class HelpdeskMemoKanbanController extends KanbanController {}

HelpdeskMemoKanbanController.components = {
    ...KanbanController.components,
    HelpdeskMemoDashboard,
};


HelpdeskMemoKanbanController.template = "helpdesk_process.HelpdeskMemoKanbanView";


import { registry } from "@web/core/registry";
registry.category("view_controllers").add("helpdeskMemoKanbanView", HelpdeskMemoKanbanController);