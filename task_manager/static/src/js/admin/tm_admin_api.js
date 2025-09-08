odoo.define('task_manager.tm_admin_api', function (require) {
  'use strict';
  const ajax = require('web.ajax');

  function pickFilters($root) {
    const df = $root.find('#tm_ad_date_from').val() || '';
    const dt = $root.find('#tm_ad_date_to').val() || '';
    const gb = $root.find('#tm_ad_groupby').val() || ''; 
    const tq = $root.find('#tm_ad_q').val() || '';    

    return {
      date_from: df,
      date_to: dt,
      group_by: gb,
      text_q: tq,                                           
    };
  }

  function _post(route, params) {
    return ajax.jsonRpc(route, 'call', params || {}).catch((err) => {
      const xhr = err && err.event && err.event.target;
      const status = xhr && xhr.status;
      const text = xhr && xhr.responseText ? xhr.responseText.slice(0, 400) : '';
      throw new Error(`[${status || 'ERR'}] ${route} failed\n${text}`);
    });
  }

  return {
    pickFilters,
    summary:      (f) => _post('/tm/admin/api/summary', f),
    distribution: (f) => _post('/tm/admin/api/distribution', f),
    leaderboard:  (f) => _post('/tm/admin/api/leaderboard', f),
    tasks:        (f) => _post('/tm/admin/api/tasks', f),
    search:       (q) => _post('/tm/admin/api/search', { q }),
  };
});
