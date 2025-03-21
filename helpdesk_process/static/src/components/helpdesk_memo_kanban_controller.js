/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { HelpdeskMemoDashboard } from "./helpdesk_memo_dashboard";

/**
 * Extends the default KanbanController
 * to include our custom HelpdeskMemoDashboard component.
 */
export class HelpdeskMemoKanbanController extends KanbanController {}

HelpdeskMemoKanbanController.components = {
    ...KanbanController.components,
    HelpdeskMemoDashboard,
};

// The template name must match what we'll define in XML
HelpdeskMemoKanbanController.template = "helpdesk_process.HelpdeskMemoKanbanView";
