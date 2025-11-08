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
    const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
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
    const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if(!res.ok) return;
    const json = await res.json();
    httpCache.set(key, json);
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
  // skeletons
  view.innerHTML = `
    <div class="grid kpi">
      <div class="card skel" style="height:84px"></div>
      <div class="card skel" style="height:84px"></div>
      <div class="card skel" style="height:84px"></div>
      <div class="card skel" style="height:84px"></div>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr; margin-top:12px;">
      <div class="card skel" style="height:300px"></div>
      <div class="card skel" style="height:300px"></div>
    </div>
  `;
  const q = buildQuery();
  // KPIs from business metrics
  const business = await safeGet(`/api/v1/metrics/business?${q}`);
  // Traffic trend and distribution from SEO analysis
  const seo = await safeGet(`/api/v1/analytics/seo?${q}`);

  const data = {
    total_sessions: business.total_sessions ?? business.sessions ?? null,
    total_users: business.total_users ?? business.users ?? null,
    conversion_rate: business.conversion_rate ?? null,
    revenue: business.revenue ?? null,
    traffic_trend: seo.traffic_trend ?? { categories: [], series: [] },
    segments: business.segments ?? { categories: [], series: [] }
  };

  el('#qk-sessions').textContent = fmt(data.total_sessions);
  el('#qk-cr').textContent = `${fmt(data.conversion_rate*100, 2)}%`;
  el('#qk-revenue').textContent = `$${fmt(data.revenue, 2)}`;

  view.innerHTML = `
    <div class="grid kpi">
      <div class="card"><h3>Total Sessions</h3><div class="kpi-value">${fmt(data.total_sessions)}</div></div>
      <div class="card"><h3>Total Users</h3><div class="kpi-value">${fmt(data.total_users)}</div></div>
      <div class="card"><h3>Conversion Rate</h3><div class="kpi-value">${fmt(data.conversion_rate*100,2)}%</div></div>
      <div class="card"><h3>Revenue</h3><div class="kpi-value">$${fmt(data.revenue,2)}</div></div>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr; margin-top:12px;">
      <div class="card"><h3>Traffic Sources Trend</h3><div class="chart" id="chart-trend"></div></div>
      <div class="card"><h3>User Segmentation</h3><div class="chart" id="chart-seg"></div></div>
    </div>
  `;

  // Trend chart
  const trendChart = echarts.init(el('#chart-trend'));
  if(Array.isArray(data.traffic_trend.categories) && data.traffic_trend.categories.length){
    trendChart.setOption({
      tooltip: {},
      legend: { data: data.traffic_trend.series.map(s=>s.name) },
      xAxis: { type: 'category', data: data.traffic_trend.categories },
      yAxis: { type: 'value' },
      series: data.traffic_trend.series
    });
  } else { el('#chart-trend').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Segmentation chart
  const segChart = echarts.init(el('#chart-seg'));
  if(Array.isArray(data.segments.categories) && data.segments.categories.length && Array.isArray(data.segments.series) && data.segments.series[0]?.data){
    segChart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: data.segments.categories },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', name: 'Users', data: data.segments.series[0].data }]
    });
  } else { el('#chart-seg').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Render cohort table if available
  const cEl = el('#cohort-table');
  function renderCohortTable(matrix){
    if(!matrix) { cEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>'; return; }
    const rows = matrix.rows || matrix.row_labels || [];
    const cols = matrix.cols || matrix.col_labels || [];
    const vals = matrix.values || matrix.data || [];
    if(!rows.length || !cols.length || !Array.isArray(vals) || !vals.length){
      cEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>';
      return;
    }
    const thead = '<thead><tr><th style="position:sticky;top:0;background:#f8fafc;padding:6px;border-bottom:1px solid #e5e7eb">Cohort\\Period</th>' + cols.map(c=>`<th style="position:sticky;top:0;background:#f8fafc;padding:6px;border-bottom:1px solid #e5e7eb">${c}</th>`).join('') + '</tr></thead>';
    const tbody = '<tbody>' + rows.map((r, i)=>{
      const cells = (vals[i] || []).map(v=>`<td style="padding:6px;border-bottom:1px solid #e5e7eb">${typeof v==='number'? (Math.round(v*1000)/10)+'%': (v??'')}</td>`).join('');
      return `<tr><th style="padding:6px;border-bottom:1px solid #e5e7eb;text-align:left">${r}</th>${cells}</tr>`;
    }).join('') + '</tbody>';
    cEl.innerHTML = `<table style="width:100%;border-collapse:collapse">${thead}${tbody}</table>`;
  }
  if(retention && (retention.cohort || retention.cohort_matrix || retention.cohorts)){
    const m = retention.cohort || retention.cohort_matrix || retention.cohorts;
    renderCohortTable(m);
  }else{
    renderCohortTable(null);
  }
}

async function renderCart(){
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card skel" style="height:300px"></div>
      <div class="card skel" style="height:300px"></div>
    </div>
  `;
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Abandonment by Channel</h3><div class="chart" id="chart-ab"></div></div>
      <div class="card"><h3>Cart Size Distribution</h3><div class="chart" id="chart-dist"></div></div>
    </div>
  `;
  const q = buildQuery();
  const analysis = await safeGet(`/api/v1/analytics/cart?${q}`);
  const trends = await safeGet(`/api/v1/cart/trends?${q}`);

  // Abandonment by channel
  const channels = (analysis.channels && Object.keys(analysis.channels)) || [];
  const abData = channels.map(c => {
    const v = analysis.channels?.[c]?.abandonment_rate;
    return typeof v === 'number' ? Math.round(v*1000)/10 : null;
  });
  const ab = echarts.init(el('#chart-ab'));
  if(abData.length){
    ab.setOption({
      tooltip: { trigger:'axis' },
      legend: { data:['Abandonment %'] },
      xAxis: { type:'category', data: channels },
      yAxis: { type:'value', axisLabel:{ formatter: '{value}%' } },
      series: [{ name:'Abandonment %', type:'bar', data: abData }]
    });
  } else { el('#chart-ab').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Cart size distribution
  const distChart = echarts.init(el('#chart-dist'));
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
  if(distData.length){
    distChart.setOption({
      tooltip: {},
      xAxis: { type:'category', data: distCats },
      yAxis: { type:'value' },
      series: [{ type:'line', data: distData }]
    });
  } else { el('#chart-dist').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
}

async function renderJourney(){
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card skel" style="height:300px"></div>
      <div class="card skel" style="height:300px"></div>
    </div>
  `;
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card"><h3>Funnel</h3><div class="chart" id="chart-funnel"></div></div>
      <div class="card"><h3>Top Paths (Sankey)</h3><div class="chart" id="chart-sankey"></div></div>
    </div>
  `;
  const q = buildQuery();
  const journey = await safeGet(`/api/v1/analytics/journey?${q}`);

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
  const funnel = echarts.init(el('#chart-funnel'));
  if(funnelData.length){
    funnel.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'funnel', data: funnelData }]
    });
  } else { el('#chart-funnel').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Sankey data
  let nodes = [];
  let links = [];
  if(journey && journey.paths){
    // shapes: paths as [{source,target,value}] or {nodes:[...], links:[...]}
    if(Array.isArray(journey.paths.links)){
      links = journey.paths.links;
      nodes = (journey.paths.nodes || Array.from(new Set(links.flatMap(l=>[l.source,l.target]))));
    }else if(Array.isArray(journey.paths)){
      links = journey.paths;
      nodes = Array.from(new Set(links.flatMap(l=>[l.source,l.target])));
    }
  }
  const sankey = echarts.init(el('#chart-sankey'));
  if(nodes.length && links.length){
    sankey.setOption({
      tooltip: {},
      series: [{ type: 'sankey', data: nodes.map(n=>({ name:n })), links }]
    });
  } else { el('#chart-sankey').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
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
      }else{
        const tf = timeSel.value;
        const q = new URLSearchParams({ timeframe: tf, limit: String(limit) });
        const res = await safeGet(`/api/v1/recommendations/trending?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
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
  await load();
}

async function renderSEO(){
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card skel" style="height:300px"></div>
      <div class="card skel" style="height:300px"></div>
    </div>
  `;
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Traffic Source Distribution</h3><div class="chart" id="chart-donut"></div></div>
      <div class="card"><h3>Traffic Trend</h3><div class="chart" id="chart-traffic"></div></div>
    </div>
  `;
  const q = buildQuery();
  const seo = await safeGet(`/api/v1/analytics/seo?${q}`);

  // Distribution
  const donut = echarts.init(el('#chart-donut'));
  let dist = [];
  if(seo && seo.sources && seo.sources.distribution){
    dist = Object.entries(seo.sources.distribution).map(([name, value])=>({ name, value }));
  }
  if(dist.length){
    donut.setOption({
      tooltip: { trigger:'item' },
      series: [{ type:'pie', radius:['40%','70%'], data: dist }]
    });
  } else { el('#chart-donut').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

  // Trend
  const traffic = echarts.init(el('#chart-traffic'));
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
  if(categories.length && series.length){
    traffic.setOption({
      tooltip: { trigger:'axis' },
      legend: { data: series.map(s=>s.name) },
      xAxis: { type:'category', data: categories },
      yAxis: { type:'value' },
      series
    });
  } else { el('#chart-traffic').innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
}

async function renderRetention(){
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card skel" style="height:300px"></div>
      <div class="card skel" style="height:300px"></div>
    </div>
  `;
  view.innerHTML = `
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Retention / Churn</h3><div class="chart" id="chart-ret"></div></div>
      <div class="card"><h3>Cohort</h3><div id="cohort-table" style="max-height:320px;overflow:auto"></div></div>
    </div>
  `;
  const q = buildQuery();
  // Prefer analytics/retention; analyses/retention as fallback
  let retention = await safeGet(`/api/v1/analytics/retention?${q}`);
  if(retention && retention.error) {
    retention = await safeGet(`/api/v1/analyses/retention?${q}`);
  }
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
  const ret = echarts.init(el('#chart-ret'));
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
    const res = await fetch(`/api/v1/analytics/orchestrator/run?${p.toString()}`, { method: 'POST' });
    const json = await res.json().catch(()=>({}));
    msg.textContent = res.ok ? 'Completed' : 'Error';
    statusPre.textContent = JSON.stringify(json, null, 2);
    const errs = json.errors || {};
    errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
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
  // Prefetch common next-tab data on idle for current filters
  requestIdle(async ()=>{
    const q = buildQuery();
    await Promise.all([
      preload(`/api/v1/analytics/seo?${q}`),
      preload(`/api/v1/analytics/cart?${q}`)
    ]);
  });
}

window.addEventListener('DOMContentLoaded', init);
