odoo.define('tm_taskboard.login', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');
    const core = require('web.core');

    publicWidget.registry.TmLogin = publicWidget.Widget.extend({
        selector: '.tm-page[data-tm-init]',

        _dragInfo: null,

        start: function () {
            // try to load board immediately
            this._fetchBoard();

            this.$('#tm_login_btn').on('click', this._onLogin.bind(this));
            this.$('#tm_refresh').on('click', this._fetchBoard.bind(this));
            this.$('#tm_switch').on('click', this._onSwitch.bind(this));
            return this._super.apply(this, arguments);
        },

        _onLogin: function () {
            const staff_id = this.$('#tm_staff_id').val().trim();
            const password = this.$('#tm_password').val();
            const $err = this.$('#tm_login_error').hide();

            if (!staff_id || !password) {
                $err.text('Enter Staff ID and Password').show();
                return;
            }
            this._rpc({ route: '/tm/api/login', params: { staff_id, password } })
                .then(res => {
                    if (res && res.ok) this._fetchBoard();
                    else $err.text('Invalid credentials or staff-ID not found.').show();
                })
                .guardedCatch(() => $err.text('Connection error. Try again.').show());
        },

        _onSwitch: function () {
            this._rpc({ route: '/tm/api/logout', params: {} }).always(() => {
                this.$('#tm_emp_name').text('Employee');
                this.$('#tm_board').empty();
                this.$('#tm_board_panel').hide();
                this.$('#tm_login_panel').show();
            });
        },

        _fetchBoard: function () {
            const $login = this.$('#tm_login_panel');
            const $panel = this.$('#tm_board_panel');
            const $name = this.$('#tm_emp_name');

            this._rpc({ route: '/tm/api/board', params: {} })
                .then(res => {
                    if (!res || !res.ok) {
                        $login.show(); $panel.hide(); return;
                    }
                    $login.hide(); $panel.show();
                    $name.text(res.staff_name || 'Employee');
                    this._renderBoard(res.data, res.counts);
                })
                .guardedCatch(() => { $login.show(); $panel.hide(); });
        },

        _renderBoard: function (grouped, counts) {
            const qweb = core.qweb;
            const stages = [
                { key: 'todo', title: 'To Do', count: counts && counts.todo || 0 },
                { key: 'in_progress', title: 'In Progress', count: counts && counts.in_progress || 0 },
                { key: 'review', title: 'Review', count: counts && counts.review || 0 },
                { key: 'done', title: 'Done', count: counts && counts.done || 0 },
            ];
            const html = stages.map(st => qweb.render('tm.Column', {
                stage: st,
                cards: (grouped && grouped[st.key]) || []
            })).join('');
            this.$('#tm_board').html(html);

            this._wireDnD();
            this._wireSearchAndFilters();

            // ensure counts & empty placeholders are correct on first render
            this._updateCounts();
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
                    const cls = $c.find('.tm-priority').attr('class') || '';
                    const prio = cls.includes('prio-2') ? '2' : cls.includes('prio-1') ? '1' : '0';

                    const matchesText = !s || title.includes(s) || desc.includes(s);
                    const matchesPrio = !p || prio === p;
                    $c.toggle(matchesText && matchesPrio);
                });

                // keep badges/empty-state in sync with visibility changes
                this._updateCounts();
            };

            $search.off('input').on('input', apply);
            $prio.off('change').on('change', apply);
        },

        _insertCard: function ($card, $body, clientY) {
            // Insert before the first sibling whose midpoint is below the drop Y.
            const $siblings = $body.children('.tm-card').not($card);
            let inserted = false;
            $siblings.each(function () {
                const $s = $(this);
                const mid = $s.offset().top + ($s.outerHeight() / 2);
                if (clientY < mid) {
                    $card.insertBefore($s);
                    inserted = true;
                    return false; // break
                }
            });
            if (!inserted) {
                $body.append($card); // fallback: end of column
            }
        },

        // _wireDnD: function () {
        //     const self = this;

        //     // drag start
        //     this.$('.tm-card').on('dragstart', function (ev) {
        //         ev.originalEvent.dataTransfer.setData('text/plain', $(this).data('id'));
        //     });

        //     // drag affordance on columns
        //     this.$('.tm-col-body')
        //         .on('dragover', function (ev) { ev.preventDefault(); })
        //         .on('dragenter', function () { $(this).closest('.tm-col').addClass('drag-over'); })
        //         .on('dragleave', function () { $(this).closest('.tm-col').removeClass('drag-over'); });

        //     // drop
        //     this.$('.tm-col-body').on('drop', function (ev) {
        //         ev.preventDefault();
        //         $(this).closest('.tm-col').removeClass('drag-over');

        //         const id = ev.originalEvent.dataTransfer.getData('text/plain');
        //         const targetStage = $(this).closest('.tm-col').data('stage');
        //         self._moveTask(id, targetStage, $(this));
        //     });
        // },

        // _moveTask: function (id, stage, $targetCol) {
        //     const stageNames = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };

        //     this._rpc({ route: '/tm/api/move', params: { task_id: id, new_stage: stage } })
        //         .then(res => {
        //             if (res && res.ok) {
        //                 const $card = this.$('.tm-card[data-id="' + id + '"]');
        //                 const $sourceCol = $card.closest('.tm-col');
        //                 const $targetOuterCol = $targetCol.closest('.tm-col');

        //                 // move in DOM
        //                 $targetCol.append($card);

        //                 // strike/unstrike when entering/leaving "done"
        //                 $card.toggleClass('tm-complete', stage === 'done');

        //                 // update only affected columns (faster)
        //                 this._updateCounts([$sourceCol, $targetOuterCol]);

        //                 // toast
        //                 this.displayNotification({
        //                     title: 'Task updated',
        //                     message: `Moved to ${stageNames[stage]} stage`,
        //                     type: 'success',
        //                     sticky: false,
        //                     className: 'tm-toast-success'
        //                 });
        //             } else if (res && res.message) {
        //                 this.displayNotification({
        //                     title: 'Move blocked',
        //                     message: res.message,
        //                     type: 'warning',
        //                     className: 'tm-toast-warning'
        //                 });
        //             }
        //         })
        //         .guardedCatch(() => {
        //             this.displayNotification({ title: 'Network', message: 'Could not move task', type: 'danger' });
        //         });
        // },
        _wireDnD: function () {
            const self = this;

            // drag start — remember source column & card
            this.$('.tm-card').on('dragstart', function (ev) {
                const $card = $(this);
                const id = $card.data('id');
                const $sourceCol = $card.closest('.tm-col');
                self._dragInfo = {
                    id,
                    $card,
                    $sourceCol,
                    sourceStage: $sourceCol.data('stage'),
                };
                ev.originalEvent.dataTransfer.setData('text/plain', String(id));
            });

            // column affordance
            this.$('.tm-col-body')
                .on('dragover', function (ev) { ev.preventDefault(); })
                .on('dragenter', function () { $(this).closest('.tm-col').addClass('drag-over'); })
                .on('dragleave', function () { $(this).closest('.tm-col').removeClass('drag-over'); });

            // drop
            this.$('.tm-col-body').on('drop', function (ev) {
                ev.preventDefault();
                const clientY = ev.originalEvent.clientY;
                const id = ev.originalEvent.dataTransfer.getData('text/plain');
                const $targetBody = $(this);
                const $targetCol = $targetBody.closest('.tm-col');
                $targetCol.removeClass('drag-over');
                const targetStage = $targetCol.data('stage');

                // If same column/stage → just reorder in DOM, no RPC, no toast
                if (self._dragInfo && String(self._dragInfo.id) === String(id) &&
                    targetStage === self._dragInfo.sourceStage) {

                    self._insertCard(self._dragInfo.$card, $targetBody, clientY);
                    self._updateCounts([$targetCol]); // counts unchanged, but keeps empty state correct
                    self._dragInfo = null;
                    return;
                }

                // Different stage → call move API; toast will show only on success
                self._moveTask(id, targetStage, $targetBody, clientY);
                self._dragInfo = null;
            });
        },
        
        _moveTask: function (id, stage, $targetBody, clientY) {
            const stageNames = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };

            this._rpc({ route: '/tm/api/move', params: { task_id: id, new_stage: stage } })
                .then(res => {
                    if (res && res.ok) {
                        const $card = this.$('.tm-card[data-id="' + id + '"]');
                        const $sourceCol = ($card.closest('.tm-col').length ? $card.closest('.tm-col') : (this._dragInfo && this._dragInfo.$sourceCol));
                        const $targetCol = $targetBody.closest('.tm-col');

                        // Move card visually at the exact drop position
                        this._insertCard($card, $targetBody, clientY);

                        // Strike/unstrike for Done
                        $card.toggleClass('tm-complete', stage === 'done');

                        // Update the two columns
                        this._updateCounts([$sourceCol, $targetCol]);

                        // ✅ Toast only for cross-stage moves (we never call here for same-stage)
                        this.displayNotification({
                            title: 'Task updated',
                            message: `Moved to ${stageNames[stage]} stage`,
                            type: 'success',
                            sticky: false,
                            className: 'tm-toast-success'
                        });
                    } else if (res && res.message) {
                        this.displayNotification({
                            title: 'Move blocked',
                            message: res.message,
                            type: 'warning',
                            className: 'tm-toast-warning'
                        });
                    }
                })
                .guardedCatch(() => {
                    this.displayNotification({ title: 'Network', message: 'Could not move task', type: 'danger' });
                });
        },

        /**
         * Update header counts and toggle each column's empty placeholder.
         * If `scopedCols` is provided, only those columns are updated.
         */
        _updateCounts: function (scopedCols) {
            const $cols = scopedCols ? $(scopedCols) : this.$('.tm-col');

            $cols.each(function () {
                const $col = $(this);
                const $body = $col.find('.tm-col-body');
                const count = $body.find('.tm-card:visible').length;

                // header badge (supports either .tm-count or a plain .badge)
                $col.find('.tm-stage-header .tm-count, .card-header .badge').text(count);

                // empty placeholder (must exist in template as .tm-empty)
                $body.find('.tm-empty').toggle(count === 0);
            });
        },
    });

    return publicWidget.registry.TmLogin;
});
