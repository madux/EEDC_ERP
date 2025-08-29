odoo.define('task_manager.tm_admin_api', function (require) {
  'use strict';
  const ajax = require('web.ajax');

  function _getMulti($root, selector) {
    const el = $root.find(selector)[0];
    if (!el) return [];
    // works for single or multiple selects
    const selected = el.multiple ? Array.from(el.selectedOptions || []) : (el.value ? [{ value: el.value }] : []);
    return selected.map(o => o.value).filter(Boolean);
  }

  function pickFilters($root) {
    const toIntOrNull = (v) => { const n = parseInt(v, 10); return Number.isFinite(n) ? n : null; };
    return {
      date_from: $root.find('#tm_ad_date_from').val() || null,
      date_to: $root.find('#tm_ad_date_to').val() || null,
      date_grain: $root.find('#tm_ad_grain').val() || 'week',
      stages: _getMulti($root, '#tm_ad_stage'),
      priorities: _getMulti($root, '#tm_ad_priority'),
      q: ($root.find('#tm_ad_q').val() || '').trim(),          // reserved for future person search
      employee_id: toIntOrNull($root.find('#tm_ad_employee_id').val()),
      manager_id: toIntOrNull($root.find('#tm_ad_manager_id').val()),
      company_id: null,

      // List controls (widget sets these data attrs)
      quick_filters: ($root.data('tm-quick') || []),
      group_by: ($root.data('tm-group') || ''),
      sort_by: ($root.data('tm-sort') || 'priority desc, due_date asc, id desc'),
      page: ($root.data('tm-page') || 1),
      limit: ($root.data('tm-limit') || 20),
      text_q: ($root.find('#tm_ad_text_q').val() || '').trim(),
    };
  }

  function _post(route, params) {
    return ajax.jsonRpc(route, 'call', params || {}).catch((err) => {
      const xhr = err && err.event && err.event.target;
      const status = xhr && xhr.status;
      const text = xhr && xhr.responseText ? xhr.responseText.slice(0, 400) : '';
      // Re-throw a clean Error so the caller's catch prints something useful
      throw new Error(`[${status || 'ERR'}] ${route} failed\n${text}`);
    });
  }


  return {
    pickFilters,
    summary:      (f) => _post('/tm/admin/api/summary', f),
    distribution: (f) => _post('/tm/admin/api/distribution', f),
    timeseries:   (f) => _post('/tm/admin/api/timeseries', f),
    leaderboard:  (f) => _post('/tm/admin/api/leaderboard', f),
    tasks:        (f) => _post('/tm/admin/api/tasks', f),
    search:       (q) => _post('/tm/admin/api/search', { q }),
  };
});
