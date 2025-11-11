const state = {
  tab: 'overview',
  filters: {
    range: '30d',
    from: null,
    to: null,
    segment: 'all',
    channel: 'all',
  },
};

const el = (sel) => document.querySelector(sel);
const httpCache = new Map();
function cacheKey(url){ return url; }
// Remove snapshot only for a specific tab under the current filter signature
function clearSnapshotForTabCurrentFilter(tab){
  try{ localStorage.removeItem(snapKey(tab)); }catch{}
  if(tab === 'journey'){
    try{ delete window.__jnSankeyHash; }catch{}
  }
}
// Remove all snapshots for a given tab across any filter signature
function clearSnapshotsForTab(tab){
  try{
    const prefix = SNAP_NS + tab + '|';
    for(let i=localStorage.length-1;i>=0;i--){
      const k = localStorage.key(i);
      if(k && k.startsWith(prefix)){
        try{ localStorage.removeItem(k); }catch{}
      }
    }
  }catch{}
}
// Remove all snapshots that match the current filter signature
function clearSnapshotsForCurrentFilters(){
  try{
    const suffix = '|' + filterSig();
    for(let i=localStorage.length-1;i>=0;i--){
      const k = localStorage.key(i);
      if(!k) continue;
      if(k.startsWith(SNAP_NS) && k.endsWith(suffix)){
        try{ localStorage.removeItem(k); }catch{}
      }
    }
  }catch{}
}

async function renderLLM(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="llm-load" class="tab">Load</button>
      <button id="llm-refresh" class="tab">Refresh</button>
      <span id="llm-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card" style="grid-column: 1 / -1"><h3>Executive Summary</h3><div id="llm-summary"></div></div>
      <div class="card"><h3>Key Insights</h3><ul id="llm-insights" class="muted"></ul></div>
      <div class="card"><h3>Recommendations</h3><ul id="llm-recs" class="muted"></ul></div>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr; margin-top:12px;">
      <div class="card"><h3>KPIs</h3>
        <div style="display:flex;gap:16px;flex-wrap:wrap" id="llm-kpis">
          <div><div class="muted">Sessions</div><div id="llm-kpi-sessions" class="kpi-value">—</div></div>
          <div><div class="muted">Users</div><div id="llm-kpi-users" class="kpi-value">—</div></div>
          <div><div class="muted">CR</div><div id="llm-kpi-cr" class="kpi-value">—</div></div>
          <div><div class="muted">Revenue</div><div id="llm-kpi-rev" class="kpi-value">—</div></div>
        </div>
      </div>
      <div class="card"><h3>Funnel (LLM view)</h3><div class="chart" id="llm-chart-funnel"></div></div>
      <div class="card"><h3>SEO Distribution</h3><div class="chart" id="llm-chart-seo"></div></div>
      <div class="card"><h3>Retention</h3><div class="chart" id="llm-chart-ret"></div></div>
      <div class="card" style="grid-column: 1 / -1"><h3>Data Quality</h3>
        <div id="llm-dq" class="muted"></div>
      </div>
    </div>
  `;
  const statusEl = el('#llm-status');

  function renderReport(payload){
    const rep = payload?.report?.parsed || payload?.report || {};
    const summary = rep.executive_summary || rep.summary || rep.insights || '';
    el('#llm-summary').innerHTML = summary ? `<div style="white-space:pre-wrap">${summary}</div>` : '<div class="muted">No summary.</div>';
    // Build grouped insights if structured schema is present
    let ins = [];
    try{
      if(rep.insights && typeof rep.insights==='object'){
        const groups = ['business','journey','seo','retention'];
        for(const g of groups){
          const v = rep.insights[g];
          if(!v) continue;
          const bullets = Array.isArray(v) ? v : (Array.isArray(v.bullets)? v.bullets : []);
          if(bullets.length){
            ins.push(`${g.toUpperCase()}:`);
            bullets.forEach(b=> ins.push(`• ${b}`));
          }
        }
      }
    }catch{}
    if(!ins.length){
      ins = Array.isArray(rep.key_insights) ? rep.key_insights : (Array.isArray(rep.highlights) ? rep.highlights : []);
    }
    const recEl = el('#llm-recs');
    const insEl = el('#llm-insights'); insEl.innerHTML = ins.length ? ins.map(i=>`<li>${i}</li>`).join('') : '<li class="muted">—</li>';
    // Recommendations: combine recommendations + next_best_actions + risk_alerts
    const recs = [];
    try{
      if(Array.isArray(rep.recommendations)) recs.push(...rep.recommendations);
      if(Array.isArray(rep.next_best_actions)) recs.push(...rep.next_best_actions.map(a=> typeof a==='string'? a : `${a.action} — impact:${a.impact||''}/effort:${a.effort||''}`));
      if(Array.isArray(rep.risk_alerts)) recs.push(...rep.risk_alerts.map(r=> typeof r==='string'? r : `Risk(${r.severity||''}): ${r.title||''} — ${r.reason||''}`));
    }catch{}
    recEl.innerHTML = recs.length ? recs.map(i=>`<li>${i}</li>`).join('') : '<li class="muted">—</li>';
  }

  function renderCharts(charts){
    if(!charts || typeof charts !== 'object') return;
    try{
      const k = charts.kpis || {};
      const s = Number(k.sessions||0), u = Number(k.users||0), cr = Number(k.cr||0), rev = Number(k.revenue||0);
      const ks = el('#llm-kpi-sessions'); if(ks) ks.textContent = fmt(s);
      const ku = el('#llm-kpi-users'); if(ku) ku.textContent = fmt(u);
      const kc = el('#llm-kpi-cr'); if(kc) kc.textContent = `${fmt((cr||0)*100,2)}%`;
      const kr = el('#llm-kpi-rev'); if(kr) kr.textContent = fmtCurrency(rev);
    }catch{}
    // Funnel
    try{
      const fEl = el('#llm-chart-funnel');
      const data = Array.isArray(charts.funnel) ? charts.funnel : [];
      if(fEl && data.length){ const c=echarts.init(fEl); c.setOption({ tooltip:{ trigger:'item' }, series:[{ type:'funnel', data }] }); }
    }catch{}
    // SEO distribution
    try{
      const sEl = el('#llm-chart-seo');
      const dist = Array.isArray(charts.seo_distribution) ? charts.seo_distribution : [];
      if(sEl && dist.length){ const c=echarts.init(sEl); c.setOption({ tooltip:{ trigger:'item' }, series:[{ type:'pie', radius:['40%','70%'], data: dist }] }); }
    }catch{}
    // Retention
    try{
      const rEl = el('#llm-chart-ret');
      const ts = Array.isArray(charts.retention_timeseries) ? charts.retention_timeseries : [];
      if(rEl && ts.length){ const cats = ts.map(r=>r.date||''); const ret = ts.map(r=> r.retained||0); const ch = ts.map(r=> r.churned||0); const c=echarts.init(rEl); c.setOption({ tooltip:{ trigger:'axis' }, legend:{ data:['Retained','Churned'] }, xAxis:{ type:'category', data: cats }, yAxis:{ type:'value' }, series:[{ name:'Retained', type:'line', data: ret }, { name:'Churned', type:'line', data: ch }] }); }
    }catch{}
    // Data quality text
    try{
      const dqEl = el('#llm-dq'); const dq = charts.data_quality || {};
      if(dqEl){ dqEl.innerHTML = `
        <div style="display:flex;gap:16px;flex-wrap:wrap">
          <div>Events: <b>${fmt(Number(dq.events_count||0))}</b></div>
          <div>Sessions: <b>${fmt(Number(dq.sessions_count||0))}</b></div>
          <div>Missing %: <b>${fmt(Number(dq.missing_values_pct||0),2)}%</b></div>
          <div>Duplicates %: <b>${fmt(Number(dq.duplicate_events_pct||0),2)}%</b></div>
          <div>Last event: <b>${dq.last_event_ts ? String(dq.last_event_ts) : '—'}</b></div>
        </div>`; }
    }catch{}
  }

  // Restore
  (function(){ const snap = snapGet('llm'); if(snap){ renderReport(snap); renderCharts(snap.charts); statusEl.textContent='Restored from cache'; } })();

  async function run(fetchFresh=false){
    const q = buildQuery();
    let url = `/api/v1/openrouter/report?${q}`;
    if(fetchFresh){ const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    const data = fetchFresh ? await safeGet(url) : await getWithTTL(url, 600000);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    snapUpdate('llm', data);
    renderReport(data);
    renderCharts(data?.charts);
  }

  el('#llm-load').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('llm'); run(true); });
  el('#llm-refresh').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('llm'); run(true); });
  if(!snapGet('llm')){ await run(false); }
}

async function renderML(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap">
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <input id="ml-user" placeholder="Username (optional)" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px" />
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button id="ml-load" class="tab">Load</button>
        <button id="ml-refresh" class="tab">Refresh</button>
        <span id="ml-status" class="muted"></span>
      </div>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Conversion Prediction</h3><div id="ml-conv" class="chart"></div></div>
      <div class="card"><h3>Purchase Probability</h3><div id="ml-prob" class="chart"></div></div>
      <div class="card" style="grid-column: 1 / -1"><h3>User Segmentation</h3><div id="ml-seg" class="chart"></div></div>
    </div>
  `;
  const userIn = el('#ml-user');
  const statusEl = el('#ml-status');

  // Restore snapshot if exists
  (function(){
    const snap = snapGet('ml');
    if(!snap) return;
    renderConv(snap.conversion||{});
    renderProb(snap.purchase||{});
    renderSeg(snap.segmentation||{});
    statusEl.textContent = 'Restored from cache';
  })();

  function renderConv(data){
    const elc = el('#ml-conv');
    if(!elc) return;
    // Support Decision Tree payload: feature_importance map and sample_predictions[].confidence
    let avg = 0; let n = 0;
    try{
      if(Array.isArray(data.sample_predictions)){
        for(const p of data.sample_predictions){
          const v = Number(p.confidence ?? p.purchase_probability ?? 0);
          if(isFinite(v)){ avg += v; n++; }
        }
      }
    }catch{}
    const score = n ? (avg/n) : Number(data.avg_probability ?? 0);
    const title = `Avg Likelihood: ${fmt((score||0)*100,2)}%` + (data.auc_score?` • AUC ${fmt(Number(data.auc_score||0),3)}`:'');
    // Feature importance bar if available
    let cats=[], vals=[];
    try{
      const fmap = data.feature_importance;
      if(fmap && typeof fmap==='object'){
        cats = Object.keys(fmap);
        vals = cats.map(k=> Number(fmap[k]||0));
      }
    }catch{}
    const chart = echarts.init(elc);
    if(cats.length){
      chart.setOption({
        title:{ text:title, left:'center', textStyle:{ fontSize:12 } },
        tooltip:{}, xAxis:{ type:'category', data: cats }, yAxis:{ type:'value' },
        series:[{ type:'bar', name:'Importance', data: vals }]
      });
    }else{
      chart.setOption({ title:{ text:title, left:'center', textStyle:{ fontSize:12 } }, xAxis:{ type:'category', data:['Likelihood'] }, yAxis:{ type:'value', max:100 }, series:[{ type:'bar', data:[Math.round((score||0)*10000)/100] }] });
    }
  }
  function renderProb(data){
    const elp = el('#ml-prob');
    if(!elp) return;
    // Logistic Regression payload: feature_coefficients map and sample_predictions[].purchase_probability
    let avg=0, n=0;
    try{
      if(Array.isArray(data.sample_predictions)){
        for(const p of data.sample_predictions){ const v=Number(p.purchase_probability||0); if(isFinite(v)){ avg+=v; n++; } }
      }
    }catch{}
    const score = n ? (avg/n) : Number(data.avg_probability||0);
    let cats=[], vals=[];
    try{
      const coeff = data.feature_coefficients;
      if(coeff && typeof coeff==='object'){
        cats = Object.keys(coeff);
        vals = cats.map(k=> Math.abs(Number(coeff[k]||0)));
      } 
    }catch{}
    const chart = echarts.init(elp);
    const title = `Avg Purchase Prob: ${fmt((score||0)*100,2)}%` + (data.auc_score?` • AUC ${fmt(Number(data.auc_score||0),3)}`:'');
    if(cats.length){ chart.setOption({ title:{ text:title, left:'center', textStyle:{ fontSize:12 } }, tooltip:{}, xAxis:{ type:'category', data: cats }, yAxis:{ type:'value' }, series:[{ type:'bar', data: vals }] }); }
    else { chart.setOption({ title:{ text:title||'No detailed features. Showing placeholder.', left:'center', textStyle:{ fontSize:12 } }, xAxis:{ show:false }, yAxis:{ show:false }, series:[{ type:'bar', data:[Math.round((score||0)*10000)/100] }] }); }
  }
  function renderSeg(data){
    const els = el('#ml-seg');
    if(!els) return;
    // KMeans payload: cluster_stats map keyed by cluster label -> {user_count,...}
    let cats=[], vals=[];
    try{
      const stats = data.cluster_stats;
      if(stats && typeof stats==='object'){
        cats = Object.keys(stats);
        vals = cats.map(k=> Number((stats[k]||{}).user_count || 0));
      }
    }catch{}
    const chart = echarts.init(els);
    if(cats.length){
      chart.setOption({ tooltip:{}, xAxis:{ type:'category', data: cats }, yAxis:{ type:'value' }, series:[{ type:'bar', data: vals }] });
    }else{
      chart.setOption({ title:{ text:'No segmentation data', left:'center', textStyle:{ fontSize:12 } } });
    }
  }

  async function run(fetchFresh=false){
    const username = (userIn.value||'').trim();
    const q = new URLSearchParams(); if(username) q.set('username', username);
    let uConv = `/api/v1/spark-analytics/conversion-prediction` + (q.toString()?`?${q.toString()}`:'');
    let uProb = `/api/v1/spark-analytics/purchase-probability` + (q.toString()?`?${q.toString()}`:'');
    let uSeg = `/api/v1/spark-analytics/user-segmentation` + (q.toString()?`?${q.toString()}`:'');
    if(fetchFresh){
      const arr = [uConv,uProb,uSeg].map(withBypass);
      arr.forEach(({clean})=>{ httpCache.delete(clean); lsDel(clean); });
      [uConv,uProb,uSeg] = arr.map(x=>x.fresh);
    }
    statusEl.textContent = 'Loading…';
    const [conv, prob, seg] = await Promise.all([
      fetchFresh ? safeGet(uConv) : getWithTTL(uConv, 600000),
      fetchFresh ? safeGet(uProb) : getWithTTL(uProb, 600000),
      fetchFresh ? safeGet(uSeg) : getWithTTL(uSeg, 600000)
    ]);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    snapUpdate('ml', { conversion: conv||{}, purchase: prob||{}, segmentation: seg||{} });
    renderConv(conv||{}); renderProb(prob||{}); renderSeg(seg||{});
  }

  el('#ml-load').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('ml'); run(true); });
  el('#ml-refresh').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('ml'); run(true); });
  if(!snapGet('ml')){ await run(false); }
}
// LocalStorage-backed persistence
const LS_NS = 'spa_cache_v1:';
const SNAP_NS = 'spa_snap_v1:';
function lsKey(url){ return LS_NS + url; }
function lsGet(url){
  try{ const s = localStorage.getItem(lsKey(url)); return s ? JSON.parse(s) : null; }catch{ return null; }
}
function lsSet(url, data){
  try{ localStorage.setItem(lsKey(url), JSON.stringify({ data, ts: Date.now() })); }catch{}
}
function lsData(payload){ return payload && typeof payload === 'object' ? (payload.data ?? payload) : payload; }
function lsDel(url){ try{ localStorage.removeItem(lsKey(url)); }catch{} }
// Build a stable signature for current filters so snapshots are scoped per-filter
function filterSig(){
  const { range, from, to, segment, channel } = state.filters || {};
  return `r=${range||''}|f=${from||''}|t=${to||''}|s=${segment||''}|c=${channel||''}`;
}
function snapKey(tab){ return SNAP_NS + tab + '|' + filterSig(); }
function snapSet(tab, payload){ try{ localStorage.setItem(snapKey(tab), JSON.stringify({ ts: Date.now(), payload })); }catch{} }
function snapGet(tab){ try{ const s = localStorage.getItem(snapKey(tab)); return s ? JSON.parse(s).payload : null; }catch{ return null; } }
function snapRaw(tab){ try{ const s = localStorage.getItem(snapKey(tab)); return s ? JSON.parse(s) : null; }catch{ return null; } }
function snapAgeMs(tab){ try{ const r = snapRaw(tab); return r && typeof r.ts==='number' ? (Date.now()-r.ts) : Infinity; }catch{ return Infinity; } }
// Only persist snapshot when payload is non-empty to avoid wiping good cache with empty results
function hasAnyData(obj){
  try{
    if(obj == null) return false;
    if(Array.isArray(obj)) return obj.length > 0;
    if(typeof obj !== 'object') return true;
    // plain object: if no keys -> empty
    const keys = Object.keys(obj);
    if(keys.length === 0) return false;
    for(const k of keys){
      const v = obj[k];
      if(Array.isArray(v)){ if(v.length > 0) return true; continue; }
      if(v && typeof v === 'object'){
        if(Object.keys(v).length > 0 && hasAnyData(v)) return true;
        continue;
      }
      if(v != null) return true;
    }
  }catch{}
  return false;
}
function snapMaybe(tab, payload){ if(hasAnyData(payload)) snapSet(tab, payload); }
// Update snapshot only if payload has data and is different from the existing one
function snapUpdate(tab, payload){
  if(!hasAnyData(payload)) return;
  try{
    const prev = snapGet(tab);
    const same = prev && JSON.stringify(prev) === JSON.stringify(payload);
    if(!same){ snapSet(tab, payload); }
  }catch{ snapSet(tab, payload); }
}
// Legacy helpers: migrate old snapshots (without filter signature) to new scoped keys
function snapGetLegacyRaw(tab){
  try{ const s = localStorage.getItem(SNAP_NS + tab); return s ? JSON.parse(s) : null; }catch{ return null; }
}
function migrateOldSnapshots(){
  try{
    const prefix = SNAP_NS;
    for(let i=0;i<localStorage.length;i++){
      const k = localStorage.key(i);
      if(!k || !k.startsWith(prefix)) continue;
      // If already contains filter pipe, skip
      if(k.includes('|')) continue;
      const tab = k.slice(prefix.length);
      const raw = snapGetLegacyRaw(tab);
      const payload = raw && raw.payload;
      if(hasAnyData(payload)){
        // write to new key scoped by current filters
        try{ localStorage.setItem(snapKey(tab), JSON.stringify({ ts: Date.now(), payload })); }catch{}
      }
    }
  }catch{}
}
// TTL-aware local cache getter
async function getWithTTL(url, ttlMs = 600000){
  const key = cacheKey(url);
  if(httpCache.has(key)) return httpCache.get(key);
  const persisted = lsGet(key);
  if(persisted && typeof persisted === 'object' && typeof persisted.ts === 'number'){
    if(Date.now() - persisted.ts <= ttlMs){
      const data = lsData(persisted);
      httpCache.set(key, data);
      return data;
    }
    // expired -> drop
    lsDel(key);
  }
  const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
  const res = await fetch(url, { headers: { 'Accept': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) } });
  if(!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  httpCache.set(key, json);
  lsSet(key, json);
  return json;
}
// Simple debounce helper
function debounce(fn, ms){ let t; return (...args)=>{ clearTimeout(t); t = setTimeout(()=>fn.apply(null,args), ms); }; }
function requestIdle(cb){
  if(window.requestIdleCallback){ return window.requestIdleCallback(cb, { timeout: 1500 }); }
  return setTimeout(cb, 300);
}
// Build a fresh URL that bypasses caches; also return the original clean URL for invalidation
function withBypass(url){
  const join = url.includes('?') ? '&' : '?';
  return { clean: url, fresh: `${url}${join}bypass_cache=true&_ts=${Date.now()}` };
}
function showToast(message, kind = 'info', timeout = 2600){
  const t = el('#toast');
  if(!t) return;
  t.textContent = message;
  t.style.display = 'block';
  t.style.background = kind === 'error' ? '#b91c1c' : (kind === 'success' ? '#065f46' : '#111827');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(()=>{ t.style.display='none'; }, timeout);
}
const view = el('#view');

function setActiveTab(name){
  state.tab = name;
  for(const b of document.querySelectorAll('.tab')){
    b.classList.toggle('active', b.dataset.tab === name);
  }
  // Expose for debugging
  window.journeyRun = (typeof run === 'function') ? run : undefined;
  render();
}

function toISO(dt){
  try{ return new Date(dt).toISOString(); } catch { return null; }
}

function presetToDates(range){
  const now = new Date();
  const end = new Date(now);
  const start = new Date(now);
  switch(range){
    case '7d': start.setDate(start.getDate()-7); break;
    case '30d': start.setDate(start.getDate()-30); break;
    case 'mtd': start.setDate(1); break;
    case 'qtd': {
      const m = start.getMonth();
      const qStartMonth = m - (m%3);
      start.setMonth(qStartMonth, 1);
      start.setHours(0,0,0,0);
      break;
    }
    case 'ytd': start.setMonth(0,1); break;
    default: return { start: null, end: null };
  }
  return { start: toISO(start), end: toISO(end) };
}

function fmt(n, digits=0){
  if(n == null || isNaN(n)) return '—';
  return Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(n);
}
function fmtCurrency(n){
  if(n == null || isNaN(n)) return '$0.00';
  try{
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(n));
  }catch{
    return `$${fmt(Number(n),2)}`;
  }
}
function fmtShort(n){
  if(!isFinite(n)) return '0';
  const abs = Math.abs(n);
  if(abs >= 1e9) return (n/1e9).toFixed(1)+'B';
  if(abs >= 1e6) return (n/1e6).toFixed(1)+'M';
  if(abs >= 1e3) return (n/1e3).toFixed(1)+'K';
  return String(Math.round(n));
}

async function safeGet(url){
  try{
    const key = cacheKey(url);
    if(httpCache.has(key)) return httpCache.get(key);
    const persisted = lsGet(key);
    if(persisted){
      const data = lsData(persisted);
      httpCache.set(key, data);
      return data;
    }
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, { headers: { 'Accept': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) } });
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
    lsSet(key, json);
    return json;
  }catch(e){
    showToast(`Request failed: ${String(e)}`, 'error');
    return { error: String(e) };
  }
}

async function safePost(url, body){
  try{
    const key = cacheKey(url + JSON.stringify(body));
    if(httpCache.has(key)) return httpCache.get(key);
    // Note: POST requests are not typically cached in localStorage the same way as GET.
    // This is a simple implementation that does not use lsGet/lsSet for POST.
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(body)
    });
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
    // Do not lsSet for POST to avoid caching mutable operations
    return json;
  }catch(e){
    showToast(`Request failed: ${String(e)}`, 'error');
    return { error: String(e) };
  }
}

async function preload(url){
  const key = cacheKey(url);
  if(httpCache.has(key)) return;
  try{
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, { headers: { 'Accept': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) } });
    if(!res.ok) return;
    const json = await res.json();
    httpCache.set(key, json);
    lsSet(key, json);
  }catch{}
}

function buildQuery(){
  const p = new URLSearchParams();
  const {range, from, to, segment, channel} = state.filters;
  // Backend expects start_date/end_date (ISO). If custom, use provided dates; else derive from preset.
  let startISO = null, endISO = null;
  if(range === 'custom' && from && to){
    startISO = toISO(new Date(from));
    // include full day for 'to'
    const toDt = new Date(to);
    toDt.setHours(23,59,59,999);
    endISO = toISO(toDt);
  }else{
    const pr = presetToDates(range);
    startISO = pr.start; endISO = pr.end;
  }
  if(startISO) p.set('start_date', startISO);
  if(endISO) p.set('end_date', endISO);
  if(segment && segment !== 'all') p.set('segment', segment);
  if(channel && channel !== 'all') p.set('channel', channel);
  return p.toString();
}

async function loadOverview(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="ov-load" class="tab">Load</button>
      <button id="ov-refresh" class="tab">Refresh</button>
      <span id="ov-status" class="muted"></span>
    </div>
    <div class="grid kpi">
      <div class="card"><h3>Total View Events</h3><div class="kpi-value" id="ov-sessions">—</div></div>
      <div class="card"><h3>Total Users</h3><div class="kpi-value" id="ov-users">—</div></div>
      <div class="card"><h3>Conversion Rate</h3><div class="kpi-value" id="ov-cr">—</div></div>
      <div class="card"><h3>Revenue</h3><div class="kpi-value" id="ov-rev">—</div></div>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr; margin-top:12px;">
      <div class="card"><h3>Traffic Sources Trend</h3><div class="chart" id="chart-trend"></div></div>
      <div class="card"><h3>User Segmentation</h3><div class="chart" id="chart-seg"></div></div>
    </div>
  `;
  const statusEl = el('#ov-status');

  // Simplified data update function
  function updateUI(data){
    if(!data) {
      statusEl.textContent = 'No data to display.';
      return;
    }
    // KPIs
    let kpiSessions = Number(data.total_sessions ?? 0);
    const kpiUsers = Number(data.total_users ?? 0);
    let kpiCR = Number(data.conversion_rate ?? 0);
    // Fallbacks if snapshot lacked computed fields
    if(!Number.isFinite(kpiSessions) || kpiSessions <= 0){
      const tv = Number(data.seo_site_metrics?.total_views ?? 0);
      if(Number.isFinite(tv) && tv > 0) kpiSessions = tv;
    }
    if(!Number.isFinite(kpiCR) || kpiCR <= 0){
      const dcr = Number(data.derived_cr ?? 0);
      if(Number.isFinite(dcr) && dcr > 0) kpiCR = dcr;
    }
    const kpiRev = Number(data.revenue ?? 0);
    // Update header quick KPIs
    el('#qk-sessions') && (el('#qk-sessions').textContent = fmt(Number.isFinite(kpiSessions) ? kpiSessions : 0));
    el('#qk-cr') && (el('#qk-cr').textContent = `${fmt(Number.isFinite(kpiCR) ? kpiCR*100 : 0, 2)}%`);
    // Update Overview card KPIs
    el('#ov-sessions') && (el('#ov-sessions').textContent = fmt(Number.isFinite(kpiSessions) ? kpiSessions : 0));
    el('#ov-users') && (el('#ov-users').textContent = fmt(Number.isFinite(kpiUsers) ? kpiUsers : 0));
    el('#ov-cr') && (el('#ov-cr').textContent = `${fmt(Number.isFinite(kpiCR) ? kpiCR*100 : 0, 2)}%`);
    // Force fill if still '—'
    const sessEl = el('#ov-sessions');
    if(sessEl && (sessEl.textContent === '—' || sessEl.textContent.trim() === '')){
      const tv = Number(data.seo_site_metrics?.total_views ?? 0);
      if(Number.isFinite(tv) && tv > 0){ sessEl.textContent = fmt(tv); }
    }
    const crEl = el('#ov-cr');
    if(crEl && (crEl.textContent.startsWith('—') || crEl.textContent.trim() === '' || /NaN/.test(crEl.textContent))){
      const dcr = Number(data.derived_cr ?? 0);
      if(Number.isFinite(dcr) && dcr > 0){ crEl.textContent = `${fmt(dcr*100, 2)}%`; }
    }
    el('#ov-rev') && (el('#ov-rev').textContent = fmtCurrency(Number.isFinite(kpiRev) ? kpiRev : 0));

    // Trend chart
    const trendEl = el('#chart-trend');
    if(trendEl && data.traffic_trend?.categories?.length){
      const chart = echarts.init(trendEl);
      chart.setOption({
        tooltip: {},
        legend: { data: data.traffic_trend.series.map(s => s.name) },
        xAxis: { type: 'category', data: data.traffic_trend.categories },
        yAxis: { type: 'value', axisLabel: { formatter: (v)=> fmtShort(v) } },
        series: data.traffic_trend.series
      });
    } else if(trendEl) {
      trendEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
    }

    // Segmentation chart
    const segEl = el('#chart-seg');
    if(segEl && data.segments?.categories?.length && data.segments.series?.[0]?.data){
      const seg = echarts.init(segEl);
      seg.setOption({
        tooltip: {},
        xAxis: { type: 'category', data: data.segments.categories },
        yAxis: { type: 'value', axisLabel: { formatter: (v)=> fmtShort(v) } },
        series: [{ type: 'bar', name: 'Users', data: data.segments.series[0].data }]
      });
    } else if(segEl) {
      segEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
    }
  }

  // Restore from snapshot if available
  const snap = snapGet('overview');
  if(snap){
    updateUI(snap);
    statusEl.textContent = 'Restored from cache';
    // If critical KPIs missing in snapshot, do an immediate fresh run; else refresh in background
    const missingCritical = !(Number.isFinite(Number(snap.total_sessions))) || !(Number.isFinite(Number(snap.total_users)));
    // Do not auto-refresh; user actions (Load/Refresh) will fetch and update cache
  }

  async function run(fetchFresh = false){
    const q = buildQuery();
    let bizUrl = `/api/v1/metrics/business?${q}`;
    let seoUrl = `/api/v1/analytics/seo?${q}`;
    let jnUrl = `/api/v1/analytics/journey?${q}`;
    if(fetchFresh){
      const arr = [bizUrl, seoUrl, jnUrl].map(withBypass);
      arr.forEach(({clean})=>{ httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); });
      [bizUrl, seoUrl, jnUrl] = arr.map(x=>x.fresh);
    }
    statusEl.textContent = 'Loading…';
    const business = await safeGet(bizUrl);
    const seo = await safeGet(seoUrl);
    const journey = await safeGet(jnUrl);
    // Guard: require SEO to succeed for charts; continue if business/journey fail
    if(seo?.error){
      statusEl.textContent = `Error: ${seo?.error}`;
      showToast('Overview load failed (SEO). Using cached data if available.', 'error');
      const snapErr = snapGet('overview');
      if(snapErr) updateUI(snapErr);
      return;
    }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;

    // Build fallbacks from SEO when business metrics are missing
    const seoSite = seo && typeof seo.site_metrics === 'object' ? seo.site_metrics : {};
    const seoDist = seo && seo.sources && seo.sources.distribution ? seo.sources.distribution : null;
    const segFromSeo = seoDist ? {
      categories: Object.keys(seoDist),
      series: [{ name: 'Users', data: Object.values(seoDist) }]
    } : { categories: [], series: [] };

    // Derive conversion rate from journey funnel when missing
    let derivedCR = null;
    try{
      const jf = journey && journey.funnel;
      if(jf){
        if(Array.isArray(jf.steps)){
          const views = jf.steps.find(s=>/(view|views)/i.test(String(s.name||s.step||'')));
          const purch = jf.steps.find(s=>/purchase/i.test(String(s.name||s.step||'')));
          const v = (views?.value ?? views?.count ?? 0);
          const p = (purch?.value ?? purch?.count ?? 0);
          derivedCR = v ? (p / v) : 0;
        }else if(typeof jf === 'object'){
          const v = Number(jf.Views ?? jf.views ?? jf.view ?? 0) || 0;
          const p = Number(jf.Purchase ?? jf.purchase ?? 0) || 0;
          derivedCR = v ? (p / v) : 0;
        }
      }
    }catch{}

    // Derive sessions from SEO timeseries if needed
    let derivedSessions = 0;
    try{
      if(Array.isArray(seo?.timeseries)){
        for(const r of seo.timeseries){
          const a = Number(r.seo ?? r.SEO ?? 0) || 0;
          const b = Number(r.direct ?? r.Direct ?? 0) || 0;
          const c = Number(r.social ?? r.Social ?? 0) || 0;
          derivedSessions += a + b + c;
        }
      }
    }catch{}

    // Traffic trend fallback from seo.timeseries when needed
    let trafficTrend = seo.traffic_trend;
    if(!trafficTrend && Array.isArray(seo?.timeseries)){
      const categories = seo.timeseries.map(r=> r.date || r.time || '');
      const build = (k)=> seo.timeseries.map(r=> Number(r[k] ?? r[k?.toUpperCase()] ?? 0) || 0);
      trafficTrend = {
        categories,
        series: [
          { name:'SEO', type:'line', data: build('seo') },
          { name:'Direct', type:'line', data: build('direct') },
          { name:'Social', type:'line', data: build('social') },
        ]
      };
    }

    // Prefer business metrics when they are positive; otherwise fallback to SEO-derived
    const totalSessions = Number(business.total_sessions ?? business.sessions ?? 0);
    const totalUsers = Number(business.total_users ?? business.users ?? 0);
    // Choose conversion rate: prefer journey-derived when business is missing/zero
    const bizCR = Number(business.conversion_rate ?? 0) || 0;
    const finalCR = (Number.isFinite(bizCR) && bizCR > 0)
      ? bizCR
      : (Number.isFinite(derivedCR) && derivedCR > 0 ? derivedCR : 0);
    const revenueVal = (Number(business.revenue ?? 0) || Number(seo.revenue ?? 0) || 0);
    const data = {
      total_sessions: (Number.isFinite(totalSessions) && totalSessions > 0)
        ? totalSessions
        : Number(seoSite.total_views ?? derivedSessions ?? 0) || 0,
      total_users: (Number.isFinite(totalUsers) && totalUsers > 0)
        ? totalUsers
        : Number(seoSite.unique_visitors ?? 0) || 0,
      conversion_rate: finalCR,
      revenue: revenueVal,
      traffic_trend: trafficTrend ?? { categories: [], series: [] },
      segments: business.segments ?? segFromSeo,
      seo_site_metrics: seoSite,
      derived_cr: finalCR
    };

    // Save snapshot only if fresh or not yet cached
    snapUpdate('overview', data);
    updateUI(data);
  }

  el('#ov-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('overview'); run(true); });
  el('#ov-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('overview'); run(true); });

  // Auto-fetch on first visit if there is no snapshot
  if(!snap){
    await run(false);
  }
}

async function renderCart(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="cart-load" class="tab">Load</button>
      <button id="cart-refresh" class="tab">Refresh</button>
      <span id="cart-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Abandonment by Channel</h3><div class="chart" id="chart-ab"></div></div>
      <div class="card"><h3>Cart Size Distribution</h3><div class="chart" id="chart-dist"></div></div>
    </div>
  `;
  const statusEl = el('#cart-status');
  // Restore snapshot
  (function(){
    const snap = snapGet('cart');
    if(!snap) return;
    // Abandonment chart
    const channels = (snap.channels && Object.keys(snap.channels)) || [];
    const abData = channels.map(c=> typeof snap.channels?.[c]?.abandonment_rate === 'number' ? Math.round(snap.channels[c].abandonment_rate*1000)/10 : null);
    const abEl = el('#chart-ab');
    if(abEl && abData.length){ const ab = echarts.init(abEl); ab.setOption({ tooltip:{ trigger:'axis' }, legend:{ data:['Abandonment %'] }, xAxis:{ type:'category', data: channels }, yAxis:{ type:'value', axisLabel:{ formatter:'{value}%' } }, series:[{ name:'Abandonment %', type:'bar', data: abData }] }); }
    // Size distribution
    const distEl = el('#chart-dist'); const distCats=['1','2','3','4','5+'];
    if(Array.isArray(snap.size_distribution)){
      const map = new Map(snap.size_distribution.map(r=>[String(r.size), r.count]));
      const distData = distCats.map(k=>map.get(k) ?? 0);
      if(distEl){ const chart = echarts.init(distEl); chart.setOption({ tooltip:{}, xAxis:{ type:'category', data: distCats }, yAxis:{ type:'value' }, series:[{ type:'line', data: distData }] }); }
    }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    let urlA = `/api/v1/analytics/cart?${q}`;
    let urlT = `/api/v1/cart/trends?${q}`;
    if(fetchFresh){ const a = withBypass(urlA), b = withBypass(urlT); [a,b].forEach(({clean})=>{ httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); }); urlA = a.fresh; urlT = b.fresh; }
    statusEl.textContent = 'Loading…';
    const analysis = await safeGet(urlA);
    const trends = await safeGet(urlT);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Cart (fresh only or if missing)
    snapUpdate('cart', { channels: analysis?.channels ?? {}, size_distribution: analysis?.size_distribution ?? [] });

  // Abandonment by channel
  const channels = (analysis.channels && Object.keys(analysis.channels)) || [];
  const abData = channels.map(c => {
    const v = analysis.channels?.[c]?.abandonment_rate;
    return typeof v === 'number' ? Math.round(v*1000)/10 : null;
  });
  const abEl = el('#chart-ab');
  if(abEl && abData.length){
    const ab = echarts.init(abEl);
    ab.setOption({
      tooltip: { trigger:'axis' },
      legend: { data:['Abandonment %'] },
      xAxis: { type:'category', data: channels },
      yAxis: { type:'value', axisLabel:{ formatter: '{value}%' } },
      series: [{ name:'Abandonment %', type:'bar', data: abData }]
    });
  } else if(abEl) { abEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Cart size distribution
  const distEl = el('#chart-dist');
  const distCats = ['1','2','3','4','5+'];
  let distData = [];
  if(analysis.size_distribution && Array.isArray(analysis.size_distribution)){
    // Expect array of {size,count}
    const map = new Map();
    for(const r of analysis.size_distribution){
      map.set(String(r.size), r.count);
    }
    distData = distCats.map(k=>map.get(k) ?? 0);
  }
  if(distEl && distData.length){
    const distChart = echarts.init(distEl);
    distChart.setOption({
      tooltip: {},
      xAxis: { type:'category', data: distCats },
      yAxis: { type:'value' },
      series: [{ type:'line', data: distData }]
    });
  } else if(distEl) { distEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  }
  el('#cart-load').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('cart'); run(true); });
  el('#cart-refresh').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('cart'); run(true); });
  // Auto-fetch on first visit if there is no snapshot yet
  if(!snapGet('cart')){ await run(false); }
}

async function renderJourney(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="jn-load" type="button" class="tab">Load</button>
      <button id="jn-refresh" type="button" class="tab">Refresh</button>
      <span id="jn-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card"><h3>Funnel</h3><div class="chart" id="chart-funnel"></div></div>
      <div class="card"><h3>Top Paths (Sankey)</h3><div class="chart" id="chart-sankey"></div></div>
    </div>
  `;
  const statusEl = el('#jn-status');
  // Restore snapshot
  (function(){
    const snap = snapGet('journey'); if(!snap) return;
    // Funnel
    let funnelData=[]; if(snap.funnel && Array.isArray(snap.funnel.steps)) funnelData = snap.funnel.steps.map(s=>({ name:s.name||s.step||'', value:s.value||s.count||0 })); else if(snap.funnel && typeof snap.funnel==='object') funnelData = Object.entries(snap.funnel).map(([name,value])=>({ name, value }));
    const funnelEl = el('#chart-funnel'); if(funnelEl && funnelData.length){ const chart=echarts.init(funnelEl); chart.setOption({ tooltip:{ trigger:'item' }, series:[{ type:'funnel', data:funnelData }] }); }
    // Sankey
    let nodes=[], links=[]; if(snap.paths?.links){ links=snap.paths.links; nodes = snap.paths.nodes || Array.from(new Set(links.flatMap(l=>[l.source,l.target]))); }
    // If snapshot lacks links, synthesize from funnel steps as a fallback
    if((!links || !links.length) && snap.funnel){
      try{
        let steps=[];
        if(Array.isArray(snap.funnel.steps)) steps = snap.funnel.steps.map(s=>({ name:s.name||s.step||'', value:s.value||s.count||0 }));
        else if(typeof snap.funnel==='object') steps = Object.entries(snap.funnel).map(([name,value])=>({ name, value }));
        steps = steps.filter(s=>s.name);
        const syn=[]; for(let i=0;i<steps.length-1;i++){ const a=steps[i], b=steps[i+1]; const v = isFinite(b.value) && b.value>0 ? b.value : Math.max(0, Math.min(a.value||0, b.value||0)); syn.push({ source:a.name, target:b.name, value:v }); }
        if(syn.length){ links = syn; nodes = Array.from(new Set(syn.flatMap(l=>[l.source,l.target]))); }
      }catch{}
    }
    // Enforce DAG and limit edges for snapshot render
    if(Array.isArray(links) && links.length){
      const stageOf = (label)=>{
        const s = String(label||'').toLowerCase();
        if(/purchase|order|success|complete/.test(s)) return 3;
        if(/checkout|payment|pay/.test(s)) return 2;
        if(/add\s*to\s*cart|cart/.test(s)) return 1;
        if(/view|landing|home|list|product/.test(s)) return 0;
        return 4;
      };
      const seen = new Set();
      links = links.filter(l=>{
        if(!l || !l.source || !l.target) return false;
        const a = String(l.source), b = String(l.target);
        if(a === b) return false;
        const sa = stageOf(a), sb = stageOf(b);
        if(!(sa < sb)) return false;
        const key = a+"->"+b;
        if(seen.has(key)) return false;
        seen.add(key); return true;
      });
      if(links.length > 100){ links = links.slice().sort((a,b)=>(b.value||0)-(a.value||0)).slice(0,100); }
      nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
    }
    const sankeyEl = el('#chart-sankey'); if(sankeyEl && nodes.length && links.length){
      const currHash = JSON.stringify({nodes,links});
      const prev = (echarts.getInstanceByDom && echarts.getInstanceByDom(sankeyEl)) || null;
      if(!prev || window.__jnSankeyHash !== currHash){
        if(prev){ prev.dispose(); }
        const sankey=echarts.init(sankeyEl);
        sankey.setOption({ animation:false, tooltip:{}, series:[{ type:'sankey', data:nodes.map(n=>({ name:n })), links }] });
        window.__jnSankeyHash = currHash;
        requestAnimationFrame(()=>{ try{ sankey.resize(); }catch{} });
      }
    }
    statusEl.textContent = 'Restored from cache';
    // Do not auto-refresh; user decides when to fetch new data via Load/Refresh
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    let url = `/api/v1/analytics/journey?${q}`;
    if(fetchFresh){ const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    let journey = null;
    try{
      journey = fetchFresh ? (await safeGet(url)) : (await getWithTTL(url, 600000));
    }catch(e){ console.debug('Journey fetch error', e); }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Do not persist raw API shape; we'll persist processed nodes/links below

  // Funnel data
  let funnelData = [];
  if(journey){
    // common shapes: journey.funnel.steps = [{name,value}] or journey.funnel = {Landing: n, ...}
    if(journey.funnel && Array.isArray(journey.funnel.steps)){
      funnelData = journey.funnel.steps.map(s=>({ name: s.name || s.step || '', value: s.value || s.count || 0 }));
    }else if(journey.funnel && typeof journey.funnel === 'object'){
      funnelData = Object.entries(journey.funnel).map(([name, value])=>({ name, value }));
    }
  }
  const funnelEl = el('#chart-funnel');
  if(funnelEl && funnelData.length){
    const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(funnelEl);
    if(prev){ prev.dispose(); }
    const funnel = echarts.init(funnelEl);
    funnel.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'funnel', data: funnelData }]
    });
    requestAnimationFrame(()=>{ try{ funnel.resize(); }catch{} });
  } else if(funnelEl) { funnelEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Sankey data
  let nodes = [];
  let links = [];
  if(journey){
    // Prefer paths if present
    if(journey.paths){
      if(Array.isArray(journey.paths.links)){
        links = journey.paths.links;
        // Limit to Top 100 edges by value
        if(links.length > 100){ links = links.slice().sort((a,b)=>(b.value||0)-(a.value||0)).slice(0,100); }
        // Recompute nodes from limited links
        nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
      }else if(Array.isArray(journey.paths)){
        links = journey.paths;
        if(links.length > 100){ links = links.slice().sort((a,b)=>(b.value||0)-(a.value||0)).slice(0,100); }
        nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
      }
    }
    // Fallback to top_paths (array of links) if paths missing
    if(!links.length && Array.isArray(journey.top_paths) && journey.top_paths.length){
      links = journey.top_paths;
      if(links.length > 100){ links = links.slice().sort((a,b)=>(b.value||0)-(a.value||0)).slice(0,100); }
      nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
    }
  }
  // Final fallback: synthesize links from funnel steps when API links are missing
  if(!links.length && Array.isArray(funnelData) && funnelData.length > 1){
    try{
      const steps = funnelData
        .map(s=>({ name: String(s.name||'').trim()||'Step', value: Number(s.value||0) }))
        .filter(s=>s.name && isFinite(s.value));
      const syn = [];
      for(let i=0;i<steps.length-1;i++){
        const a = steps[i];
        const b = steps[i+1];
        const v = isFinite(b.value) && b.value>0 ? b.value : Math.max(0, Math.min(a.value||0, b.value||0));
        syn.push({ source: a.name, target: b.name, value: v });
      }
      if(syn.length){
        links = syn;
        nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
      }
    }catch{}
  }
  // Persist processed nodes/links snapshot only if there is meaningful new data.
  try{
    const hasLinks = Array.isArray(links) && links.length > 0;
    const payload = { funnel: journey?.funnel ?? null, paths: { nodes, links } };
    if(hasLinks){
      if(fetchFresh){ snapSet('journey', payload); }
      else { snapUpdate('journey', payload); }
    }
  }catch{}
  const sankeyEl = el('#chart-sankey');
  if(sankeyEl && nodes.length && links.length){
    const currHash = JSON.stringify({nodes,links});
    const prev = (echarts.getInstanceByDom && echarts.getInstanceByDom(sankeyEl)) || null;
    if(!prev || window.__jnSankeyHash !== currHash){
      if(prev){ prev.dispose(); }
      sankeyEl.innerHTML = '';
      const sankey = echarts.init(sankeyEl);
      sankey.setOption({
        animation:false,
        tooltip: {},
        series: [{ type: 'sankey', data: nodes.map(n=>({ name:n })), links }]
      });
      window.__jnSankeyHash = currHash;
      requestAnimationFrame(()=>{ try{ sankey.resize(); }catch{} });
      console.debug('Journey Sankey rendered', { nodeCount: nodes.length, linkCount: links.length });
    }
  } else if(sankeyEl) { sankeyEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  if(!(nodes.length && links.length)){
    console.debug('Journey Sankey empty', { nodes, links });
    statusEl.textContent = 'No path data';
  }
  }
  // Ensure buttons are clickable
  const jnLoadBtn = el('#jn-load');
  const jnRefBtn = el('#jn-refresh');
  const runDeb = debounce((fresh)=>run(fresh), 700);
  if(jnLoadBtn){
    jnLoadBtn.disabled = false; jnLoadBtn.style.pointerEvents = 'auto'; jnLoadBtn.style.cursor = 'pointer'; jnLoadBtn.style.zIndex = 10; jnLoadBtn.style.position = 'relative';
    const handler=()=>{ console.debug('Journey: Load clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('journey'); run(true); };
    jnLoadBtn.addEventListener('click', handler, { capture: true });
    jnLoadBtn.onclick = handler;
  }
  if(jnRefBtn){
    jnRefBtn.disabled = false; jnRefBtn.style.pointerEvents = 'auto'; jnRefBtn.style.cursor = 'pointer'; jnRefBtn.style.zIndex = 10; jnRefBtn.style.position = 'relative';
    const handler=()=>{ console.debug('Journey: Refresh clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('journey'); run(true); };
    jnRefBtn.addEventListener('click', handler, { capture: true });
    jnRefBtn.onclick = handler;
  }
  // Do not auto-fetch; show cache only until user clicks Load/Refresh
  // Expose for console-driven testing
  window.journeyRun = run;
}

async function renderReco(){
  view.innerHTML = `
    <div class="card">
      <h3>Recommendations</h3>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
        <select id="reco-mode" aria-label="Chế độ" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px">
          <option value="personalized" selected>Personalized</option>
          <option value="trending">Trending</option>
        </select>
        <input id="reco-user" placeholder="User ID (optional)" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px" />
        <select id="reco-time" aria-label="Khung thởi gian" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px;display:none">
          <option value="day" selected>Day</option>
          <option value="week">Week</option>
          <option value="month">Month</option>
        </select>
        <select id="reco-limit" aria-label="Số lượng" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px">
          <option value="5">5</option>
          <option value="10" selected>10</option>
          <option value="20">20</option>
        </select>
        <button id="reco-run" class="tab">Load</button>
      </div>
      <div id="reco-grid" class="grid" style="grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px"></div>
    </div>
  `;

  const modeSel = el('#reco-mode');
  const userIn = el('#reco-user');
  const timeSel = el('#reco-time');
  const limitSel = el('#reco-limit');
  const runBtn = el('#reco-run');
  const grid = el('#reco-grid');

  function skeleton(){
    grid.innerHTML = Array.from({length: 6}, ()=>`<div class="card skel" style="height:120px"></div>`).join('');
  }

  function renderItems(items){
    if(!Array.isArray(items) || !items.length){
      grid.innerHTML = `<div class="muted" style="padding:8px">Không có gợi ý.</div>`;
      return;
    }
    grid.innerHTML = items.map(it=>{
      const title = it.title || it.name || it.product_name || `#${it.product_id || ''}`;
      const score = typeof it.score === 'number' ? `Score: ${it.score.toFixed(3)}` : '';
      const price = it.price ? `$${it.price}` : '';
      return `<div class="card"><h3>${title}</h3><div class="muted">${score}</div><div>${price}</div></div>`;
    }).join('');
  }

  async function load(){
    try{
      skeleton();
      const limit = Number(limitSel.value || '10');
      let data = [];
      if(modeSel.value === 'personalized'){
        const uid = userIn.value.trim();
        const q = new URLSearchParams(); if(uid) q.set('user_id', uid); q.set('limit', String(limit));
        const res = await safeGet(`/api/v1/recommendations/personalized?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
        // Save snapshot for personalized: only store recommendations array from first entry
        const recs = Array.isArray(data) && data[0]?.recommendations ? data[0].recommendations : [];
        snapMaybe('reco:personalized', { user_id: uid || null, items: recs });
        renderItems(recs);
        return;
      }else{
        const tf = timeSel.value;
        const q = new URLSearchParams({ timeframe: tf, limit: String(limit) });
        const res = await safeGet(`/api/v1/recommendations/trending?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
        // Save snapshot for trending keyed by timeframe
        snapMaybe(`reco:trending:${tf}`, { items: data });
      }
      renderItems(data);
    }catch(e){
      showToast('Recommendation load failed', 'error');
    }
  }

  modeSel.addEventListener('change', ()=>{
    const trending = modeSel.value === 'trending';
    timeSel.style.display = trending ? '' : 'none';
    userIn.style.display = trending ? 'none' : '';
  });
  runBtn.addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('reco'); load(); });

  // initial state
  timeSel.style.display = 'none';
  // Restore snapshot without network
  (function(){
    const mode = 'personalized';
    const snapP = snapGet('reco:personalized');
    if(snapP && Array.isArray(snapP.items) && snapP.items.length){
      renderItems(snapP.items);
      return;
    }
    const snapT = snapGet('reco:trending:day');
    if(snapT && Array.isArray(snapT.items)) renderItems(snapT.items);
  })();
  // Auto-fetch on first visit if there is no snapshot for either mode
  if(!(snapGet('reco:personalized')?.items?.length) && !(snapGet('reco:trending:day')?.items?.length)){
    await load();
  }
}

async function renderSEO(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="seo-load" class="tab">Load</button>
      <button id="seo-refresh" class="tab">Refresh</button>
      <span id="seo-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Traffic Source Distribution</h3><div class="chart" id="chart-donut"></div></div>
      <div class="card"><h3>Traffic Trend</h3><div class="chart" id="chart-traffic"></div></div>
    </div>
  `;
  const statusEl = el('#seo-status');
  // Restore snapshot
  (function(){
    const snap = snapGet('seo'); if(!snap) return;
    // Donut
    const donutEl = el('#chart-donut'); let dist=[]; if(snap.sources?.distribution){ dist = Object.entries(snap.sources.distribution).map(([name,value])=>({ name, value })); }
    if(donutEl && dist.length){ const donut=echarts.init(donutEl); donut.setOption({ tooltip:{ trigger:'item' }, series:[{ type:'pie', radius:['40%','70%'], data: dist }] }); }
    // Trend
    const trafficEl = el('#chart-traffic'); if(trafficEl && Array.isArray(snap.timeseries)){ const categories = snap.timeseries.map(r=> r.date || r.time || r.t || ''); const build = k=> snap.timeseries.map(r=> r[k] ?? r[k?.toUpperCase()] ?? 0); const series=[{ name:'SEO', type:'line', data: build('seo') },{ name:'Direct', type:'line', data: build('direct') },{ name:'Social', type:'line', data: build('social') }]; const traffic=echarts.init(trafficEl); traffic.setOption({ tooltip:{ trigger:'axis' }, legend:{ data: series.map(s=>s.name) }, xAxis:{ type:'category', data: categories }, yAxis:{ type:'value' }, series }); }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    let url = `/api/v1/analytics/seo?${q}`;
    if(fetchFresh){ const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    const seo = await safeGet(url);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for SEO (fresh only or if missing)
    snapUpdate('seo', seo || {});

  // Distribution
  const donutEl = el('#chart-donut');
  let dist = [];
  if(seo && seo.sources && seo.sources.distribution){
    dist = Object.entries(seo.sources.distribution).map(([name, value])=>({ name, value }));
  }
  if(donutEl && dist.length){
    const donut = echarts.init(donutEl);
    donut.setOption({
      tooltip: { trigger:'item' },
      series: [{ type:'pie', radius:['40%','70%'], data: dist }]
    });
  } else if(donutEl) { donutEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Trend
  const trafficEl = el('#chart-traffic');
  let series = [];
  let categories = [];
  if(Array.isArray(seo?.timeseries)){
    categories = seo.timeseries.map(r=> r.date || r.time || r.t || '');
    const build = (key) => seo.timeseries.map(r=> r[key] ?? r[key?.toUpperCase()] ?? 0);
    series = [
      { name:'SEO', type:'line', data: build('seo') },
      { name:'Direct', type:'line', data: build('direct') },
      { name:'Social', type:'line', data: build('social') },
    ];
  }
  if(trafficEl && categories.length && series.length){
    const traffic = echarts.init(trafficEl);
    traffic.setOption({
      tooltip: { trigger:'axis' },
      legend: { data: series.map(s=>s.name) },
      xAxis: { type:'category', data: categories },
      yAxis: { type:'value' },
      series
    });
  } else if(trafficEl) { trafficEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  }
  el('#seo-load').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('seo'); run(true); });
  el('#seo-refresh').addEventListener('click', ()=>{ clearSnapshotForTabCurrentFilter('seo'); run(true); });
  // Auto-fetch on first visit if there is no snapshot yet
  if(!snapGet('seo')){ await run(false); }
}

async function renderRetention(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="ret-load" class="tab">Load</button>
      <button id="ret-refresh" class="tab">Refresh</button>
      <span id="ret-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Retention / Churn</h3><div class="chart" id="chart-ret"></div></div>
      <div class="card"><h3>Cohort</h3><div id="cohort-table" style="max-height:320px;overflow:auto"></div></div>
    </div>
  `;
  const statusEl = el('#ret-status');
  // Restore snapshot
  (function(){
    const snap = snapGet('retention'); if(!snap) return;
    const labels = []; const retVals=[]; const churnVals=[];
    if(Array.isArray(snap.timeseries)){
      for(const r of snap.timeseries){ labels.push(r.date || r.t || r.period || ''); retVals.push(typeof r.retention==='number'? Math.round(r.retention*1000)/10 : (r.retention ?? 0)); churnVals.push(typeof r.churn==='number'? Math.round(r.churn*1000)/10 : (r.churn ?? 0)); }
      const retEl = el('#chart-ret'); if(retEl){ const chart=echarts.init(retEl); chart.setOption({ tooltip:{ trigger:'axis' }, legend:{ data:['Retention %','Churn %'] }, xAxis:{ type:'category', data: labels }, yAxis:{ type:'value', axisLabel:{ formatter:'{value}%' } }, series:[{ name:'Retention %', type:'line', data: retVals }, { name:'Churn %', type:'line', data: churnVals }] }); }
    }
    // Render cohort table from snapshot
    const cohortDiv = el('#cohort-table');
    if(cohortDiv){
      let cohort = Array.isArray(snap.cohort) ? snap.cohort : [];
      if(cohort.length){
        try{ cohort = cohort.sort((a,b)=> String(a.cohort).localeCompare(String(b.cohort))).slice(-12); }catch{}
        const monthCount = Math.max(...cohort.map(c => Array.isArray(c.months) ? c.months.length : 0));
        const header = ['Cohort','Size', ...Array.from({length: monthCount}, (_,i)=>`M+${i}`)];
        cohortDiv.innerHTML = `
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb">${header.map(h=>`<th style=\"padding:6px\">${h}</th>`).join('')}</tr></thead>
            <tbody>
              ${cohort.map(row => `
                <tr style=\"border-bottom:1px solid #e5e7eb\">
                  <td style=\"padding:6px\">${row.cohort||''}</td>
                  <td style=\"padding:6px\">${row.size??''}</td>
                  ${Array.from({length: monthCount}, (_,i)=>{
                    const v = (row.months||[])[i];
                    const pct = (typeof v === 'number' && isFinite(v)) ? (Math.round(v*1000)/10)+'%' : '';
                    return `<td style=\"padding:6px\">${pct}</td>`;
                  }).join('')}
                </tr>`).join('')}
            </tbody>
          </table>
        `;
      }else{
        cohortDiv.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>';
      }
    }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    let urlA = `/api/v1/analytics/retention?${q}`;
    let urlB = `/api/v1/analyses/retention?${q}`;
    if(fetchFresh){ const a = withBypass(urlA), b = withBypass(urlB); [a,b].forEach(({clean})=>{ httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); }); urlA = a.fresh; urlB = b.fresh; }
    // Prefer analytics/retention; analyses/retention as fallback
    let retention = fetchFresh ? (await safeGet(urlA)) : (await getWithTTL(urlA, 600000));
    if(retention && retention.error) {
      retention = fetchFresh ? (await safeGet(urlB)) : (await getWithTTL(urlB, 600000));
    }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Retention (fresh only or if missing)
    snapUpdate('retention', retention || {});
  const labels = [];
  const retVals = [];
  const churnVals = [];
  if(Array.isArray(retention?.timeseries)){
    for(const r of retention.timeseries){
      labels.push(r.date || r.t || r.period || '');
      retVals.push(typeof r.retention === 'number' ? Math.round(r.retention*1000)/10 : (r.retention ?? 0));
      churnVals.push(typeof r.churn === 'number' ? Math.round(r.churn*1000)/10 : (r.churn ?? 0));
    }
  }else{
    // fallback demo data
    labels.push('Jan','Feb','Mar','Apr','May','Jun');
    retVals.push(68,66,64,65,67,69);
    churnVals.push(32,34,36,35,33,31);
  }
  const retEl = el('#chart-ret');
  if(!retEl) return;
  const ret = echarts.init(retEl);
  ret.setOption({
    tooltip: { trigger:'axis' },
    legend: { data:['Retention %','Churn %'] },
    xAxis: { type:'category', data: labels },
    yAxis: { type:'value', axisLabel:{ formatter: '{value}%' } },
    series: [
      { name:'Retention %', type:'line', data: retVals },
      { name:'Churn %', type:'line', data: churnVals },
    ]
  });

  // Render cohort table
  const cohortDiv = el('#cohort-table');
  if(cohortDiv){
    let cohort = Array.isArray(retention?.cohort) ? retention.cohort : [];
    if(cohort.length){
      // Keep only the 12 most recent cohorts (by cohort label like 'YYYY-MM')
      try{
        cohort = cohort.sort((a,b)=> String(a.cohort).localeCompare(String(b.cohort))).slice(-12);
      }catch{}
      const monthCount = Math.max(...cohort.map(c => Array.isArray(c.months) ? c.months.length : 0));
      const header = ['Cohort','Size', ...Array.from({length: monthCount}, (_,i)=>`M+${i}`)];
      cohortDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb">${header.map(h=>`<th style="padding:6px">${h}</th>`).join('')}</tr></thead>
          <tbody>
            ${cohort.map(row => `
              <tr style="border-bottom:1px solid #e5e7eb">
                <td style="padding:6px">${row.cohort||''}</td>
                <td style="padding:6px">${row.size??''}</td>
                ${Array.from({length: monthCount}, (_,i)=>{
                  const v = (row.months||[])[i];
                  const pct = (typeof v === 'number' && isFinite(v)) ? (Math.round(v*1000)/10)+'%' : '';
                  return `<td style="padding:6px">${pct}</td>`;
                }).join('')}
              </tr>`).join('')}
          </tbody>
        </table>
      `;
    }else{
      cohortDiv.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>';
    }
  }
  }
  const retLoadBtn = el('#ret-load');
  const retRefBtn = el('#ret-refresh');
  const runRetDeb = debounce((fresh)=>run(fresh), 700);
  if(retLoadBtn){
    retLoadBtn.disabled = false; retLoadBtn.style.pointerEvents = 'auto'; retLoadBtn.style.cursor = 'pointer';
    retLoadBtn.addEventListener('click', ()=>{ console.debug('Retention: Load clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('retention'); runRetDeb(true); });
  }
  if(retRefBtn){
    retRefBtn.disabled = false; retRefBtn.style.pointerEvents = 'auto'; retRefBtn.style.cursor = 'pointer';
    retRefBtn.addEventListener('click', ()=>{ console.debug('Retention: Refresh clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('retention'); runRetDeb(true); });
  }
  // Auto-fetch on first visit if there is no snapshot yet
  if(!snapGet('retention')){ await run(false); }
}

async function renderOrchestrator(){
  view.innerHTML = `
    <div class="card">
      <h3>Orchestrator</h3>
      <div style="display:flex;gap:8px;align-items:center;margin:8px 0;flex-wrap:wrap">
        <input id="orch-username" placeholder="Username (optional)" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px" />
        <select id="orch-max" aria-label="Số luồng" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px">
          <option value="2">2 workers</option>
          <option value="4" selected>4 workers</option>
          <option value="8">8 workers</option>
        </select>
        <button id="orch-run" class="tab">Run All Analytics</button>
        <button id="orch-refresh" class="tab">Refresh Status</button>
        <span id="orch-msg" class="muted"></span>
      </div>
      <div class="grid" style="grid-template-columns: 1fr 1fr; gap:12px;">
        <div class="card"><h3>Status</h3><pre id="orch-status" class="muted" style="max-height:260px;overflow:auto"></pre></div>
        <div class="card"><h3>Errors</h3><pre id="orch-errors" class="muted" style="max-height:260px;overflow:auto"></pre></div>
      </div>
      <div class="card" style="margin-top:12px">
        <h3>Module Details (Latest Run)</h3>
        <div id="orch-modules" class="muted"></div>
      </div>
      <div class="card" style="margin-top:12px">
        <h3>Run History</h3>
        <div id="orch-history" class="muted" style="max-height:260px;overflow:auto"></div>
      </div>
      <div class="card" style="margin-top:12px">
        <h3>Run Detail</h3>
        <div class="muted" style="margin-bottom:6px">Click a history row to view details</div>
        <pre id="orch-detail" class="muted" style="max-height:320px;overflow:auto"></pre>
      </div>
    </div>
  `;

  const msg = el('#orch-msg');
  const statusPre = el('#orch-status');
  const errorsPre = el('#orch-errors');
  const runBtn = el('#orch-run');
  const refBtn = el('#orch-refresh');
  const userIn = el('#orch-username');
  const maxSel = el('#orch-max');
  const historyDiv = el('#orch-history');
  const modulesDiv = el('#orch-modules');
  const detailPre = el('#orch-detail');

  async function loadStatus(){
    const s = await safeGet('/api/v1/analytics/orchestrator/status');
    statusPre.textContent = JSON.stringify(s, null, 2);
    const errs = s.errors || {};
    errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
    // Render module details
    const mods = Array.isArray(s.modules) ? s.modules : [];
    if(mods.length){
      modulesDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Module</th><th style="padding:6px">Status</th><th style="padding:6px">Exec Time (s)</th></tr></thead>
          <tbody>
            ${mods.map(m=>`<tr style=\"border-bottom:1px solid #e5e7eb\"><td style=\"padding:6px\">${m.name || ''}</td><td style=\"padding:6px\">${m.status || ''}</td><td style=\"padding:6px\">${m.execution_time != null ? Number(m.execution_time).toFixed(2) : ''}</td></tr>`).join('')}
          </tbody>
        </table>
      `;
    }else{
      modulesDiv.innerHTML = '<div class="muted" style="padding:6px">No module details available.</div>';
    }
    const h = await safeGet('/api/v1/analytics/orchestrator/history?limit=20');
    if(Array.isArray(h?.items)){
      historyDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Time</th><th style="padding:6px">Status</th><th style="padding:6px">Duration</th><th style="padding:6px">Workers</th><th style="padding:6px">User</th></tr></thead>
          <tbody>
            ${h.items.map(it=>`<tr data-ts="${it.ts || ''}" style="cursor:pointer;border-bottom:1px solid #e5e7eb"><td style="padding:6px">${it.ts || it.end_time || ''}</td><td style="padding:6px">${it.status || ''}</td><td style="padding:6px">${it.duration_seconds ?? ''}</td><td style="padding:6px">${it.max_workers ?? ''}</td><td style="padding:6px">${it.username ?? ''}</td></tr>`).join('')}
          </tbody>
        </table>
      `;
      // attach click to load detail
      historyDiv.querySelector('tbody')?.addEventListener('click', async (e)=>{
        const tr = e.target.closest('tr[data-ts]');
        if(!tr) return;
        const ts = tr.getAttribute('data-ts');
        if(!ts) return;
        detailPre.textContent = 'Loading…';
        const doc = await safeGet(`/api/v1/analytics/orchestrator/history/item?ts=${encodeURIComponent(ts)}`);
        detailPre.textContent = JSON.stringify(doc, null, 2);
      });
    }
  }

  async function run(){
    msg.textContent = 'Running…';
    const p = new URLSearchParams();
    const u = userIn.value.trim(); if(u) p.set('username', u);
    p.set('max_workers', maxSel.value);
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(`/api/v1/analytics/orchestrator/run?${p.toString()}&_ts=${Date.now()}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    });
    const json = await res.json().catch(()=>({}));
    msg.textContent = res.ok ? 'Completed' : 'Error';
    statusPre.textContent = JSON.stringify(json, null, 2);
    const errs = json.errors || {};
    errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
    // Auto-refresh latest status + modules + history
    await loadStatus();
  }

  runBtn.addEventListener('click', run);
  refBtn.addEventListener('click', loadStatus);
  await loadStatus();
}

async function renderRaw(){
  view.innerHTML = `
    <div class="card">
      <h3>Raw Data - Recent Sessions</h3>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap">
        <label class="muted">Limit</label>
        <select id="raw-limit" aria-label="Số lượng phiên" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px;">
          <option value="10">10</option>
          <option value="25">25</option>
          <option value="50" selected>50</option>
          <option value="100">100</option>
        </select>
        <button id="raw-reload" class="tab">Reload</button>
        <input id="raw-userq" placeholder="Filter by User ID" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px;min-width:220px" />
      </div>
      <div class="muted" id="raw-status">Loading…</div>
      <div style="display:grid;grid-template-columns: 2fr 1fr; gap:12px; margin-top:8px;">
        <div>
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr style="text-align:left;border-bottom:1px solid #e5e7eb">
                <th style="padding:6px">Session ID</th>
                <th style="padding:6px">User</th>
                <th style="padding:6px">First</th>
                <th style="padding:6px">Last</th>
                <th style="padding:6px">Events</th>
              </tr>
            </thead>
            <tbody id="raw-rows"></tbody>
          </table>
        </div>
        <div>
          <div class="card" style="min-height:200px">
            <h3>Session Details</h3>
            <div id="raw-detail" class="muted">Chọn một session để xem chi tiết.</div>
          </div>
        </div>
      </div>
    </div>
  `;

  const limitSel = el('#raw-limit');
  const reloadBtn = el('#raw-reload');
  const userQ = el('#raw-userq');
  const statusEl = el('#raw-status');
  const rowsEl = el('#raw-rows');
  const detailEl = el('#raw-detail');

  let allItems = [];

  function renderRows(){
    const q = String(userQ.value || '').trim().toLowerCase();
    rowsEl.innerHTML = '';
    const items = q ? allItems.filter(s => String(s.user_id||'').toLowerCase().includes(q)) : allItems;
    statusEl.textContent = `${items.length} sessions` + (q ? ` • filtered` : '');
    for(const s of items){
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #e5e7eb';
      tr.innerHTML = `
        <td style="padding:6px"><button class="tab" data-sid="${s.session_id}">${s.session_id}</button></td>
        <td style="padding:6px">${s.user_id ?? ''}</td>
        <td style="padding:6px" class="muted">${s.first_event_at ?? ''}</td>
        <td style="padding:6px" class="muted">${s.last_event_at ?? ''}</td>
        <td style="padding:6px">${s.events_count ?? s.event_count ?? ''}</td>
      `;
      rowsEl.appendChild(tr);
    }
  }

  async function loadSessions(fetchFresh=false){
    statusEl.textContent = 'Loading…';
    rowsEl.innerHTML = '';
    const limit = Math.min(500, Number(limitSel.value || '50'));
    const params = new URLSearchParams({ limit: String(limit) });
    const q = String(userQ.value || '').trim();
    if(q) params.set('user', q);
    let url = `/api/v1/events/sessions/recent?${params.toString()}`;
    if(fetchFresh){
      httpCache.delete(url);
    }
    const data = await safeGet(url);
    allItems = data.items || data.sessions || [];
    renderRows();
  }

  function toCSV(rows){
    if(!Array.isArray(rows) || !rows.length) return '';
    const cols = Array.from(new Set(rows.flatMap(r=>Object.keys(r||{}))));
    const esc = v => '"' + String(v ?? '').replace(/"/g,'""') + '"';
    const header = cols.map(esc).join(',');
    const body = rows.map(r=> cols.map(c=>esc(r[c])).join(',')).join('\n');
    return header + '\n' + body;
  }

  function download(filename, content){
    const blob = new Blob([content], {type:'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  async function loadDetail(sessionId){
    detailEl.textContent = 'Loading…';
    const sum = await safeGet(`/api/v1/events/sessions/${encodeURIComponent(sessionId)}/summary`);
    const events = sum.events || [];
    const meta = {
      session_id: sum.session_id || sessionId,
      event_count: sum.event_count || events.length,
    };
    detailEl.innerHTML = `
      <div class="muted">Session: <b>${meta.session_id}</b> • Events: <b>${meta.event_count}</b></div>
      <div style="margin:8px 0">
        <button id="raw-export" class="tab">Export CSV</button>
      </div>
      <pre style="max-height:360px;overflow:auto;background:#0b1020;color:#d1d5db;padding:8px;border-radius:8px">${
        JSON.stringify(sum, null, 2)
      }</pre>
    `;
    const exportBtn = el('#raw-export');
    exportBtn?.addEventListener('click', ()=>{
      const csv = toCSV(events);
      download(`session_${meta.session_id}.csv`, csv);
    });
  }

  rowsEl.addEventListener('click', (e)=>{
    const btn = e.target.closest('button[data-sid]');
    if(!btn) return;
    loadDetail(btn.dataset.sid);
  });
  reloadBtn.addEventListener('click', ()=>loadSessions(true));
  limitSel.addEventListener('change', ()=>loadSessions(true));
  userQ.addEventListener('input', debounce(()=>loadSessions(true), 300));

  await loadSessions();
}
async function render(){
  switch(state.tab){
    case 'overview': await loadOverview(); break;
    case 'cart': await renderCart(); break;
    case 'journey': await renderJourney(); break;
    case 'reco': renderReco(); break;
    case 'ml': await renderML(); break;
    case 'llm': await renderLLM(); break;
    case 'seo': await renderSEO(); break;
    case 'retention': await renderRetention(); break;
    case 'orchestrator': await renderOrchestrator(); break;
    case 'raw': await renderRaw(); break;
    default: view.textContent = 'Unknown tab';
  }
}

function initNav(){
  const nav = document.getElementById('nav');
  nav.addEventListener('click', (e)=>{
    const btn = e.target.closest('.tab');
    if(!btn) return;
    setActiveTab(btn.dataset.tab);
  });
  // default active (render will be called after filters and migration)
  setActiveTab('overview');
}

function initFilters(){
  const fTime = el('#f-time');
  const fFrom = el('#f-from');
  const fTo = el('#f-to');
  const fSeg = el('#f-segment');
  const fCh = el('#f-channel');

  function apply(){
    state.filters.range = fTime.value;
    state.filters.from = fFrom.value || null;
    state.filters.to = fTo.value || null;
    state.filters.segment = fSeg.value;
    state.filters.channel = fCh.value;
    let applyTimer = null;
    function applyDebounced(){
      if(applyTimer){ clearTimeout(applyTimer); }
      applyTimer = setTimeout(()=>{
        applyTimer = null;
        state.filters.range = fTime.value;
        state.filters.from = fFrom.value || null;
        state.filters.to = fTo.value || null;
        state.filters.segment = fSeg.value;
        state.filters.channel = fCh.value;
        // Clear existing snapshots for the new filter set to avoid showing stale data
        clearSnapshotsForCurrentFilters();
        render();
      }, 250);
    }
    applyDebounced();
  }

  fTime.addEventListener('change', ()=>{
    const custom = fTime.value === 'custom';
    fFrom.style.display = custom ? '' : 'none';
    fTo.style.display = custom ? '' : 'none';
    apply();
  });
  [fFrom, fTo, fSeg, fCh].forEach(elm=>elm.addEventListener('change', apply));
}

function guardAuth(){
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');
  try{
    if(!token || !userStr) throw new Error('unauth');
    const user = JSON.parse(userStr);
    if((user.role || 'user') !== 'admin') throw new Error('not-admin');
  }catch{
    window.location.replace('/auth');
  }
}

function init(){
  guardAuth();
  // Initialize filters first so filterSig() is ready
  initFilters();
  // Migrate old snapshots (pre-filter-scoped) to the new keys for current filters
  migrateOldSnapshots();
  // Now init navigation and render
  initNav();
}

window.addEventListener('DOMContentLoaded', init);
