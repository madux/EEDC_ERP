odoo.define('task_manager.tm_admin_front', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');
  const API = require('task_manager.tm_admin_api');
  const Charts = require('task_manager.tm_admin_charts');

  // ==== Debug helpers ====
  const DEBUG = true;
  const dbg = (...args) => { if (DEBUG) console.log('[TM-Admin]', ...args); };
  const warn = (...args) => { console.warn('[TM-Admin]', ...args); };
  const err = (...args) => { console.error('[TM-Admin]', ...args); };

  function debounce(fn, ms, ctx) {
    let t;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(ctx || this, args), ms || 220);
    };
  }

  publicWidget.registry.TMAdminFront = publicWidget.Widget.extend({
    selector: '.tm-admin-page[data-tm-admin-init]',

    start: function () {
      dbg('Widget start()');
      const superDef = this._super.apply(this, arguments);
      this.$root = this.$el;

      // Bootstrap presence check (both bridges)
      const hasJqModal = !!($.fn && $.fn.modal);
      const hasBS5 = !!(window.bootstrap && window.bootstrap.Modal);
      dbg('Bootstrap present?', { jQueryModalPlugin: hasJqModal, bs5: hasBS5 });

      this._bindToolbar();
      this._bindChartControls(); // modal + type controls
      Charts.initCharts(this.$root[0]);

      const initDef = Promise.all([ this._refreshAll(), this._refreshList() ]);
      return Promise.all([superDef, initDef]);
    },

    // --- Chart toolbar + modal wiring ---
    _bindChartControls: function () {
      const $r = this.$root;
      dbg('_bindChartControls()');

      // helper: re-render the modal canvas if it's open for this chart key
      const rerenderModalFor = (key) => {
        const $m = $('#tm_ad_modal');
        if (!$m.is(':visible') || $m.data('chartKey') !== key) return;
        const canvas = document.getElementById('tm_ad_modal_canvas');
        try { if (Charts.destroyModal) Charts.destroyModal(key); } catch (_e) {}
        try {
          Charts.renderModal(key, canvas);
          const type = (Charts._state && Charts._state[key] && Charts._state[key].type) || 'bar';
          // sync active state in modal toolbar
          $m.find('.tm-ct[data-type]').removeClass('is-active');
          $m.find(`.tm-ct[data-type="${type}"]`).addClass('is-active');
          dbg('Modal re-rendered', { key, type });
        } catch (e2) {
          err('Modal re-render failed', e2);
        }
      };

      // helper: mark active type (cards + modal)
      const markActive = (key, type) => {
        dbg('markActive', { key, type });
        // cards
        this.$(`.tm-card[data-chart-key="${key}"] .tm-ct[data-type]`).removeClass('is-active');
        this.$(`.tm-card[data-chart-key="${key}"] .tm-ct[data-type="${type}"]`).addClass('is-active');
        // modal (if open & same key) + re-render modal canvas
        rerenderModalFor(key);
      };

      // initialize active type badges on first paint
      setTimeout(() => {
        ['stage','priority','overdueMgr','mgrDone','empDone','empOverdue'].forEach((key) => {
          const t = (Charts._state && Charts._state[key] && Charts._state[key].type) || 'bar';
          markActive(key, t);
        });
      }, 0);

      // change type (works for card toolbar; modal re-sync happens if modal is open)
      $r.on('click', '.tm-card-tools .tm-ct[data-type]', (e) => {
        const $btn = $(e.currentTarget);
        const key  = $btn.closest('.tm-card').data('chartKey') || $('#tm_ad_modal').data('chartKey');
        const type = $btn.data('type');
        dbg('Type button click', { key, type, origin: $btn.closest('.tm-card').length ? 'card' : 'modal' });
        if (!key || !type) return;
        Charts.setType(key, type);
        markActive(key, type);      // also re-renders modal if open
      });

      // expand → open static modal and render chart
      $(document)
        .off('click.tmExpand')
        .on('click.tmExpand', '.tm-card-tools .tm-ct[data-action="expand"]', (e) => {
          const $btn  = $(e.currentTarget);
          const $card = $btn.closest('.tm-card');
          const key   = $card.data('chartKey');
          const title = $card.find('.tm-card-title').text().trim() || 'Chart';
          dbg('Expand clicked', { key, title, cardFound: !!$card.length });
          if (!key) { warn('No chartKey on card. Aborting.'); return; }

          let $modal = $('#tm_ad_modal');
          if (!$modal.length) { err('Modal #tm_ad_modal not found'); return; }
          if ($modal.length > 1) $modal = $($modal[0]);
          if (!$modal.parent().is('body')) { $modal.appendTo('body'); }

          $modal.data('chartKey', key);
          $modal.find('.modal-title').text(title);

          $modal.off('show.bs.modal.tm shown.bs.modal.tm hide.bs.modal.tm hidden.bs.modal.tm');
          $modal.on('shown.bs.modal.tm', () => {
            dbg('Modal event: shown.bs.modal -> rendering chart');
            const canvas = document.getElementById('tm_ad_modal_canvas');
            try {
              Charts.renderModal(key, canvas);
              const type = (Charts._state && Charts._state[key] && Charts._state[key].type) || 'bar';
              $modal.find('.tm-ct[data-type]').removeClass('is-active');
              $modal.find(`.tm-ct[data-type="${type}"]`).addClass('is-active');
              dbg('Chart rendered OK', { key, type });
            } catch (e2) {
              err('renderModal failed', e2);
              $(canvas).closest('.tm-modal-canvas-wrap')
                .append('<div class="alert alert-warning mt-3">Could not render chart. Check data/Chart.js.</div>');
            }
          });
          $modal.on('hidden.bs.modal.tm', () => {
            dbg('Modal event: hidden.bs.modal -> destroying chart');
            try { Charts.destroyModal(key); } catch (_e) {}
          });

          $modal.modal({ backdrop: 'static', keyboard: false });
          $modal.modal('show');
        });

      // modal: change chart type (re-render modal immediately)
      $(document)
        .off('click.tmModalType')
        .on('click.tmModalType', '#tm_ad_modal .tm-ct[data-type]', (e) => {
          const $b   = $(e.currentTarget);
          const type = $b.data('type');
          const key  = $('#tm_ad_modal').data('chartKey');
          if (!key || !type) return;
          dbg('Modal type click', { key, type });
          Charts.setType(key, type);
          rerenderModalFor(key);        // <- make the modal reflect the new type now
        });

      // modal "collapse" icon
      $(document)
        .off('click.tmCollapse')
        .on('click.tmCollapse', '#tm_ad_modal .tm-ct[data-action="collapse"]', () => {
          dbg('Collapse clicked');
          $('#tm_ad_modal').modal('hide');
        });
    },
    // --- end chart controls ---


    _bindToolbar: function () {
      dbg('_bindToolbar()');
      // Apply / Reset
      this.$root.on('click', '#tm_ad_apply', () => { dbg('Apply clicked'); this._refreshAll(); this._refreshList(); });
      this.$root.on('click', '#tm_ad_reset', () => {
        dbg('Reset clicked');
        this.$root.find('#tm_ad_date_from,#tm_ad_date_to').val('');
        this.$root.find('#tm_ad_groupby').val('');
        this.$root.data('tm-group', '');
        this.$root.data('tm-page', 1);
        this._refreshAll(); this._refreshList();
      });

      // Debounced search
      this._refreshBothDebounced = debounce(() => {
        dbg('Search debounced apply');
        this.$root.data('tm-page', 1);
        this._refreshAll(); this._refreshList();
      }, 280, this);
      this.$root.on('input', '#tm_ad_q', () => this._refreshBothDebounced());

      // Sorting
      this.$root.on('click', '#tm_ad_table thead th', (e) => {
        const key = $(e.currentTarget).data('sort'); if (!key) return;
        const cur = this.$root.data('tm-sort') || '';
        const asc = (cur === key + ' asc');
        const next = asc ? (key + ' desc') : (key + ' asc');
        dbg('Sort click', { key, next });
        this.$root.data('tm-sort', next);
        this._syncSortIndicators();
        this._refreshList();
      });

      // Pager
      this.$root.on('click', '#tm_ad_prev', () => {
        const p = this.$root.data('tm-page') || 1;
        dbg('Pager prev', { p });
        if (p > 1) { this.$root.data('tm-page', p - 1); this._refreshList(); }
      });
      this.$root.on('click', '#tm_ad_next', () => {
        const p = this.$root.data('tm-page') || 1;
        const pages = this.$root.data('tm-pages') || 1;
        dbg('Pager next', { p, pages });
        if (p < pages) { this.$root.data('tm-page', p + 1); this._refreshList(); }
      });

      this.$root.on('change', '#tm_ad_page_input', (e) => {
        let val = parseInt($(e.currentTarget).val(), 10);
        const pages = this.$root.data('tm-pages') || 1;
        if (val >= 1 && val <= pages) {
          this.$root.data('tm-page', val);
          this._refreshList();
        } else {
          $(e.currentTarget).val(this.$root.data('tm-page') || 1);
        }
      });

    },

    /**
     * Highlight sorted column and show arrow.
     */
    _syncSortIndicators: function () {
      const sort = this.$root.data('tm-sort') || ''; // e.g. "due_date asc"
      const parts = sort.trim().split(/\s+/);
      const field = parts[0] || '';
      const dir   = (parts[1] || 'asc').toLowerCase();

      const $ths = this.$('#tm_ad_table thead th');
      $ths.removeClass('is-sorted is-sorted-asc is-sorted-desc');

      if (field) {
        const $th = this.$(`#tm_ad_table thead th[data-sort="${field}"]`);
        $th.addClass('is-sorted').addClass(dir === 'desc' ? 'is-sorted-desc' : 'is-sorted-asc');
      }
    },


    _filters: function () {
      const f = API.pickFilters(this.$root);
      dbg('_filters()', f);
      return f;
    },

    _refreshAll: async function () {
      dbg('_refreshAll() begin');
      const f = this._filters();
      const [pSummary, pDist, pLb] = await Promise.allSettled([
        API.summary(f), API.distribution(f), API.leaderboard(f),
      ]);

      const okVal = (p) => (p && p.status === 'fulfilled' && p.value && p.value.ok) ? p.value : null;

      const summary = okVal(pSummary);
      if (summary) {
        const s = summary.data || {};
        dbg('Summary data', s);
        this.$('#tm_ad_kpi_total').text(s.total ?? 0);
        this.$('#tm_ad_kpi_overdue').text(s.overdue ?? 0);
        this.$('#tm_ad_kpi_today').text(s.due_today ?? 0);
        this.$('#tm_ad_kpi_done_period').text(s.done_period ?? 0);
        this.$('#tm_ad_kpi_blocked').text(s.blocked ?? 0);
      }

      const dist = okVal(pDist);
      if (dist) {
        const d = dist.data || {};
        dbg('Distribution data', d);
        Charts.updateStage(d.by_stage || []);
        Charts.updatePriority(d.by_priority || []);
        Charts.updateOverdueMgr(d.overdue_by_manager || d.by_manager_overdue || []);
        if (d.by_employee_done) Charts.updateEmpDone(d.by_employee_done || []);
      }

      const lb = okVal(pLb);
      if (lb) {
        const L = lb.data || {};
        dbg('Leaderboard data', L);
        Charts.updateEmpDone(L.employees_done || []);
        Charts.updateEmpOverdue(L.employees_overdue || []);
        Charts.updateMgrDone(L.managers_done || []);
      }
      dbg('_refreshAll() end');
    },

    _refreshList: async function () {
      dbg('_refreshList() begin');
      try {
        const f = this._filters();

        // include paging + sort from widget state
        f.page     = this.$root.data('tm-page')  || 1;
        f.sort_by  = this.$root.data('tm-sort')  || '';
        // (server already defaults limit=20; keep as-is unless you add a selector)
        // f.limit = ...

        const res = await API.tasks(f);
        if (!(res && res.ok)) { warn('Tasks API not ok', res); return; }

        const d = res.data || {};
        dbg('Tasks data', d);

        // keep page state for PREV/NEXT and page input
        this.$root.data('tm-page',  d.page || 1);
        this.$root.data('tm-pages', d.pages || 1);

        // pager text + input sync
        this.$('#tm_ad_pager_info').text(`Page ${d.page} of ${d.pages}`);
        this.$('#tm_ad_page_input').val(d.page); // (safe even if the input isn't present)

        // “1–20 of 26 results” (handle empty set nicely)
        let start = 0, end = 0;
        if ((d.total || 0) > 0) {
          start = (d.page - 1) * d.limit + 1;
          end   = start + (d.rows?.length || 0) - 1;
        }
        this.$('#tm_ad_results_info').text(
          `${start}-${end} of ${d.total || 0} results`
        );

        // enable/disable edge buttons
        this.$('#tm_ad_prev').prop('disabled', (d.page <= 1));
        this.$('#tm_ad_next').prop('disabled', (d.page >= d.pages));

        // render table rows
        this._renderTable(d.rows || [], this.$root.data('tm-group') || '');

      } catch (e) {
        err('List refresh failed:', e);
      } finally {
        dbg('_refreshList() end');
      }
    },


    _renderTable: function (rows, groupBy) {
      const $tb = this.$('#tm_ad_table tbody').empty();
      const niceStage = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };
      const nicePrio  = { '2': 'High', '1': 'Medium', '0': 'Low' };
      dbg('_renderTable()', { rows: rows.length, groupBy });

      let lastGroup = null;
      const pushGroupRow = (label) => {
        $tb.append(`<tr class="table-light"><td colspan="7" class="fw-bold">${_.escape(label || '—')}</td></tr>`);
      };

      rows.forEach(r => {
        if (groupBy) {
          let gval = '';
          if (groupBy === 'stage') gval = niceStage[r.stage] || r.stage || '—';
          else if (groupBy === 'priority') gval = nicePrio[r.priority] || r.priority || '—';
          else if (groupBy === 'employee_id') gval = r.employee || '—';
          else if (groupBy === 'manager_id') gval = r.manager || '—';
          if (gval !== lastGroup) { pushGroupRow(gval); lastGroup = gval; }
        }

        const tr = `
          <tr>
            <td>${_.escape(r.key || '')}</td>
            <td>${_.escape(r.name || '')}</td>
            <td>${_.escape(r.employee || '')}</td>
            <td>${_.escape(niceStage[r.stage] || r.stage || '')}</td>
            <td><span class="badge rounded-pill ${r.priority==='2'?'bg-danger':r.priority==='1'?'bg-warning text-dark':'bg-secondary'}">${_.escape(r.priority_label || '')}</span></td>
            <td>${_.escape(r.due_date || '')}</td>
            <td>${_.escape(r.manager || '')}</td>
          </tr>`;
        $tb.append(tr);
      });
    },
  });

  return publicWidget.registry.TMAdminFront;
});
