/** @odoo-module **/
import { session } from '@web/session';
import { formatFloat, formatFloatTime } from '@web/views/fields/formatters';
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class memoModelDashboard extends Component {
    setup() {
        this.action = useService('action');
        this.orm = useService('orm');
        this.state = useState({
            dashboardValues: null,
        });

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        await this._fetchData();
    }
    async onActionClicked(e) {
        const action = e.currentTarget;
        const actionRef = action.getAttribute('name');
        const title = action.dataset.actionTitle || action.getAttribute('title');
        const searchViewRef = action.getAttribute('search_view_ref');
        const buttonContext = action.getAttribute('context') || '';

        if (action.getAttribute('name').includes('memo.model')) {
            return await this.action.doActionButton({
                resModel: 'memo.model',
                name: 'create_action',
                args: JSON.stringify([actionRef, title, searchViewRef]),
                context: '',
                buttonContext,
                type: 'object',
            });
        } else {
            return this.action.doActionButton({
                resModel: 'memo.model',
                name: actionRef,
                context: '',
                buttonContext,
                type: 'object',
            });
            // if (['action_view_rating_today', 'action_view_rating_7days'].includes(actionRef)) {
                
            // }
            // return this.action.doAction(actionRef);
        }
    }

    // get showDemo() {
    //     return Boolean(this.state.dashboardValues) && this.state.dashboardValues.show_demo;
    // }

    // get demoClass() {
    //     return this.showDemo ? 'o_demo o_disabled o_cursor_default' : '';
    // }

    // async onWillStart() {
    //     await this._fetchData();
    // }

    // async updateHelpdeskTarget(targetName, value) {
    //     await this.orm.write(
    //         'res.users',
    //         [session.uid],
    //         { [targetName]: value },
    //     );
    //     this.state.dashboardValues[targetName] = value;
    // }

    /**
     * @param {MouseEvent} e
     */
    // async onActionClicked(e) {
    //     if (this.showDemo) {
    //         return;
    //     }
    //     const action = e.currentTarget;
    //     const actionRef = action.getAttribute('name');
    //     const title = action.dataset.actionTitle || action.getAttribute('title');
    //     const searchViewRef = action.getAttribute('search_view_ref');
    //     const buttonContext = action.getAttribute('context') || '';

    //     if (action.getAttribute('name').includes('memo.model')) {
    //         return await this.action.doActionButton({
    //             resModel: 'helpdesk.ticket',
    //             name: 'create_action',
    //             args: JSON.stringify([actionRef, title, searchViewRef]),
    //             context: '',
    //             buttonContext,
    //             type: 'object',
    //         });
    //     } else {
    //         if (['action_view_rating_today', 'action_view_rating_7days'].includes(actionRef)) {
    //             return this.action.doActionButton({
    //                 resModel: 'helpdesk.team',
    //                 name: actionRef,
    //                 context: '',
    //                 buttonContext,
    //                 type: 'object',
    //             });
    //         }
    //         return this.action.doAction(actionRef);
    //     }
    // }

    async _fetchData() {
        this.state.dashboardValues = await this.orm.call(
            'memo.model',
            'retrieve_dashboard',
            [],
            { context: session.user_context },
        );
    }

    formatFloat(value, options = {}) {
        return formatFloat(value, options);
    }

    formatTime(value, options = {}) {
        return formatFloatTime(value, options);
    }

    parseInteger(value) {
        return parseInt(value);
    }
}

// memoModelDashboard.components = {
//     HelpdeskTeamTarget,
// };
memoModelDashboard.template = 'maach_dashboard.memoModelDashboard';
