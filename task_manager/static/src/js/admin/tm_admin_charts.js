odoo.define('task_manager.tm_admin_charts', function (require) {
  'use strict';

  let Chart = window.Chart;
  function _ensureChart() { if (!Chart) Chart = window.Chart; }

  // ===== State =====
  const charts = {};           // main card instances
  const modalCharts = {};      // modal instances (per key, 0/1)
  const cache = {};            // latest data per key: { labels:[], data:[], colors?[] }
  const state = {};            // per key: { type: 'bar'|'bar-h'|'line'|'pie'|'doughnut' }

  const KEY_TO_CANVAS = {
    stage: '#tm_ad_chart_stage',
    priority: '#tm_ad_chart_priority',
    overdueMgr: '#tm_ad_chart_overdue_mgr',
    empDone: '#tm_ad_chart_emp_done',
    empOverdue: '#tm_ad_chart_emp_overdue',
    mgrDone: '#tm_ad_chart_mgr_done',
  };

  const COLORS = {
    stage: {
    todo: '#6366f1',          // indigo
      in_progress: '#f59e0b', // amber
      review: '#a855f7',      // purple
      done: '#16a34a',        // green
    },
    priority: ['#ef4444', '#f59e0b', '#9ca3af'], // high, med, low
    bars: '#4f46e5',
    grid: 'rgba(2,6,23,.08)',
    tick: '#64748b',
    text: '#0f172a',
  };

  // --- Dynamic color utilities ---
  function _hashString(str) {
    // simple deterministic hash → integer ≥ 0
    let h = 0;
    for (let i = 0; i < str.length; i++) { h = ((h << 5) - h) + str.charCodeAt(i); h |= 0; }
    return Math.abs(h);
  }
  function _hslToHex(h, s, l) {
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs((h / 60) % 2 - 1));
    const m = l - c / 2;
    let r = 0, g = 0, b = 0;
    if (h < 60) { r = c; g = x; }
    else if (h < 120) { r = x; g = c; }
    else if (h < 180) { g = c; b = x; }
    else if (h < 240) { g = x; b = c; }
    else if (h < 300) { r = x; b = c; }
    else { r = c; b = x; }
    r = Math.round((r + m) * 255);
    g = Math.round((g + m) * 255);
    b = Math.round((b + m) * 255);
    return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
  }
  // Stable color per label (manager/employee name)
  function _colorForLabel(label, sat = 68, light = 56) {
    const hue = _hashString(String(label || '')) % 360;   // 0..359
    return _hslToHex(hue, sat, light);
  }
  // Build a color array for a list of labels
  function _colorsForLabels(labels, sat = 68, light = 56) {
    return labels.map(l => _colorForLabel(l, sat, light));
  }


  function _axis() {
    return { grid: { color: COLORS.grid }, ticks: { color: COLORS.tick } };
  }

  function _readLS(key, dflt) {
    try { return JSON.parse(localStorage.getItem(key)) ?? dflt; } catch (e) { return dflt; }
  }
  function _writeLS(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { }
  }

  function _defaultTypeFor(key) {
    // Keep your original defaults; user can override and it persists.
    if (key === 'stage') return 'doughnut';
    if (key === 'priority') return 'bar';
    if (key === 'overdueMgr') return 'bar-h';
    if (key === 'mgrDone') return 'bar-h';
    return 'bar';
  }

  function _paletteForKey(key) {
    if (key === 'stage') {
      return [COLORS.stage.todo, COLORS.stage.in_progress, COLORS.stage.review, COLORS.stage.done];
    }
    if (key === 'priority') {
      return COLORS.priority; // [high, medium, low]
    }
    return null; // dynamic (manager/employee) → computed per label
  }

  function _datasetFor(key, type) {
    const c = cache[key] || { labels: [], data: [] };
    const circular = (type === 'pie' || type === 'doughnut');
    const fixedPalette = _paletteForKey(key);
    const labelMap = {
      stage: 'Tasks', priority: 'Tasks', overdueMgr: 'Overdue',
      empDone: 'Done', empOverdue: 'Overdue', mgrDone: 'Done',
    };

    // choose colors
    const colors = fixedPalette
      ? fixedPalette.slice(0, c.labels.length)
      : _colorsForLabels(c.labels); // dynamic set, stable by label

    if (circular) {
      return [{
        label: '',
        data: c.data.slice(),
        backgroundColor: colors,
        borderColor: '#ffffff',
        borderWidth: 2,
      }];
    }

    // LINE → single stroke color
    if (type === 'line') {
      return [{
        label: labelMap[key] || 'Value',
        data: c.data.slice(),
        borderColor: COLORS.bars,
        pointBackgroundColor: COLORS.bars,
        tension: 0.3,
        fill: false,
      }];
    }

    // BAR / HORIZONTAL BAR → per-bar colors when we have a palette (fixed or dynamic)
    return [{
      label: labelMap[key] || 'Value',
      data: c.data.slice(),
      backgroundColor: (fixedPalette || key === 'overdueMgr' || key === 'empDone' || key === 'empOverdue' || key === 'mgrDone')
        ? colors
        : COLORS.bars,
      borderWidth: 0,
    }];
  }



  function _baseOptions(type, key) {
    const isCircular = (type === 'pie' || type === 'doughnut');
    const horiz = (type === 'bar-h');

    const opts = {
      plugins: { legend: { display: isCircular, position: 'bottom' } },
      maintainAspectRatio: false,
    };

    if (!isCircular) {
      opts.scales = horiz
        ? { x: { ..._axis(), beginAtZero: true }, y: _axis() }
        : { x: _axis(), y: { ..._axis(), beginAtZero: true } };
      if (type === 'line') {
        opts.plugins.legend.display = false;
      } else if (key === 'priority') {
        opts.plugins.legend.display = false;
      }
    }
    if (horiz) opts.indexAxis = 'y';
    return opts;
  }

  function _makeChart(ctx, key, type) {
    return new Chart(ctx, {
      type: (type === 'bar-h') ? 'bar' : type,
      data: { labels: (cache[key] && cache[key].labels) || [], datasets: _datasetFor(key, type) },
      options: _baseOptions(type, key),
    });
  }

  function _applyTo(inst, key, type) {
    if (!inst) return;
    const c = cache[key] || { labels: [], data: [] };
    inst.data.labels = c.labels.slice();
    inst.data.datasets = _datasetFor(key, type);
    inst.update();
  }

  function _applyAll(key) {
    const t = state[key]?.type || _defaultTypeFor(key);
    _applyTo(charts[key], key, t);
    if (modalCharts[key]) _applyTo(modalCharts[key], key, t);
  }

  // ===== Public API =====
  function initCharts(rootEl) {
    _ensureChart(); if (!Chart) return;

    Chart.defaults.color = COLORS.text;
    Chart.defaults.borderColor = COLORS.grid;

    Object.entries(KEY_TO_CANVAS).forEach(([key, sel]) => {
      const canvas = rootEl.querySelector(sel);
      const type = _readLS(`tmad:chartType:${key}`, _defaultTypeFor(key));
      state[key] = { type };
      charts[key] = _makeChart(canvas.getContext('2d'), key, type);
      // prefill empty cache
      cache[key] = cache[key] || { labels: [], data: [] };
    });
  }

  function setType(key, type) {
    if (!KEY_TO_CANVAS[key]) return;
    if (!['bar', 'bar-h', 'line', 'pie', 'doughnut'].includes(type)) return;

    state[key] = { type };
    _writeLS(`tmad:chartType:${key}`, type);

    // rebuild main instance
    if (charts[key]) { charts[key].destroy(); }
    const canvas = document.querySelector(KEY_TO_CANVAS[key]);
    charts[key] = _makeChart(canvas.getContext('2d'), key, type);

    // rebuild modal instance if open
    if (modalCharts[key]) {
      const modalCanvas = document.getElementById('tm_ad_modal_canvas');
      if (modalCanvas) {
        modalCharts[key].destroy();
        modalCharts[key] = _makeChart(modalCanvas.getContext('2d'), key, type);
      }
    }
    _applyAll(key);
  }

  function renderModal(key, canvasEl) {
    if (!canvasEl) return null;
    const type = state[key]?.type || _defaultTypeFor(key);
    if (modalCharts[key]) { try { modalCharts[key].destroy(); } catch (e) { } }
    modalCharts[key] = _makeChart(canvasEl.getContext('2d'), key, type);
    _applyAll(key);
    return modalCharts[key];
  }
  function destroyModal(key) {
    if (modalCharts[key]) { try { modalCharts[key].destroy(); } catch (e) { } delete modalCharts[key]; }
  }

  // -------- Updaters (compute cache then apply) --------
  function _valCount(r) {
    return Number((r && (r.count ?? r.id_count ?? r.employee_id_count ?? r.manager_id_count)) || 0);
  }

  function updateStage(rows) {
    const ORDER = ['todo', 'in_progress', 'review', 'done'];
    const LABELS = { todo: 'To Do', in_progress: 'In Progress', review: 'Review', done: 'Done' };

    const labels = ORDER.map(k => (rows.find(x => x.key === k)?.label || LABELS[k]));
    const data = ORDER.map(k => {
      const r = rows.find(x => (x.key ?? x.stage) === k) || {};
      return Number(r.count ?? r.id_count ?? 0);
    });
    cache.stage = { labels, data };
    _applyAll('stage');
  }

  function updatePriority(rows) {
    const ORDER = ['2', '1', '0']; // High, Medium, Low
    const LABELS = { '2': 'High', '1': 'Medium', '0': 'Low' };

    const labels = ORDER.map(k => (rows.find(x => String(x.key) === k)?.label || LABELS[k]));
    const data = ORDER.map(k => {
      const r = rows.find(x => (String(x.key ?? x.priority) === k)) || {};
      return Number(r.count ?? r.id_count ?? 0);
    });
    cache.priority = { labels, data };
    _applyAll('priority');
  }

  function updateOverdueMgr(rows) {
    cache.overdueMgr = { labels: rows.map(r => r.name || '—'), data: rows.map(_valCount) };
    _applyAll('overdueMgr');
  }

  function updateEmpDone(rows) {
    cache.empDone = { labels: rows.map(r => r.name || '—'), data: rows.map(_valCount) };
    _applyAll('empDone');
  }

  function updateEmpOverdue(rows) {
    cache.empOverdue = { labels: rows.map(r => r.name || '—'), data: rows.map(_valCount) };
    _applyAll('empOverdue');
  }

  function updateMgrDone(rows) {
    cache.mgrDone = { labels: rows.map(r => r.name || '—'), data: rows.map(_valCount) };
    _applyAll('mgrDone');
  }

  return {
    initCharts,
    setType,
    renderModal,
    destroyModal,
    updateStage,
    updatePriority,
    updateOverdueMgr,
    updateEmpDone,
    updateEmpOverdue,
    updateMgrDone,
    _state: state,   // (optional) for debugging
  };
});
