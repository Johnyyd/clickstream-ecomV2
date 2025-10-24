// Import displayAnalysisResults from the analysisDisplay module
import { displayAnalysisResults } from './analysisDisplay.js';

// DOM Elements
const simulateBtn = document.getElementById('simulateBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
let autoAnalyzeBtn = null;
const output = document.getElementById('output');
const summaryEl = document.getElementById('summary');
const pythonDetailsEl = document.getElementById('pythonDetails');
const llmParsedEl = document.getElementById('llmParsed');
const llmRawEl = document.getElementById('llmRaw');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const checkKeyBtn = document.getElementById('checkKeyBtn');
const openrouterKeyInput = document.getElementById('openrouterKey');
const keyStatus = document.getElementById('keyStatus');
const recsEl = document.getElementById('recs');
const useSparkToggle = document.getElementById('useSparkToggle');
const analysisModeText = document.getElementById('analysisModeText');
const analysisModeBadge = document.getElementById('analysisModeBadge');

// State
let token = null;
let currentUserId = null;
let useSpark = true; // Default to Spark analysis
let metricsTimer = null;
const METRICS_INTERVAL_MS = 10000;
const AUTO_ANALYZE_INTERVAL_MS = 60000;
let autoAnalyzeTimer = null;
let cachedProducts = [];

// Persistence keys
const ANALYTICS_KEYS = {
  analysis: 'analytics:analysis',
  mlPrefix: 'analytics:ml:'
};

function saveAnalysisToStorage(analysis) {
  try {
    localStorage.setItem(ANALYTICS_KEYS.analysis, JSON.stringify({ ts: Date.now(), data: analysis }));
  } catch (e) { console.warn('Failed to save analysis to storage', e); }
}

function loadAnalysisFromStorage() {
  try {
    const raw = localStorage.getItem(ANALYTICS_KEYS.analysis);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && parsed.data ? parsed.data : null;
  } catch (e) { console.warn('Failed to load analysis from storage', e); return null; }
}

function saveMLResultToStorage(algorithmName, result) {
  try {
    const key = ANALYTICS_KEYS.mlPrefix + algorithmName.replace(/\s+/g, '_').toLowerCase();
    localStorage.setItem(key, JSON.stringify({ ts: Date.now(), data: result }));
  } catch (e) { console.warn('Failed to save ML result to storage', e); }
}

function loadMLResultFromStorage(algorithmName) {
  try {
    const key = ANALYTICS_KEYS.mlPrefix + algorithmName.replace(/\s+/g, '_').toLowerCase();
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && parsed.data ? parsed.data : null;
  } catch (e) { console.warn('Failed to load ML result from storage', e); return null; }
}

function clearStoredAnalysisAndML() {
  try {
    localStorage.removeItem(ANALYTICS_KEYS.analysis);
    // remove ml keys
    for (const k in localStorage) {
      if (k && k.startsWith(ANALYTICS_KEYS.mlPrefix)) localStorage.removeItem(k);
    }
  } catch (e) { console.warn('Failed to clear stored analysis/ML', e); }
}

// Handle clearOnLoad flag from hard reload (set by comprehensiveAnalytics.js)
function handleClearOnLoadFlag_dashboard() {
  try {
    if (sessionStorage.getItem('clearOnLoad')) {
      clearStoredAnalysisAndML();
      sessionStorage.removeItem('clearOnLoad');
      console.log('Dashboard: cleared persisted analysis/ML due to hard reload');
    }
  } catch (e) { console.warn('Error handling clearOnLoad flag (dashboard)', e); }
}

// Load stored analysis + ML into UI
function loadStoredAnalysisAndMLToUI() {
  try {
    const analysis = loadAnalysisFromStorage();
    if (analysis) {
      const resultsContainer = document.getElementById('results');
      if (resultsContainer) displayAnalysisResults(analysis, resultsContainer);
      output.innerText = 'Loaded persisted analysis results';
    }

    // Try to load common ML algorithms and display them if present
    const mlAlgos = ['K-Means Clustering','Decision Tree','FP-Growth Patterns','Logistic Regression'];
    for (const algo of mlAlgos) {
      const ml = loadMLResultFromStorage(algo);
      if (ml) {
        displayMLResults(algo, ml);
      }
    }
  } catch (e) { console.warn('Failed to load stored analysis/ML to UI', e); }
}

// Real-time metrics time range
let currentTimeRange = 60; // minutes
const TIME_RANGES = {
  '15min': { minutes: 15, label: '15 Phút', points: 15 },
  '30min': { minutes: 30, label: '30 Phút', points: 30 },
  '1hour': { minutes: 60, label: '1 Giờ', points: 60 },
  '3hours': { minutes: 180, label: '3 Giờ', points: 60 },
  '6hours': { minutes: 360, label: '6 Giờ', points: 72 },
  '12hours': { minutes: 720, label: '12 Giờ', points: 72 },
  '1day': { minutes: 1440, label: '1 Ngày', points: 96 },
  '7days': { minutes: 10080, label: '7 Ngày', points: 168 }
};

function ensureMetricsPanel() {
  let panel = document.getElementById('rt-metrics');
  if (!panel) {
    const controls = document.getElementById('controls');
    panel = document.createElement('div');
    panel.id = 'rt-metrics';
    panel.className = 'analysis-section';
    panel.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2 class="section-title" id="rt-title" style="margin:0;">Real-time Metrics (last 1 Giờ)</h2>
        <div class="time-range-selector" id="timeRangeSelector">
          <button class="time-range-btn" data-range="15min">15p</button>
          <button class="time-range-btn" data-range="30min">30p</button>
          <button class="time-range-btn active" data-range="1hour">1h</button>
          <button class="time-range-btn" data-range="3hours">3h</button>
          <button class="time-range-btn" data-range="6hours">6h</button>
          <button class="time-range-btn" data-range="12hours">12h</button>
          <button class="time-range-btn" data-range="1day">1d</button>
          <button class="time-range-btn" data-range="7days">7d</button>
        </div>
      </div>
      <div id="rt-summary" class="metrics-grid"></div>
      <div style="display:grid; gap:12px; margin-top:12px">
        <div style="position:relative">
          <h3 style="margin:6px 0" id="rt-chart-title">Events per minute (last 1 Giờ)</h3>
          <div id="rt-line"></div>
          <div id="chart-tooltip" style="display:none; position:absolute; background:#1e293b; color:#e2e8f0; padding:8px 12px; border-radius:6px; font-size:12px; pointer-events:none; box-shadow:0 4px 6px rgba(0,0,0,0.3); z-index:1000; white-space:nowrap;">
            <div style="font-weight:600; margin-bottom:4px;" id="tooltip-time"></div>
            <div id="tooltip-date" style="color:#94a3b8; font-size:11px; margin-bottom:4px;"></div>
            <div id="tooltip-count" style="color:#60a5fa; font-weight:600;"></div>
          </div>
        </div>
        <div>
          <h3 style="margin:6px 0" id="rt-pages-title">Top pages (1h)</h3>
          <div id="rt-bars"></div>
        </div>
      </div>
      <details>
        <summary>Raw aggregates</summary>
        <pre id="rt-raw"></pre>
      </details>
    `;
    controls.appendChild(panel);
    
    // Add event listeners for time range buttons
    const timeRangeButtons = panel.querySelectorAll('.time-range-btn');
    timeRangeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const range = btn.getAttribute('data-range');
        changeTimeRange(range);
      });
    });
  }
  return panel;
}

function changeTimeRange(rangeKey) {
  const range = TIME_RANGES[rangeKey];
  if (!range) return;
  
  currentTimeRange = range.minutes;
  
  // Update active button
  const panel = document.getElementById('rt-metrics');
  if (panel) {
    panel.querySelectorAll('.time-range-btn').forEach(btn => {
      if (btn.getAttribute('data-range') === rangeKey) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
    
    // Update titles
    const title = panel.querySelector('#rt-title');
    const chartTitle = panel.querySelector('#rt-chart-title');
    const pagesTitle = panel.querySelector('#rt-pages-title');
    const summaryLabel = panel.querySelector('.metric-label');
    
    const shortLabel = rangeKey.replace('min', 'p').replace('hour', 'h').replace('day', 'd');
    
    if (title) title.textContent = `Real-time Metrics (last ${range.label})`;
    if (chartTitle) chartTitle.textContent = `Events per minute (last ${range.label})`;
    if (pagesTitle) pagesTitle.textContent = `Top pages (${shortLabel})`;
  }
  
  // Fetch new data
  console.log(`[changeTimeRange] Switching to ${rangeKey} (${range.minutes} minutes)`);
  pollMetricsOnce();
}

window.showChartTooltip = function(event, timeStr, dateStr, count) {
  const tooltip = document.getElementById('chart-tooltip');
  if (!tooltip) return;
  
  document.getElementById('tooltip-time').textContent = `🕐 ${timeStr}`;
  document.getElementById('tooltip-date').textContent = dateStr;
  document.getElementById('tooltip-count').textContent = `📊 ${count} events`;
  
  tooltip.style.display = 'block';
  
  // Position tooltip near mouse with smart positioning to avoid overflow
  const container = tooltip.parentElement;
  const rect = container.getBoundingClientRect();
  let x = event.clientX - rect.left + 15;
  let y = event.clientY - rect.top - 15;
  
  // Adjust if tooltip would overflow right edge
  const tooltipWidth = tooltip.offsetWidth;
  if (x + tooltipWidth > container.offsetWidth) {
    x = event.clientX - rect.left - tooltipWidth - 15;
  }
  
  // Adjust if tooltip would overflow top edge
  if (y < 0) {
    y = event.clientY - rect.top + 15;
  }
  
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
};

window.hideChartTooltip = function() {
  const tooltip = document.getElementById('chart-tooltip');
  if (tooltip) tooltip.style.display = 'none';
};

async function fetchAggregates() {
  try {
    // Fetch data based on current time range
    const minutes = Math.min(currentTimeRange, 10080); // API max is 10080 (7 days)
    console.log(`[fetchAggregates] Fetching ${minutes} minutes of data`);
    const resp = await fetch(`/api/metrics/aggregates?minutes=${minutes}`);
    if (!resp.ok) {
      console.error('[fetchAggregates] API error:', resp.status, resp.statusText);
      return null;
    }
    const data = await resp.json();
    console.log('[fetchAggregates] Raw API response:', data);
    return data;
  } catch (e) {
    console.error('[fetchAggregates] Exception:', e);
    return null;
  }
}

function renderAggregates(data) {
  const panel = ensureMetricsPanel();
  const items = (data && data.items) || [];
  console.log('[renderAggregates] Received items:', items.length);
  
  // Use pre-aggregated data from API if available (more efficient)
  // Otherwise fall back to computing from items (backward compatibility)
  let byPage = data.by_page || {};
  let byEvent = data.by_event || {};
  
  // Fallback: compute from items if not pre-aggregated
  if (!data.by_page && items.length > 0 && items[0].page !== undefined) {
    byPage = {};
    byEvent = {};
    for (const r of items) {
      if (r.event_type) byEvent[r.event_type] = (byEvent[r.event_type] || 0) + (r.count || 0);
      if (r.page) byPage[r.page] = (byPage[r.page] || 0) + (r.count || 0);
    }
  }
  
  // Build minute map from aggregated items
  const byMinute = new Map();
  let total = 0;
  
  for (const r of items) {
    total += (r.count || 0);
    
    // Parse window_end - handle both ISO string and Date object
    let end = null;
    if (r.window_end) {
      if (typeof r.window_end === 'string') {
        // ISO string from API - ensure it's parsed as UTC
        // Add 'Z' if not present to force UTC interpretation
        const isoStr = r.window_end.endsWith('Z') ? r.window_end : r.window_end + 'Z';
        end = new Date(isoStr);
      } else if (r.window_end instanceof Date) {
        end = r.window_end;
      } else {
        console.warn('[renderAggregates] Unknown window_end format:', r.window_end);
      }
    }
    
    if (end && !isNaN(end.getTime())) {
      const key = `${end.getUTCFullYear()}-${String(end.getUTCMonth()+1).padStart(2,'0')}-${String(end.getUTCDate()).padStart(2,'0')} ${String(end.getUTCHours()).padStart(2,'0')}:${String(end.getUTCMinutes()).padStart(2,'0')}`;
      // Items are already aggregated by minute, so just set directly
      byMinute.set(key, r.count || 0);
    }
  }
  
  console.log('[renderAggregates] byMinute Map size:', byMinute.size, 'Total events:', total);
  const topEvent = Object.entries(byEvent).sort((a,b)=>b[1]-a[1])[0] || ['',0];
  const topPage = Object.entries(byPage).sort((a,b)=>b[1]-a[1])[0] || ['',0];
  
  // Get current time range label
  let timeLabel = '1h';
  for (const [key, range] of Object.entries(TIME_RANGES)) {
    if (range.minutes === currentTimeRange) {
      timeLabel = key.replace('min', 'p').replace('hour', 'h').replace('day', 'd');
      break;
    }
  }
  
  const grid = panel.querySelector('#rt-summary');
  grid.innerHTML = `
    <div class="metric-card"><div class="metric-value">${total}</div><div class="metric-label">Events (${timeLabel})</div></div>
    <div class="metric-card"><div class="metric-value">${topEvent[0]||'-'}: ${topEvent[1]||0}</div><div class="metric-label">Top Event</div></div>
    <div class="metric-card"><div class="metric-value">${topPage[0]||'-'}: ${topPage[1]||0}</div><div class="metric-label">Top Page</div></div>
  `;
  const raw = panel.querySelector('#rt-raw');
  raw.textContent = JSON.stringify(items.slice(-50), null, 2);

  // Render simple charts
  const lineHost = panel.querySelector('#rt-line');
  const barHost = panel.querySelector('#rt-bars');
  if (lineHost) lineHost.innerHTML = renderLineChartSVG(byMinute);
  if (barHost) barHost.innerHTML = renderBarChartSVG(byPage);
}

async function pollMetricsOnce() {
  const data = await fetchAggregates();
  if (data) renderAggregates(data);
}

function startMetricsPolling() {
  ensureMetricsPanel();
  if (metricsTimer) clearInterval(metricsTimer);
  pollMetricsOnce();
  metricsTimer = setInterval(pollMetricsOnce, METRICS_INTERVAL_MS);
}

function renderLineChartSVG(byMinuteMap) {
  // Prepare timeline based on current time range
  const now = new Date();
  const labels = [];
  const timeLabels = []; // Store Date objects for X-axis labels
  const values = [];
  
  // Determine number of data points and interval
  const minutes = currentTimeRange;
  let dataPoints = minutes;
  let intervalMinutes = 1;
  
  // For longer periods, aggregate data points
  if (minutes > 180) {
    dataPoints = 120; // Max 120 points on chart
    intervalMinutes = Math.ceil(minutes / dataPoints);
  }
  
  for (let i = dataPoints - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * intervalMinutes * 60000);
    const key = `${t.getUTCFullYear()}-${String(t.getUTCMonth()+1).padStart(2,'0')}-${String(t.getUTCDate()).padStart(2,'0')} ${String(t.getUTCHours()).padStart(2,'0')}:${String(t.getUTCMinutes()).padStart(2,'0')}`;
    labels.push(key);
    timeLabels.push(t);
    const val = byMinuteMap.get(key) || 0;
    values.push(val);
  }
  
  const nonZeroCount = values.filter(v => v > 0).length;
  const totalEvents = values.reduce((sum, v) => sum + v, 0);
  console.log(`[renderLineChartSVG] ${nonZeroCount}/${dataPoints} data points with events, ${totalEvents} total events`);
  
  const width = 600, height = 180, pad = 24, bottomPad = 40; // Extra space for X-axis labels
  const maxV = Math.max(1, ...values);
  
  const chartHeight = height - bottomPad;
  const pts = values.map((v, idx) => {
    const x = pad + (idx/(values.length-1))*(width-2*pad);
    const y = pad + (1 - (v/maxV))*(chartHeight-pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  
  // Y-axis ticks
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(fr => {
    const y = pad + (1-fr)*(chartHeight-pad);
    const val = Math.round(maxV*fr);
    return `<line x1=\"${pad}\" y1=\"${y}\" x2=\"${width-pad}\" y2=\"${y}\" stroke=\"#233046\" stroke-width=\"1\" />
            <text x=\"${pad-4}\" y=\"${y+3}\" fill=\"#98a5b5\" font-size=\"10\" text-anchor=\"end\">${val}</text>`;
  }).join('');
  
  // X-axis time labels (show every 10 minutes + first and last)
  const xAxisLabels = [];
  for (let i = 0; i < timeLabels.length; i++) {
    if (i === 0 || i === timeLabels.length - 1 || i % 10 === 0) {
      const t = timeLabels[i];
      const x = pad + (i/(values.length-1))*(width-2*pad);
      const timeStr = `${String(t.getUTCHours()).padStart(2,'0')}:${String(t.getUTCMinutes()).padStart(2,'0')}`;
      xAxisLabels.push(`<text x="${x}" y="${chartHeight + 15}" fill="#98a5b5" font-size="10" text-anchor="middle">${timeStr}</text>`);
      // Small tick mark
      xAxisLabels.push(`<line x1="${x}" y1="${chartHeight}" x2="${x}" y2="${chartHeight + 5}" stroke="#233046" stroke-width="1" />`);
    }
  }
  
  // X-axis line
  const xAxisLine = `<line x1="${pad}" y1="${chartHeight}" x2="${width-pad}" y2="${chartHeight}" stroke="#233046" stroke-width="1" />`;
  
  // Interactive data points with hover
  const interactivePoints = values.map((v, idx) => {
    const x = pad + (idx/(values.length-1))*(width-2*pad);
    const y = pad + (1 - (v/maxV))*(chartHeight-pad);
    const t = timeLabels[idx];
    const timeStr = `${String(t.getUTCHours()).padStart(2,'0')}:${String(t.getUTCMinutes()).padStart(2,'0')}`;
    const dateStr = `${t.getUTCFullYear()}-${String(t.getUTCMonth()+1).padStart(2,'0')}-${String(t.getUTCDate()).padStart(2,'0')}`;
    
    return `
      <g class="data-point-group">
        <!-- Invisible larger circle for easier hovering -->
        <circle cx="${x}" cy="${y}" r="8" fill="transparent" style="cursor:pointer"
                onmouseover="showChartTooltip(event, '${timeStr}', '${dateStr}', ${v}); document.getElementById('point-${idx}').setAttribute('opacity','1')"
                onmouseout="hideChartTooltip(); document.getElementById('point-${idx}').setAttribute('opacity','0')" />
        <!-- Visible point that appears on hover -->
        <circle id="point-${idx}" cx="${x}" cy="${y}" r="4" fill="#2563eb" opacity="0" style="pointer-events:none; transition:opacity 0.2s" />
      </g>`;
  }).join('');
  
  return `<svg width=\"100%\" viewBox=\"0 0 ${width} ${height}\" preserveAspectRatio=\"xMidYMid meet\">
    <rect x=\"0\" y=\"0\" width=\"${width}\" height=\"${height}\" fill=\"rgba(255,255,255,0.02)\" />
    ${ticks}
    ${xAxisLine}
    ${xAxisLabels.join('')}
    <polyline fill=\"none\" stroke=\"#2563eb\" stroke-width=\"2\" points=\"${pts}\" />
    ${interactivePoints}
  </svg>`;
}

function renderBarChartSVG(byPageObj) {
  const entries = Object.entries(byPageObj).sort((a,b)=>b[1]-a[1]).slice(0,20);
  const width = 600, barH = 18, gap = 8, pad = 24;
  const height = pad + entries.length*(barH+gap) + pad;
  const maxV = Math.max(1, ...entries.map(e=>e[1]));
  const bars = entries.map((e, i) => {
    const label = (e[0]||'').slice(0,40);
    const v = e[1];
    const w = (v/maxV)*(width-2*pad);
    const y = pad + i*(barH+gap);
    return `<g>
      <rect x=\"${pad}\" y=\"${y}\" width=\"${w}\" height=\"${barH}\" fill=\"#10b981\" />
      <text x=\"${pad+4}\" y=\"${y+barH-5}\" fill=\"#0b1220\" font-size=\"11\" >${label}</text>
      <text x=\"${pad+w+4}\" y=\"${y+barH-5}\" fill=\"#98a5b5\" font-size=\"11\" >${v}</text>
    </g>`;
  }).join('');
  return `<svg width=\"100%\" viewBox=\"0 0 ${width} ${height}\" preserveAspectRatio=\"xMidYMid meet\">
    <rect x=\"0\" y=\"0\" width=\"${width}\" height=\"${height}\" fill=\"rgba(255,255,255,0.02)\" />
    ${bars}
  </svg>`;
}

// Login is now handled by /auth page, no need for inline login
// Token is already set from localStorage by the auth check at page load

// Initialize on page load
(async function init() {
  token = localStorage.getItem('token');
  if (token) {
    try {
      const meResp = await fetch('/api/me', { headers: { 'Authorization': token }});
      if (meResp.ok) {
        const me = await meResp.json();
        currentUserId = me.user_id || me._id || me.id || null;
        console.log('Logged in user ID:', currentUserId);
      }
    } catch(e) {
      console.error('Failed to fetch user info:', e);
    }
    
    // Load initial data
  try { await checkKey(); } catch(e) {}
  try { await loadRecommendations(); } catch(e) {}
  try { await loadProducts(); } catch(e) {}
  // Respect hard-reload clear flag and restore any stored analysis/ML results
  handleClearOnLoadFlag_dashboard();
  loadStoredAnalysisAndMLToUI();
  startMetricsPolling();
    ensureAutoAnalyzeButton();
    if (autoAnalyzeBtn) {
      autoAnalyzeBtn.onclick = () => {
        if (autoAnalyzeTimer) stopAutoAnalyze(); else startAutoAnalyze();
      };
    }
    const savedAuto = localStorage.getItem('autoAnalyze');
    if (savedAuto === 'true') startAutoAnalyze();
    ensureUsernameInput();
  }
})();

async function loadProducts() {
  try {
    const resp = await fetch('/api/products?limit=100');
    if (resp.ok) {
      const data = await resp.json();
      cachedProducts = data.items || [];
      console.log(`Loaded ${cachedProducts.length} products for simulation`);
    }
  } catch(e) {
    console.error('Failed to load products:', e);
  }
}

simulateBtn.onclick = async () => {
  if (!token) { output.innerText = "login first"; return; }
  
  // Ensure products are loaded
  if (cachedProducts.length === 0) {
    await loadProducts();
    if (cachedProducts.length === 0) {
      output.innerText = "No products available. Please seed products first.";
      return;
    }
  }
  
  output.innerText = "Simulating realistic events...";
  
  try {
    const simSessionId = `session_sim_${Date.now()}`;
    // Match seed_realistic_data.py client_id format
    const clientId = currentUserId ? `client_${currentUserId.slice(-6)}` : `client_anon_${Math.random().toString(36).slice(2, 8)}`;
    
    // Personas synchronized with seed_realistic_data.py
    const personas = [
      {name: "bouncer", weight: 0.15, events: 2, browseRate: 0.8, productRate: 0.15, cartRate: 0.03, checkoutRate: 0.02},
      {name: "browser", weight: 0.35, events: 7, browseRate: 0.5, productRate: 0.35, cartRate: 0.1, checkoutRate: 0.05},
      {name: "shopper", weight: 0.25, events: 10, browseRate: 0.3, productRate: 0.4, cartRate: 0.2, checkoutRate: 0.1},
      {name: "power_buyer", weight: 0.15, events: 12, browseRate: 0.2, productRate: 0.35, cartRate: 0.25, checkoutRate: 0.2},
      {name: "returning_customer", weight: 0.10, events: 9, browseRate: 0.25, productRate: 0.4, cartRate: 0.2, checkoutRate: 0.15}
    ];
    
    // Select persona
    const rand = Math.random();
    let cumWeight = 0;
    let persona = personas[1]; // default
    for (const p of personas) {
      cumWeight += p.weight;
      if (rand <= cumWeight) {
        persona = p;
        break;
      }
    }
    
    const categories = ["computer", "phone", "shoes", "shirt", "coffee", "pants"];
    const searchTerms = ["laptop", "phone", "coffee", "shoes", "shirt", "pizza", "sushi"];
    const referrers = ["direct", "email", "social", "ads", "google", "facebook"];
    let viewedProducts = [];
    let cartItems = [];
    
    // Entry point - synchronized with seed_realistic_data.py
    const entryPoints = [
      {page: "/home", type: "pageview", props: {referrer: referrers[Math.floor(Math.random() * referrers.length)], source: "simulate"}},
      {page: "/search", type: "search", props: {search_term: searchTerms[Math.floor(Math.random() * searchTerms.length)], referrer: "google", source: "simulate"}},
      {page: `/category?category=${categories[Math.floor(Math.random() * categories.length)]}`, type: "pageview", props: {referrer: "social", source: "simulate"}}
    ];
    const entry = entryPoints[Math.random() < 0.6 ? 0 : (Math.random() < 0.85 ? 1 : 2)];
    
    // First event with current timestamp
    await fetch('/api/ingest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': token},
      body: JSON.stringify({
        client_id: clientId,
        page: entry.page,
        event_type: entry.type,
        timestamp: Math.floor(Date.now() / 1000),
        user_id: currentUserId || undefined,
        session_id: simSessionId,
        properties: entry.props
      })
    });
    
    // Generate remaining events with current timestamp for each
    for (let i = 1; i < persona.events && i < 100; i++) {
      // Use current system time for each event instead of incrementing
      // Add small delay to simulate realistic spacing (5-15 seconds)
      await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50));
      
      const currentTimestamp = Math.floor(Date.now() / 1000);
      const r = Math.random();
      
      let event;
      if (r < persona.browseRate) {
        // Browse - category or search
        if (Math.random() < 0.55) {
          const category = categories[Math.floor(Math.random() * categories.length)];
          event = {
            client_id: clientId,
            page: `/category?category=${category}`,
            event_type: "pageview",
            timestamp: currentTimestamp,
            user_id: currentUserId || undefined,
            session_id: simSessionId,
            properties: {category: category, source: "simulate"}
          };
        } else {
          const term = searchTerms[Math.floor(Math.random() * searchTerms.length)];
          event = {
            client_id: clientId,
            page: "/search",
            event_type: "search",
            timestamp: currentTimestamp,
            user_id: currentUserId || undefined,
            session_id: simSessionId,
            properties: {search_term: term, source: "simulate"}
          };
        }
      } else if (r < persona.browseRate + persona.productRate) {
        // View product - use real products from DB
        const product = cachedProducts[Math.floor(Math.random() * cachedProducts.length)];
        viewedProducts.push(product);
        event = {
          client_id: clientId,
          page: `/p/${product.slug}?id=${product._id}`,
          event_type: "pageview",
          timestamp: currentTimestamp,
          user_id: currentUserId || undefined,
          session_id: simSessionId,
          properties: {
            product_id: product._id,
            product_name: product.name,
            product_category: product.category,
            product_price: product.price,
            source: "simulate"
          }
        };
      } else if (r < persona.browseRate + persona.productRate + persona.cartRate) {
        // Add to cart
        if (viewedProducts.length > 0) {
          const product = viewedProducts[Math.floor(Math.random() * viewedProducts.length)];
          cartItems.push(product);
          event = {
            client_id: clientId,
            page: "/cart",
            event_type: "add_to_cart",
            timestamp: currentTimestamp,
            user_id: currentUserId || undefined,
            session_id: simSessionId,
            properties: {
              product_id: product._id,
              product_name: product.name,
              product_price: product.price,
              quantity: 1,
              source: "simulate"
            }
          };
        } else {
          event = {
            client_id: clientId,
            page: "/home",
            event_type: "pageview",
            timestamp: currentTimestamp,
            user_id: currentUserId || undefined,
            session_id: simSessionId,
            properties: {source: "simulate"}
          };
        }
      } else {
        // Checkout/Purchase
        if (cartItems.length > 0 && Math.random() < 0.65) {
          const totalAmount = cartItems.reduce((sum, p) => sum + p.price, 0);
          event = {
            client_id: clientId,
            page: "/checkout",
            event_type: "purchase",
            timestamp: currentTimestamp,
            user_id: currentUserId || undefined,
            session_id: simSessionId,
            properties: {
              cart_items: cartItems.length,
              total_amount: Math.round(totalAmount * 100) / 100,
              payment_method: ["credit_card", "paypal", "apple_pay"][Math.floor(Math.random() * 3)],
              order_id: `order_${Math.floor(Math.random() * 9000) + 1000}`,
              source: "simulate"
            }
          };
          cartItems = []; // Clear cart after purchase
        } else {
          // Navigate to home or category
          if (Math.random() < 0.5) {
            event = {
              client_id: clientId,
              page: "/home",
              event_type: "pageview",
              timestamp: currentTimestamp,
              user_id: currentUserId || undefined,
              session_id: simSessionId,
              properties: {source: "simulate"}
            };
          } else {
            const cat = categories[Math.floor(Math.random() * categories.length)];
            event = {
              client_id: clientId,
              page: `/category?category=${cat}`,
              event_type: "pageview",
              timestamp: currentTimestamp,
              user_id: currentUserId || undefined,
              session_id: simSessionId,
              properties: {category: cat, source: "simulate"}
            };
          }
        }
      }
      
      await fetch('/api/ingest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Authorization': token},
        body: JSON.stringify(event)
      });
    }
    
    output.innerText = `${persona.events} realistic events ingested successfully (${persona.name} persona)`;
    
    // Dispatch custom event to notify analytics modules to refresh
    window.dispatchEvent(new CustomEvent('dataUpdated', { 
      detail: { 
        type: 'simulate',
        events: persona.events,
        persona: persona.name 
      } 
    }));
  } catch (error) {
    console.error('Error simulating events:', error);
    output.innerText = `Error: ${error.message}`;
  }
};

// Toggle between Spark and Python analysis
if (useSparkToggle) {
  useSparkToggle.addEventListener('change', (e) => {
    useSpark = e.target.checked;
    e.target.setAttribute('aria-checked', useSpark.toString());
    updateAnalysisModeUI();
    
    // Save preference to localStorage
    localStorage.setItem('useSpark', useSpark.toString());
    
    // Notify screen readers of the change
    const mode = useSpark ? 'Spark' : 'Python';
    const statusMessage = `Analysis mode changed to ${mode}`;
    const statusEl = document.createElement('div');
    statusEl.setAttribute('role', 'status');
    statusEl.textContent = statusMessage;
    document.body.appendChild(statusEl);
    
    // Remove the status message after it's been announced
    setTimeout(() => {
      document.body.removeChild(statusEl);
    }, 1000);
  });
}

// Update UI based on analysis mode
function updateAnalysisModeUI() {
  const mode = useSpark ? 'Spark' : 'Python';
  if (analysisModeText) {
    analysisModeText.textContent = `${mode} Analysis`;
    analysisModeText.setAttribute('aria-label', `Current analysis engine: ${mode}`);
    
    // Update the tooltip based on the mode
    analysisModeText.title = useSpark 
      ? 'Using Apache Spark for large-scale data processing' 
      : 'Using Python for small to medium datasets';
  }
  
  if (analysisModeBadge) {
    analysisModeBadge.textContent = mode;
    analysisModeBadge.className = `badge ${mode.toLowerCase()}`;
    analysisModeBadge.setAttribute('aria-hidden', 'true');
    
    // Add tooltip to the badge
    analysisModeBadge.title = useSpark 
      ? 'Click to switch to Python analysis' 
      : 'Click to switch to Spark analysis';
  }
  
  // Update the analyze button text and tooltip
  if (analyzeBtn) {
    analyzeBtn.textContent = `Run ${mode} Analysis`;
    analyzeBtn.title = `Run analysis using ${mode} engine`;
  }
}

// Load analysis mode preference from localStorage
function loadPreferences() {
  const savedUseSpark = localStorage.getItem('useSpark');
  if (savedUseSpark !== null) {
    useSpark = savedUseSpark === 'true';
    if (useSparkToggle) useSparkToggle.checked = useSpark;
    updateAnalysisModeUI();
  }
}

// Check the current analysis mode from the server
async function checkAnalysisMode() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/analysis/mode', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      const serverUseSpark = data.use_spark;
      
      // Update UI if it doesn't match the server
      if (serverUseSpark !== useSpark) {
        useSpark = serverUseSpark;
        if (useSparkToggle) useSparkToggle.checked = useSpark;
        updateAnalysisModeUI();
      }
      // Clarify message to reflect server default mode, not per-run selection
      output.innerText = `Server default mode: ${serverUseSpark ? 'Spark' : 'Python'}`;
    }
  } catch (e) {
    console.error('Failed to check analysis mode:', e);
  }
}

// displayAnalysisResults is now imported from analysisDisplay.js

// Helper to run analysis with options
async function runAnalysis({ skipLLM = false, limit = null, useSparkFlag = null, analysisTarget = null } = {}) {
  if (!token) { output.innerText = 'login first'; return null; }
  const mode = (useSparkFlag === null ? useSpark : !!useSparkFlag) ? 'Spark' : 'Python';
  
  // Determine analysis target
  let targetDesc = 'current user';
  if (analysisTarget === 'all') {
    targetDesc = 'ALL USERS (entire database)';
  } else if (analysisTarget && analysisTarget.startsWith('username:')) {
    const username = analysisTarget.split(':', 1)[1];
    targetDesc = `user: ${username}`;
  }
  
  output.innerText = `Running ${mode} analysis for ${targetDesc}...`;
  try {
    const params = { use_spark: mode === 'Spark' };
    // Add analysis target
    if (analysisTarget) params.analysis_target = analysisTarget;
    // Omit limit to analyze all available events unless a specific limit is provided
    if (limit != null) params.limit = limit;
    if (skipLLM) params.skip_llm = true;

    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: JSON.stringify({ params })
    });
    if (!resp.ok) {
      const error = await resp.json().catch(() => ({}));
      throw new Error(error.error || 'Failed to run analysis');
    }
    const j = await resp.json();
    if (j.error) {
      output.innerText = `Error: ${j.error}`;
      return null;
    }
    const analysisResp = await fetch(`/api/analyses/${j.analysis._id}`, {
      headers: { 'Authorization': token }
    });
    if (!analysisResp.ok) throw new Error('Failed to fetch analysis details');
    const analysis = await analysisResp.json();
    const resultsContainer = document.getElementById('results');
    displayAnalysisResults(analysis, resultsContainer);
    checkAnalysisMode();
  // Persist analysis so a normal reload (F5) will restore it
  try { saveAnalysisToStorage(analysis); } catch (e) { console.warn('Failed to persist analysis', e); }
    output.innerText = `Analysis completed with ${mode}!`;
    return analysis;
  } catch (e) {
    output.innerText = `Error: ${e.message}`;
    console.error('Analysis error:', e);
    return null;
  }
}

function ensureAutoAnalyzeButton() {
  if (autoAnalyzeBtn) return autoAnalyzeBtn;
  const controls = document.getElementById('controls');
  const btn = document.createElement('button');
  btn.id = 'autoAnalyzeBtn';
  btn.textContent = 'Start Auto-Analyze';
  btn.title = 'Auto-run analysis periodically (LLM skipped)';
  btn.style.marginLeft = '8px';
  controls.querySelector('.analysis-controls')?.appendChild(btn);
  autoAnalyzeBtn = btn;
  return btn;
}

function startAutoAnalyze() {
  if (autoAnalyzeTimer) clearInterval(autoAnalyzeTimer);
  
  // Determine current analysis target based on username field
  const getAnalysisTarget = () => {
    const usernameInput = document.getElementById('targetUsername');
    const username = usernameInput ? usernameInput.value.trim() : '';
    return username ? `username:${username}` : 'all';
  };
  
  // First immediate run with skip LLM and no limit
  const target = getAnalysisTarget();
  runAnalysis({ skipLLM: true, limit: null, analysisTarget: target });
  autoAnalyzeTimer = setInterval(() => {
    const target = getAnalysisTarget();
    runAnalysis({ skipLLM: true, limit: null, analysisTarget: target });
  }, AUTO_ANALYZE_INTERVAL_MS);
  localStorage.setItem('autoAnalyze', 'true');
  if (autoAnalyzeBtn) autoAnalyzeBtn.textContent = 'Stop Auto-Analyze';
}

function stopAutoAnalyze() {
  if (autoAnalyzeTimer) clearInterval(autoAnalyzeTimer);
  autoAnalyzeTimer = null;
  localStorage.setItem('autoAnalyze', 'false');
  if (autoAnalyzeBtn) autoAnalyzeBtn.textContent = 'Start Auto-Analyze';
}

// Check OpenRouter API key status
async function checkKey() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/openrouter/key', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      if (data.exists && data.masked_key) {
        keyStatus.innerHTML = `✅ API Key is set: <code>${data.masked_key}</code>`;
        keyStatus.className = 'key-status success';
        return true;
      } else {
        keyStatus.textContent = '❌ No API Key found';
        keyStatus.className = 'key-status error';
        return false;
      }
    } else {
      const error = await resp.json().catch(() => ({}));
      keyStatus.textContent = `❌ Error: ${error.error || 'Failed to check key'}`;
      keyStatus.className = 'key-status error';
      return false;
    }
  } catch (e) {
    console.error('Error checking key:', e);
    keyStatus.textContent = `❌ Error: ${e.message}`;
    keyStatus.className = 'key-status error';
    return false;
  }
}

// Save OpenRouter API key
async function saveKey() {
  if (!token) {
    output.innerText = 'Please login first';
    return false;
  }
  
  const key = openrouterKeyInput.value.trim();
  if (!key) {
    keyStatus.textContent = '❌ Please enter an API key';
    keyStatus.className = 'key-status error';
    return false;
  }
  
  try {
    const resp = await fetch('/api/openrouter/key', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: JSON.stringify({ api_key: key })
    });
    
    if (resp.ok) {
      const data = await resp.json();
      keyStatus.textContent = '✅ API Key saved successfully';
      keyStatus.className = 'key-status success';
      openrouterKeyInput.value = ''; // Clear the input field
      return true;
    } else {
      const error = await resp.json().catch(() => ({}));
      keyStatus.textContent = `❌ Error: ${error.error || 'Failed to save key'}`;
      keyStatus.className = 'key-status error';
      return false;
    }
  } catch (e) {
    console.error('Error saving key:', e);
    keyStatus.textContent = `❌ Error: ${e.message}`;
    keyStatus.className = 'key-status error';
    return false;
  }
}

// Load product recommendations
async function loadRecommendations() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/recommendations', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      const recItems = data.items || data.recommendations || [];
      if (recItems && recItems.length > 0) {
        recsEl.innerHTML = '<h3>Recommended for You</h3>';
        const ul = document.createElement('ul');
        
        recItems.forEach(rec => {
          const li = document.createElement('li');
          li.innerHTML = `
            <a href="/p/${encodeURIComponent(rec.product_id)}?id=${encodeURIComponent(rec.product_id)}">
              <img src="${rec.image_url || '/static/images/placeholder.svg'}" alt="${rec.name}">
              <h4>${rec.name}</h4>
              <p>$${rec.price?.toFixed(2) || 'N/A'}</p>
            </a>
          `;
          ul.appendChild(li);
        });
        
        recsEl.appendChild(ul);
      } else {
        recsEl.innerHTML = '<p>No recommendations available. Generate some by analyzing your data!</p>';
      }
    }
  } catch (e) {
    console.error('Error loading recommendations:', e);
    recsEl.innerHTML = '<p>Error loading recommendations. Please try again later.</p>';
  }
}

// Event listeners for key management
if (saveKeyBtn) {
  saveKeyBtn.addEventListener('click', saveKey);
}

if (checkKeyBtn) {
  checkKeyBtn.addEventListener('click', checkKey);
}

// Initialize
loadPreferences();
startMetricsPolling();

// Set initial ARIA attributes
if (useSparkToggle) {
  useSparkToggle.setAttribute('aria-checked', useSpark.toString());
  useSparkToggle.setAttribute('role', 'switch');
  useSparkToggle.setAttribute('aria-labelledby', 'analysisModeLabel');
}

// Username input for optional single-user analysis
function ensureUsernameInput() {
  const controls = document.getElementById('controls');
  if (!controls) return;
  
  // Check if already exists
  if (document.getElementById('usernameInputSection')) return;
  
  const inputDiv = document.createElement('div');
  inputDiv.id = 'usernameInputSection';
  inputDiv.className = 'username-section';
  inputDiv.innerHTML = `
    <div class="username-field">
      <label for="targetUsername" class="username-label">
        <span class="label-text">Username (Optional)</span>
        <span class="label-hint">Leave empty to analyze all users</span>
      </label>
      <input 
        type="text" 
        id="targetUsername" 
        placeholder="Enter username to analyze specific user..."
        class="username-input"
      />
    </div>
  `;
  
  // Insert before analyze button
  const analyzeSection = controls.querySelector('.analysis-controls');
  if (analyzeSection) {
    analyzeSection.parentNode.insertBefore(inputDiv, analyzeSection);
  } else {
    controls.appendChild(inputDiv);
  }
}

analyzeBtn.onclick = async () => {
  // Check if username is provided
  const usernameInput = document.getElementById('targetUsername');
  const username = usernameInput ? usernameInput.value.trim() : '';
  
  let analysisTarget = null;
  
  if (username) {
    // If username provided, analyze that specific user
    analysisTarget = `username:${username}`;
  } else {
    // If no username, analyze all users (entire database)
    analysisTarget = 'all';
  }
  
  await runAnalysis({ skipLLM: false, limit: null, analysisTarget });
};

// ML Algorithm buttons
const mlKmeansBtn = document.getElementById('mlKmeansBtn');
const mlTreeBtn = document.getElementById('mlTreeBtn');
const mlFpGrowthBtn = document.getElementById('mlFpGrowthBtn');
const mlLogisticBtn = document.getElementById('mlLogisticBtn');

async function runMLAlgorithm(endpoint, algorithmName) {
  if (!token) {
    output.innerText = "Please login first";
    return;
  }
  
  const usernameInput = document.getElementById('targetUsername');
  const username = usernameInput ? usernameInput.value.trim() : null;
  
  output.innerText = `Running ${algorithmName}...`;
  
  try {
    const resp = await fetch(`/api/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: JSON.stringify({ username })
    });
    
    // Check HTTP status first
    if (!resp.ok) {
      const errorData = await resp.json();
      const errorMsg = errorData.detail || errorData.error || `HTTP ${resp.status} error`;
      output.innerText = `Error: ${errorMsg}`;
      return;
    }
    
    const result = await resp.json();
    
    // Additional check for error in response
    if (result.error) {
      output.innerText = `Error: ${result.error}`;
      return;
    }
    
  // Display results
  displayMLResults(algorithmName, result);
  // Persist ML result so normal reload restores it
  try { saveMLResultToStorage(algorithmName, result); } catch (e) { console.warn('Failed to persist ML result', e); }
  output.innerText = `${algorithmName} completed successfully`;
  } catch (error) {
    console.error(`Error running ${algorithmName}:`, error);
    output.innerText = `Error: ${error.message}`;
  }
}

function displayMLResults(algorithmName, result) {
  // Validate result object
  if (!result || typeof result !== 'object') {
    console.error('Invalid result object:', result);
    return;
  }
  
  // Create or get ML results container
  let mlResultsDiv = document.getElementById('ml-results');
  if (!mlResultsDiv) {
    mlResultsDiv = document.createElement('div');
    mlResultsDiv.id = 'ml-results';
    mlResultsDiv.className = 'analysis-section ml-results-section';
    const resultsDiv = document.getElementById('results');
    if (resultsDiv) {
      resultsDiv.insertBefore(mlResultsDiv, resultsDiv.firstChild);
    }
  }
  
  // Build HTML based on algorithm
  let html = `<h2>🤖 ${algorithmName}</h2>`;
  
  if (algorithmName === 'K-Means Clustering') {
    html += `
      <div class="ml-result-card">
        <h3>Cluster Analysis</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon">👥</div>
            <div class="metric-value">${result.total_users}</div>
            <div class="metric-label">Total Users</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value">${result.num_clusters}</div>
            <div class="metric-label">Clusters</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-value">${result.silhouette_score}</div>
            <div class="metric-label">Silhouette Score</div>
          </div>
        </div>
        
        <h4>Cluster Characteristics</h4>
        <div class="clusters-grid">
    `;
    
    if (result.cluster_stats && typeof result.cluster_stats === 'object') {
      for (const [clusterId, stats] of Object.entries(result.cluster_stats)) {
        const clusterNames = ['🔵 Low Value', '🟢 Medium Value', '🟡 High Value'];
        html += `
          <div class="cluster-card">
            <div class="cluster-header">${clusterNames[clusterId] || `Cluster ${clusterId}`}</div>
            <div class="cluster-stats">
              <div><strong>Users:</strong> ${stats.user_count || 0}</div>
              <div><strong>Avg Events:</strong> ${stats.avg_events || 0}</div>
              <div><strong>Conversion:</strong> ${((stats.avg_conversion || 0) * 100).toFixed(2)}%</div>
              <div><strong>Cart Rate:</strong> ${((stats.avg_cart_rate || 0) * 100).toFixed(2)}%</div>
            </div>
          </div>
        `;
      }
    }
    
    html += `
        </div>
      </div>
    `;
  } else if (algorithmName === 'Decision Tree') {
    html += `
      <div class="ml-result-card">
        <h3>Conversion Prediction Model</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value">${result.auc_score}</div>
            <div class="metric-label">AUC Score</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🌳</div>
            <div class="metric-value">${result.tree_depth}</div>
            <div class="metric-label">Tree Depth</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📦</div>
            <div class="metric-value">${result.training_samples}</div>
            <div class="metric-label">Training Samples</div>
          </div>
        </div>
        
        <h4>Feature Importance</h4>
        <div class="feature-importance">
    `;
    
    if (result.feature_importance && typeof result.feature_importance === 'object') {
      const maxImportance = Math.max(...Object.values(result.feature_importance));
      for (const [feature, importance] of Object.entries(result.feature_importance)) {
      const percentage = (importance / maxImportance * 100);
      html += `
        <div class="feature-bar">
          <span class="feature-name">${feature}</span>
          <div class="bar-container">
            <div class="bar-fill" style="width: ${percentage}%"></div>
          </div>
          <span class="feature-value">${importance}</span>
        </div>
      `;
      }
    }
    
    html += `
        </div>
        
        <h4>Sample Predictions</h4>
        <table class="predictions-table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Actual</th>
              <th>Predicted</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
    `;
    
    if (result.sample_predictions && Array.isArray(result.sample_predictions)) {
      for (const sample of result.sample_predictions) {
        const match = sample.actual === sample.predicted;
        html += `
          <tr class="${match ? 'correct' : 'incorrect'}">
            <td>${sample.session_id}</td>
            <td>${sample.actual ? '✅ Purchase' : '❌ No Purchase'}</td>
            <td>${sample.predicted ? '✅ Purchase' : '❌ No Purchase'}</td>
            <td>${(sample.confidence * 100).toFixed(1)}%</td>
          </tr>
        `;
      }
    }
    
    html += `
          </tbody>
        </table>
      </div>
    `;
  } else if (algorithmName === 'FP-Growth Pattern Mining') {
    html += `
      <div class="ml-result-card">
        <h3>Frequent Navigation Patterns</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-value">${result.total_transactions}</div>
            <div class="metric-label">Sessions Analyzed</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🔍</div>
            <div class="metric-value">${result.num_frequent_patterns}</div>
            <div class="metric-label">Patterns Found</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📈</div>
            <div class="metric-value">${result.num_rules}</div>
            <div class="metric-label">Association Rules</div>
          </div>
        </div>
        
        <h4>Top Frequent Patterns</h4>
        <div class="patterns-list">
    `;
    
    if (result.top_patterns && Array.isArray(result.top_patterns)) {
      for (const pattern of result.top_patterns.slice(0, 10)) {
        html += `
          <div class="pattern-item">
            <div class="pattern-pages">${pattern.pattern.join(' → ')}</div>
            <div class="pattern-stats">
              <span class="freq-badge">${pattern.frequency} sessions</span>
              <span class="support-badge">Support: ${(pattern.support * 100).toFixed(1)}%</span>
            </div>
          </div>
        `;
      }
    }
    
    html += `
        </div>
        
        <h4>Top Association Rules</h4>
        <div class="rules-list">
    `;
    
    if (result.top_rules && Array.isArray(result.top_rules)) {
      for (const rule of result.top_rules.slice(0, 8)) {
        html += `
          <div class="rule-item">
            <div class="rule-text">
              <span class="if-part">${rule.if.join(', ')}</span>
              <span class="arrow">⇒</span>
              <span class="then-part">${rule.then.join(', ')}</span>
            </div>
            <div class="rule-stats">
              <span>Confidence: ${(rule.confidence * 100).toFixed(1)}%</span>
              <span>Lift: ${rule.lift.toFixed(2)}</span>
            </div>
          </div>
        `;
      }
    }
    
    html += `
        </div>
      </div>
    `;
  } else if (algorithmName === 'Logistic Regression') {
    html += `
      <div class="ml-result-card">
        <h3>Purchase Probability Prediction</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value">${result.auc_score}</div>
            <div class="metric-label">AUC Score</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📦</div>
            <div class="metric-value">${result.training_samples}</div>
            <div class="metric-label">Training Samples</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🧪</div>
            <div class="metric-value">${result.test_samples}</div>
            <div class="metric-label">Test Samples</div>
          </div>
        </div>
        
        <h4>Feature Coefficients</h4>
        <div class="coefficients-list">
    `;
    
    if (result.feature_coefficients && typeof result.feature_coefficients === 'object') {
      for (const [feature, coef] of Object.entries(result.feature_coefficients)) {
        const isPositive = coef > 0;
        html += `
          <div class="coef-item">
            <span class="coef-name">${feature}</span>
            <span class="coef-value ${isPositive ? 'positive' : 'negative'}">
              ${isPositive ? '+' : ''}${coef}
            </span>
          </div>
        `;
      }
    }
    
    html += `
          <div class="coef-item intercept">
            <span class="coef-name">Intercept</span>
            <span class="coef-value">${result.intercept}</span>
          </div>
        </div>
        
        <h4>Sample Predictions</h4>
        <table class="predictions-table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Actual</th>
              <th>Predicted</th>
              <th>Purchase Probability</th>
            </tr>
          </thead>
          <tbody>
    `;
    
    if (result.sample_predictions && Array.isArray(result.sample_predictions)) {
      for (const sample of result.sample_predictions) {
        const match = sample.actual === sample.predicted;
        html += `
          <tr class="${match ? 'correct' : 'incorrect'}">
            <td>${sample.session_id}</td>
            <td>${sample.actual ? '✅ Purchase' : '❌ No Purchase'}</td>
            <td>${sample.predicted ? '✅ Purchase' : '❌ No Purchase'}</td>
            <td>
              <div class="prob-bar-container">
                <div class="prob-bar" style="width: ${sample.purchase_probability * 100}%"></div>
                <span class="prob-text">${(sample.purchase_probability * 100).toFixed(1)}%</span>
              </div>
            </td>
          </tr>
        `;
      }
    }
    
    html += `
          </tbody>
        </table>
      </div>
    `;
  }
  
  mlResultsDiv.innerHTML = html;
}

if (mlKmeansBtn) {
  mlKmeansBtn.onclick = () => runMLAlgorithm('ml/kmeans', 'K-Means Clustering');
}

if (mlTreeBtn) {
  mlTreeBtn.onclick = () => runMLAlgorithm('ml/decision-tree', 'Decision Tree');
}

if (mlFpGrowthBtn) {
  mlFpGrowthBtn.onclick = () => runMLAlgorithm('ml/fp-growth', 'FP-Growth Pattern Mining');
}

if (mlLogisticBtn) {
  mlLogisticBtn.onclick = () => runMLAlgorithm('ml/logistic-regression', 'Logistic Regression');
}
