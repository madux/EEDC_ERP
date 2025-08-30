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
    return {
      date_from: ($root.find('#tm_ad_date_from').val() || ''),
      date_to:   ($root.find('#tm_ad_date_to').val() || ''),
      q:         ($root.find('#tm_ad_q').val() || ''),
      text_q:    ($root.find('#tm_ad_q').val() || ''),
      group_by:  ($root.find('#tm_ad_groupby').val() || ''),
      page:      Number($root.data('tm-page') || 1),
      sort:      ($root.data('tm-sort') || ''),
      limit:     20,
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
