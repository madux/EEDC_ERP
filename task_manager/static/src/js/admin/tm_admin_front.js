odoo.define('task_manager.tm_admin_front', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');
  const API = require('task_manager.tm_admin_api');
  const Charts = require('task_manager.tm_admin_charts');

  publicWidget.registry.TMAdminFront = publicWidget.Widget.extend({
    selector: '.tm-admin-page[data-tm-admin-init]',

    // IMPORTANT: classic function syntax so this._super is available
    start: function () {
      const superDef = this._super.apply(this, arguments);

      this.$root = this.$el;
      this._bindToolbar();
      Charts.initCharts(this.$root[0]);

      const initDef = this._refreshAll(); // returns a Promise
      return Promise.all([superDef, initDef]);
    },

    _bindToolbar: function () {
      this.$root.on('click', '#tm_ad_apply', () => this._refreshAll());
      this.$root.on('click', '#tm_ad_reset', () => {
        this.$root.find('#tm_ad_date_from,#tm_ad_date_to').val('');
        this.$root.find('#tm_ad_grain').val('week');
        this.$root.find('#tm_ad_stage option,#tm_ad_priority option').prop('selected', false);
        this._refreshAll();
      });
      this.$root.on('change', '#tm_ad_stacked', () => this._refreshTimeseriesOnly());

      // Optional: submit on Enter in search (if you add #tm_ad_q)
      this.$root.on('keydown', '#tm_ad_q', (e) => { if (e.key === 'Enter') this._refreshAll(); });

      // quick filters
      this.$root.on('click', '.tm-filter', (e) => {
        e.preventDefault();
        const k = $(e.currentTarget).data('key');
        const arr = this.$root.data('tm-quick') || [];
        const i = arr.indexOf(k);
        if (i === -1) arr.push(k); else arr.splice(i, 1);
        this.$root.data('tm-quick', arr);
        this._refreshAll(); this._refreshList();
      });

      // group by
      this.$root.on('click', '.tm-groupby', (e) => {
        e.preventDefault();
        const k = $(e.currentTarget).data('key') || '';
        this.$root.data('tm-group', k);
        this.$root.data('tm-page', 1);
        this._refreshList();
      });

      // view toggle
      this.$root.on('click', '[data-view]', (e) => {
        const v = $(e.currentTarget).data('view');
        this.$root.find('[data-view]').removeClass('active');
        $(e.currentTarget).addClass('active');
        if (v === 'list') {
          this.$('#tm_ad_list_wrap').removeClass('d-none');
          this._refreshList();
        } else {
          this.$('#tm_ad_list_wrap').addClass('d-none');
        }
      });

      // list search
      this.$root.on('input', '#tm_ad_text_q', () => {
        this.$root.data('tm-page', 1);
        this._refreshListDebounced();
      });

      // table sort
      this.$root.on('click', '#tm_ad_table thead th', (e) => {
        const key = $(e.currentTarget).data('sort');
        if (!key) return;
        // toggle asc/desc for simple keys; keep default for composite
        const cur = this.$root.data('tm-sort') || '';
        const asc = (cur === key + ' asc');
        const next = asc ? (key + ' desc') : (key + ' asc');
        this.$root.data('tm-sort', next);
        this._refreshList();
      });

      // pager
      this.$root.on('click', '#tm_ad_prev', () => {
        const p = this.$root.data('tm-page') || 1;
        if (p > 1) { this.$root.data('tm-page', p - 1); this._refreshList(); }
      });
      this.$root.on('click', '#tm_ad_next', () => {
        const p = this.$root.data('tm-page') || 1;
        const pages = this.$root.data('tm-pages') || 1;
        if (p < pages) { this.$root.data('tm-page', p + 1); this._refreshList(); }
      });

      // debounce
      this._refreshListDebounced = (function (fn, ms) {
        let t; return () => { clearTimeout(t); t = setTimeout(() => this._refreshList(), ms || 220); };
      }).call(this);
    },

    _filters: function () {
      return API.pickFilters(this.$root);
    },

    _refreshAll: async function () {
      const f = this._filters();

      // Run all calls in parallel but don't fail-fast
      const [pSummary, pDist, pTs, pLb] = await Promise.allSettled([
        API.summary(f),
        API.distribution(f),
        API.timeseries(f),
        API.leaderboard(f),
      ]);

      // Small helper
      const okVal = (p) => (p && p.status === 'fulfilled' && p.value && p.value.ok) ? p.value : null;
      const logRej = (label, p) => { if (p && p.status === 'rejected') console.error(`${label} failed:`, p.reason); };

      // KPIs
      const summary = okVal(pSummary);
      if (summary) {
        const s = summary.data || {};
        this.$('#tm_ad_kpi_total').text(s.total ?? 0);
        this.$('#tm_ad_kpi_overdue').text(s.overdue ?? 0);
        this.$('#tm_ad_kpi_today').text(s.due_today ?? 0);
        this.$('#tm_ad_kpi_done_period').text(s.done_period ?? 0);
        this.$('#tm_ad_kpi_blocked').text(s.blocked ?? 0);
      } else { logRej('summary', pSummary); }

      // Distribution charts
      const dist = okVal(pDist);
      if (dist) {
        const d = dist.data || {};
        Charts.updateStage(d.by_stage || []);
        Charts.updatePriority(d.by_priority || []);
        // accept either key name
        Charts.updateOverdueMgr(d.overdue_by_manager || d.by_manager_overdue || []);
        // if your distribution endpoint also returns top employees (optional)
        if (d.by_employee_done) Charts.updateEmpDone(d.by_employee_done || []);
      } else { logRej('distribution', pDist); }

      // Leaderboards
      const lb = okVal(pLb);
      if (lb) {
        const L = lb.data || {};
        Charts.updateEmpDone(L.employees_done || L.by_employee_done || []);
        Charts.updateEmpOverdue(L.employees_overdue || L.by_employee_overdue || []);
        // if leaderboard also carries manager overdue
        if (L.overdue_by_manager || L.by_manager_overdue) {
          Charts.updateOverdueMgr(L.overdue_by_manager || L.by_manager_overdue || []);
        }
      } else { logRej('leaderboard', pLb); }

      // Time series (respect the stacked toggle)
      const ts = okVal(pTs);
      if (ts) {
        const stacked = this.$('#tm_ad_stacked').is(':checked');
        Charts.updateTimeseries(ts.data.grain, ts.data.points || [], stacked);
      } else { logRej('timeseries', pTs); }
    },

    _refreshTimeseriesOnly: async function () {
      try {
        const f = this._filters();
        const ts = await API.timeseries(f);
        if (ts && ts.ok) {
          const stacked = this.$('#tm_ad_stacked').is(':checked');
          Charts.updateTimeseries(ts.data.grain, ts.data.points || [], stacked);
        }
      } catch (err) {
        console.error('Timeseries refresh failed:', err);
      }
    },

    _refreshList: async function () {
      try {
        const f = this._filters();
        const res = await API.tasks(f);
        if (!(res && res.ok)) return;
        const d = res.data;

        this.$root.data('tm-pages', d.pages || 1);
        this.$('#tm_ad_pager_info').text(`Page ${d.page} of ${d.pages}`);
        this.$('#tm_ad_results_info').text(`${d.total} result${d.total === 1 ? '' : 's'}`);

        this._renderTable(d.rows || [], this.$root.data('tm-group') || '');
      } catch (err) {
        console.error('List refresh failed:', err);
      }
    },

    _renderTable: function (rows, groupBy) {
      const $tb = this.$('#tm_ad_table tbody').empty();

      const niceStage = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };
      const nicePrio  = { '2':'High', '1':'Medium', '0':'Low' };

      let lastGroup = null;
      const pushGroupRow = (label) => {
        $tb.append(`<tr class="table-light"><td colspan="7" class="fw-bold">${_.escape(label || '—')}</td></tr>`);
      };

      rows.forEach(r => {
        // group break headers
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
