/* finance_portal.js — jQuery + Chart.js + jsPDF + SheetJS */
$(function(){
'use strict';
const META_EL=document.querySelector('meta[name="fp-meta"]');
const META=META_EL?JSON.parse(META_EL.getAttribute('content')):{};
let currentPage='dashboard',currentPayType='supplier',payFilters={state:'',search:'',page:1};
let metaCache={},selectedMoveId=null,formLineCount=0,chartMonthly=null,chartDonut=null;
const PALETTE=['#f0a500','#3fb950','#f85149','#58a6ff','#bc8cff','#39d353','#e3b341'];
const esc=s=>$('<span>').text(String(s||'')).html();
const fmt=n=>n===null||n===undefined?'—':parseFloat(n).toLocaleString('en-NG',{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtK=n=>{const v=Math.abs(n);if(v>=1e9)return(n/1e9).toFixed(1)+'B';if(v>=1e6)return(n/1e6).toFixed(1)+'M';if(v>=1e3)return(n/1e3).toFixed(0)+'K';return fmt(n);};
const today=()=>new Date().toISOString().slice(0,10);

function toast(msg,type='info'){
  const ic={success:'fa-circle-check',error:'fa-circle-xmark',info:'fa-circle-info'};
  const cl={success:'var(--green)',error:'var(--red)',info:'var(--blue)'};
  const $t=$(`<div class="toast ${type}"><i class="fa-solid ${ic[type]}" style="color:${cl[type]}"></i><span>${esc(msg)}</span></div>`);
  $('#toast-container').append($t);
  setTimeout(()=>$t.fadeOut(300,()=>$t.remove()),3200);
}

function rpc(url,params={}){
  return $.ajax({url,type:'POST',contentType:'application/json',
    data:JSON.stringify({jsonrpc:'2.0',method:'call',id:Date.now(),params})
  }).then(r=>{if(r.error)throw new Error(r.error.data?.message||r.error.message);return r.result;});
}

function stateBadge(s){const l={posted:'Confirmed',draft:'Draft',cancel:'Cancelled'};return`<span class="state-badge ${s}">${l[s]||s}</span>`;}
function payBadge(ps){const l={paid:'Paid',not_paid:'Unpaid',in_payment:'In Payment',partial:'Partial'};const c={paid:'paid',not_paid:'not_paid',in_payment:'in_payment',partial:'partial'};return ps?`<span class="state-badge ${c[ps]||''}">${l[ps]||ps}</span>`:'';} 
function populateSelect(
  $s,
  items,
  vid,
  vlabel,
  empty=false){
    $s.empty();
    if(empty)$s.append('<option value="">-- Select --</option>');
    items.forEach(it=>$s.append(`<option value="${it[vid]}">${esc(it[vlabel])}</option>`));
  }

/* theme */
let dark=true;
$('#theme-toggle').on('click',function(){dark=!dark;$('html').attr('data-theme',dark?'':'light');$(this).html(dark?'<i class="fa-solid fa-sun"></i> Light':'<i class="fa-solid fa-moon"></i> Dark');});

/* dates */
const curYear=META.today?META.today.slice(0,4):new Date().getFullYear();
$('#g_date_from').val(`${curYear}-01-01`);
$('#g_date_to').val(META.today||today());
$('#active_company').text(META.company_name||'');

/* nav */
function switchPage(pg,opts={}){
  currentPage=pg;
  $('.page-section').removeClass('active');$(`#page-${pg}`).addClass('active');
  $('.sb-item').removeClass('active');$(`.sb-item[data-page="${pg}"]`).addClass('active');
  loadPage(pg,opts);
}
$(document).on('click','.sb-item[data-page]',function(){
  const pg=$(this).data('page'),pt=$(this).data('ptype');
  if(pt)currentPayType=pt;
  switchPage(pg);
});
$('#btn_run').on('click',()=>loadPage(currentPage));

function loadPage(pg){
  if(pg==='dashboard')loadDashboard();
  else if(pg==='payments')loadPayments(currentPayType);
}

/* ── DASHBOARD ──────────────────────────────────────────── */
function loadDashboard(){
  rpc('/finance-portal/dashboard',{date_from:$('#g_date_from').val(),date_to:$('#g_date_to').val(),company_ids:[META.company_id].filter(Boolean)}).then(d=>{
    if(!d.status){toast(d.message,'error');return;}
    $('#kpi_sup_total').text(fmtK(d.supplier_posted.total));$('#kpi_sup_count').text(`${d.supplier_posted.count} confirmed`);
    $('#kpi_cust_total').text(fmtK(d.customer_posted.total));$('#kpi_cust_count').text(`${d.customer_posted.count} confirmed`);
    $('#kpi_sup_draft_total').text(fmtK(d.supplier_draft.total));$('#kpi_sup_draft_count').text(`${d.supplier_draft.count} pending`);
    $('#kpi_cust_draft_total').text(fmtK(d.customer_draft.total));$('#kpi_cust_draft_count').text(`${d.customer_draft.count} pending`);
    $('#kpi_aged_pay').text(fmtK(d.aged_payable.total));$('#kpi_aged_pay_count').text(`${d.aged_payable.count} invoices`);
    $('#kpi_aged_rec').text(fmtK(d.aged_receivable.total));$('#kpi_aged_rec_count').text(`${d.aged_receivable.count} invoices`);
    $('#kpi_credit').text(fmtK(d.credit_notes.total));$('#kpi_credit_count').text(`${d.credit_notes.count} notes`);
    $('#kpi_tax').text(fmtK(d.tax_paid.total));

    if(chartMonthly)chartMonthly.destroy();
    chartMonthly=new Chart($('#chart_monthly')[0].getContext('2d'),{type:'bar',data:{labels:d.monthly.map(m=>m.month),datasets:[{label:'Supplier',data:d.monthly.map(m=>m.supplier),backgroundColor:'rgba(88,166,255,.7)',borderRadius:4},{label:'Customer',data:d.monthly.map(m=>m.customer),backgroundColor:'rgba(63,185,80,.7)',borderRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#8b949e',font:{family:"'DM Sans'"}}},tooltip:{backgroundColor:'#161b22',borderColor:'#30363d',borderWidth:1}},scales:{x:{ticks:{color:'#6e7681',font:{size:10}},grid:{display:false}},y:{ticks:{color:'#6e7681',font:{size:10},callback:v=>fmtK(v)},grid:{color:'rgba(128,128,128,.08)'}}}}});

    if(chartDonut)chartDonut.destroy();
    chartDonut=new Chart($('#chart_donut')[0].getContext('2d'),{type:'doughnut',data:{labels:['Supplier Bills','Customer Invoices','Aged Payable','Aged Receivable'],datasets:[{data:[d.supplier_posted.total||0,d.customer_posted.total||0,d.aged_payable.total||0,d.aged_receivable.total||0],backgroundColor:['rgba(88,166,255,.8)','rgba(63,185,80,.8)','rgba(248,81,73,.8)','rgba(240,165,0,.8)'],borderWidth:2,borderColor:'#161b22'}]},options:{responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{legend:{position:'bottom',labels:{color:'#8b949e',font:{family:"'DM Sans'",size:10},padding:12}},tooltip:{backgroundColor:'#161b22'}}}});
  }).catch(e=>toast('Dashboard: '+e.message,'error'));
}

/* ── PAYMENTS LIST ──────────────────────────────────────── */
function loadPayments(ptype){
  currentPayType=ptype;
  $('#pay_list_title').text(ptype==='supplier'?'Supplier Payments':'Customer Payments');
  $('#pay_list_sub').text(ptype==='supplier'?'Vendor bills & purchase receipts':'Customer invoices & sales receipts');
  $('.sb-item').removeClass('active');$(`.sb-item[data-ptype="${ptype}"]`).addClass('active');
  $('#pay_tbody').html(Array(5).fill(`<tr class="skeleton"><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`).join(''));
  rpc('/finance-portal/payments',{payment_type:ptype,date_from:$('#g_date_from').val(),date_to:$('#g_date_to').val(),state:payFilters.state,search:payFilters.search,page:payFilters.page,per_page:50,company_ids:[META.company_id].filter(Boolean)}).then(d=>{
    if(!d.status){toast(d.message,'error');return;}
    renderPayList(d);
  }).catch(e=>toast('Payments: '+e.message,'error'));
}

function renderPayList(d){
  const tbody=$('#pay_tbody');
  if(!d.rows.length){tbody.html(`<tr><td colspan="8"><div class="empty-state"><i class="fa-solid fa-file-invoice"></i><p>No payments found</p></div></td></tr>`);$('#pay_count').text('0 records');buildPagination(d);return;}
  let html='';
  d.rows.forEach(r=>{
    html+=`<tr data-id="${r.id}"><td><span style="font-family:var(--mono);font-size:11px;color:var(--amber)">${esc(r.name)}</span></td><td>${esc(r.date)}</td><td>${esc(r.partner)}</td><td>${esc(r.journal)}</td><td>${esc(r.ref)}</td><td class="num">${esc(r.currency)}${esc(r.amount)}</td><td class="num">${esc(r.currency)}${esc(r.amount_due)}</td><td>${stateBadge(r.state)} ${payBadge(r.payment_state)}</td></tr>`;
  });
  tbody.html(html);
  $('#pay_count').text(`${d.total} records · page ${d.page}/${d.pages}`);
  buildPagination(d);
}

function buildPagination(d){
  let h='';
  for(let i=1;i<=d.pages;i++){
    if(d.pages>10&&i>3&&i<d.pages-2&&Math.abs(i-d.page)>2){if(i===4)h+='<span style="padding:0 4px;color:var(--muted)">…</span>';continue;}
    h+=`<button class="pg-btn${i===d.page?' active':''}" data-pg="${i}">${i}</button>`;
  }
  $('#pay_pages').html(h);
}

$(document).on('click','.pg-btn[data-pg]',function(){payFilters.page=parseInt($(this).data('pg'));loadPayments(currentPayType);});
$(document).on('click','#pay_tbody tr[data-id]',function(){
  $('#pay_tbody tr').removeClass('selected-row'); // this removes all classes of lines
  $(this).addClass('selected-row');
  openDrawer(parseInt($(this).data('id')));});
$('#pay_state_filter').on('change',function(){payFilters.state=$(this).val();payFilters.page=1;loadPayments(currentPayType);});
let stimer;$('#pay_search').on('input',function(){clearTimeout(stimer);const v=$(this).val();stimer=setTimeout(()=>{payFilters.search=v;payFilters.page=1;loadPayments(currentPayType);},400);});

/* ── DETAIL DRAWER ──────────────────────────────────────── */
function openDrawer(id){
  $('#drawer-loading').show();
  $('#drawer-content').hide();
  $('#detail-drawer').addClass('open');
  rpc(`/finance-portal/payment/${id}`,{}).then(d=>{
    if(!d.status){toast(d.message,'error');return;}
    renderDrawer(d);$('#drawer-loading').hide();$('#drawer-content').show();
  }).catch(e=>toast(e.message,'error'));
}

function renderDrawer(d){
  const m=d.move;
  const TL={in_invoice:'Vendor Bill',in_receipt:'Purchase Receipt',out_invoice:'Customer Invoice',out_receipt:'Sales Receipt',in_refund:'Vendor Credit Note',out_refund:'Customer Credit Note'};
  $('#drawer-title').text(`${TL[m.move_type]||m.move_type} · ${m.name}`);
  const fields=[['Reference',m.name],['Type',TL[m.move_type]||m.move_type],['Partner',m.partner_name],['Date',m.date],['Invoice Date',m.invoice_date],['Due Date',m.invoice_date_due],['Journal',m.journal_name],['Payment Term',m.payment_term],['Status',stateBadge(m.state)],['Payment',payBadge(m.payment_state)],['Company',m.company],['Branch',m.branch],['Ref',m.ref],['Note',m.narration]];
  let info='';fields.forEach(([k,v])=>{if(!v)return;info+=`<div class="detail-row"><span class="detail-key">${esc(k)}</span><span class="detail-val">${v}</span></div>`;});
  $('#drawer-info').html(info);
  let lines=`<table class="detail-line-table"><thead><tr><th>Account</th><th>Description</th><th>Tax(es)</th><th class="num">Qty</th><th class="num">Unit Price</th><th class="num">Subtotal</th><th class="num">Total</th></tr></thead><tbody>`;
  d.lines.forEach(ln=>{
    lines+=`<tr><td><span style="color:var(--amber);font-family:var(--mono);font-size:10px">
    ${esc(ln.account_code)}</span> ${esc(ln.account_name)}</td><td>${esc(ln.description)}</td><td>${ln.tax_ids.map(t=>`<span style="background:var(--amber-gl);color:var(--amber);border-radius:3px;padding:1px 5px;font-size:9px">${esc(t.name)}</span>`).join(' ')}</td><td class="num">${ln.quantity}</td><td class="num">${esc(ln.currency)}${esc(ln.price_unit)}</td><td class="num">${esc(ln.currency)}${esc(ln.price_subtotal)}</td><td class="num">${esc(ln.currency)}${esc(ln.price_total)}</td></tr>`;});
  lines+='</tbody></table>';$('#drawer-lines').html(lines);
  $('#drawer-totals').html(`<div><span>Untaxed</span><span>${m.currency}${m.amount_untaxed}</span></div><div><span>Tax</span><span>${m.currency}${m.amount_tax}</span></div><div><span style="color:var(--amber);font-weight:700">Total</span><span style="color:var(--amber);font-weight:700">${m.currency}${m.amount_total}</span></div><div style="font-size:11px;color:var(--muted)"><span>Amount Due</span><span>${m.currency}${m.amount_residual}</span></div>`);
  const posted=m.state==='posted',draft=m.state==='draft';
  $('#btn_drawer_confirm').toggle(draft).off('click').on('click',()=>confirmMove(m.id));
  $('#btn_drawer_cancel').toggle(posted||draft).off('click').on('click',()=>cancelMove(m.id));
  $('#btn_drawer_edit').toggle(draft).off('click').on('click',()=>{
    closeDrawer();
    openEditModal(m.id);
  });
}

$('#btn_drawer_close').on('click',closeDrawer);
function closeDrawer(){$('#detail-drawer').removeClass('open');selectedMoveId=null;}

function confirmMove(id){rpc(`/finance-portal/payment/confirm/${id}`,{}).then(r=>{toast(r.message,r.status?'success':'error');if(r.status){closeDrawer();loadPayments(currentPayType);loadDashboard();}}).catch(e=>toast(e.message,'error'));}
function cancelMove(id){if(!confirm('Reset this record?'))return;rpc(`/finance-portal/payment/cancel/${id}`,{}).then(r=>{toast(r.message,r.status?'success':'error');if(r.status){closeDrawer();loadPayments(currentPayType);loadDashboard();}}).catch(e=>toast(e.message,'error'));}

/* ── CREATE / EDIT MODAL ────────────────────────────────── */
$(document).on('click','#btn_create_payment,.btn-create-pay',function(){
  const pt=$(this).data('ptype')||currentPayType;
  openCreateModal(pt);
});

async function openCreateModal(ptype){
  formLineCount=0;$('#form_lines_body').empty();resetTotals();
  const dt=ptype==='supplier'?'in_invoice':'out_invoice';
  $('#f_move_type').val(dt);onMTChange();
  $('#modal-title').text(ptype==='supplier'?'New Supplier Payment':'New Customer Payment');
  $('#f_invoice_date').val(today());$('#f_ref,#f_narration').val('');
  $('#f_partner_ac').val('');$('#f_partner_id').val('');
  $('#f_journal_id,#f_payment_term_id').val('');
  $('#f_currency_id').val(META.currency_id||'');
  $('#btn_save_payment').removeData('edit-id');
  await loadFormMeta(ptype);addFormLine();
  $('#modal-overlay').addClass('open');
}

async function openEditModal(id){
  const d=await rpc(`/finance-portal/payment/${id}`,{}).catch(()=>null);
  if(!d||!d.status){toast('Could not load record','error');return;}
  const m=d.move;
  formLineCount=0;$('#form_lines_body').empty();resetTotals();
  $('#modal-title').text(`Edit · ${m.name}`);
  $('#f_move_type').val(m.move_type);onMTChange();
  $('#f_invoice_date').val(m.invoice_date);$('#f_ref').val(m.ref);$('#f_narration').val(m.narration);
  $('#f_partner_ac').val(m.partner_name);$('#f_partner_id').val(m.partner_id);
  $('#btn_save_payment').data('edit-id',id);
  const ptype=['in_invoice','in_receipt','in_refund'].includes(m.move_type)?'supplier':'customer';
  await loadFormMeta(ptype);
  $(`#f_journal_id option[value="${m.journal_id}"]`).prop('selected',true);
  d.lines.forEach(ln=>addFormLine(ln));calcTotals();
  $('#modal-overlay').addClass('open');
}

$('#modal-overlay .modal-close,#btn_cancel_payment').on('click',()=>{$('#modal-overlay').removeClass('open');$('#btn_save_payment').removeData('edit-id');});
$('#modal-overlay').on('click',function(e){if($(e.target).is(this))$(this).removeClass('open');});

function onMTChange(){
  const mt=$('#f_move_type').val();
  const jt=['in_invoice','in_receipt','in_refund'].includes(mt)?'purchase':'sale';
  const cached=metaCache[`journals_${jt}`];
  if(cached)populateSelect($('#f_journal_id'),cached,'id','name');
}
$('#f_move_type').on('change',onMTChange);

async function loadFormMeta(ptype){
  const jt=ptype==='supplier'?'purchase':'sale';
  const cids=[META.company_id].filter(Boolean);
  const [jR,ptR,curR,brR]=await Promise.all([
    metaCache[`journals_${jt}`]?Promise.resolve({journals:metaCache[`journals_${jt}`]}):rpc('/finance-portal/meta/journals',{type:jt,company_ids:cids}),
    metaCache.payment_terms?Promise.resolve({terms:metaCache.payment_terms}):rpc('/finance-portal/meta/payment_terms',{}),
    metaCache.currencies?Promise.resolve({currencies:metaCache.currencies}):rpc('/finance-portal/meta/currencies',{}),
    metaCache.branches?Promise.resolve({branches:metaCache.branches}):rpc('/finance-portal/meta/branches',{company_ids:cids}),
  ]);
  if(jR.journals){metaCache[`journals_${jt}`]=jR.journals;populateSelect($('#f_journal_id'),jR.journals,'id','name');}
  if(ptR.terms){
    metaCache.payment_terms=ptR.terms;
    populateSelect($('#f_payment_term_id'), ptR.terms, 'id', 'name',true);
  }
  if(curR.currencies){metaCache.currencies=curR.currencies;populateSelect($('#f_currency_id'),curR.currencies,'id','name');$('#f_currency_id').val(META.currency_id||'');}
  if(brR.branches)metaCache.branches=brR.branches;
  if(!metaCache.accounts){const aR=await rpc('/finance-portal/meta/accounts',{company_ids:cids});if(aR.accounts)metaCache.accounts=aR.accounts;}
  if(!metaCache.taxes){const tR=await rpc('/finance-portal/meta/taxes',{company_ids:cids});if(tR.taxes)metaCache.taxes=tR.taxes;}
}

/* partner autocomplete */
let ptimer;
$('#f_partner_ac').on('input',function(){
  clearTimeout(ptimer);const q=$(this).val().trim();
  if(q.length<2){$('#partner_dropdown').removeClass('open');return;}
  const mt=$('#f_move_type').val();const ptype=['in_invoice','in_receipt','in_refund'].includes(mt)?'supplier':'customer';
  ptimer=setTimeout(()=>{
    rpc('/finance-portal/meta/partners',{q,type:ptype}).then(r=>{
      const $dd=$('#partner_dropdown');
      if(!r.partners.length){$dd.html('<div class="ac-empty">No partners found</div>').addClass('open');return;}
      $dd.html(r.partners.map(p=>`<div class="ac-item" data-id="${p.id}" data-name="${esc(p.name)}">${esc(p.name)}${p.email?` <small style="color:var(--muted)">${esc(p.email)}</small>`:''}</div>`).join('')).addClass('open');
    });
  },300);
});
$(document).on('click','#partner_dropdown .ac-item',function(){$('#f_partner_id').val($(this).data('id'));$('#f_partner_ac').val($(this).data('name'));$('#partner_dropdown').removeClass('open');});
$(document).on('click',function(e){if(!$(e.target).closest('.ac-wrap').length)$('.ac-dropdown').removeClass('open');});

/* line items */
function addFormLine(pf=null){
  formLineCount++;const n=formLineCount;
  const brOpts=(metaCache.branches||[]).map(b=>`<option value="${b.id}">${esc(b.name)}</option>`).join('');
  const defBr=META.user_branch_id||'';
  const $tr=$(`<tr data-line="${n}">
    <td><div class="ac-wrap"><input class="line-input line-account-ac" data-line="${n}" placeholder="Search account…" autocomplete="off" value="${pf?esc(pf.account_name):''}"/><input type="hidden" class="line-account-id" data-line="${n}" value="${pf?pf.account_id:''}"/><div class="ac-dropdown line-account-dd" data-line="${n}"></div></div></td>
    <td><input class="line-input line-desc" data-line="${n}" placeholder="Description" value="${pf?esc(pf.description):''}"/></td>
    <td><div class="tag-input-wrap line-tax-wrap" data-line="${n}"><input class="line-input line-tax-search" data-line="${n}" placeholder="Add tax…" style="min-width:80px;flex:1" autocomplete="off"/></div><div class="ac-dropdown line-tax-dd" data-line="${n}"></div></td>
    <td><select class="line-select line-branch" data-line="${n}"><option value="">—</option>${brOpts}</select></td>
    <td><select class="line-select line-currency" data-line="${n}">${(metaCache.currencies||[]).map(c=>`<option value="${c.id}">${esc(c.symbol)}</option>`).join('')}</select></td>
    <td><input class="line-input line-qty num" data-line="${n}" type="number" value="${pf?pf.quantity:1}" min="0" style="width:58px;text-align:right"/></td>
    <td><input class="line-input line-price num" data-line="${n}" type="number" value="${pf?pf.price_unit:0}" min="0" style="width:88px;text-align:right"/></td>
    <td class="num line-subtotal" data-line="${n}">0.00</td>
    <td class="num line-tax-amount" data-line="${n}">0.00</td>
    <td class="num line-total" data-line="${n}">0.00</td>
    <td><button class="line-del" data-line="${n}"><i class="fa-solid fa-xmark"></i></button></td>
  </tr>`);
  if(defBr)$tr.find('.line-branch').val(defBr);
  if(META.currency_id)$tr.find('.line-currency').val(META.currency_id);
  if(pf&&pf.tax_ids)pf.tax_ids.forEach(t=>addTaxTag($tr.find('.line-tax-wrap'),t.id,t.name));
  $('#form_lines_body').append($tr);calcLineRow(n);
}

$('#btn_add_line').on('click',()=>addFormLine());
$(document).on('click','.line-del',function(){$(this).closest('tr').remove();calcTotals();});
$(document).on('input','.line-qty,.line-price',function(){calcLineRow($(this).data('line'));});

/* account ac on lines */
let acT;
$(document).on('input','.line-account-ac',function(){
  clearTimeout(acT);const n=$(this).data('line'),q=$(this).val().trim();
  const $dd=$(`.line-account-dd[data-line="${n}"]`);
  if(q.length<2){$dd.removeClass('open');return;}
  acT=setTimeout(()=>{rpc('/finance-portal/meta/accounts',{q,company_ids:[META.company_id].filter(Boolean)}).then(r=>{if(!r.accounts.length){$dd.html('<div class="ac-empty">Not found</div>').addClass('open');return;}$dd.html(r.accounts.slice(0,30).map(a=>`<div class="ac-item" data-id="${a.id}" data-name="${esc(a.name)}" data-line="${n}">${esc(a.name)}</div>`).join('')).addClass('open');});},300);
});
$(document).on('click','.line-account-dd .ac-item',function(){const n=$(this).data('line');$(`.line-account-id[data-line="${n}"]`).val($(this).data('id'));$(`.line-account-ac[data-line="${n}"]`).val($(this).data('name'));$(`.line-account-dd[data-line="${n}"]`).removeClass('open');});

/* tax search on lines */
$(document).on('input','.line-tax-search',function(){
  const n=$(this).data('line'),q=$(this).val().toLowerCase();
  const $dd=$(`.line-tax-dd[data-line="${n}"]`);
  const taxes=(metaCache.taxes||[]).filter(t=>t.name.toLowerCase().includes(q));
  if(!taxes.length){$dd.removeClass('open');return;}
  $dd.html(taxes.slice(0,20).map(t=>`<div class="ac-item" data-id="${t.id}" data-name="${esc(t.name)}" data-amount="${t.amount}" data-line="${n}">${esc(t.name)} (${t.amount}%)</div>`).join('')).addClass('open');
});
$(document).on('click','.line-tax-dd .ac-item',function(){
  const n=$(this).data('line'),$w=$(`.line-tax-wrap[data-line="${n}"]`);
  const id=$(this).data('id'),name=$(this).data('name');
  if($w.find(`.tax-tag[data-id="${id}"]`).length)return;
  addTaxTag($w,id,name);$(`.line-tax-dd[data-line="${n}"]`).removeClass('open');$(`.line-tax-search[data-line="${n}"]`).val('');calcLineRow(n);
});
$(document).on('click','.tax-tag .rm',function(){const n=$(this).closest('tr').data('line');$(this).closest('.tax-tag').remove();calcLineRow(n);});

function addTaxTag($w,id,name){$w.find('.line-tax-search').before(`<span class="tax-tag" data-id="${id}" data-name="${esc(name)}" data-amount="${getTaxAmt(id)}">${esc(name)}<span class="rm">✕</span></span>`);}
function getTaxAmt(id){const t=(metaCache.taxes||[]).find(x=>x.id==id);return t?t.amount:0;}

function calcLineRow(n){
  const qty=parseFloat($(`.line-qty[data-line="${n}"]`).val())||0;
  const price=parseFloat($(`.line-price[data-line="${n}"]`).val())||0;
  const sub=qty*price;let tax=0;
  $(`.line-tax-wrap[data-line="${n}"] .tax-tag`).each(function(){tax+=sub*(parseFloat($(this).data('amount'))||0)/100;});
  const total=sub+tax;
  $(`.line-subtotal[data-line="${n}"]`).text(sub.toLocaleString('en-NG',{minimumFractionDigits:2}));
  $(`.line-tax-amount[data-line="${n}"]`).text(tax.toLocaleString('en-NG',{minimumFractionDigits:2}));
  $(`.line-total[data-line="${n}"]`).text(total.toLocaleString('en-NG',{minimumFractionDigits:2}));
  calcTotals();
}
function calcTotals(){
  let sub=0,tax=0;
  $('#form_lines_body tr').each(function(){const n=$(this).data('line');sub+=parseFloat($(`.line-subtotal[data-line="${n}"]`).text().replace(/,/g,''))||0;tax+=parseFloat($(`.line-tax-amount[data-line="${n}"]`).text().replace(/,/g,''))||0;});
  $('#total_untaxed').text(fmt(sub));$('#total_tax').text(fmt(tax));$('#total_amount').text(fmt(sub+tax));
}
function resetTotals(){$('#total_untaxed,#total_tax,#total_amount').text('0.00');}

function collectLines(){
  const lines=[];
  $('#form_lines_body tr').each(function(){
    const n=$(this).data('line');const accId=parseInt($(`.line-account-id[data-line="${n}"]`).val())||0;
    if(!accId)return;
    const taxIds=[];$(`.line-tax-wrap[data-line="${n}"] .tax-tag`).each(function(){taxIds.push(parseInt($(this).data('id')));});
    lines.push({account_id:accId,description:$(`.line-desc[data-line="${n}"]`).val()||'/',quantity:parseFloat($(`.line-qty[data-line="${n}"]`).val())||1,price_unit:parseFloat($(`.line-price[data-line="${n}"]`).val())||0,tax_ids:taxIds,branch_id:$(`.line-branch[data-line="${n}"]`).val()||META.user_branch_id||'',currency_id:$(`.line-currency[data-line="${n}"]`).val()||META.currency_id||''});
  });
  return lines;
}

/* save */
$('#btn_save_payment').on('click',async function(){
  const editId=$(this).data('edit-id');
  const lines=collectLines();
  if(!$('#f_partner_id').val()){toast('Please select a partner','error');return;}
  if(!$('#f_journal_id').val()){toast('Please select a journal','error');return;}
  if(!lines.length){toast('Add at least one line item','error');return;}
  const payload={
    move_type:$('#f_move_type').val(),
    partner_id:parseInt($('#f_partner_id').val()),
    journal_id:parseInt($('#f_journal_id').val()),
    invoice_date:$('#f_invoice_date').val(),
    invoice_date_due:$('#f_due_date').val()||'',
    payment_term_id:parseInt($('#f_payment_term_id').val())||0,
    ref:$('#f_ref').val(),
    narration:$('#f_narration').val(),
    currency_id:parseInt($('#f_currency_id').val())||0,lines
  };
  $(this).prop('disabled',true).html('<i class="fa-solid fa-spinner fa-spin"></i> Saving…');
  try{const r=await rpc('/finance-portal/payment/create',payload);if(r.status){toast(`Created: ${r.name}`,'success');$('#modal-overlay').removeClass('open');$(this).removeData('edit-id');loadPayments(currentPayType);loadDashboard();}else toast(r.message,'error');}catch(e){toast(e.message,'error');}finally{$(this).prop('disabled',false).html('<i class="fa-solid fa-floppy-disk"></i> Save');}
});

/* export */
$('#btn_export_excel').on('click',()=>{
  const headers=['Ref','Date','Partner','Journal','Ext Ref','Amount','Amount Due','Status'];
  const rows=[];$('#pay_tbody tr[data-id]').each(function(){rows.push($(this).find('td').map((_,td)=>$(td).text().trim()).get());});
  if(!rows.length){toast('No data to export','info');return;}
  const WB=XLSX.utils.book_new();
  const WS=XLSX.utils.aoa_to_sheet([[`${currentPayType==='supplier'?'Supplier':'Customer'} Payments`],[`Period: ${$('#g_date_from').val()} – ${$('#g_date_to').val()}`],[],headers,...rows]);
  WS['!cols']=headers.map(()=>({wch:18}));XLSX.utils.book_append_sheet(WB,WS,'Payments');
  XLSX.writeFile(WB,`${currentPayType}_payments_${today()}.xlsx`);toast('Excel exported','success');
});

$('#btn_export_pdf').on('click',()=>{
  if(!window.jspdf){toast('jsPDF not loaded','error');return;}
  const {jsPDF}=window.jspdf;
  const doc=new jsPDF({orientation:'landscape',unit:'pt',format:'a4'});
  const pW=doc.internal.pageSize.getWidth(),ML=36;
  doc.setFillColor(21,27,34);doc.rect(0,0,pW,46,'F');
  doc.setFont('helvetica','bold');doc.setFontSize(13);doc.setTextColor(240,165,0);
  doc.text(`${currentPayType==='supplier'?'Supplier':'Customer'} Payments`,ML,28);
  doc.setFont('helvetica','normal');doc.setFontSize(8);doc.setTextColor(180,190,200);
  doc.text(`${$('#g_date_from').val()} – ${$('#g_date_to').val()}`,ML,40);
  doc.text(`Generated: ${new Date().toLocaleString()}`,pW-ML,40,{align:'right'});
  const hds=[['Ref','Date','Partner','Journal','Ext Ref','Amount','Amount Due','Status']];
  const rows=[];$('#pay_tbody tr[data-id]').each(function(){rows.push($(this).find('td').map((_,td)=>$(td).text().trim()).get());});
  doc.autoTable({head:hds,body:rows,startY:54,margin:{left:ML,right:ML,top:54,bottom:34},styles:{font:'helvetica',fontSize:8,cellPadding:{top:4,bottom:4,left:5,right:5},lineColor:[50,54,61],lineWidth:.25,textColor:[200,209,217]},headStyles:{fillColor:[21,27,34],textColor:[240,165,0],fontStyle:'bold',fontSize:8},alternateRowStyles:{fillColor:[33,38,45]},bodyStyles:{fillColor:[22,27,34]},didDrawPage(h){const pH=doc.internal.pageSize.getHeight();doc.setFontSize(7);doc.setTextColor(140,150,165);doc.text(`Page ${h.pageNumber}`,pW/2,pH-14,{align:'center'});}});
  doc.save(`${currentPayType}_payments_${today()}.pdf`);toast('PDF exported','success');
});

/* boot */
switchPage('dashboard');
});
