odoo.define('task_manager.tm_admin_charts', function (require) {
  'use strict';

  let Chart = window.Chart;
  function _ensureChart() { if (!Chart) Chart = window.Chart; }

  const charts = {};
  const COLORS = {
    stage: {
      todo:        '#6366f1', // indigo
      in_progress: '#f59e0b', // amber
      review:      '#a855f7', // purple
      done:        '#16a34a', // green
    },
    priority: ['#ef4444', '#f59e0b', '#9ca3af'], // high, med, low
    bars: '#4f46e5',
    grid: 'rgba(2,6,23,.08)',
    tick: '#64748b',
    text: '#0f172a',
  };

  function _axis() {
    return {
      grid:  { color: COLORS.grid },
      ticks: { color: COLORS.tick },
    };
  }

  // Coerce any “count-like” property coming from read_group
  function _valCount(r) {
    return Number(
      (r && (r.count ?? r.id_count ?? r.employee_id_count ?? r.manager_id_count)) || 0
    );
  }

  function initCharts(rootEl) {
    _ensureChart();
    if (!Chart) return;

    Chart.defaults.color = COLORS.text;
    Chart.defaults.borderColor = COLORS.grid;

    // Stage distribution (doughnut)
    charts.stage = new Chart(rootEl.querySelector('#tm_ad_chart_stage'), {
      type: 'doughnut',
      data: {
        labels: [],
        datasets: [{
          data: [],
          backgroundColor: [
            COLORS.stage.todo,
            COLORS.stage.in_progress,
            COLORS.stage.review,
            COLORS.stage.done,
          ],
        }],
      },
      options: { plugins: { legend: { position: 'bottom' } } },
    });

    // Priority mix (bar)
    charts.priority = new Chart(rootEl.querySelector('#tm_ad_chart_priority'), {
      type: 'bar',
      data: {
        labels: ['High', 'Medium', 'Low'],
        datasets: [{ label: 'Tasks', data: [], backgroundColor: COLORS.priority }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } },
      },
    });

    // Overdue by Manager (horizontal bar)
    charts.overdueMgr = new Chart(rootEl.querySelector('#tm_ad_chart_overdue_mgr'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Overdue', data: [], backgroundColor: COLORS.bars }] },
      options: { indexAxis: 'y', plugins: { legend: { display: false } },
        scales: { x: { ..._axis(), beginAtZero: true }, y: _axis() },
      },
    });

    // Top Employees (Done)
    charts.empDone = new Chart(rootEl.querySelector('#tm_ad_chart_emp_done'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Done', data: [], backgroundColor: COLORS.stage.done }] },
      options: { plugins: { legend: { display: false } },
        scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } },
      },
    });

    // Top Overdue (Employees)
    charts.empOverdue = new Chart(rootEl.querySelector('#tm_ad_chart_emp_overdue'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Overdue', data: [], backgroundColor: COLORS.stage.review }] },
      options: { plugins: { legend: { display: false } },
        scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } },
      },
    });

    // Top Managers (Done)
    charts.mgrDone = new Chart(rootEl.querySelector('#tm_ad_chart_mgr_done'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Done', data: [], backgroundColor: COLORS.stage.done }] },
      options: { indexAxis: 'y', plugins: { legend: { display: false } },
        scales: { x: { ..._axis(), beginAtZero: true }, y: _axis() },
      },
    });
  }

  // -------- Updaters --------
  function updateStage(rows) {
    const ORDER = ['todo', 'in_progress', 'review', 'done'];
    const LABELS = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };

    const counts = ORDER.map(k => {
      const r = rows.find(x => (x.key ?? x.stage) === k) || {};
      return Number(r.count ?? r.id_count ?? 0);
    });

    charts.stage.data.labels = ORDER.map(k => (rows.find(x => x.key === k)?.label || LABELS[k]));
    charts.stage.data.datasets[0].data = counts;
    charts.stage.update();
  }

  function updatePriority(rows) {
    const ORDER = ['2', '1', '0']; // High, Medium, Low
    const LABELS = { '2': 'High', '1': 'Medium', '0': 'Low' };

    charts.priority.data.labels = ORDER.map(k => (rows.find(x => x.key === k)?.label || LABELS[k]));
    charts.priority.data.datasets[0].data = ORDER.map(k => {
      const r = rows.find(x => (String(x.key ?? x.priority) === k)) || {};
      return Number(r.count ?? r.id_count ?? 0);
    });
    charts.priority.update();
  }

  function updateOverdueMgr(rows) {
    charts.overdueMgr.data.labels = rows.map(r => r.name || '—');
    charts.overdueMgr.data.datasets[0].data = rows.map(_valCount);
    charts.overdueMgr.update();
  }

  function updateEmpDone(rows) {
    charts.empDone.data.labels = rows.map(r => r.name || '—');
    charts.empDone.data.datasets[0].data = rows.map(_valCount);
    charts.empDone.update();
  }

  function updateEmpOverdue(rows) {
    charts.empOverdue.data.labels = rows.map(r => r.name || '—');
    charts.empOverdue.data.datasets[0].data = rows.map(_valCount);
    charts.empOverdue.update();
  }

  function updateMgrDone(rows) {
    charts.mgrDone.data.labels = rows.map(r => r.name || '—');
    charts.mgrDone.data.datasets[0].data = rows.map(_valCount);
    charts.mgrDone.update();
  }

  // Export 
  return {
    initCharts,
    updateStage,
    updatePriority,
    updateOverdueMgr,
    updateEmpDone,
    updateEmpOverdue,
    updateMgrDone,
  };
});