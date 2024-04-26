import { KanbanController } from '@web/views/kanban/kanban_controller';
import { memoModelDashboard } from '@maach_dashboard/components/memo_model_dashboard';

export class memoModelKanbanController extends KanbanController { }

memoModelKanbanController.components = {
    ...KanbanController.components,
    memoModelDashboard,
};
memoModelKanbanController.template = 'maach_dashboard.memoModelKanbanView';