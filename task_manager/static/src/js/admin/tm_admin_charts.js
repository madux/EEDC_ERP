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

  function initCharts(rootEl) {
    _ensureChart();
    if (!Chart) return;

    Chart.defaults.color = COLORS.text;
    Chart.defaults.borderColor = COLORS.grid;

    // Stage distribution (doughnut)
    charts.stage = new Chart(rootEl.querySelector('#tm_ad_chart_stage'), {
      type: 'doughnut',
      data: { labels: [], datasets: [{ data: [], backgroundColor: [
        COLORS.stage.todo, COLORS.stage.in_progress, COLORS.stage.review, COLORS.stage.done
      ]}]},
      options: { plugins: { legend: { position: 'bottom' } } },
    });

    // Priority mix (bar)
    charts.priority = new Chart(rootEl.querySelector('#tm_ad_chart_priority'), {
      type: 'bar',
      data: { labels: ['High','Medium','Low'], datasets: [{ label: 'Tasks', data: [], backgroundColor: COLORS.priority }] },
      options: { plugins: { legend: { display: false }}, scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } } },
    });

    // Overdue by Manager (horizontal bar)
    charts.overdueMgr = new Chart(rootEl.querySelector('#tm_ad_chart_overdue_mgr'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Overdue', data: [], backgroundColor: COLORS.bars }] },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false }},
        scales: { x: { ..._axis(), beginAtZero: true }, y: _axis() },
      },
    });

    // Timeseries (line with time scale)
    charts.timeseries = new Chart(rootEl.querySelector('#tm_ad_chart_timeseries'), {
      type: 'line',
      data: { datasets: [] },
      options: {
        parsing: false,
        plugins: { legend: { position: 'bottom' } },
        elements: { line: { tension: 0.25 } },
        scales: { x: { type: 'time', ..._axis() }, y: { ..._axis(), beginAtZero: true } },
      },
    });

    // Leaderboards
    charts.empDone = new Chart(rootEl.querySelector('#tm_ad_chart_emp_done'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Done', data: [], backgroundColor: COLORS.stage.done }] },
      options: { plugins: { legend: { display: false } }, scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } } },
    });

    charts.empOverdue = new Chart(rootEl.querySelector('#tm_ad_chart_emp_overdue'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Overdue', data: [], backgroundColor: COLORS.stage.review }] },
      options: { plugins: { legend: { display: false } }, scales: { x: _axis(), y: { ..._axis(), beginAtZero: true } } },
    });
  }

  function updateStage(rows) {
    const ORDER = ['todo','in_progress','review','done'];
    const LABELS = { todo:'To Do', in_progress:'In Progress', review:'Review', done:'Done' };
    const counts = ORDER.map(k => {
      const r = rows.find(x => (x.key ?? x.stage) === k) || {};
      return (r.count ?? r.id_count ?? 0);
    });
    charts.stage.data.labels = ORDER.map(k => (rows.find(x => x.key === k)?.label || LABELS[k]));
    charts.stage.data.datasets[0].data = counts;
    charts.stage.update();
  }

  function updatePriority(rows) {
    const ORDER = ['2','1','0']; // High, Medium, Low
    const LABELS = { '2':'High', '1':'Medium', '0':'Low' };
    charts.priority.data.labels = ORDER.map(k => (rows.find(x => x.key === k)?.label || LABELS[k]));
    charts.priority.data.datasets[0].data = ORDER.map(k => {
      const r = rows.find(x => (String(x.key ?? x.priority) === k)) || {};
      return (r.count ?? r.id_count ?? 0);
    });
    charts.priority.update();
  }

  function updateOverdueMgr(rows) {
    charts.overdueMgr.data.labels = rows.map(r => r.name || '—');
    charts.overdueMgr.data.datasets[0].data = rows.map(r => r.count || 0);
    charts.overdueMgr.update();
  }

  function _toXY(points, key) {
    return points.map(p => ({ x: p.period, y: p[key] || 0 }));
  }

  function updateTimeseries(grain, points, stacked) {
    if (!stacked) {
      charts.timeseries.data.datasets = [{
        label: 'Total',
        data: _toXY(points, 'total'),
        borderColor: COLORS.stage.in_progress,
        backgroundColor: 'transparent',
      }];
    } else {
      charts.timeseries.data.datasets = [
        { label: 'To Do',       data: _toXY(points, 'todo'),        borderColor: COLORS.stage.todo,        backgroundColor: 'transparent' },
        { label: 'In Progress', data: _toXY(points, 'in_progress'), borderColor: COLORS.stage.in_progress, backgroundColor: 'transparent' },
        { label: 'Review',      data: _toXY(points, 'review'),      borderColor: COLORS.stage.review,      backgroundColor: 'transparent' },
        { label: 'Done',        data: _toXY(points, 'done'),        borderColor: COLORS.stage.done,        backgroundColor: 'transparent' },
      ];
    }
    charts.timeseries.update();
  }

  function updateEmpDone(rows) {
    charts.empDone.data.labels = rows.map(r => r.name || '—');
    charts.empDone.data.datasets[0].data = rows.map(r => r.count || 0);
    charts.empDone.update();
  }

  function updateEmpOverdue(rows) {
    charts.empOverdue.data.labels = rows.map(r => r.name || '—');
    charts.empOverdue.data.datasets[0].data = rows.map(r => r.count || 0);
    charts.empOverdue.update();
  }

  return { initCharts, updateStage, updatePriority, updateOverdueMgr, updateTimeseries, updateEmpDone, updateEmpOverdue };
});
