// Import displayAnalysisResults from the analysisDisplay module
import { displayAnalysisResults } from './analysisDisplay.js';

// DOM Elements
const loginBtn = document.getElementById('loginBtn');
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
let useSpark = true;
let metricsTimer = null;
const METRICS_INTERVAL_MS = 10000;
const AUTO_ANALYZE_INTERVAL_MS = 60000;
let autoAnalyzeTimer = null;

function ensureMetricsPanel() {
  let panel = document.getElementById('rt-metrics');
  if (!panel) {
    const controls = document.getElementById('controls');
    panel = document.createElement('div');
    panel.id = 'rt-metrics';
    panel.className = 'analysis-section';
    panel.innerHTML = `
      <h2 class="section-title">Real-time Metrics (last 60 min)</h2>
      <div id="rt-summary" class="metrics-grid"></div>
      <div style="display:grid; gap:12px; margin-top:12px">
        <div>
          <h3 style="margin:6px 0">Events per minute</h3>
          <div id="rt-line"></div>
        </div>
        <div>
          <h3 style="margin:6px 0">Top pages (60m)</h3>
          <div id="rt-bars"></div>
        </div>
      </div>
      <details>
        <summary>Raw aggregates</summary>
        <pre id="rt-raw"></pre>
      </details>
    `;
    controls.appendChild(panel);
  }
  return panel;
}

async function fetchAggregates() {
  try {
    const resp = await fetch('/api/metrics/aggregates?minutes=60');
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

function renderAggregates(data) {
  const panel = ensureMetricsPanel();
  const items = (data && data.items) || [];
  const total = items.reduce((s, r) => s + (r.count || 0), 0);
  const byEvent = {};
  const byPage = {};
  const byMinute = new Map(); // key: epoch minute string, val: total count
  for (const r of items) {
    byEvent[r.event_type] = (byEvent[r.event_type] || 0) + (r.count || 0);
    if (r.page) byPage[r.page] = (byPage[r.page] || 0) + (r.count || 0);
    const end = r.window_end ? new Date(r.window_end) : null;
    if (end && !isNaN(end.getTime())) {
      const key = `${end.getUTCFullYear()}-${String(end.getUTCMonth()+1).padStart(2,'0')}-${String(end.getUTCDate()).padStart(2,'0')} ${String(end.getUTCHours()).padStart(2,'0')}:${String(end.getUTCMinutes()).padStart(2,'0')}`;
      byMinute.set(key, (byMinute.get(key)||0) + (r.count||0));
    }
  }
  const topEvent = Object.entries(byEvent).sort((a,b)=>b[1]-a[1])[0] || ['',0];
  const topPage = Object.entries(byPage).sort((a,b)=>b[1]-a[1])[0] || ['',0];
  const grid = panel.querySelector('#rt-summary');
  grid.innerHTML = `
    <div class="metric-card"><div class="metric-value">${total}</div><div class="metric-label">Events (60m)</div></div>
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
  // Prepare last 60 minute timeline
  const now = new Date();
  const labels = [];
  const values = [];
  for (let i = 59; i >= 0; i--) {
    const t = new Date(now.getTime() - i*60000);
    const key = `${t.getUTCFullYear()}-${String(t.getUTCMonth()+1).padStart(2,'0')}-${String(t.getUTCDate()).padStart(2,'0')} ${String(t.getUTCHours()).padStart(2,'0')}:${String(t.getUTCMinutes()).padStart(2,'0')}`;
    labels.push(key);
    values.push(byMinuteMap.get(key) || 0);
  }
  const width = 600, height = 160, pad = 24;
  const maxV = Math.max(1, ...values);
  const pts = values.map((v, idx) => {
    const x = pad + (idx/(values.length-1))*(width-2*pad);
    const y = pad + (1 - (v/maxV))*(height-2*pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(fr => {
    const y = pad + (1-fr)*(height-2*pad);
    const val = Math.round(maxV*fr);
    return `<line x1=\"${pad}\" y1=\"${y}\" x2=\"${width-pad}\" y2=\"${y}\" stroke=\"#233046\" stroke-width=\"1\" />
            <text x=\"${pad-4}\" y=\"${y}\" fill=\"#98a5b5\" font-size=\"10\" text-anchor=\"end\">${val}</text>`;
  }).join('');
  return `<svg width=\"100%\" viewBox=\"0 0 ${width} ${height}\" preserveAspectRatio=\"xMidYMid meet\">
    <rect x=\"0\" y=\"0\" width=\"${width}\" height=\"${height}\" fill=\"rgba(255,255,255,0.02)\" />
    ${ticks}
    <polyline fill=\"none\" stroke=\"#2563eb\" stroke-width=\"2\" points=\"${pts}\" />
  </svg>`;
}

function renderBarChartSVG(byPageObj) {
  const entries = Object.entries(byPageObj).sort((a,b)=>b[1]-a[1]).slice(0,5);
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

loginBtn.onclick = async () => {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const resp = await fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username, password})
  });
  const j = await resp.json();
  if (j.token) {
    token = j.token;
    
    // Hiển thị API key status
    let statusMsg = `Logged in as ${j.username}!`;
    if (j.api_key_status) {
      if (j.api_key_status.has_key) {
        statusMsg += `\n✅ API Key: Ready (source: ${j.api_key_status.source})`;
        if (j.api_key_status.synced) {
          statusMsg += ` [synced to database]`;
        }
      } else {
        statusMsg += `\n⚠️ No API Key found`;
      }
    }
    output.innerText = statusMsg;
    
    document.getElementById('controls').style.display = 'block';
    
    // After login, check current key
    try { await checkKey(); } catch(e) {}
    // Also load latest recommendations if any
    try { await loadRecommendations(); } catch(e) {}
    // Start/refresh real-time metrics polling
    startMetricsPolling();
    // Ensure auto-analyze control and restore last state
    ensureAutoAnalyzeButton();
    autoAnalyzeBtn.onclick = () => {
      if (autoAnalyzeTimer) stopAutoAnalyze(); else startAutoAnalyze();
    };
    const savedAuto = localStorage.getItem('autoAnalyze');
    if (savedAuto === 'true') startAutoAnalyze();
  } else {
    output.innerText = JSON.stringify(j);
  }
};

simulateBtn.onclick = async () => {
  if (!token) { output.innerText = "login first"; return; }
  output.innerText = "Simulating 10 events...";
  
  try {
    // create 10 simple events
    for (let i = 0; i < 10; i++) {
      const event = {
        client_id: "client-demo",
        page: i % 3 === 0 ? "/home" : (i % 3 === 1 ? "/product" : "/checkout"),
        event_type: "pageview",
        timestamp: Math.floor(Date.now() / 1000)
      };
      
      await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token
        },
        body: JSON.stringify(event)
      });
    }
    
    output.innerText = "10 events ingested successfully";
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
async function runAnalysis({ skipLLM = false, limit = null, useSparkFlag = null } = {}) {
  if (!token) { output.innerText = 'login first'; return null; }
  const mode = (useSparkFlag === null ? useSpark : !!useSparkFlag) ? 'Spark' : 'Python';
  output.innerText = `Running analysis with ${mode}...`;
  try {
    const params = { use_spark: mode === 'Spark' };
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
  // First immediate run with skip LLM and no limit
  runAnalysis({ skipLLM: true, limit: null });
  autoAnalyzeTimer = setInterval(() => runAnalysis({ skipLLM: true, limit: null }), AUTO_ANALYZE_INTERVAL_MS);
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

analyzeBtn.onclick = async () => {
  await runAnalysis({ skipLLM: false, limit: null });
};
