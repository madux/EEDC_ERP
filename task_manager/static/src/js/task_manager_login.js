odoo.define('tm_taskboard.login', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');
    const core = require('web.core');

    publicWidget.registry.TmLogin = publicWidget.Widget.extend({
        selector: '.tm-page[data-tm-init]',
        start: function () {
            const loginPanel = this.$('#tm_login_panel');
            const boardPanel = this.$('#tm_board_panel');
            const loginBtn = this.$('#tm_login_btn');
            const refreshBtn = this.$('#tm_refresh');
            const switchBtn = this.$('#tm_switch');

            // Try to fetch board immediately; if session exists backend will return data
            this._fetchBoard();

            loginBtn.on('click', this._onLogin.bind(this));
            refreshBtn.on('click', this._fetchBoard.bind(this));
            switchBtn.on('click', this._onSwitch.bind(this));
            return this._super.apply(this, arguments);
        },

        _onLogin: function () {
            const staff_id = this.$('#tm_staff_id').val().trim();
            const password = this.$('#tm_password').val();
            const $err = this.$('#tm_login_error');
            $err.hide();
            if (!staff_id || !password) {
                $err.text('Enter Staff ID and Password').show();
                return;
            }
            this._rpc({
                route: '/tm/api/login',
                params: { staff_id: staff_id, password: password }
            }).then(res => {
                if (res && res.ok) {
                    this._fetchBoard();
                } else {
                    $err.text('Invalid credentials or staff-ID not found.').show();
                }
            }).guardedCatch(() => {
                $err.text('Connection error. Try again.').show();
            });
        },

        _onSwitch: function () {
            // clear session on server
            this._rpc({ route: '/tm/api/logout', params: {} }).always(() => {
                this.$('#tm_emp_name').text('Employee');
                this.$('#tm_board').empty();
                this.$('#tm_board_panel').hide();
                this.$('#tm_login_panel').show();
            });
        },

        _fetchBoard: function () {
            const loginPanel = this.$('#tm_login_panel');
            const boardPanel = this.$('#tm_board_panel');
            const $name = this.$('#tm_emp_name');
            const $board = this.$('#tm_board');
            this._rpc({ route: '/tm/api/board', params: {} }).then(res => {
                if (!res || !res.ok) {
                    loginPanel.show();
                    boardPanel.hide();
                    return;
                }
                loginPanel.hide();
                boardPanel.show();
                $name.text(res.staff_name || 'Employee');
                this._renderBoard(res.data, res.counts);
            }).guardedCatch(() => {
                loginPanel.show();
                boardPanel.hide();
            });
        },

        _renderBoard: function (grouped, counts) {
            // const qweb = this.qweb; // provided by base Widget
            const qweb = core.qweb; // provided by base Widget
            const stages = [
                { key: 'todo', title: 'To Do', count: counts && counts.todo || 0 },
                { key: 'in_progress', title: 'In Progress', count: counts && counts.in_progress || 0 },
                { key: 'review', title: 'Review', count: counts && counts.review || 0 },
                { key: 'done', title: 'Done', count: counts && counts.done || 0 },
            ];
            const html = stages.map(st => qweb.render('tm.Column', {
                stage: st,
                cards: grouped && grouped[st.key] || []
            })).join('');
            this.$('#tm_board').html(html);
            this._wireDnD();
            this._wireSearchAndFilters();
        },

        _wireSearchAndFilters: function () {
            const $search = this.$('#tm_search');
            const $prio = this.$('#tm_filter_priority');
            const apply = () => {
                const s = ($search.val() || '').toLowerCase();
                const p = $prio.val();
                this.$('.tm-card').each(function () {
                    const $c = $(this);
                    const title = ($c.find('.tm-card-title').text() || '').toLowerCase();
                    const desc = ($c.find('.tm-card-desc').text() || '').toLowerCase();
                    const prioClass = $c.find('.tm-priority').attr('class') || '';
                    const prio = prioClass.includes('prio-2') ? '2' : prioClass.includes('prio-1') ? '1' : '0';
                    const matchesText = !s || title.includes(s) || desc.includes(s);
                    const matchesPrio = !p || prio === p;
                    $c.toggle(matchesText && matchesPrio);
                });
            };
            $search.off('input').on('input', apply);
            $prio.off('change').on('change', apply);
        },

        _wireDnD: function () {
            const self = this;
            // drag start
            this.$('.tm-card').on('dragstart', function (ev) {
                ev.originalEvent.dataTransfer.setData('text/plain', $(this).data('id'));
            });
            // allow drop
            this.$('.tm-col-body').on('dragover', function (ev) { ev.preventDefault(); });
            // drop
            this.$('.tm-col-body').on('drop', function (ev) {
                ev.preventDefault();
                const id = ev.originalEvent.dataTransfer.getData('text/plain');
                const targetStage = $(this).closest('.tm-col').data('stage');
                self._moveTask(id, targetStage, $(this));
            });
        },

        // _moveTask: function (id, stage, $targetCol) {
        //     this._rpc({route: '/tm/api/move', params: {task_id: id, new_stage: stage}}).then(res => {
        //         if (res && res.ok) {
        //             // Optimistic: append card to target column
        //             const $card = this.$('.tm-card[data-id="' + id + '"]');
        //             $targetCol.append($card);
        //         } else if (res && res.message) {
        //             this.displayNotification({title: 'Move blocked', message: res.message, type: 'warning'});
        //         }
        //     }).guardedCatch(() => {
        //         this.displayNotification({title: 'Network', message: 'Could not move task', type: 'danger'});
        //     });
        // },

        _moveTask: function (id, stage, $targetCol) {
            const stageNames = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };

            this._rpc({ route: '/tm/api/move', params: { task_id: id, new_stage: stage } }).then(res => {
                if (res && res.ok) {
                    // Move the card in the DOM
                    const $card = this.$('.tm-card[data-id="' + id + '"]');
                    $targetCol.append($card);

                    // strike/unstrike when moving in/out of "done"
                    $card.toggleClass('tm-complete', stage === 'done');

                    // refresh the little count badges in each column header
                    this._updateCounts();

                    // ✅ success toast
                    this.displayNotification({
                        title: 'Task updated',
                        message: `Moved to ${stageNames[stage]} stage`,
                        type: 'success',
                        sticky: false,
                        className: 'tm-toast-success'
                    });
                } else if (res && res.message) {
                    this.displayNotification({ title: 'Move blocked', message: res.message, type: 'warning', className: 'tm-toast-warning' });
                }
            }).guardedCatch(() => {
                this.displayNotification({ title: 'Network', message: 'Could not move task', type: 'danger' });
            });
        },

        _updateCounts: function () {
            // For each column, count visible cards and update the header badge
            this.$('.tm-col').each(function () {
                const $col = $(this);
                const count = $col.find('.tm-col-body .tm-card').length;
                $col.find('.card-header .badge').text(count);
            });
        },

    });

    return publicWidget.registry.TmLogin;
});