odoo.define('portal_request.portal_employee_dashboard', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');
  const ajax = require('web.ajax');
  const Charts = require('task_manager.tm_admin_charts');       // shared chart engine
  const AdminFront = require('task_manager.tm_admin_front');    // for modal tool wiring (type switch/expand)

  publicWidget.registry.EmployeeDashboard = publicWidget.Widget.extend({
    selector: '#portal-dashboard-form',

    start() {
      // Prepare chart canvases + bind chart toolbar / modal actions
      Charts.initCharts(this.el);
      // Reuse the admin front widget’s chart controls (tools + modal)
      // by instantiating a lightweight instance on this page container:
      this._bindChartControlsLikeAdmin();

      this._loadData();
      return this._super.apply(this, arguments);
    },

    events: {
      'click #app-icon': '_openAppGrid',
      'click #navigateBack': '_goBack',
      'click #pf_refresh': '_loadData',
      // chart type and expand/collapse are handled by _bindChartControlsLikeAdmin
    },

    _openAppGrid() {
      $('.page-section').removeClass('active');
      $('#website-app-section').addClass('active');
    },

    _goBack() {
      $('.page-section').removeClass('active');
      $('#portal-dashboard-content').addClass('active');
    },

     /** Show a message block instead of a chart when there's nothing to plot */
    _showEmptyIfNeeded(canvasSelector, show, message) {
        const $canvas = this.$(canvasSelector);
        const $body = $canvas.closest('.tm-card-body');
        const cls = 'tm-empty-chart';

        if (show) {
        $canvas.addClass('d-none');
        if (!$body.find('.' + cls).length) {
            $body.append(`
            <div class="${cls}">
                <i class="fa fa-info-circle tm-empty-icn" aria-hidden="true"></i>
                <div class="tm-empty-title">No data yet</div>
                <div class="tm-empty-sub">${_.escape(message || "There's nothing to show here yet.")}</div>
            </div>
            `);
        }
        } else {
        $canvas.removeClass('d-none');
        $body.find('.' + cls).remove();
        }
    },

    async _loadData() {
      try {
        const res = await ajax.rpc('/portal_request/api/data', {});  // implement server route
        if (!res || !res.ok) return;

        const d = res.data || {};

        // Helper: Capitalize each word
        const smartCap = (s) => String(s).split(/\s+/).map(w => {
            const cleaned = w.replace(/[^\w&]/g, '');
            const isAcronym = /^(IT|HR|ERP|R&D|CEO|CFO)$/i.test(cleaned);
            if (isAcronym) return cleaned.toUpperCase() + w.slice(cleaned.length); // keep punctuation
            return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
        }).join(' ');


        // KPI tiles
        $('#open_request').text(d.open_request ?? 0);
        $('#approved_request').text(d.approved_request ?? 0);
        $('#closed_request').text(d.closed_request ?? 0);
        $('#leave_remaining').text(d.leave_remaining ?? 0);

        // Profile (if you send these back)
        if (d.employee_name) $('#pf_name').text(smartCap(d.employee_name));
        if (d.department)    $('#pf_department').text(smartCap(d.department));
        if (d.role)          $('#pf_role').text(smartCap(d.role));
        if (d.manager)       $('#pf_manager').text(smartCap(d.manager));

        // ===== CHARTS =====
        // 1) Workload distribution
        if (Array.isArray(d.stage_distribution)) {
            Charts.updateStage(d.stage_distribution);
            const totalStage = d.stage_distribution.reduce(
            (s, r) => s + Number(r.count ?? r.id_count ?? r.employee_id_count ?? 0), 0
            );
            this._showEmptyIfNeeded(
            '#tm_ad_chart_stage',
            totalStage === 0,
            "You haven't been assigned any tasks yet by your manager. When tasks are assigned, they’ll appear here."
            );
        }

        // 2) Performance chart (optional empty state too)
        if (Array.isArray(d.performance_rows)) {
            Charts.updateEmpDone(d.performance_rows);
            const totalPerf = d.performance_rows.reduce((s, r) => s + Number(r.count ?? 0), 0);
            this._showEmptyIfNeeded(
            '#tm_ad_chart_emp_done',
            totalPerf === 0,
            "No performance data to display yet."
            );
        }

      } catch (e) {
        console.error('[EmployeeDashboard] load error', e);
      }
    },

    // Borrow the admin dashboard chart-toolbar behavior without duplicating code
    _bindChartControlsLikeAdmin() {
      // Minimal subset of tm_admin_front’s behavior to keep this file self-contained:
      const $root = $(this.el);

      // Change type (works for cards; modal will sync when open)
      $root.on('click', '.tm-card-tools .tm-ct[data-type]', (e) => {
        const $btn = $(e.currentTarget);
        const $card = $btn.closest('.tm-card');
        const key = $card.data('chartKey') ||
                    ($card.find('canvas#tm_ad_chart_stage').length ? 'stage' :
                     $card.find('canvas#tm_ad_chart_emp_done').length ? 'empDone' : null);
        const type = $btn.data('type');
        if (!key || !type) return;
        Charts.setType(key, type);
        $card.find('.tm-ct[data-type]').removeClass('is-active');
        $btn.addClass('is-active');
      });

      // Expand to modal
      $(document).off('click.pfExpand')
        .on('click.pfExpand', '.tm-card-tools .tm-ct[data-action="expand"]', (e) => {
          const $card = $(e.currentTarget).closest('.tm-card');
          let key = null, title = $card.find('.tm-card-head').text().trim() || 'Chart';
          if ($card.find('canvas#tm_ad_chart_stage').length) key = 'stage';
          if ($card.find('canvas#tm_ad_chart_emp_done').length) key = 'empDone';
          if (!key) return;

          const $modal = $('#tm_ad_modal').appendTo('body');
          $modal.data('chartKey', key);
          $modal.find('.modal-title').text(title);
          $modal.off('shown.bs.modal hidden.bs.modal');

          $modal.on('shown.bs.modal', () => {
            const canvas = document.getElementById('tm_ad_modal_canvas');
            Charts.renderModal(key, canvas);
            // mark active in modal toolbar
            const t = (Charts._state && Charts._state[key] && Charts._state[key].type) || 'bar';
            $modal.find('.tm-ct[data-type]').removeClass('is-active');
            $modal.find(`.tm-ct[data-type="${t}"]`).addClass('is-active');
          });
          $modal.on('hidden.bs.modal', () => Charts.destroyModal(key));

          $modal.modal({ backdrop: 'static', keyboard: false }).modal('show');
        });

      // Collapse modal
      $(document).off('click.pfCollapse')
        .on('click.pfCollapse', '#tm_ad_modal .tm-ct[data-action="collapse"]', () => {
          $('#tm_ad_modal').modal('hide');
        });
    },
  });

  return publicWidget.registry.EmployeeDashboard;
});
