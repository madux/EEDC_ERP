odoo.define('appraisals.list.ui', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');
  const data = require('appraisals.data');

  const LS_VIEW = 'appraisals:view';
  const LS_SORT = 'appraisals:sort';
  const LS_Q = 'appraisals:q';

  function iconUpDown(dir) { return dir === 'asc' ? 'fa-sort-asc' : 'fa-sort-desc'; }

  publicWidget.registry.AppraisalsListUI = publicWidget.Widget.extend({
    selector: '#appraisals-root',

    events: {
      'click #btnTree': '_showTree',
      'click #btnKanban': '_showKanban',
      'input #appq': '_onSearch',
      'click th.sortable': '_onSort',
      'click #btnClearSearch': '_clearSearch',
    },

    start() {
      this.$q = this.$('#appq');
      this.$tree = this.$('#appTree');
      this.$tbody = this.$('#appTbody');
      this.$kanban = this.$('#appKanban');
      this.$cards = this.$('#appCards');
      this.$empty = this.$('#appEmpty');
      this.$btnTree = this.$('#btnTree');
      this.$btnKanban = this.$('#btnKanban');

      this.records = data.getAll();

      // restore view & sort & query
      this.view = localStorage.getItem(LS_VIEW) || 'tree';
      this.sort = JSON.parse(localStorage.getItem(LS_SORT) || '{"col":"employee","dir":"asc"}');
      const q0 = localStorage.getItem(LS_Q) || '';
      if (q0) this.$q.val(q0);

      this._render();
      return this._super.apply(this, arguments);
    },

    /* View switching */
    _showTree() { this.view = 'tree'; localStorage.setItem(LS_VIEW, 'tree'); this._render(); },
    _showKanban() { this.view = 'kanban'; localStorage.setItem(LS_VIEW, 'kanban'); this._render(); },

    /* Search */
    _onSearch() { localStorage.setItem(LS_Q, this.$q.val()); this._render(); },

    /* Sort */
    _onSort(ev) {
      const col = ev.currentTarget.getAttribute('data-col');
      if (!col) return;
      const prev = this.sort || {col:'employee', dir:'asc'};
      const dir = (prev.col === col && prev.dir === 'asc') ? 'desc' : 'asc';
      this.sort = { col, dir };
      localStorage.setItem(LS_SORT, JSON.stringify(this.sort));
      this._render();
    },

    _clearSearch() { this.$q.val(''); localStorage.removeItem(LS_Q); this._render(); },

    /* Render pipeline */
    _render() {
      // 1) source
      let rows = data.getAll();

      // 2) filter by query
      const q = (this.$q.val() || '').trim().toLowerCase();
      if (q) {
        rows = rows.filter(r => (
          (r.employee || '').toLowerCase().includes(q) ||
          (r.department || '').toLowerCase().includes(q) ||
          String(r.year || '').toLowerCase().includes(q)
        ));
      }

      // 3) sort
      const sort = this.sort || { col:'employee', dir:'asc' };
      rows.sort((a,b) => {
        const A = String(a[sort.col] || '').toLowerCase();
        const B = String(b[sort.col] || '').toLowerCase();
        if (A < B) return sort.dir === 'asc' ? -1 : 1;
        if (A > B) return sort.dir === 'asc' ? 1 : -1;
        return 0;
      });

      // 4) draw
      if (rows.length === 0) {
        this.$tree.hide();
        this.$kanban.hide();
        this.$empty.show();
      } else {
        this.$empty.hide();
        if (this.view === 'kanban') {
          this._renderKanban(rows);
        } else {
          this._renderTree(rows);
        }
      }

      // 5) active view button styling
      this._updateToggleButtons();

      // 6) update sort icons (only in tree header)
      this.$('th.sortable i').attr('class', 'fa');
      const $th = this.$(`th.sortable[data-col="${sort.col}"] i`);
      $th.addClass(sort.dir === 'asc' ? 'fa-sort-asc' : 'fa-sort-desc');
    },

    _updateToggleButtons() {
      const active = (btn) => {
        btn.removeClass('btn-outline-primary appraisal-btn-outline')
           .addClass('btn-primary appraisal-btn-primary');
      };
      const inactive = (btn) => {
        btn.removeClass('btn-primary appraisal-btn-primary')
           .addClass('btn-outline-primary appraisal-btn-outline');
      };
      if (this.view === 'kanban') { inactive(this.$btnTree); active(this.$btnKanban); }
      else { active(this.$btnTree); inactive(this.$btnKanban); }
    },

    _renderTree(rows) {
      this.$kanban.hide();
      this.$tree.show();
      const html = rows.map(r => `
        <tr class="app-row" data-id="${r.id}">
          <td>${_.escape(r.employee)}</td>
          <td>${_.escape(r.year)}</td>
          <td>${_.escape(r.department)}</td>
          <td style="text-align:right;">${_.escape(r.total)}</td>
        </tr>`).join('');
      this.$tbody.html(html);
      // row click → handoff via URL ?rid=
      this.$tbody.find('tr.app-row').on('click', (ev) => {
        const rid = ev.currentTarget.getAttribute('data-id');
        window.location = `/appraisal-system?rid=${encodeURIComponent(rid)}`;
      });
    },

    _renderKanban(rows) {
      this.$tree.hide();
      this.$kanban.show();
      const cards = rows.map(r => `
        <div class="kanban-card" data-id="${r.id}">
          <div class="kanban-card__header">
            <div class="kanban-card__title">${_.escape(r.employee)}</div>
            <div class="kanban-card__badge">${_.escape(r.total)}</div>
          </div>
          <div class="kanban-card__meta">${_.escape(r.department)} • ${_.escape(r.year)}</div>
          <div class="kanban-card__cta"><i class="fa fa-eye"></i> View details</div>
        </div>`).join('');
      this.$cards.html(cards);
      this.$cards.find('.kanban-card').on('click', (ev) => {
        const rid = ev.currentTarget.getAttribute('data-id');
        window.location = `/appraisal-system?rid=${encodeURIComponent(rid)}`;
      });
    },
  });

  return publicWidget.registry.AppraisalsListUI;
});