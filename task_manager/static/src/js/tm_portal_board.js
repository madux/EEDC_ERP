odoo.define('tm_taskboard.portal_board', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');
    const core = require('web.core');

    publicWidget.registry.TmPortalBoard = publicWidget.Widget.extend({
        selector: '.tm-page[data-tm-init]',

        _dragInfo: null,

        start: function () {
            // No custom login: just fetch data. Keep Refresh.
            this._fetchBoard();
            this.$('#tm_refresh').on('click', this._fetchBoard.bind(this));
            return this._super.apply(this, arguments);
        },

        // -------- data --------
        _fetchBoard: function () {
            this._rpc({ route: '/tm/api/board', params: {} })
                .then(res => {
                    if (!res || !res.ok) return;
                    this._renderBoard(res.data, res.counts);
                })
                .guardedCatch(() => {
                    this.displayNotification({ title: 'Network', message: 'Could not load board', type: 'danger' });
                });
        },

        _renderBoard: function (grouped, counts) {
            const qweb = core.qweb;
            const stages = [
                { key: 'todo', title: 'To Do', count: (counts && counts.todo) || 0 },
                { key: 'in_progress', title: 'In Progress', count: (counts && counts.in_progress) || 0 },
                { key: 'review', title: 'Review', count: (counts && counts.review) || 0 },
                { key: 'done', title: 'Done', count: (counts && counts.done) || 0 },
            ];
            const html = stages.map(st => qweb.render('tm.Column', {
                stage: st,
                cards: (grouped && grouped[st.key]) || []
            })).join('');
            this.$('#tm_board').html(html);

            this._wireDnD();
            this._wireSearchAndFilters();
            this._applyOverdueBadges();
            this._updateCounts(); // ensure empty-state aligned with visibility

            //apply due/overdue visuals
            this._applyOverdueBadges(this.$('#tm_board'));
            this._refreshDoneDueLabels(this.$('#tm_board'));
        },

        // -------- search & filters --------
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

                this._updateCounts();
            };

            $search.off('input').on('input', apply);
            $prio.off('change').on('change', apply);
        },

        // -------- drag & drop (with same-column reorder, no toast) --------
        _insertCard: function ($card, $body, clientY) {
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
            if (!inserted) $body.append($card);
        },

        _wireDnD: function () {
            const self = this;

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

            this.$('.tm-col-body')
                .on('dragover', function (ev) { ev.preventDefault(); })
                .on('dragenter', function () { $(this).closest('.tm-col').addClass('drag-over'); })
                .on('dragleave', function () { $(this).closest('.tm-col').removeClass('drag-over'); });

            this.$('.tm-col-body').on('drop', function (ev) {
                ev.preventDefault();
                const clientY = ev.originalEvent.clientY;
                const id = ev.originalEvent.dataTransfer.getData('text/plain');
                const $targetBody = $(this);
                const $targetCol = $targetBody.closest('.tm-col');
                $targetCol.removeClass('drag-over');
                const targetStage = $targetCol.data('stage');

                // Same-stage reorder: DOM only, no RPC, no toast
                if (self._dragInfo && String(self._dragInfo.id) === String(id) &&
                    targetStage === self._dragInfo.sourceStage) {

                    self._insertCard(self._dragInfo.$card, $targetBody, clientY);
                    self._updateCounts([$targetCol]); // keeps empty placeholder correct
                    self._dragInfo = null;
                    return;
                }

                // Cross-stage move → RPC + success toast on OK
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
                        const $sourceCol = $card.closest('.tm-col');
                        const $targetCol = $targetBody.closest('.tm-col');

                        // insert at drop position
                        this._insertCard($card, $targetBody, clientY);

                        this._applyOverdueBadges($targetBody.closest('.tm-col'));
                        this._refreshDoneDueLabels($targetBody.closest('.tm-col'));

                        // strike-through when moved to Done
                        $card.toggleClass('tm-complete', stage === 'done');

                        // refresh counts/empty for both cols
                        this._updateCounts([$sourceCol, $targetCol]);

                        this.displayNotification({
                            title: 'Task updated',
                            message: `Moved to ${stageNames[stage]} stage`,
                            type: 'success', sticky: false, className: 'tm-toast-success'
                        });
                    } else if (res && res.message) {
                        this.displayNotification({
                            title: 'Move blocked',
                            message: res.message,
                            type: 'warning', className: 'tm-toast-warning'
                        });
                    }
                })
                .guardedCatch(() => {
                    this.displayNotification({ title: 'Network', message: 'Could not move task', type: 'danger' });
                });
        },

        // -------- counts & empty state --------
        _updateCounts: function (scopedCols) {
            const $cols = scopedCols ? $(scopedCols) : this.$('.tm-col');
            $cols.each(function () {
                const $col = $(this);
                const $body = $col.find('.tm-col-body');
                const count = $body.find('.tm-card:visible').length;

                $col.find('.tm-stage-header .tm-count, .card-header .badge').text(count);
                $body.find('.tm-empty').toggle(count === 0);
            });
        },

        // -------- overdue visuals --------
        // Parse "YYYY-MM-DD" as LOCAL midnight (reliable across browsers)
        _safeParseISODate: function (iso) {
            if (!iso || typeof iso !== 'string') return null;
            const parts = iso.split('-');
            if (parts.length !== 3) return null;
            const y = Number(parts[0]), m = Number(parts[1]) - 1, d = Number(parts[2]);
            if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return null;
            return new Date(y, m, d); // local midnight
        },

        // Paint overdue (red stripe + red due text), but never in Done column
        _applyOverdueBadges: function (scope) {
            const today = new Date();
            const todayMid = new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const $scope = scope ? $(scope) : this.$el;

            $scope.find('.tm-card').each((_, el) => {
                const $c = $(el);
                const $due = $c.find('.tm-due');
                const iso = $due.attr('data-due');   // use attr to avoid jQuery data cache
                if (!iso) return;

                const dueDate = this._safeParseISODate(iso);
                if (!dueDate) return;

                const inDone = $c.closest('.tm-col').is('[data-stage="done"]');
                const isOverdue = !inDone && (dueDate < todayMid);

                $c.toggleClass('tm-overdue', isOverdue);
                $due.toggleClass('overdue', isOverdue);
            });
        },

        // In the Done column show "Completed: <date>" and clear overdue visuals
        _refreshDoneDueLabels: function (scope) {
            const $scope = scope ? $(scope) : this.$el;
            $scope.find('.tm-col[data-stage="done"] .tm-card').each((_, el) => {
                const $c = $(el);
                const $due = $c.find('.tm-due');
                const iso = $due.attr('data-due');
                if (!iso) return;

                // Clear any overdue styling for completed tasks
                $c.removeClass('tm-overdue');
                $due.removeClass('overdue');

                // Replace label text (keeps the clock icon)
                $due.html('<i class="fa fa-clock-o me-1"></i>Completed: ' + iso);
            });
        },

    });

    return publicWidget.registry.TmPortalBoard;
});
