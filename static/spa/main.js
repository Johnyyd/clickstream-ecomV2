import {
  el,
  debounce,
  requestIdle,
  withBypass,
  showToast,
  setActiveTab,
  toISO,
  presetToDates,
  fmt,
  fmtCurrency,
  fmtShort
} from './lib/utils.js';

import {
  httpCache,
  cacheKey,
  lsGet,
  lsSet,
  lsData,
  lsDel,
  filterSig,
  snapKey,
  snapSet,
  snapGet,
  snapUpdate,
  clearSnapshotForTabCurrentFilter,
  clearSnapshotsForTab,
  clearSnapshotsForCurrentFilters,
  migrateOldSnapshots,
  getWithTTL
} from './lib/cache.js';


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

// Expose state to window for cache module access
window.__spaState = state;

// Cache functions imported from lib/cache.js


async function renderLLM() {
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
          <div><div class="muted">AOV</div><div id="llm-kpi-aov" class="kpi-value">—</div></div>
        </div>
      </div>
      <div class="card"><h3>Funnel (LLM view) / Phễu (Góc nhìn LLM)</h3><div class="chart" id="llm-chart-funnel"></div></div>
      <div class="card"><h3>SEO Distribution / Phân phối SEO</h3><div class="chart" id="llm-chart-seo"></div></div>
      <div class="card"><h3>Retention / Giữ chân</h3><div class="chart" id="llm-chart-ret"></div></div>
      <div class="card" style="grid-column: 1 / -1"><h3>Data Quality</h3>
        <div id="llm-dq" class="muted"></div>
      </div>
    </div>
  `;
  const statusEl = el('#llm-status');

  function renderReport(payload) {
    const rep = payload?.report?.parsed || payload?.report || {};
    const summary = rep.executive_summary || rep.summary || rep.insights || '';
    el('#llm-summary').innerHTML = summary ? `<div style="white-space:pre-wrap">${summary}</div>` : '<div class="muted">No summary.</div>';
    // Build grouped insights per module if structured schema is present
    const recEl = el('#llm-recs');
    const insEl = el('#llm-insights');
    let insightsHtml = '';
    try {
      if (rep.insights && typeof rep.insights === 'object') {
        const groups = [
          { key: 'business', label: 'Business' },
          { key: 'journey', label: 'Journey / Funnel' },
          { key: 'seo', label: 'SEO & Traffic' },
          { key: 'retention', label: 'Retention & Churn' },
          { key: 'cart', label: 'Cart & Abandonment' },
          { key: 'ml_prediction', label: 'ML Prediction' },
        ];
        for (const { key, label } of groups) {
          const v = rep.insights[key];
          if (!v) continue;
          const bullets = Array.isArray(v) ? v : (Array.isArray(v?.bullets) ? v.bullets : []);
          if (!bullets.length) continue;
          const items = bullets.map(b => {
            if (b == null) return '';
            if (typeof b === 'string' || typeof b === 'number') return String(b);
            // Support object shape from LLM like { text, module, ... }
            if (typeof b === 'object' && b.text) return String(b.text);
            try { return JSON.stringify(b); } catch { return String(b); }
          }).filter(Boolean);
          if (!items.length) continue;
          insightsHtml += `<li><b>${label}</b><ul>` + items.map(t => `<li>${t}</li>`).join('') + '</ul></li>';
        }
      }
    } catch { }

    // Fallback: flat list from key_insights/highlights if no structured insights
    if (!insightsHtml) {
      let ins = Array.isArray(rep.key_insights) ? rep.key_insights : (Array.isArray(rep.highlights) ? rep.highlights : []);
      insightsHtml = ins.length ? ins.map(i => `<li>${i}</li>`).join('') : '<li class="muted">—</li>';
    }
    if (insEl) { insEl.innerHTML = insightsHtml || '<li class="muted">—</li>'; }
    // Recommendations: combine recommendations + next_best_actions + risk_alerts
    const recs = [];
    try {
      if (Array.isArray(rep.recommendations)) recs.push(...rep.recommendations);
      if (Array.isArray(rep.next_best_actions)) recs.push(...rep.next_best_actions.map(a => typeof a === 'string' ? a : `${a.action} — impact:${a.impact || ''}/effort:${a.effort || ''}`));
      if (Array.isArray(rep.risk_alerts)) recs.push(...rep.risk_alerts.map(r => typeof r === 'string' ? r : `Risk(${r.severity || ''}): ${r.title || ''} — ${r.reason || ''}`));
    } catch { }
    recEl.innerHTML = recs.length ? recs.map(i => `<li>${i}</li>`).join('') : '<li class="muted">—</li>';
  }

  function renderCharts(charts) {
    if (!charts || typeof charts !== 'object') return;
    try {
      const k = charts.kpis || {};
      const s = Number(k.sessions || 0), u = Number(k.users || 0), cr = Number(k.cr || 0), rev = Number(k.revenue || 0), aov = Number(k.aov || 0);
      const ks = el('#llm-kpi-sessions'); if (ks) ks.textContent = fmt(s);
      const ku = el('#llm-kpi-users'); if (ku) ku.textContent = fmt(u);
      const kc = el('#llm-kpi-cr'); if (kc) kc.textContent = `${fmt((cr || 0) * 100, 2)}%`;
      const kr = el('#llm-kpi-rev'); if (kr) kr.textContent = fmtCurrency(rev);
      const ka = el('#llm-kpi-aov'); if (ka) ka.textContent = aov > 0 ? fmtCurrency(aov) : '—';
    } catch { }
    // Funnel
    try {
      const fEl = el('#llm-chart-funnel');
      const data = Array.isArray(charts.funnel) ? charts.funnel : [];
      if (fEl && data.length) { const c = echarts.init(fEl); c.setOption({ tooltip: { trigger: 'item' }, series: [{ type: 'funnel', data }] }); }
    } catch { }
    // SEO distribution
    try {
      const sEl = el('#llm-chart-seo');
      const dist = Array.isArray(charts.seo_distribution) ? charts.seo_distribution : [];
      if (sEl && dist.length) { const c = echarts.init(sEl); c.setOption({ tooltip: { trigger: 'item' }, series: [{ type: 'pie', radius: ['40%', '70%'], data: dist }] }); }
    } catch { }
    // Retention
    try {
      const rEl = el('#llm-chart-ret');
      const ts = Array.isArray(charts.retention_timeseries) ? charts.retention_timeseries : [];
      if (rEl && ts.length) { const cats = ts.map(r => r.date || ''); const ret = ts.map(r => r.retained || 0); const ch = ts.map(r => r.churned || 0); const c = echarts.init(rEl); c.setOption({ tooltip: { trigger: 'axis' }, legend: { data: ['Retained', 'Churned'] }, xAxis: { type: 'category', data: cats }, yAxis: { type: 'value' }, series: [{ name: 'Retained', type: 'line', data: ret }, { name: 'Churned', type: 'line', data: ch }] }); }
    } catch { }
    // Data quality text
    try {
      const dqEl = el('#llm-dq'); const dq = charts.data_quality || {};
      if (dqEl) {
        dqEl.innerHTML = `
        <div style="display:flex;gap:16px;flex-wrap:wrap">
          <div>Events: <b>${fmt(Number(dq.events_count || 0))}</b></div>
          <div>Sessions: <b>${fmt(Number(dq.sessions_count || 0))}</b></div>
          <div>Missing %: <b>${fmt(Number(dq.missing_values_pct || 0), 2)}%</b></div>
          <div>Duplicates %: <b>${fmt(Number(dq.duplicate_events_pct || 0), 2)}%</b></div>
          <div>Last event: <b>${dq.last_event_ts ? String(dq.last_event_ts) : '—'}</b></div>
        </div>`;
      }
    } catch { }
  }

  // Restore
  (function () {
    const snap = snapGet('llm');
    if (snap) {
      renderReport(snap);
      try {
        const chartsTop = snap?.charts || {};
        const chartsParsed = snap?.report?.parsed?.charts || {};
        const mergedCharts = {
          ...chartsTop,
          // ưu tiên retention_timeseries từ parsed nếu có
          retention_timeseries: chartsParsed.retention_timeseries || chartsTop.retention_timeseries,
        };
        renderCharts(mergedCharts);
      } catch {
        renderCharts(snap?.charts);
      }
      statusEl.textContent = 'Restored from cache';
    }
  })();

  async function run(fetchFresh = false) {
    const q = buildQuery();
    let url = `/api/v1/openrouter/report?${q}`;
    if (fetchFresh) { const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    const data = fetchFresh ? await safeGet(url) : await getWithTTL(url, 600000);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Always save to cache when fetching fresh data
    if (fetchFresh) {
      snapSet('llm', data);
    } else {
      snapUpdate('llm', data);
    }
    renderReport(data);
    try {
      const chartsTop = data?.charts || {};
      const chartsParsed = data?.report?.parsed?.charts || {};
      const mergedCharts = {
        ...chartsTop,
        retention_timeseries: chartsParsed.retention_timeseries || chartsTop.retention_timeseries,
      };
      renderCharts(mergedCharts);
    } catch {
      renderCharts(data?.charts);
    }
  }

  el('#llm-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('llm'); run(true); });
  el('#llm-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('llm'); run(true); });
  if (!snapGet('llm')) { await run(false); }
}

async function renderML() {
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
  (function () {
    const snap = snapGet('ml');
    if (!snap) return;
    renderConv(snap.conversion || {});
    renderProb(snap.purchase || {});
    renderSeg(snap.segmentation || {});
    statusEl.textContent = 'Restored from cache';
  })();

  function renderConv(data) {
    const elc = el('#ml-conv');
    if (!elc) return;
    // Support Decision Tree payload: feature_importance map and sample_predictions[].confidence
    let avg = 0; let n = 0;
    try {
      if (Array.isArray(data.sample_predictions)) {
        for (const p of data.sample_predictions) {
          const v = Number(p.confidence ?? p.purchase_probability ?? 0);
          if (isFinite(v)) { avg += v; n++; }
        }
      }
    } catch { }
    const score = n ? (avg / n) : Number(data.avg_probability ?? 0);
    const aucScore = Number(data.auc_score || 0);
    const title = `Conversion Prediction / Dự đoán chuyển đổi`;
    const subtitle = `Avg Likelihood / Khả năng TB: ${fmt((score || 0) * 100, 2)}%` + (aucScore ? ` • AUC: ${fmt(aucScore, 3)}` : '');

    // Feature importance bar if available
    let cats = [], vals = [];
    try {
      const fmap = data.feature_importance;
      if (fmap && typeof fmap === 'object') {
        cats = Object.keys(fmap);
        vals = cats.map(k => Number(fmap[k] || 0));
      }
    } catch { }

    const chart = echarts.init(elc);
    if (cats.length) {
      chart.setOption({
        title: [
          { text: title, left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 'bold' } },
          { text: subtitle, left: 'center', top: 30, textStyle: { fontSize: 11, color: '#666' } }
        ],
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            const p = params[0];
            return `<div style="padding:8px">
              <strong>${p.name}</strong><br/>
              Importance / Độ quan trọng: <strong>${fmt(p.value, 4)}</strong><br/>
              <span style="color:#666;font-size:11px">Influence on conversion / Ảnh hưởng đến chuyển đổi</span>
            </div>`;
          }
        },
        grid: { left: 60, right: 30, bottom: 60, top: 70 },
        xAxis: {
          type: 'category',
          data: cats,
          axisLabel: { rotate: 45, fontSize: 10 },
          name: 'Features',
          nameLocation: 'middle',
          nameGap: 40
        },
        yAxis: {
          type: 'value',
          name: 'Importance Score',
          nameLocation: 'middle',
          nameGap: 45
        },
        series: [{
          type: 'bar',
          name: 'Feature Importance',
          data: vals,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#1d4ed8' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}',
            fontSize: 10
          }
        }]
      });
    } else {
      chart.setOption({
        title: [
          { text: title, left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 'bold' } },
          { text: subtitle, left: 'center', top: 30, textStyle: { fontSize: 11, color: '#666' } }
        ],
        tooltip: {
          formatter: function (params) {
            return `<div style="padding:8px">
              <strong>Conversion Likelihood / Khả năng chuyển đổi</strong><br/>
              Score: <strong>${params.value}%</strong><br/>
              <span style="color:#666;font-size:11px">Probability of purchase / Xác suất mua hàng</span>
            </div>`;
          }
        },
        grid: { left: 60, right: 30, bottom: 40, top: 70 },
        xAxis: { type: 'category', data: ['Likelihood'] },
        yAxis: { type: 'value', max: 100, name: 'Percentage (%)' },
        series: [{
          type: 'bar',
          data: [Math.round((score || 0) * 10000) / 100],
          itemStyle: { color: '#10b981' },
          label: { show: true, position: 'top', formatter: '{c}%' }
        }]
      });
    }
  }
  function renderProb(data) {
    const elp = el('#ml-prob');
    if (!elp) return;
    // Logistic Regression payload: feature_coefficients map and sample_predictions[].purchase_probability
    let avg = 0, n = 0;
    try {
      if (Array.isArray(data.sample_predictions)) {
        for (const p of data.sample_predictions) { const v = Number(p.purchase_probability || 0); if (isFinite(v)) { avg += v; n++; } }
      }
    } catch { }
    const score = n ? (avg / n) : Number(data.avg_probability || 0);
    const aucScore = Number(data.auc_score || 0);
    let cats = [], vals = [];
    try {
      const coeff = data.feature_coefficients;
      if (coeff && typeof coeff === 'object') {
        cats = Object.keys(coeff);
        vals = cats.map(k => Math.abs(Number(coeff[k] || 0)));
      }
    } catch { }

    const chart = echarts.init(elp);
    const title = `Purchase Probability / Xác suất mua hàng`;
    const subtitle = `Avg Prob / Xác suất TB: ${fmt((score || 0) * 100, 2)}%` + (aucScore ? ` • AUC: ${fmt(aucScore, 3)}` : '');

    if (cats.length) {
      chart.setOption({
        title: [
          { text: title, left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 'bold' } },
          { text: subtitle, left: 'center', top: 30, textStyle: { fontSize: 11, color: '#666' } }
        ],
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            const p = params[0];
            return `<div style="padding:8px">
              <strong>${p.name}</strong><br/>
              Coefficient / Hệ số: <strong>${fmt(p.value, 4)}</strong><br/>
              <span style="color:#666;font-size:11px">Impact (absolute) / Tác động (giá trị tuyệt đối)</span>
            </div>`;
          }
        },
        grid: { left: 60, right: 30, bottom: 60, top: 70 },
        xAxis: {
          type: 'category',
          data: cats,
          axisLabel: { rotate: 45, fontSize: 10 },
          name: 'Features',
          nameLocation: 'middle',
          nameGap: 40
        },
        yAxis: {
          type: 'value',
          name: 'Coefficient (abs)',
          nameLocation: 'middle',
          nameGap: 45
        },
        series: [{
          type: 'bar',
          data: vals,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#8b5cf6' },
              { offset: 1, color: '#6d28d9' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}',
            fontSize: 10
          }
        }]
      });
    } else {
      chart.setOption({
        title: [
          { text: title, left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 'bold' } },
          { text: subtitle, left: 'center', top: 30, textStyle: { fontSize: 11, color: '#666' } }
        ],
        tooltip: {
          formatter: function (params) {
            return `<div style="padding:8px">
              <strong>Purchase Probability / Xác suất mua hàng</strong><br/>
              Score: <strong>${params.value}%</strong><br/>
              <span style="color:#666;font-size:11px">Likelihood of purchase / Khả năng mua hàng</span>
            </div>`;
          }
        },
        grid: { left: 60, right: 30, bottom: 40, top: 70 },
        xAxis: { type: 'category', data: ['Probability'] },
        yAxis: { type: 'value', max: 100, name: 'Percentage (%)' },
        series: [{
          type: 'bar',
          data: [Math.round((score || 0) * 10000) / 100],
          itemStyle: { color: '#f59e0b' },
          label: { show: true, position: 'top', formatter: '{c}%' }
        }]
      });
    }
  }
  function renderSeg(data) {
    const els = el('#ml-seg');
    if (!els) return;
    // KMeans payload: cluster_stats map keyed by cluster label -> {user_count,...}
    let cats = [], vals = [], avgEvents = [], convRates = [];
    try {
      const stats = data.cluster_stats;
      if (stats && typeof stats === 'object') {
        cats = Object.keys(stats);
        vals = cats.map(k => Number((stats[k] || {}).user_count || 0));
        avgEvents = cats.map(k => Number((stats[k] || {}).avg_events || 0));
        convRates = cats.map(k => Number((stats[k] || {}).conversion_rate || 0) * 100);
      }
    } catch { }

    const chart = echarts.init(els);
    const totalUsers = vals.reduce((a, b) => a + b, 0);

    if (cats.length) {
      chart.setOption({
        title: [
          { text: 'User Segmentation / Phân khúc người dùng', left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 'bold' } },
          { text: `Total / Tổng: ${totalUsers.toLocaleString()} users • ${cats.length} segments`, left: 'center', top: 30, textStyle: { fontSize: 11, color: '#666' } }
        ],
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            const idx = params[0].dataIndex;
            const cluster = cats[idx];
            const users = vals[idx];
            const events = avgEvents[idx] || 0;
            const conv = convRates[idx] || 0;
            const pct = totalUsers > 0 ? ((users / totalUsers) * 100).toFixed(1) : 0;

            return `<div style="padding:8px">
              <strong>Cluster ${cluster}</strong><br/>
              Users: <strong>${users.toLocaleString()}</strong> (${pct}%)<br/>
              Avg Events: <strong>${fmt(events, 1)}</strong><br/>
              Conversion Rate: <strong>${fmt(conv, 1)}%</strong><br/>
              <span style="color:#666;font-size:11px">User behavior segment / Phân nhóm hành vi khách hàng</span>
            </div>`;
          }
        },
        legend: {
          data: ['User Count', 'Avg Events', 'Conversion Rate (%)'],
          top: 55,
          textStyle: { fontSize: 11 }
        },
        grid: { left: 60, right: 80, bottom: 60, top: 100 },
        xAxis: {
          type: 'category',
          data: cats.map(c => `Cluster ${c}`),
          axisLabel: { fontSize: 11 },
          name: 'User Segments',
          nameLocation: 'middle',
          nameGap: 40
        },
        yAxis: [
          {
            type: 'value',
            name: 'User Count',
            position: 'left',
            axisLine: { show: true, lineStyle: { color: '#0891b2' } },
            axisLabel: { color: '#0891b2' }
          },
          {
            type: 'value',
            name: 'Avg Events',
            position: 'right',
            offset: 0,
            axisLine: { show: true, lineStyle: { color: '#f59e0b' } },
            axisLabel: { color: '#f59e0b' },
            splitLine: { show: false }
          },
          {
            type: 'value',
            name: 'Conv Rate (%)',
            position: 'right',
            offset: 50,
            axisLine: { show: true, lineStyle: { color: '#10b981' } },
            axisLabel: { formatter: '{value}%', color: '#10b981' },
            splitLine: { show: false }
          }
        ],
        series: [
          {
            type: 'bar',
            name: 'User Count',
            data: vals,
            yAxisIndex: 0,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#06b6d4' },
                { offset: 1, color: '#0891b2' }
              ])
            },
            label: {
              show: true,
              position: 'top',
              formatter: '{c}',
              fontSize: 10
            }
          },
          {
            type: 'line',
            name: 'Avg Events',
            data: avgEvents,
            yAxisIndex: 1,
            smooth: true,
            itemStyle: { color: '#f59e0b' },
            lineStyle: { width: 2 }
          },
          {
            type: 'line',
            name: 'Conversion Rate (%)',
            data: convRates,
            yAxisIndex: 2,
            smooth: true,
            itemStyle: { color: '#10b981' },
            lineStyle: { width: 2 }
          }
        ]
      });
    } else {
      chart.setOption({
        title: {
          text: 'No segmentation data available',
          subtext: 'Run user segmentation analysis to see clusters / Chạy phân tích để xem các nhóm',
          left: 'center',
          top: 'middle',
          textStyle: { fontSize: 14, color: '#666' },
          subtextStyle: { fontSize: 12, color: '#999' }
        }
      });
    }
  }

  async function run(fetchFresh = false) {
    const username = (userIn.value || '').trim();
    const q = new URLSearchParams(); if (username) q.set('username', username);
    let uConv = `/api/v1/spark-analytics/conversion-prediction` + (q.toString() ? `?${q.toString()}` : '');
    let uProb = `/api/v1/spark-analytics/purchase-probability` + (q.toString() ? `?${q.toString()}` : '');
    let uSeg = `/api/v1/spark-analytics/user-segmentation` + (q.toString() ? `?${q.toString()}` : '');
    if (fetchFresh) {
      const arr = [uConv, uProb, uSeg].map(withBypass);
      arr.forEach(({ clean }) => { httpCache.delete(clean); lsDel(clean); });
      [uConv, uProb, uSeg] = arr.map(x => x.fresh);
    }
    statusEl.textContent = 'Loading…';
    const [conv, prob, seg] = await Promise.all([
      fetchFresh ? safeGet(uConv) : getWithTTL(uConv, 600000),
      fetchFresh ? safeGet(uProb) : getWithTTL(uProb, 600000),
      fetchFresh ? safeGet(uSeg) : getWithTTL(uSeg, 600000)
    ]);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Always save to cache when fetching fresh data
    const payload = { conversion: conv || {}, purchase: prob || {}, segmentation: seg || {} };
    if (fetchFresh) {
      snapSet('ml', payload);
    } else {
      snapUpdate('ml', payload);
    }
    renderConv(conv || {}); renderProb(prob || {}); renderSeg(seg || {});
  }

  el('#ml-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('ml'); run(true); });
  el('#ml-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('ml'); run(true); });
  if (!snapGet('ml')) { await run(false); }
}
const view = el('#view');

// Wrapper for setActiveTab (imported from utils) that also updates state
function switchTab(name) {
  state.tab = name;
  setActiveTab(name); // From utils.js - handles UI
  // Expose for debugging
  window.journeyRun = (typeof run === 'function') ? run : undefined;
  render();
}

async function safeGet(url) {
  try {
    const key = cacheKey(url);
    if (httpCache.has(key)) return httpCache.get(key);
    const persisted = lsGet(key);
    if (persisted) {
      const data = lsData(persisted);
      httpCache.set(key, data);
      return data;
    }
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, { headers: { 'Accept': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
    lsSet(key, json);
    return json;
  } catch (e) {
    showToast(`Request failed: ${String(e)}`, 'error');
    return { error: String(e) };
  }
}

async function safePost(url, body) {
  try {
    const key = cacheKey(url + JSON.stringify(body));
    if (httpCache.has(key)) return httpCache.get(key);
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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    httpCache.set(key, json);
    // Do not lsSet for POST to avoid caching mutable operations
    return json;
  } catch (e) {
    showToast(`Request failed: ${String(e)}`, 'error');
    return { error: String(e) };
  }
}

async function preload(url) {
  const key = cacheKey(url);
  if (httpCache.has(key)) return;
  try {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(url, { headers: { 'Accept': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) } });
    if (!res.ok) return;
    const json = await res.json();
    httpCache.set(key, json);
    lsSet(key, json);
  } catch { }
}

function buildQuery() {
  const p = new URLSearchParams();
  const { range, from, to, segment, channel } = state.filters;
  // Backend expects start_date/end_date (ISO). If custom, use provided dates; else derive from preset.
  let startISO = null, endISO = null;
  if (range === 'custom' && from && to) {
    startISO = toISO(new Date(from));
    // include full day for 'to'
    const toDt = new Date(to);
    toDt.setHours(23, 59, 59, 999);
    endISO = toISO(toDt);
  } else {
    const pr = presetToDates(range);
    startISO = pr.start; endISO = pr.end;
  }
  if (startISO) p.set('date_from', startISO);
  if (endISO) p.set('date_to', endISO);
  if (segment && segment !== 'all') p.set('segment', segment);
  if (channel && channel !== 'all') p.set('channel', channel);
  return p.toString();
}

async function loadOverview() {
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
      <div class="card"><h3>Traffic Sources Trend / Xu hướng nguồn truy cập</h3><div class="chart" id="chart-trend"></div></div>
      <div class="card"><h3>User Segmentation / Phân khúc người dùng</h3><div class="chart" id="chart-seg"></div></div>
      <div class="card" style="grid-column: 1 / -1"><h3>Peaks / Đỉnh điểm</h3>
        <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">
          <div>Peak Day / Ngày cao điểm: <b id="ov-peak-day" class="muted">—</b></div>
          <div>Peak Hour / Giờ cao điểm (Users): <b id="ov-peak-hour" class="muted">—</b></div>
        </div>
        <div id="ov-peak-extra" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
          <div><div class="muted" style="margin-bottom:4px">Top Hours / Giờ phổ biến</div><ul id="ov-peak-hours-list" style="margin:0;padding-left:18px"></ul></div>
          <div><div class="muted" style="margin-bottom:4px">Top Days / Ngày phổ biến</div><ul id="ov-peak-days-list" style="margin:0;padding-left:18px"></ul></div>
        </div>
      </div>
      <div class="card"><h3>User Activity by Hour / Hoạt động theo giờ</h3><div class="chart" id="chart-hr"></div></div>
      <div class="card"><h3>User Activity by Day / Hoạt động theo ngày</h3><div class="chart" id="chart-dow"></div></div>
    </div>
  `;
  const statusEl = el('#ov-status');

  // Simplified data update function
  function updateUI(data) {
    if (!data) {
      statusEl.textContent = 'No data to display.';
      return;
    }
    // KPIs
    let kpiSessions = Number(data.total_sessions ?? 0);
    const kpiUsers = Number(data.total_users ?? 0);
    let kpiCR = Number(data.conversion_rate ?? 0);
    // Fallbacks if snapshot lacked computed fields
    if (!Number.isFinite(kpiSessions) || kpiSessions <= 0) {
      const tv = Number(data.seo_site_metrics?.total_views ?? 0);
      if (Number.isFinite(tv) && tv > 0) kpiSessions = tv;
    }
    if (!Number.isFinite(kpiCR) || kpiCR <= 0) {
      const dcr = Number(data.derived_cr ?? 0);
      if (Number.isFinite(dcr) && dcr > 0) kpiCR = dcr;
    }
    const kpiRev = Number(data.revenue ?? 0);
    // Update header quick KPIs
    el('#qk-sessions') && (el('#qk-sessions').textContent = fmt(Number.isFinite(kpiSessions) ? kpiSessions : 0));
    el('#qk-cr') && (el('#qk-cr').textContent = `${fmt(Number.isFinite(kpiCR) ? kpiCR * 100 : 0, 2)}%`);
    // AOV header
    try {
      const aov = Number(data.aov ?? 0);
      const aovEl = el('#qk-aov');
      if (aovEl) { aovEl.textContent = aov > 0 ? fmtCurrency(aov) : '—'; }
    } catch { }
    // Update Overview card KPIs
    el('#ov-sessions') && (el('#ov-sessions').textContent = fmt(Number.isFinite(kpiSessions) ? kpiSessions : 0));
    el('#ov-users') && (el('#ov-users').textContent = fmt(Number.isFinite(kpiUsers) ? kpiUsers : 0));
    el('#ov-cr') && (el('#ov-cr').textContent = `${fmt(Number.isFinite(kpiCR) ? kpiCR * 100 : 0, 2)}%`);
    // Force fill if still '—'
    const sessEl = el('#ov-sessions');
    if (sessEl && (sessEl.textContent === '—' || sessEl.textContent.trim() === '')) {
      const tv = Number(data.seo_site_metrics?.total_views ?? 0);
      if (Number.isFinite(tv) && tv > 0) { sessEl.textContent = fmt(tv); }
    }
    const crEl = el('#ov-cr');
    if (crEl && (crEl.textContent.startsWith('—') || crEl.textContent.trim() === '' || /NaN/.test(crEl.textContent))) {
      const dcr = Number(data.derived_cr ?? 0);
      if (Number.isFinite(dcr) && dcr > 0) { crEl.textContent = `${fmt(dcr * 100, 2)}%`; }
    }
    el('#ov-rev') && (el('#ov-rev').textContent = fmtCurrency(Number.isFinite(kpiRev) ? kpiRev : 0));

    // Peak labels & lists (ưu tiên dữ liệu từ activity API)
    try {
      const pd = data.peak_day || data.peak_day_label || '';
      const ph = data.peak_hour || data.peak_hour_users_label || '';
      const elPd = el('#ov-peak-day'); if (elPd) elPd.textContent = pd || '—';
      const elPh = el('#ov-peak-hour'); if (elPh) elPh.textContent = ph || '—';

      // Top Hours: ưu tiên server-side top_hours, fallback sang tự tính từ activity_hourly
      let hTop = [];
      if (Array.isArray(data.top_hours) && data.top_hours.length) {
        hTop = data.top_hours.map(h => ({
          label: String(h.label ?? (typeof h.hour === 'number' ? String(h.hour).padStart(2, '0') + ':00' : '')),
          v: Number(h.count || 0),
          pct: Number(h.pct || 0)
        }));
      } else {
        const hours = Array.isArray(data.activity_hourly) ? data.activity_hourly : [];
        const hTotal = hours.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
        hTop = hours.map((v, i) => ({ label: String(i).padStart(2, '0') + ':00', v: Number(v) || 0, pct: ((Number(v) || 0) * 100) / hTotal }))
          .sort((a, b) => b.v - a.v).slice(0, 3);
      }
      const hEl = el('#ov-peak-hours-list');
      if (hEl) { hEl.innerHTML = hTop.length ? hTop.map(x => `<li>${x.label}: ${fmt(x.v)} (${x.pct.toFixed(1)}%)</li>`).join('') : '<li class="muted">—</li>'; }

      // Top Days: ưu tiên server-side top_days, fallback sang tự tính từ by_date
      let dTop = [];
      if (Array.isArray(data.top_days) && data.top_days.length) {
        const dTotal = data.top_days.reduce((a, b) => a + (Number(b?.count) || 0), 0) || 1;
        dTop = data.top_days.map(r => ({
          label: String(r.date || ''),
          v: Number(r.count) || 0,
          pct: ((Number(r.count) || 0) * 100) / dTotal
        }));
      } else {
        const byDate = Array.isArray(data.by_date) ? data.by_date : [];
        const dTotal = byDate.reduce((a, b) => a + (Number(b?.count) || 0), 0) || 1;
        dTop = byDate.map(r => ({ label: String(r.date || ''), v: Number(r.count) || 0, pct: ((Number(r.count) || 0) * 100) / dTotal }))
          .sort((a, b) => b.v - a.v).slice(0, 3);
      }
      const dEl = el('#ov-peak-days-list');
      if (dEl) { dEl.innerHTML = dTop.length ? dTop.map(x => `<li>${x.label}: ${fmt(x.v)} (${x.pct.toFixed(1)}%)</li>`).join('') : '<li class="muted">—</li>'; }
    } catch { }

    // Trend chart
    const trendEl = el('#chart-trend');
    if (trendEl && data.traffic_trend?.categories?.length) {
      const chart = echarts.init(trendEl);
      chart.setOption({
        tooltip: {},
        legend: { data: data.traffic_trend.series.map(s => s.name) },
        xAxis: { type: 'category', data: data.traffic_trend.categories },
        yAxis: { type: 'value', axisLabel: { formatter: (v) => fmtShort(v) } },
        series: data.traffic_trend.series
      });
    } else if (trendEl) {
      trendEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
    }

    // Segmentation chart
    const segEl = el('#chart-seg');
    if (segEl && data.segments?.categories?.length && data.segments.series?.[0]?.data) {
      const seg = echarts.init(segEl);
      seg.setOption({
        tooltip: {},
        xAxis: { type: 'category', data: data.segments.categories },
        yAxis: { type: 'value', axisLabel: { formatter: (v) => fmtShort(v) } },
        series: [{ type: 'bar', name: 'Users', data: data.segments.series[0].data }]
      });
    } else if (segEl) {
      segEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
    }

    // Activity by Hour chart
    try {
      const hrEl = el('#chart-hr');
      const arr = Array.isArray(data.activity_hourly) ? data.activity_hourly : [];
      if (hrEl) {
        if (arr.length === 24) {
          const labels = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0') + ':00');
          const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(hrEl);
          if (prev) { prev.dispose(); }
          const c = echarts.init(hrEl);
          c.setOption({ tooltip: {}, xAxis: { type: 'category', data: labels }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: arr }] });
        } else {
          hrEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
        }
      }
    } catch { }

    // Activity by Day chart: ưu tiên theo từng ngày trong khoảng lọc (by_date), fallback theo thứ trong tuần
    try {
      const dwEl = el('#chart-dow');
      if (dwEl) {
        const byDate = Array.isArray(data.by_date) ? data.by_date : [];
        const hasByDate = byDate.length > 0;
        const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(dwEl);
        if (prev) { prev.dispose(); }
        if (hasByDate) {
          const labels = byDate.map(r => String(r.date || ''));
          const vals = byDate.map(r => Number(r.count) || 0);
          const c = echarts.init(dwEl);
          c.setOption({
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: labels, axisLabel: { rotate: 45 } },
            yAxis: { type: 'value' },
            series: [{ type: 'bar', data: vals }]
          });
        } else {
          const arr = Array.isArray(data.activity_dow) ? data.activity_dow : [];
          if (arr.length === 7) {
            const labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const c = echarts.init(dwEl);
            c.setOption({ tooltip: {}, xAxis: { type: 'category', data: labels }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: arr }] });
          } else {
            dwEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>';
          }
        }
      }
    } catch { }
  }

  // Restore from snapshot if available
  const snap = snapGet('overview');
  if (snap) {
    updateUI(snap);
    statusEl.textContent = 'Restored from cache';
    // If critical KPIs missing in snapshot, do an immediate fresh run; else refresh in background
    const missingCritical = !(Number.isFinite(Number(snap.total_sessions))) || !(Number.isFinite(Number(snap.total_users)));
    // Do not auto-refresh; user actions (Load/Refresh) will fetch and update cache
  }

  async function run(fetchFresh = false) {
    const q = buildQuery();
    let bizUrl = `/api/v1/metrics/business?${q}`;
    let seoUrl = `/api/v1/analytics/seo?${q}`;
    let jnUrl = `/api/v1/analytics/journey?${q}`;
    const tzOff = new Date().getTimezoneOffset();
    let actUrl = `/api/v1/events/activity?${q}&tz_offset_minutes=${encodeURIComponent(tzOff)}`;
    if (fetchFresh) {
      const arr = [bizUrl, seoUrl, jnUrl, actUrl].map(withBypass);
      arr.forEach(({ clean }) => { httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); });
      [bizUrl, seoUrl, jnUrl, actUrl] = arr.map(x => x.fresh);
    }
    statusEl.textContent = 'Loading…';
    const business = await safeGet(bizUrl);
    const seo = await safeGet(seoUrl);
    const journey = await safeGet(jnUrl);
    const activity = await safeGet(actUrl);
    // Fetch recent sessions to build user activity histograms
    let recent = null;
    try {
      let recUrl = '/api/v1/events/sessions/recent?limit=500';
      if (fetchFresh) {
        const b = withBypass(recUrl);
        httpCache.delete(cacheKey(b.clean));
        lsDel(cacheKey(b.clean));
        recUrl = b.fresh;
        recent = await safeGet(recUrl);
        console.debug('Recent sessions (fresh) fetched', { count: Array.isArray(recent?.items) ? recent.items.length : (Array.isArray(recent?.sessions) ? recent.sessions.length : 0) });
      } else {
        recent = await getWithTTL(recUrl, 600000);
        console.debug('Recent sessions (ttl) fetched', { count: Array.isArray(recent?.items) ? recent.items.length : (Array.isArray(recent?.sessions) ? recent.sessions.length : 0) });
      }
    } catch { }
    // Guard: require SEO to succeed for charts; continue if business/journey fail
    if (seo?.error) {
      statusEl.textContent = `Error: ${seo?.error}`;
      showToast('Overview load failed (SEO). Using cached data if available.', 'error');
      const snapErr = snapGet('overview');
      if (snapErr) updateUI(snapErr);
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

    // Derive conversion rate and purchases from journey funnel when missing
    let derivedCR = null;
    let derivedPurchases = null;
    try {
      const jf = journey && journey.funnel;
      if (jf) {
        if (Array.isArray(jf.steps)) {
          const views = jf.steps.find(s => /(view|views)/i.test(String(s.name || s.step || '')));
          const purch = jf.steps.find(s => /purchase/i.test(String(s.name || s.step || '')));
          const v = (views?.value ?? views?.count ?? 0);
          const p = (purch?.value ?? purch?.count ?? 0);
          derivedCR = v ? (p / v) : 0;
          derivedPurchases = Number(p) || 0;
        } else if (typeof jf === 'object') {
          const v = Number(jf.Views ?? jf.views ?? jf.view ?? 0) || 0;
          const p = Number(jf.Purchase ?? jf.purchase ?? 0) || 0;
          derivedCR = v ? (p / v) : 0;
          derivedPurchases = Number(p) || 0;
        }
      }
    } catch { }

    // Derive sessions from SEO timeseries if needed
    let derivedSessions = 0;
    try {
      if (Array.isArray(seo?.timeseries)) {
        for (const r of seo.timeseries) {
          const a = Number(r.seo ?? r.SEO ?? 0) || 0;
          const b = Number(r.direct ?? r.Direct ?? 0) || 0;
          const c = Number(r.social ?? r.Social ?? 0) || 0;
          derivedSessions += a + b + c;
        }
      }
    } catch { }

    // Traffic trend fallback from seo.timeseries when needed
    let trafficTrend = seo.traffic_trend;
    if (!trafficTrend && Array.isArray(seo?.timeseries)) {
      const categories = seo.timeseries.map(r => r.date || r.time || '');
      const build = (k) => seo.timeseries.map(r => Number(r[k] ?? r[k?.toUpperCase()] ?? 0) || 0);
      trafficTrend = {
        categories,
        series: [
          { name: 'SEO', type: 'line', data: build('seo') },
          { name: 'Direct', type: 'line', data: build('direct') },
          { name: 'Social', type: 'line', data: build('social') },
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
    // Compute AOV: prefer business.orders/purchases, fallback to derivedPurchases from journey
    const orders = Number(business.orders ?? business.purchases ?? 0) || 0;
    const effOrders = orders > 0 ? orders : (Number.isFinite(derivedPurchases) ? derivedPurchases : 0);
    const aovVal = (Number(revenueVal) > 0 && effOrders > 0) ? (Number(revenueVal) / effOrders) : 0;

    const data = {
      total_sessions: (Number.isFinite(totalSessions) && totalSessions > 0)
        ? totalSessions
        : Number(seoSite.total_views ?? derivedSessions ?? 0) || 0,
      total_users: (Number.isFinite(totalUsers) && totalUsers > 0)
        ? totalUsers
        : Number(seoSite.unique_visitors ?? 0) || 0,
      conversion_rate: finalCR,
      revenue: revenueVal,
      aov: aovVal,
      traffic_trend: trafficTrend ?? { categories: [], series: [] },
      segments: business.segments ?? segFromSeo,
      seo_site_metrics: seoSite,
      derived_cr: finalCR
    };

    // Prefer server-side activity histograms aligned to filter window
    try {
      const hh = Array.isArray(activity?.hourly) ? activity.hourly : null;
      const dd = Array.isArray(activity?.dow) ? activity.dow : null;
      if (hh && hh.length === 24) data.activity_hourly = hh;
      if (dd && dd.length === 7) data.activity_dow = dd;
      // Prefer server-provided by_date and peak_day; override snapshot/trend
      if (Array.isArray(activity?.by_date)) data.by_date = activity.by_date;
      if (activity?.peak_day) data.peak_day_label = String(activity.peak_day);
      // Always recompute peak hour from hourly if present
      if (Array.isArray(data.activity_hourly) && data.activity_hourly.length === 24) {
        let idx = 0, best = -1; for (let i = 0; i < 24; i++) { const v = Number(data.activity_hourly[i] || 0); if (v > best) { best = v; idx = i; } }
        data.peak_hour_users_label = String(idx).padStart(2, '0') + ':00';
      }
    } catch { }

    // Build activity histograms from recent sessions (fallback-only when API histograms missing)
    try {
      // Chỉ dùng fallback nếu API không trả về histogram đầy đủ
      const hasApiHourly = Array.isArray(data.activity_hourly) && data.activity_hourly.length === 24;
      const hasApiDow = Array.isArray(data.activity_dow) && data.activity_dow.length === 7;
      if (!hasApiHourly || !hasApiDow) {
        const items = Array.isArray(recent?.items) ? recent.items : (Array.isArray(recent?.sessions) ? recent.sessions : []);
        if (items && items.length) {
          console.debug('Building activity histograms from recent sessions (fallback)', { sample: items[0] });
          const hourly = Array(24).fill(0);
          const dow = Array(7).fill(0);
          for (const s of items) {
            const raw = s.first_event_at || s.last_event_at || s.last_event || s.start_time || s.end_time || s.ts || null;
            if (raw == null) continue;
            let d;
            if (typeof raw === 'number') {
              const ms = raw > 1e12 ? raw : raw * 1000;
              d = new Date(ms);
            } else if (typeof raw === 'string' && /^\d+$/.test(raw)) {
              const num = Number(raw);
              const ms = num > 1e12 ? num : num * 1000;
              d = new Date(ms);
            } else {
              d = new Date(raw);
            }
            if (isFinite(d.getTime())) {
              hourly[d.getHours()] += 1;
              dow[d.getDay()] += 1;
            }
          }
          if (!hasApiHourly && hourly.some(v => v > 0)) data.activity_hourly = hourly;
          if (!hasApiDow && dow.some(v => v > 0)) data.activity_dow = dow;
          console.debug('Histogram fallback built', { hourlyNonZero: hourly.filter(v => v > 0).length, dow, peakHour: data.peak_hour_users_label });
          // Nếu đang dùng fallback (không có peak từ API) thì tính peak hour từ histogram fallback
          if (!data.peak_hour_users_label && hourly.some(v => v > 0)) {
            let idx = 0; let best = -1; for (let i = 0; i < 24; i++) { if (hourly[i] > best) { best = hourly[i]; idx = i; } }
            data.peak_hour_users_label = String(idx).padStart(2, '0') + ':00';
          }
        }
      }
    } catch { }

    // Compute peaks from traffic trend chỉ khi chưa có dữ liệu từ activity API
    try {
      if (!data.peak_day && !data.peak_day_label && !data.peak_hour && !data.peak_hour_users_label) {
        const tt = data.traffic_trend;
        const cats = Array.isArray(tt?.categories) ? tt.categories : [];
        const series = Array.isArray(tt?.series) ? tt.series : [];
        if (cats.length && series.length) {
          const sums = cats.map((_, i) => series.reduce((acc, s) => acc + (Number(s?.data?.[i] ?? 0) || 0), 0));
          // Peak Day (by sessions)
          let peakDayIdx = -1, peakDayVal = -1;
          for (let i = 0; i < sums.length; i++) { if (sums[i] > peakDayVal) { peakDayVal = sums[i]; peakDayIdx = i; } }
          if (peakDayIdx >= 0) { data.peak_day_label = String(cats[peakDayIdx]); }
          // Peak Hour (Users proxy): only if category includes hour info (e.g., contains ':')
          const hasHour = cats.some(c => /\d{1,2}:\d{2}/.test(String(c)) || /T\d{2}:\d{2}/.test(String(c)));
          if (hasHour) {
            let peakHourIdx = -1, peakHourVal = -1;
            for (let i = 0; i < sums.length; i++) { if (sums[i] > peakHourVal) { peakHourVal = sums[i]; peakHourIdx = i; } }
            if (peakHourIdx >= 0) { data.peak_hour_users_label = String(cats[peakHourIdx]); }
          }
        }
      }
    } catch { }

    // Always save to cache when fetching fresh data
    if (fetchFresh) {
      snapSet('overview', data);
    } else {
      snapUpdate('overview', data);
    }
    updateUI(data);
  }

  el('#ov-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('overview'); run(true); });
  el('#ov-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('overview'); run(true); });

  // Auto-fetch on first visit if there is no snapshot
  if (!snap) {
    await run(false);
  }
}

async function renderCart() {
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="cart-load" class="tab">Load</button>
      <button id="cart-refresh" class="tab">Refresh</button>
      <span id="cart-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Abandonment by Channel / Tỷ lệ bỏ giỏ theo kênh</h3><div class="chart" id="chart-ab"></div></div>
      <div class="card"><h3>Cart Size Distribution / Phân phối kích thước giỏ hàng</h3><div class="chart" id="chart-dist"></div></div>
    </div>
  `;
  const statusEl = el('#cart-status');
  // Restore snapshot
  (function () {
    const snap = snapGet('cart');
    if (!snap) return;
    // Abandonment chart
    const channels = (snap.channels && Object.keys(snap.channels)) || [];
    const abData = channels.map(c => typeof snap.channels?.[c]?.abandonment_rate === 'number' ? Math.round(snap.channels[c].abandonment_rate * 1000) / 10 : null);
    const abEl = el('#chart-ab');
    if (abEl && abData.length) { const ab = echarts.init(abEl); ab.setOption({ tooltip: { trigger: 'axis' }, legend: { data: ['Abandonment %'] }, xAxis: { type: 'category', data: channels }, yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } }, series: [{ name: 'Abandonment %', type: 'bar', data: abData }] }); }
    // Size distribution
    const distEl = el('#chart-dist'); const distCats = ['1', '2', '3', '4', '5+'];
    if (Array.isArray(snap.size_distribution)) {
      const map = new Map(snap.size_distribution.map(r => [String(r.size), r.count]));
      const distData = distCats.map(k => map.get(k) ?? 0);
      if (distEl) { const chart = echarts.init(distEl); chart.setOption({ tooltip: {}, xAxis: { type: 'category', data: distCats }, yAxis: { type: 'value' }, series: [{ type: 'line', data: distData }] }); }
    }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh = false) {
    const q = buildQuery();
    let urlA = `/api/v1/analytics/cart?${q}`;
    let urlT = `/api/v1/cart/trends?${q}`;
    if (fetchFresh) { const a = withBypass(urlA), b = withBypass(urlT);[a, b].forEach(({ clean }) => { httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); }); urlA = a.fresh; urlT = b.fresh; }
    statusEl.textContent = 'Loading…';
    const analysis = await safeGet(urlA);
    const trends = await safeGet(urlT);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Cart (fresh only or if missing)
    // Always save to cache when fetching fresh data
    const payload = { channels: analysis?.channels ?? {}, size_distribution: analysis?.size_distribution ?? [] };
    if (fetchFresh) {
      snapSet('cart', payload);
    } else {
      snapUpdate('cart', payload);
    }

    // Abandonment by channel
    const channels = (analysis.channels && Object.keys(analysis.channels)) || [];
    const abData = channels.map(c => {
      const v = analysis.channels?.[c]?.abandonment_rate;
      return typeof v === 'number' ? Math.round(v * 1000) / 10 : null;
    });
    const abEl = el('#chart-ab');
    if (abEl && abData.length) {
      const ab = echarts.init(abEl);
      ab.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['Abandonment %'] },
        xAxis: { type: 'category', data: channels },
        yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
        series: [{ name: 'Abandonment %', type: 'bar', data: abData }]
      });
    } else if (abEl) { abEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

    // Cart size distribution
    const distEl = el('#chart-dist');
    const distCats = ['1', '2', '3', '4', '5+'];
    let distData = [];
    if (analysis.size_distribution && Array.isArray(analysis.size_distribution)) {
      // Expect array of {size,count}
      const map = new Map();
      for (const r of analysis.size_distribution) {
        map.set(String(r.size), r.count);
      }
      distData = distCats.map(k => map.get(k) ?? 0);
    }
    if (distEl && distData.length) {
      const distChart = echarts.init(distEl);
      distChart.setOption({
        tooltip: {},
        xAxis: { type: 'category', data: distCats },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: distData }]
      });
    } else if (distEl) { distEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  }
  el('#cart-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('cart'); run(true); });
  el('#cart-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('cart'); run(true); });
  // Auto-fetch on first visit if there is no snapshot yet
  if (!snapGet('cart')) { await run(false); }
}

async function renderJourney() {
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="jn-load" type="button" class="tab">Load</button>
      <button id="jn-refresh" type="button" class="tab">Refresh</button>
      <span id="jn-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 2fr 1fr;">
      <div class="card"><h3>Funnel / Phễu chuyển đổi</h3><div class="chart" id="chart-funnel"></div></div>
      <div class="card"><h3>Top Paths (Sankey) / Luồng hành trình phổ biến</h3><div class="chart" id="chart-sankey"></div></div>
    </div>
  `;
  const statusEl = el('#jn-status');

  // Restore and render charts from cache immediately (no API call)
  // This provides instant feedback when switching tabs
  const cachedData = snapGet('journey');
  if (cachedData) {
    statusEl.textContent = 'Restored from cache';

    // Render Funnel from cache
    let funnelData = [];
    if (cachedData.funnel && Array.isArray(cachedData.funnel.steps)) {
      funnelData = cachedData.funnel.steps.map(s => ({ name: s.name || s.step || '', value: s.value || s.count || 0 }));
    } else if (cachedData.funnel && typeof cachedData.funnel === 'object') {
      funnelData = Object.entries(cachedData.funnel).map(([name, value]) => ({ name, value }));
    }

    if (funnelData.length) {
      const funnelEl = el('#chart-funnel');
      if (funnelEl) {
        const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(funnelEl);
        if (prev) prev.dispose();
        const funnel = echarts.init(funnelEl);

        const totalUsers = funnelData[0]?.value || 0;
        const enrichedData = funnelData.map((step, idx) => {
          const conversionRate = totalUsers > 0 ? (step.value / totalUsers * 100) : 0;
          const dropOff = idx > 0 ? ((funnelData[idx - 1].value - step.value) / funnelData[idx - 1].value * 100) : 0;
          return { ...step, conversionRate, dropOff, index: idx };
        });

        funnel.setOption({
          title: {
            text: 'Conversion Funnel',
            subtext: `Total Users: ${totalUsers.toLocaleString()}`,
            left: 'center', top: 10,
            textStyle: { fontSize: 14, fontWeight: 'bold' },
            subtextStyle: { fontSize: 11, color: '#666' }
          },
          tooltip: { trigger: 'item' },
          series: [{ type: 'funnel', data: funnelData }]
        });
      }
    }

    // Render Sankey from cache
    let nodes = [], links = [];
    if (cachedData.paths?.links) {
      links = cachedData.paths.links;
      nodes = cachedData.paths.nodes || Array.from(new Set(links.flatMap(l => [l.source, l.target])));
    }

    if (nodes.length && links.length) {
      const sankeyEl = el('#chart-sankey');
      if (sankeyEl) {
        const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(sankeyEl);
        if (prev) prev.dispose();
        const sankey = echarts.init(sankeyEl);
        const totalFlow = links.reduce((sum, link) => sum + (link.value || 0), 0);

        sankey.setOption({
          animation: false,
          title: {
            text: 'User Journey Paths',
            subtext: `${nodes.length} stages, ${links.length} transitions`,
            left: 'center', top: 10,
            textStyle: { fontSize: 14, fontWeight: 'bold' },
            subtextStyle: { fontSize: 11, color: '#666' }
          },
          tooltip: { trigger: 'item' },
          series: [{ type: 'sankey', data: nodes.map(n => ({ name: n })), links }]
        });
      }
    }
  }

  async function run(fetchFresh = false) {
    const q = buildQuery();
    let url = `/api/v1/analytics/journey?${q}`;
    if (fetchFresh) { const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    let journey = null;
    try {
      journey = fetchFresh ? (await safeGet(url)) : (await getWithTTL(url, 600000));
    } catch (e) { console.debug('Journey fetch error', e); }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Do not persist raw API shape; we'll persist processed nodes/links below

    // Funnel data
    let funnelData = [];
    if (journey) {
      // common shapes: journey.funnel.steps = [{name,value}] or journey.funnel = {Landing: n, ...}
      if (journey.funnel && Array.isArray(journey.funnel.steps)) {
        funnelData = journey.funnel.steps.map(s => ({ name: s.name || s.step || '', value: s.value || s.count || 0 }));
      } else if (journey.funnel && typeof journey.funnel === 'object') {
        funnelData = Object.entries(journey.funnel).map(([name, value]) => ({ name, value }));
      }
    }
    const funnelEl = el('#chart-funnel');
    if (funnelEl && funnelData.length) {
      const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(funnelEl);
      if (prev) { prev.dispose(); }
      const funnel = echarts.init(funnelEl);

      // Calculate conversion rates and drop-off
      const totalUsers = funnelData[0]?.value || 0;
      const enrichedData = funnelData.map((step, idx) => {
        const conversionRate = totalUsers > 0 ? (step.value / totalUsers * 100) : 0;
        const dropOff = idx > 0 ? ((funnelData[idx - 1].value - step.value) / funnelData[idx - 1].value * 100) : 0;
        return {
          ...step,
          conversionRate,
          dropOff,
          index: idx
        };
      });

      funnel.setOption({
        title: {
          text: 'Conversion Funnel',
          subtext: `Total Users: ${totalUsers.toLocaleString()}`,
          left: 'center',
          top: 10,
          textStyle: { fontSize: 14, fontWeight: 'bold' },
          subtextStyle: { fontSize: 11, color: '#666' }
        },
        tooltip: {
          trigger: 'item',
          formatter: function (params) {
            const data = enrichedData[params.dataIndex];
            const nextStep = enrichedData[params.dataIndex + 1];
            const dropOffToNext = nextStep ? ((data.value - nextStep.value) / data.value * 100) : 0;

            return `<div style="padding:8px">
              <strong>${params.name}</strong><br/>
              Users: <strong>${params.value.toLocaleString()}</strong><br/>
              Conversion Rate: <strong>${data.conversionRate.toFixed(1)}%</strong><br/>
              ${data.index > 0 ? `Drop-off from previous: <strong style="color:#ef4444">${data.dropOff.toFixed(1)}%</strong><br/>` : ''}
              ${nextStep ? `Drop-off to next: <strong style="color:#ef4444">${dropOffToNext.toFixed(1)}%</strong><br/>` : ''}
              <span style="color:#666;font-size:11px">Stage ${data.index + 1} of ${funnelData.length}</span>
            </div>`;
          }
        },
        legend: {
          show: false
        },
        grid: {
          left: 60,
          right: 60,
          top: 80,
          bottom: 40
        },
        series: [{
          type: 'funnel',
          data: funnelData,
          label: {
            show: true,
            position: 'inside',
            formatter: function (params) {
              const data = enrichedData[params.dataIndex];
              return `${params.name}\\n${params.value.toLocaleString()} (${data.conversionRate.toFixed(1)}%)`;
            },
            fontSize: 11,
            color: '#fff'
          },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
            color: function (params) {
              const colors = [
                new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#3b82f6' },
                  { offset: 1, color: '#1d4ed8' }
                ]),
                new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#8b5cf6' },
                  { offset: 1, color: '#6d28d9' }
                ]),
                new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#f59e0b' },
                  { offset: 1, color: '#d97706' }
                ]),
                new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#10b981' },
                  { offset: 1, color: '#059669' }
                ])
              ];
              return colors[params.dataIndex % colors.length];
            }
          },
          emphasis: {
            label: {
              fontSize: 12,
              fontWeight: 'bold'
            }
          }
        }]
      });
      requestAnimationFrame(() => { try { funnel.resize(); } catch { } });
    } else if (funnelEl) { funnelEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

    // Sankey data
    let nodes = [];
    let links = [];
    if (journey) {
      // Prefer paths if present
      if (journey.paths) {
        if (Array.isArray(journey.paths.links)) {
          links = journey.paths.links;
          // Limit to Top 100 edges by value
          if (links.length > 100) { links = links.slice().sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, 100); }
          // Recompute nodes from limited links
          nodes = Array.from(new Set(links.flatMap(l => [l.source, l.target])));
        } else if (Array.isArray(journey.paths)) {
          links = journey.paths;
          if (links.length > 100) { links = links.slice().sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, 100); }
          nodes = Array.from(new Set(links.flatMap(l => [l.source, l.target])));
        }
      }
      // Fallback to top_paths (array of links) if paths missing
      if (!links.length && Array.isArray(journey.top_paths) && journey.top_paths.length) {
        links = journey.top_paths;
        if (links.length > 100) { links = links.slice().sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, 100); }
        nodes = Array.from(new Set(links.flatMap(l => [l.source, l.target])));
      }
    }
    // Final fallback: synthesize links from funnel steps when API links are missing
    if (!links.length && Array.isArray(funnelData) && funnelData.length > 1) {
      try {
        const steps = funnelData
          .map(s => ({ name: String(s.name || '').trim() || 'Step', value: Number(s.value || 0) }))
          .filter(s => s.name && isFinite(s.value));
        const syn = [];
        for (let i = 0; i < steps.length - 1; i++) {
          const a = steps[i];
          const b = steps[i + 1];
          const v = isFinite(b.value) && b.value > 0 ? b.value : Math.max(0, Math.min(a.value || 0, b.value || 0));
          syn.push({ source: a.name, target: b.name, value: v });
        }
        if (syn.length) {
          links = syn;
          nodes = Array.from(new Set(links.flatMap(l => [l.source, l.target])));
        }
      } catch { }
    }
    // Persist latest payload - always save when fetchFresh=true
    try {
      const payload = { funnel: journey?.funnel ?? null, paths: { nodes, links } };
      if (fetchFresh) {
        snapSet('journey', payload);
      } else {
        snapUpdate('journey', payload);
      }
    } catch { }
    const sankeyEl = el('#chart-sankey');
    if (sankeyEl && nodes.length && links.length) {
      const currHash = JSON.stringify({ nodes, links });
      const prev = (echarts.getInstanceByDom && echarts.getInstanceByDom(sankeyEl)) || null;
      if (!prev || window.__jnSankeyHash !== currHash) {
        if (prev) { prev.dispose(); }
        sankeyEl.innerHTML = '';
        const sankey = echarts.init(sankeyEl);

        // Calculate total flow for percentage calculations
        const totalFlow = links.reduce((sum, link) => sum + (link.value || 0), 0);

        sankey.setOption({
          animation: false,
          title: {
            text: 'User Journey Paths',
            subtext: `${nodes.length} stages, ${links.length} transitions`,
            left: 'center',
            top: 10,
            textStyle: { fontSize: 14, fontWeight: 'bold' },
            subtextStyle: { fontSize: 11, color: '#666' }
          },
          tooltip: {
            trigger: 'item',
            formatter: function (params) {
              if (params.dataType === 'edge') {
                const pct = totalFlow > 0 ? (params.value / totalFlow * 100) : 0;
                return `<div style="padding:8px">
                  <strong>${params.data.source}</strong> → <strong>${params.data.target}</strong><br/>
                  Users: <strong>${params.value.toLocaleString()}</strong><br/>
                  Flow: <strong>${pct.toFixed(1)}%</strong> of total<br/>
                  <span style="color:#666;font-size:11px">User transition between stages</span>
                </div>`;
              } else {
                // Node tooltip
                const nodeLinks = links.filter(l => l.source === params.name || l.target === params.name);
                const inFlow = nodeLinks.filter(l => l.target === params.name).reduce((sum, l) => sum + (l.value || 0), 0);
                const outFlow = nodeLinks.filter(l => l.source === params.name).reduce((sum, l) => sum + (l.value || 0), 0);
                return `<div style="padding:8px">
                  <strong>${params.name}</strong><br/>
                  Incoming: <strong>${inFlow.toLocaleString()}</strong> users<br/>
                  Outgoing: <strong>${outFlow.toLocaleString()}</strong> users<br/>
                  <span style="color:#666;font-size:11px">Journey stage</span>
                </div>`;
              }
            }
          },
          grid: {
            top: 70,
            bottom: 20
          },
          series: [{
            type: 'sankey',
            data: nodes.map(n => ({ name: n })),
            links: links,
            emphasis: {
              focus: 'adjacency'
            },
            lineStyle: {
              color: 'gradient',
              curveness: 0.5
            },
            label: {
              fontSize: 11,
              color: '#333'
            }
          }]
        });
        window.__jnSankeyHash = currHash;
        requestAnimationFrame(() => { try { sankey.resize(); } catch { } });
        console.debug('Journey Sankey rendered', { nodeCount: nodes.length, linkCount: links.length });
      }
    } else if (sankeyEl) { sankeyEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
    if (!(nodes.length && links.length)) {
      console.debug('Journey Sankey empty', { nodes, links });
      statusEl.textContent = 'No path data';
    }
  }
  // Ensure buttons are clickable
  const jnLoadBtn = el('#jn-load');
  const jnRefBtn = el('#jn-refresh');
  const runDeb = debounce((fresh) => run(fresh), 700);
  if (jnLoadBtn) {
    jnLoadBtn.disabled = false; jnLoadBtn.style.pointerEvents = 'auto'; jnLoadBtn.style.cursor = 'pointer'; jnLoadBtn.style.zIndex = 10; jnLoadBtn.style.position = 'relative';
    const handler = () => { console.debug('Journey: Load clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('journey'); runDeb(true); };
    jnLoadBtn.addEventListener('click', handler, { capture: true });
  }
  if (jnRefBtn) {
    jnRefBtn.disabled = false; jnRefBtn.style.pointerEvents = 'auto'; jnRefBtn.style.cursor = 'pointer'; jnRefBtn.style.zIndex = 10; jnRefBtn.style.position = 'relative';
    const handler = () => { console.debug('Journey: Refresh clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('journey'); runDeb(true); };
    jnRefBtn.addEventListener('click', handler, { capture: true });
  }
  // Don't auto-call run() - charts already rendered from cache above
  // User can click Load/Refresh to fetch fresh data
  // Expose for console-driven testing
  window.journeyRun = run;
}

async function renderReco() {
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

  function skeleton() {
    grid.innerHTML = Array.from({ length: 6 }, () => `<div class="card skel" style="height:120px"></div>`).join('');
  }

  const productCache = new Map(); // pid -> product doc

  async function renderItems(items) {
    if (!Array.isArray(items) || !items.length) {
      grid.innerHTML = `<div class="muted" style="padding:8px">Không có gợi ý.</div>`;
      return;
    }

    // Thu thập danh sách product_id duy nhất để enrich tên, category, giá
    const ids = new Set();
    for (const it of items) {
      const pid = it.product_id || it.productId || it.id;
      if (pid) ids.add(String(pid));
    }

    try {
      const fetches = [];
      for (const pid of ids) {
        if (productCache.has(pid)) continue;
        fetches.push((async () => {
          try {
            const prod = await safeGet(`/api/product/${encodeURIComponent(pid)}`);
            if (prod && prod._id) { productCache.set(pid, prod); }
          } catch {
            // best-effort: nếu fail thì cứ để cache trống, UI sẽ fallback sang id
          }
        })());
      }
      if (fetches.length) { await Promise.all(fetches); }
    } catch { }

    grid.innerHTML = items.map(it => {
      const pid = String(it.product_id || it.productId || it.id || '');
      const prod = productCache.get(pid) || null;
      const title = prod?.name || it.title || it.name || it.product_name || pid;
      const category = prod?.category || it.category || '';
      // Ưu tiên hiện relevance/confidence nếu có, fallback sang score
      let scoreText = '';
      if (typeof it.relevance_score === 'number') {
        scoreText = `Relevance: ${it.relevance_score.toFixed(1)}`;
      } else if (typeof it.confidence_score === 'number') {
        scoreText = `Confidence: ${it.confidence_score.toFixed(2)}`;
      } else if (typeof it.score === 'number') {
        scoreText = `Score: ${it.score.toFixed(3)}`;
      }
      const priceVal = prod?.price ?? it.price;
      const price = priceVal != null ? fmtCurrency(Number(priceVal)) : '';
      const reason = it.reason || '';
      return `<div class="card">
        <h3>${title}</h3>
        <div class="muted">${category || (reason || '')}</div>
        <div class="muted">${scoreText}</div>
        <div>${price}</div>
      </div>`;
    }).join('');
  }

  async function load() {
    try {
      skeleton();
      const limit = Number(limitSel.value || '10');
      let data = [];
      if (modeSel.value === 'personalized') {
        const uid = userIn.value.trim();
        const q = new URLSearchParams(); if (uid) q.set('user_id', uid); q.set('limit', String(limit));
        const res = await safeGet(`/api/v1/recommendations/personalized?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
        // Save snapshot for personalized: only store recommendations array from first entry
        const recs = Array.isArray(data) && data[0]?.recommendations ? data[0].recommendations : [];
        snapMaybe('reco:personalized', { user_id: uid || null, items: recs });
        await renderItems(recs);
        return;
      } else {
        const tf = timeSel.value;
        const q = new URLSearchParams({ timeframe: tf, limit: String(limit) });
        const res = await safeGet(`/api/v1/recommendations/trending?${q.toString()}`);
        data = Array.isArray(res) ? res : (res.items || []);
        // Save snapshot for trending keyed by timeframe
        snapMaybe(`reco:trending:${tf}`, { items: data });
      }
      await renderItems(data);
    } catch (e) {
      showToast('Recommendation load failed', 'error');
    }
  }

  modeSel.addEventListener('change', () => {
    const trending = modeSel.value === 'trending';
    timeSel.style.display = trending ? '' : 'none';
    userIn.style.display = trending ? 'none' : '';
  });
  // Ensure we clear all reco snapshots (both personalized and trending variants)
  runBtn.addEventListener('click', () => {
    clearSnapshotsForTab('reco:personalized');
    clearSnapshotsForTab('reco:trending');
    load();
  });

  // initial state
  timeSel.style.display = 'none';
  // Restore snapshot without network
  (async function () {
    const mode = 'personalized';
    const snapP = snapGet('reco:personalized');
    if (snapP && Array.isArray(snapP.items) && snapP.items.length) {
      await renderItems(snapP.items);
      return;
    }
    const snapT = snapGet('reco:trending:day');
    if (snapT && Array.isArray(snapT.items)) await renderItems(snapT.items);
  })();
  // Auto-fetch on first visit if there is no snapshot for either mode
  if (!(snapGet('reco:personalized')?.items?.length) && !(snapGet('reco:trending:day')?.items?.length)) {
    await load();
  }
}

async function renderSEO() {
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="seo-load" class="tab">Load</button>
      <button id="seo-refresh" class="tab">Refresh</button>
      <span id="seo-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Traffic Source Distribution / Phân phối nguồn truy cập</h3><div class="chart" id="chart-donut"></div></div>
      <div class="card"><h3>Traffic Trend / Xu hướng lưu lượng</h3><div class="chart" id="chart-traffic"></div></div>
    </div>
  `;
  const statusEl = el('#seo-status');

  // Restore and render charts from cache immediately (no API call)
  const cachedData = snapGet('seo');
  if (cachedData) {
    statusEl.textContent = 'Restored from cache';

    // Render Donut chart
    const donutEl = el('#chart-donut');
    let dist = [];
    if (cachedData.sources?.distribution) {
      dist = Object.entries(cachedData.sources.distribution).map(([name, value]) => ({ name, value }));
    }
    if (donutEl && dist.length) {
      const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(donutEl);
      if (prev) prev.dispose();
      const donut = echarts.init(donutEl);
      const total = dist.reduce((sum, item) => sum + (item.value || 0), 0);
      donut.setOption({
        title: {
          text: 'Traffic Sources',
          subtext: `Total: ${total.toLocaleString()} visits`,
          left: 'center', top: 10,
          textStyle: { fontSize: 14, fontWeight: 'bold' },
          subtextStyle: { fontSize: 11, color: '#666' }
        },
        tooltip: { trigger: 'item' },
        legend: { orient: 'vertical', right: 10, top: 'middle' },
        series: [{ type: 'pie', radius: ['40%', '70%'], data: dist }]
      });
    }

    // Render Traffic Trend
    const trafficEl = el('#chart-traffic');
    if (trafficEl && Array.isArray(cachedData.timeseries)) {
      const prev = echarts.getInstanceByDom && echarts.getInstanceByDom(trafficEl);
      if (prev) prev.dispose();
      const traffic = echarts.init(trafficEl);
      const categories = cachedData.timeseries.map(r => r.date || r.time || r.t || '');
      const build = k => cachedData.timeseries.map(r => r[k] ?? r[k?.toUpperCase()] ?? 0);
      const series = [
        { name: 'SEO', type: 'line', data: build('seo') },
        { name: 'Direct', type: 'line', data: build('direct') },
        { name: 'Social', type: 'line', data: build('social') }
      ];
      traffic.setOption({
        title: { text: 'Traffic Trend Over Time', left: 'center', top: 10 },
        tooltip: { trigger: 'axis' },
        legend: { data: series.map(s => s.name), top: 50 },
        xAxis: { type: 'category', data: categories },
        yAxis: { type: 'value' },
        series
      });
    }
  }

  async function run(fetchFresh = false) {
    const q = buildQuery();
    let url = `/api/v1/analytics/seo?${q}`;
    if (fetchFresh) { const b = withBypass(url); httpCache.delete(cacheKey(b.clean)); lsDel(cacheKey(b.clean)); url = b.fresh; }
    statusEl.textContent = 'Loading…';
    const seo = await safeGet(url);
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Always save to cache when fetching fresh data
    if (fetchFresh) {
      snapSet('seo', seo || {});
    } else {
      snapUpdate('seo', seo || {});
    }

    // Distribution
    const donutEl = el('#chart-donut');
    let dist = [];
    if (seo && seo.sources && seo.sources.distribution) {
      dist = Object.entries(seo.sources.distribution).map(([name, value]) => ({ name, value }));
    }
    if (donutEl && dist.length) {
      const donut = echarts.init(donutEl);
      const total = dist.reduce((sum, item) => sum + (item.value || 0), 0);

      donut.setOption({
        title: {
          text: 'Traffic Sources',
          subtext: `Total: ${total.toLocaleString()} visits`,
          left: 'center',
          top: 10,
          textStyle: { fontSize: 14, fontWeight: 'bold' },
          subtextStyle: { fontSize: 11, color: '#666' }
        },
        tooltip: {
          trigger: 'item',
          formatter: function (params) {
            const pct = params.percent;
            return `<div style="padding:8px">
              <strong>${params.name}</strong><br/>
              Visits: <strong>${params.value.toLocaleString()}</strong><br/>
              Percentage: <strong>${pct.toFixed(1)}%</strong><br/>
              <span style="color:#666;font-size:11px">Traffic source contribution</span>
            </div>`;
          }
        },
        legend: {
          orient: 'vertical',
          right: 10,
          top: 'middle',
          textStyle: { fontSize: 11 }
        },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: dist,
          label: {
            formatter: '{b}: {d}%',
            fontSize: 11
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          itemStyle: {
            color: function (params) {
              const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];
              return colors[params.dataIndex % colors.length];
            }
          }
        }]
      });
    } else if (donutEl) { donutEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }

    // Trend
    const trafficEl = el('#chart-traffic');
    let series = [];
    let categories = [];
    if (Array.isArray(seo?.timeseries)) {
      categories = seo.timeseries.map(r => r.date || r.time || r.t || '');
      const build = (key) => seo.timeseries.map(r => r[key] ?? r[key?.toUpperCase()] ?? 0);
      series = [
        { name: 'SEO', type: 'line', data: build('seo') },
        { name: 'Direct', type: 'line', data: build('direct') },
        { name: 'Social', type: 'line', data: build('social') },
      ];
    }
    if (trafficEl && categories.length && series.length) {
      const traffic = echarts.init(trafficEl);

      // Calculate totals for each source
      const totals = series.map(s => ({
        name: s.name,
        total: s.data.reduce((sum, val) => sum + val, 0)
      }));

      traffic.setOption({
        title: {
          text: 'Traffic Trend Over Time',
          subtext: totals.map(t => `${t.name}: ${t.total.toLocaleString()}`).join(' | '),
          left: 'center',
          top: 10,
          textStyle: { fontSize: 14, fontWeight: 'bold' },
          subtextStyle: { fontSize: 10, color: '#666' }
        },
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            let result = `<div style="padding:8px"><strong>${params[0].axisValue}</strong><br/>`;
            const total = params.reduce((sum, p) => sum + p.value, 0);
            params.forEach(p => {
              const pct = total > 0 ? (p.value / total * 100) : 0;
              result += `${p.marker} ${p.seriesName}: <strong>${p.value.toLocaleString()}</strong> (${pct.toFixed(1)}%)<br/>`;
            });
            result += `Total: <strong>${total.toLocaleString()}</strong></div>`;
            return result;
          }
        },
        legend: {
          data: series.map(s => s.name),
          top: 50,
          textStyle: { fontSize: 11 }
        },
        grid: {
          left: 60,
          right: 30,
          bottom: 60,
          top: 90
        },
        xAxis: {
          type: 'category',
          data: categories,
          axisLabel: { rotate: 45, fontSize: 10 },
          name: 'Date',
          nameLocation: 'middle',
          nameGap: 40
        },
        yAxis: {
          type: 'value',
          name: 'Visits',
          nameLocation: 'middle',
          nameGap: 45
        },
        series: series.map((s, idx) => ({
          ...s,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2 },
          itemStyle: {
            color: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'][idx % 4]
          },
          areaStyle: {
            opacity: 0.1
          }
        }))
      });
    } else if (trafficEl) { trafficEl.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu.</div>'; }
  }
  el('#seo-load').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('seo'); run(true); });
  el('#seo-refresh').addEventListener('click', () => { clearSnapshotForTabCurrentFilter('seo'); run(true); });
  // Don't auto-call run() - charts already rendered from cache above
  // User can click Load/Refresh to fetch fresh data
}

async function renderRetention() {
  view.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-bottom:8px">
      <button id="ret-load" class="tab">Load</button>
      <button id="ret-refresh" class="tab">Refresh</button>
      <span id="ret-status" class="muted"></span>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="card"><h3>Retention & Churn / Tỷ lệ giữ chân & rời bỏ</h3><div class="chart" id="chart-ret"></div></div>
      <div class="card"><h3>Cohort Analysis / Phân tích tổ hợp</h3><div id="cohort-table" style="max-height:320px;overflow:auto"></div></div>
    </div>
  `;
  const statusEl = el('#ret-status');
  // Restore snapshot
  (function () {
    const snap = snapGet('retention'); if (!snap) return;
    const labels = []; const retVals = []; const churnVals = [];
    if (Array.isArray(snap.timeseries)) {
      for (const r of snap.timeseries) { labels.push(r.date || r.t || r.period || ''); retVals.push(typeof r.retention === 'number' ? Math.round(r.retention * 1000) / 10 : (r.retention ?? 0)); churnVals.push(typeof r.churn === 'number' ? Math.round(r.churn * 1000) / 10 : (r.churn ?? 0)); }
      const retEl = el('#chart-ret'); if (retEl) { const chart = echarts.init(retEl); chart.setOption({ tooltip: { trigger: 'axis' }, legend: { data: ['Retention %', 'Churn %'] }, xAxis: { type: 'category', data: labels }, yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } }, series: [{ name: 'Retention %', type: 'line', data: retVals }, { name: 'Churn %', type: 'line', data: churnVals }] }); }
    }
    // Render cohort table from snapshot
    const cohortDiv = el('#cohort-table');
    if (cohortDiv) {
      let cohort = Array.isArray(snap.cohort) ? snap.cohort : [];
      if (cohort.length) {
        try { cohort = cohort.sort((a, b) => String(a.cohort).localeCompare(String(b.cohort))).slice(-12); } catch { }
        const monthCount = Math.max(...cohort.map(c => Array.isArray(c.months) ? c.months.length : 0));
        const header = ['Cohort', 'Size', ...Array.from({ length: monthCount }, (_, i) => `M+${i}`)];
        cohortDiv.innerHTML = `
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb">${header.map(h => `<th style=\"padding:6px\">${h}</th>`).join('')}</tr></thead>
            <tbody>
              ${cohort.map(row => `
                <tr style=\"border-bottom:1px solid #e5e7eb\">
                  <td style=\"padding:6px\">${row.cohort || ''}</td>
                  <td style=\"padding:6px\">${row.size ?? ''}</td>
                  ${Array.from({ length: monthCount }, (_, i) => {
          const v = (row.months || [])[i];
          const pct = (typeof v === 'number' && isFinite(v)) ? (Math.round(v * 1000) / 10) + '%' : '';
          return `<td style=\"padding:6px\">${pct}</td>`;
        }).join('')}
                </tr>`).join('')}
            </tbody>
          </table>
        `;
      } else {
        cohortDiv.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>';
      }
    }
    statusEl.textContent = 'Restored from cache';
  })();
  async function run(fetchFresh = false) {
    const q = buildQuery();
    let urlA = `/api/v1/analytics/retention?${q}`;
    let urlB = `/api/v1/analyses/retention?${q}`;
    if (fetchFresh) { const a = withBypass(urlA), b = withBypass(urlB);[a, b].forEach(({ clean }) => { httpCache.delete(cacheKey(clean)); lsDel(cacheKey(clean)); }); urlA = a.fresh; urlB = b.fresh; }
    // Prefer analytics/retention; analyses/retention as fallback
    let retention = fetchFresh ? (await safeGet(urlA)) : (await getWithTTL(urlA, 600000));
    if (retention && retention.error) {
      retention = fetchFresh ? (await safeGet(urlB)) : (await getWithTTL(urlB, 600000));
    }
    statusEl.textContent = `Updated ${new Date().toLocaleString()}`;
    // Save snapshot for Retention (fresh only or if missing)
    // Always save to cache when fetching fresh data
    if (fetchFresh) {
      snapSet('retention', retention || {});
    } else {
      snapUpdate('retention', retention || {});
    }
    const labels = [];
    const retVals = [];
    const churnVals = [];
    if (Array.isArray(retention?.timeseries)) {
      for (const r of retention.timeseries) {
        labels.push(r.date || r.t || r.period || '');
        retVals.push(typeof r.retention === 'number' ? Math.round(r.retention * 1000) / 10 : (r.retention ?? 0));
        churnVals.push(typeof r.churn === 'number' ? Math.round(r.churn * 1000) / 10 : (r.churn ?? 0));
      }
    } else {
      // fallback demo data
      labels.push('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun');
      retVals.push(68, 66, 64, 65, 67, 69);
      churnVals.push(32, 34, 36, 35, 33, 31);
    }
    const retEl = el('#chart-ret');
    if (!retEl) return;
    const ret = echarts.init(retEl);
    ret.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['Retention %', 'Churn %'] },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [
        { name: 'Retention %', type: 'line', data: retVals },
        { name: 'Churn %', type: 'line', data: churnVals },
      ]
    });

    // Render cohort table
    const cohortDiv = el('#cohort-table');
    if (cohortDiv) {
      let cohort = Array.isArray(retention?.cohort) ? retention.cohort : [];
      if (cohort.length) {
        // Keep only the 12 most recent cohorts (by cohort label like 'YYYY-MM')
        try {
          cohort = cohort.sort((a, b) => String(a.cohort).localeCompare(String(b.cohort))).slice(-12);
        } catch { }
        const monthCount = Math.max(...cohort.map(c => Array.isArray(c.months) ? c.months.length : 0));
        const header = ['Cohort', 'Size', ...Array.from({ length: monthCount }, (_, i) => `M+${i}`)];
        cohortDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb">${header.map(h => `<th style="padding:6px">${h}</th>`).join('')}</tr></thead>
          <tbody>
            ${cohort.map(row => `
              <tr style="border-bottom:1px solid #e5e7eb">
                <td style="padding:6px">${row.cohort || ''}</td>
                <td style="padding:6px">${row.size ?? ''}</td>
                ${Array.from({ length: monthCount }, (_, i) => {
          const v = (row.months || [])[i];
          const pct = (typeof v === 'number' && isFinite(v)) ? (Math.round(v * 1000) / 10) + '%' : '';
          return `<td style="padding:6px">${pct}</td>`;
        }).join('')}
              </tr>`).join('')}
          </tbody>
        </table>
      `;
      } else {
        cohortDiv.innerHTML = '<div class="muted" style="padding:12px">Không có dữ liệu cohort.</div>';
      }
    }
  }
  const retLoadBtn = el('#ret-load');
  const retRefBtn = el('#ret-refresh');
  const runRetDeb = debounce((fresh) => run(fresh), 700);
  if (retLoadBtn) {
    retLoadBtn.disabled = false; retLoadBtn.style.pointerEvents = 'auto'; retLoadBtn.style.cursor = 'pointer';
    retLoadBtn.addEventListener('click', () => { console.debug('Retention: Load clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('retention'); runRetDeb(true); });
  }
  if (retRefBtn) {
    retRefBtn.disabled = false; retRefBtn.style.pointerEvents = 'auto'; retRefBtn.style.cursor = 'pointer';
    retRefBtn.addEventListener('click', () => { console.debug('Retention: Refresh clicked'); statusEl.textContent = 'Loading…'; clearSnapshotForTabCurrentFilter('retention'); runRetDeb(true); });
  }
  // Auto-fetch on first visit if there is no snapshot yet
  if (!snapGet('retention')) { await run(false); }
}

async function renderOrchestrator() {
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

  // Restore snapshot if available to avoid empty UI while fetching
  (function () {
    try {
      const snap = snapGet('orchestrator');
      if (!snap) return;
      const s = snap.status || {};
      const h = snap.history || {};
      const lastRun = snap.last_run || null;
      // Status and errors
      statusPre.textContent = JSON.stringify(s, null, 2);
      const errs = (s.errors || {});
      errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
      // Module details
      let mods = Array.isArray(s.modules) ? s.modules : [];
      // If status lacks modules, prefer latest run payload
      if ((!mods || !mods.length) && lastRun && lastRun.results) {
        try {
          const results = lastRun.results || {};
          const rows = Object.keys(results).map(name => {
            const it = results[name] || {};
            const exec = Number(it.execution_time_seconds || it.execution_time || 0);
            const status = it.status || it.outcome || 'done';
            return { name, status, execution_time: exec };
          });
          mods = rows;
        } catch { }
      }
      if (Array.isArray(mods) && mods.length) {
        modulesDiv.innerHTML = `
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Module</th><th style="padding:6px">Status</th><th style="padding:6px">Exec Time (s)</th></tr></thead>
            <tbody>
              ${mods.map(m => `<tr style=\"border-bottom:1px solid #e5e7eb\"><td style=\"padding:6px\">${m.name || ''}</td><td style=\"padding:6px\">${m.status || ''}</td><td style=\"padding:6px\">${m.execution_time != null ? Number(m.execution_time).toFixed(2) : ''}</td></tr>`).join('')}
            </tbody>
          </table>
        `;
      }
      // History
      if (Array.isArray(h?.items)) {
        historyDiv.innerHTML = `
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Time</th><th style="padding:6px">Status</th><th style="padding:6px">Duration</th><th style="padding:6px">Workers</th><th style="padding:6px">User</th></tr></thead>
            <tbody>
              ${h.items.map(it => `<tr data-ts="${it.ts || ''}" style="cursor:pointer;border-bottom:1px solid #e5e7eb"><td style="padding:6px">${it.ts || it.end_time || ''}</td><td style="padding:6px">${it.status || ''}</td><td style="padding:6px">${it.duration_seconds ?? ''}</td><td style="padding:6px">${it.max_workers ?? ''}</td><td style="padding:6px">${it.username ?? ''}</td></tr>`).join('')}
            </tbody>
          </table>
        `;
      }
    } catch { }
  })();

  async function loadStatus() {
    const s = await safeGet('/api/v1/analytics/orchestrator/status');
    statusPre.textContent = JSON.stringify(s, null, 2);
    const errs = s.errors || {};
    errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
    // Render module details
    const mods = Array.isArray(s.modules) ? s.modules : [];
    if (mods.length) {
      modulesDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Module</th><th style="padding:6px">Status</th><th style="padding:6px">Exec Time (s)</th></tr></thead>
          <tbody>
            ${mods.map(m => `<tr style=\"border-bottom:1px solid #e5e7eb\"><td style=\"padding:6px\">${m.name || ''}</td><td style=\"padding:6px\">${m.status || ''}</td><td style=\"padding:6px\">${m.execution_time != null ? Number(m.execution_time).toFixed(2) : ''}</td></tr>`).join('')}
          </tbody>
        </table>
      `;
    } else {
      modulesDiv.innerHTML = '<div class="muted" style="padding:6px">No module details available.</div>';
    }
    const h = await safeGet('/api/v1/analytics/orchestrator/history?limit=20');
    if (Array.isArray(h?.items)) {
      historyDiv.innerHTML = `
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Time</th><th style="padding:6px">Status</th><th style="padding:6px">Duration</th><th style="padding:6px">Workers</th><th style="padding:6px">User</th></tr></thead>
          <tbody>
            ${h.items.map(it => `<tr data-ts="${it.ts || ''}" style="cursor:pointer;border-bottom:1px solid #e5e7eb"><td style="padding:6px">${it.ts || it.end_time || ''}</td><td style="padding:6px">${it.status || ''}</td><td style="padding:6px">${it.duration_seconds ?? ''}</td><td style="padding:6px">${it.max_workers ?? ''}</td><td style="padding:6px">${it.username ?? ''}</td></tr>`).join('')}
          </tbody>
        </table>
      `;
      // attach click to load detail
      historyDiv.querySelector('tbody')?.addEventListener('click', async (e) => {
        const tr = e.target.closest('tr[data-ts]');
        if (!tr) return;
        const ts = tr.getAttribute('data-ts');
        if (!ts) return;
        detailPre.textContent = 'Loading…';
        const doc = await safeGet(`/api/v1/analytics/orchestrator/history/item?ts=${encodeURIComponent(ts)}`);
        detailPre.textContent = JSON.stringify(doc, null, 2);
      });
    }
    // Persist latest status+history snapshot
    try { snapUpdate('orchestrator', { status: s, history: h, last_run: (snapGet('orchestrator') || {}).last_run || null }); } catch { }
  }

  async function run() {
    msg.textContent = 'Running…';
    const p = new URLSearchParams();
    const u = userIn.value.trim(); if (u) p.set('username', u);
    p.set('max_workers', maxSel.value);
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const res = await fetch(`/api/v1/analytics/orchestrator/run?${p.toString()}&_ts=${Date.now()}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    });
    const json = await res.json().catch(() => ({}));
    msg.textContent = res.ok ? 'Completed' : 'Error';
    statusPre.textContent = JSON.stringify(json, null, 2);
    const errs = json.errors || {};
    errorsPre.textContent = Object.keys(errs).length ? JSON.stringify(errs, null, 2) : '(no errors)';
    // Render module details from the run response if available
    try {
      const results = json.results || {};
      const rows = Object.keys(results).map(name => {
        const it = results[name] || {};
        const exec = Number(it.execution_time_seconds || it.execution_time || 0);
        const status = it.status || it.outcome || 'done';
        return { name, status, execution_time: exec };
      });
      if (rows.length) {
        modulesDiv.innerHTML = `
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="text-align:left;border-bottom:1px solid #e5e7eb"><th style="padding:6px">Module</th><th style="padding:6px">Status</th><th style="padding:6px">Exec Time (s)</th></tr></thead>
            <tbody>
              ${rows.map(m => `<tr style=\"border-bottom:1px solid #e5e7eb\"><td style=\"padding:6px\">${m.name}</td><td style=\"padding:6px\">${m.status}</td><td style=\"padding:6px\">${isFinite(m.execution_time) ? m.execution_time.toFixed(2) : ''}</td></tr>`).join('')}
            </tbody>
          </table>
        `;
      }
    } catch { }
    // Persist last run payload to snapshot so UI restores immediately after tab switch
    try {
      const prev = snapGet('orchestrator') || {};
      snapUpdate('orchestrator', { ...(prev || {}), last_run: json });
    } catch { }
    // Auto-refresh latest status + modules + history
    await loadStatus();
  }

  runBtn.addEventListener('click', () => { clearSnapshotsForTab('orchestrator'); run(); });
  refBtn.addEventListener('click', () => { clearSnapshotsForTab('orchestrator'); loadStatus(); });
  await loadStatus();
}

async function renderRaw() {
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

  function renderRows() {
    const q = String(userQ.value || '').trim().toLowerCase();
    rowsEl.innerHTML = '';
    const items = q ? allItems.filter(s => String(s.user_id || '').toLowerCase().includes(q)) : allItems;
    statusEl.textContent = `${items.length} sessions` + (q ? ` • filtered` : '');
    for (const s of items) {
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

  async function loadSessions(fetchFresh = false) {
    statusEl.textContent = 'Loading…';
    rowsEl.innerHTML = '';
    const limit = Math.min(500, Number(limitSel.value || '50'));
    const params = new URLSearchParams({ limit: String(limit) });
    const q = String(userQ.value || '').trim();
    if (q) params.set('user', q);
    let url = `/api/v1/events/sessions/recent?${params.toString()}`;
    if (fetchFresh) {
      httpCache.delete(url);
    }
    const data = await safeGet(url);
    allItems = data.items || data.sessions || [];
    renderRows();
  }

  function toCSV(rows) {
    if (!Array.isArray(rows) || !rows.length) return '';
    const cols = Array.from(new Set(rows.flatMap(r => Object.keys(r || {}))));
    const esc = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
    const header = cols.map(esc).join(',');
    const body = rows.map(r => cols.map(c => esc(r[c])).join(',')).join('\n');
    return header + '\n' + body;
  }

  function download(filename, content) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  async function loadDetail(sessionId) {
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
      <pre style="max-height:360px;overflow:auto;background:#0b1020;color:#d1d5db;padding:8px;border-radius:8px">${JSON.stringify(sum, null, 2)
      }</pre>
    `;
    const exportBtn = el('#raw-export');
    exportBtn?.addEventListener('click', () => {
      const csv = toCSV(events);
      download(`session_${meta.session_id}.csv`, csv);
    });
  }

  rowsEl.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-sid]');
    if (!btn) return;
    loadDetail(btn.dataset.sid);
  });
  reloadBtn.addEventListener('click', () => loadSessions(true));
  limitSel.addEventListener('change', () => loadSessions(true));
  userQ.addEventListener('input', debounce(() => loadSessions(true), 300));

  await loadSessions();
}
async function render() {
  switch (state.tab) {
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

function initNav() {
  const nav = document.getElementById('nav');
  nav.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    switchTab(btn.dataset.tab);
  });
  // default active - switchTab triggers render + data load
  switchTab('overview');
}

function initFilters() {
  const fTime = el('#f-time');
  const fFrom = el('#f-from');
  const fTo = el('#f-to');
  const fSeg = el('#f-segment');
  const fCh = el('#f-channel');

  function apply() {
    state.filters.range = fTime.value;
    state.filters.from = fFrom.value || null;
    state.filters.to = fTo.value || null;
    state.filters.segment = fSeg.value;
    state.filters.channel = fCh.value;
    let applyTimer = null;
    function applyDebounced() {
      if (applyTimer) { clearTimeout(applyTimer); }
      applyTimer = setTimeout(() => {
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

  fTime.addEventListener('change', () => {
    const custom = fTime.value === 'custom';
    fFrom.style.display = custom ? '' : 'none';
    fTo.style.display = custom ? '' : 'none';
    apply();
  });
  [fFrom, fTo, fSeg, fCh].forEach(elm => elm.addEventListener('change', apply));
}

function guardAuth() {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');
  try {
    if (!token || !userStr) throw new Error('unauth');
    const user = JSON.parse(userStr);
    if ((user.role || 'user') !== 'admin') throw new Error('not-admin');
  } catch {
    window.location.replace('/auth');
  }
}

function init() {
  guardAuth();
  // Initialize filters first so filterSig() is ready
  initFilters();
  // Migrate old snapshots (pre-filter-scoped) to the new keys for current filters
  migrateOldSnapshots();
  // Now init navigation and render
  initNav();
  // Clear Cache button: clear dashboard caches while preserving auth
  try {
    const btn = document.getElementById('btn-clear-cache');
    btn?.addEventListener('click', () => {
      const LS_NS = 'spa_cache_v1:'; const SNAP_NS = 'spa_snap_v1:';
      const keys = Object.keys(localStorage);
      for (const k of keys) { if (k.startsWith(LS_NS) || k.startsWith(SNAP_NS)) localStorage.removeItem(k); }
      try { if (window.httpCache && typeof window.httpCache.clear === 'function') window.httpCache.clear(); } catch { }
      showToast('Cleared dashboard cache');
    });
  } catch { }
}

// ES6 modules are deferred by default, so DOM is ready when this executes
init();

