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
function snapKey(tab){ return SNAP_NS + tab; }
function snapSet(tab, payload){ try{ localStorage.setItem(snapKey(tab), JSON.stringify({ ts: Date.now(), payload })); }catch{} }
function snapGet(tab){ try{ const s = localStorage.getItem(snapKey(tab)); return s ? JSON.parse(s).payload : null; }catch{ return null; } }
function requestIdle(cb){
  if(window.requestIdleCallback){ return window.requestIdleCallback(cb, { timeout: 1500 }); }
  return setTimeout(cb, 300);
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
      <div class="card"><h3>Total Sessions</h3><div class="kpi-value" id="ov-sessions">—</div></div>
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
    el('#ov-rev') && (el('#ov-rev').textContent = `$${fmt(Number.isFinite(kpiRev) ? kpiRev : 0, 2)}`);

    // Trend chart
    const trendEl = el('#chart-trend');
    if(trendEl && data.traffic_trend?.categories?.length){
      const chart = echarts.init(trendEl);
      chart.setOption({
        tooltip: {},
        legend: { data: data.traffic_trend.series.map(s => s.name) },
        xAxis: { type: 'category', data: data.traffic_trend.categories },
        yAxis: { type: 'value' },
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
        yAxis: { type: 'value' },
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
    if(missingCritical){
      run(true).catch(()=>{});
    }else{
      // Background refresh so KPIs update even if snapshot was slightly stale
      requestIdle(()=>{ run(false).catch(()=>{}); });
    }
  }

  async function run(fetchFresh = false){
    const q = buildQuery();
    let bizUrl = `/api/v1/metrics/business?${q}`;
    const seoUrl = `/api/v1/analytics/seo?${q}`;
    const jnUrl = `/api/v1/analytics/journey?${q}`;
    if(fetchFresh){
      [bizUrl, seoUrl, jnUrl].forEach(u=>{ httpCache.delete(cacheKey(u)); lsDel(cacheKey(u)); });
      bizUrl = `${bizUrl}&bypass_cache=true`;
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
    const data = {
      total_sessions: (Number.isFinite(totalSessions) && totalSessions > 0)
        ? totalSessions
        : Number(seoSite.total_views ?? derivedSessions ?? 0) || 0,
      total_users: (Number.isFinite(totalUsers) && totalUsers > 0)
        ? totalUsers
        : Number(seoSite.unique_visitors ?? 0) || 0,
      conversion_rate: finalCR,
      revenue: (business.revenue ?? 0),
      traffic_trend: trafficTrend ?? { categories: [], series: [] },
      segments: business.segments ?? segFromSeo,
      seo_site_metrics: seoSite,
      derived_cr: finalCR
    };

    // Save snapshot and update UI
    snapSet('overview', data);
    updateUI(data);
  }

  el('#ov-load').addEventListener('click', () => run(false));
  el('#ov-refresh').addEventListener('click', () => run(true));

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
    const urlA = `/api/v1/analytics/cart?${q}`;
    const urlT = `/api/v1/cart/trends?${q}`;
    if(fetchFresh){ [urlA,urlT].forEach(u=>{ httpCache.delete(cacheKey(u)); lsDel(cacheKey(u)); }); }
    statusEl.textContent = 'Loading…';
    const analysis = await safeGet(urlA);
    const trends = await safeGet(urlT);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Cart
    snapSet('cart', { channels: analysis?.channels ?? {}, size_distribution: analysis?.size_distribution ?? [] });

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
  el('#cart-load').addEventListener('click', ()=>run(false));
  el('#cart-refresh').addEventListener('click', ()=>run(true));
  // Auto-fetch on first visit if there is no snapshot yet
  if(!snapGet('cart')){ await run(false); }
}

async function renderJourney(){
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="jn-load" class="tab">Load</button>
      <button id="jn-refresh" class="tab">Refresh</button>
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
    const sankeyEl = el('#chart-sankey'); if(sankeyEl && nodes.length && links.length){ const sankey=echarts.init(sankeyEl); sankey.setOption({ tooltip:{}, series:[{ type:'sankey', data:nodes.map(n=>({ name:n })), links }] }); }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    const url = `/api/v1/analytics/journey?${q}`;
    if(fetchFresh){ httpCache.delete(cacheKey(url)); lsDel(cacheKey(url)); }
    statusEl.textContent = 'Loading…';
    const journey = await safeGet(url);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Journey
    snapSet('journey', { funnel: journey?.funnel ?? null, paths: journey?.paths ?? null });

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
    const funnel = echarts.init(funnelEl);
    funnel.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'funnel', data: funnelData }]
    });
  } else if(funnelEl) { funnelEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Sankey data
  let nodes = [];
  let links = [];
  if(journey){
    // Prefer paths if present
    if(journey.paths){
      if(Array.isArray(journey.paths.links)){
        links = journey.paths.links;
        nodes = (journey.paths.nodes || Array.from(new Set(links.flatMap(l=>[l.source,l.target]))));
      }else if(Array.isArray(journey.paths)){
        links = journey.paths;
        nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
      }
    }
    // Fallback to top_paths (array of links) if paths missing
    if(!links.length && Array.isArray(journey.top_paths) && journey.top_paths.length){
      links = journey.top_paths;
      nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
    }
  }
  const sankeyEl = el('#chart-sankey');
  if(sankeyEl && nodes.length && links.length){
    const sankey = echarts.init(sankeyEl);
    sankey.setOption({
      tooltip: {},
      series: [{ type: 'sankey', data: nodes.map(n=>({ name:n })), links }]
    });
  } else if(sankeyEl) { sankeyEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  }
  // Ensure buttons are clickable
  const jnLoadBtn = el('#jn-load');
  const jnRefBtn = el('#jn-refresh');
  if(jnLoadBtn){ jnLoadBtn.disabled = false; jnLoadBtn.style.pointerEvents = 'auto'; jnLoadBtn.addEventListener('click', ()=>run(false)); }
  if(jnRefBtn){ jnRefBtn.disabled = false; jnRefBtn.style.pointerEvents = 'auto'; jnRefBtn.addEventListener('click', ()=>run(true)); }
  // Auto-fetch on first visit if there is no snapshot yet
  if(!snapGet('journey')){ await run(false); }
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
        <select id="reco-time" aria-label="Khung thời gian" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px;display:none">
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
        snapSet('reco:personalized', { user_id: uid || null, items: recs });
        renderItems(recs);
        return;
      }else{
        const tf = timeSel.value;
        const q = new URLSearchParams({ timeframe: tf, limit: String(limit) });
        const res = await safeGet(`/api/v1/recommendations/trending?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
        // Save snapshot for trending keyed by timeframe
        snapSet(`reco:trending:${tf}`, { items: data });
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
  runBtn.addEventListener('click', load);

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
    const url = `/api/v1/analytics/seo?${q}`;
    if(fetchFresh){ httpCache.delete(cacheKey(url)); lsDel(cacheKey(url)); }
    statusEl.textContent = 'Loading…';
    const seo = await safeGet(url);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for SEO
    snapSet('seo', seo || {});

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
  el('#seo-load').addEventListener('click', ()=>run(false));
  el('#seo-refresh').addEventListener('click', ()=>run(true));
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
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh=false){
    const q = buildQuery();
    let urlA = `/api/v1/analytics/retention?${q}`;
    let urlB = `/api/v1/analyses/retention?${q}`;
    if(fetchFresh){ [urlA,urlB].forEach(u=>{ httpCache.delete(cacheKey(u)); lsDel(cacheKey(u)); }); }
    // Prefer analytics/retention; analyses/retention as fallback
    let retention = await safeGet(urlA);
    if(retention && retention.error) {
      retention = await safeGet(urlB);
    }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Retention
    snapSet('retention', retention || {});
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
    const cohort = Array.isArray(retention?.cohort) ? retention.cohort : [];
    if(cohort.length){
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
  if(retLoadBtn){ retLoadBtn.disabled = false; retLoadBtn.style.pointerEvents = 'auto'; retLoadBtn.addEventListener('click', ()=>run(false)); }
  if(retRefBtn){ retRefBtn.disabled = false; retRefBtn.style.pointerEvents = 'auto'; retRefBtn.addEventListener('click', ()=>run(true)); }
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
    const res = await fetch(`/api/v1/analytics/orchestrator/run?${p.toString()}`, {
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
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
        <label class="muted">Limit</label>
        <select id="raw-limit" aria-label="Số lượng phiên" style="padding:6px;border:1px solid #e5e7eb;border-radius:8px;">
          <option value="10">10</option>
          <option value="25">25</option>
          <option value="50" selected>50</option>
          <option value="100">100</option>
        </select>
        <button id="raw-reload" class="tab">Reload</button>
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
  const statusEl = el('#raw-status');
  const rowsEl = el('#raw-rows');
  const detailEl = el('#raw-detail');

  async function loadSessions(){
    statusEl.textContent = 'Loading…';
    rowsEl.innerHTML = '';
    const limit = Number(limitSel.value || '50');
    const data = await safeGet(`/api/v1/events/sessions/recent?limit=${limit}`);
    const items = data.items || data.sessions || [];
    statusEl.textContent = `${items.length} sessions`;
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
  reloadBtn.addEventListener('click', loadSessions);
  limitSel.addEventListener('change', loadSessions);

  await loadSessions();
}
async function render(){
  switch(state.tab){
    case 'overview': await loadOverview(); break;
    case 'cart': await renderCart(); break;
    case 'journey': await renderJourney(); break;
    case 'reco': renderReco(); break;
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
  // default active
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
  initNav();
  initFilters();
}

window.addEventListener('DOMContentLoaded', init);
