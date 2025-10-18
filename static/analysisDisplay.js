// Analysis Display Module - Handles rendering of analysis results
import { displayLLMAnalysis } from './llmDisplay.js';

// Main function to display analysis results
export function displayAnalysisResults(analysis, container) {
  if (!analysis) {
    container.innerHTML = '<div class="error">No analysis data available</div>';
    return;
  }

  // Clear previous results
  container.innerHTML = '';

  try {
    // 1. Summary Section
    const summary = createSummarySection(analysis);
    container.appendChild(summary);

    // 2. Key Metrics Cards
    const metrics = createMetricsSection(analysis);
    if (metrics) container.appendChild(metrics);

    // 3. Funnel Analysis
    const funnel = createFunnelSection(analysis);
    if (funnel) container.appendChild(funnel);

    // 4. Top Pages & Events
    const pagesEvents = createPagesAndEventsSection(analysis);
    if (pagesEvents) container.appendChild(pagesEvents);

    // 5. Time Analysis
    const timeAnalysis = createTimeAnalysisSection(analysis);
    if (timeAnalysis) container.appendChild(timeAnalysis);

    // 6. Session Analysis
    const sessionAnalysis = createSessionAnalysisSection(analysis);
    if (sessionAnalysis) container.appendChild(sessionAnalysis);

    // 6.5 Spark Summary (from spark_summary)
    const sparkSection = createSparkSummarySection(analysis);
    if (sparkSection) container.appendChild(sparkSection);

    // 7. LLM Analysis (New comprehensive display)
    const llmSection = createLLMSection(analysis);
    if (llmSection) container.appendChild(llmSection);

    // 8. Raw Data (collapsible)
    const rawSection = createRawDataSection(analysis);
    container.appendChild(rawSection);

  } catch (error) {
    console.error('Error displaying analysis results:', error);
    container.innerHTML = `
      <div class="error">
        <p>Error displaying analysis results. Showing raw data instead.</p>
        <pre>${JSON.stringify(analysis, null, 2)}</pre>
      </div>
    `;
  }
}

// Helper function to create the summary section
function createSummarySection(analysis) {
  const section = document.createElement('div');
  section.className = 'analysis-section summary-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Analysis Summary';
  title.className = 'section-title';
  
  const summary = document.createElement('div');
  summary.className = 'summary-content';
  
  // Get basic metrics
  const basicMetrics = analysis.detailed_metrics?.basic_metrics || {};
  const sparkSummary = analysis.spark_summary || {};
  
  const metrics = [
    {
      label: 'Total Events',
      value: sparkSummary.total_events || basicMetrics.total_events || 0,
      icon: '📊'
    },
    {
      label: 'Total Sessions',
      value: sparkSummary.sessions || basicMetrics.total_sessions || 0,
      icon: '🔄'
    },
    {
      label: 'Unique Users',
      value: basicMetrics.unique_users || 1,
      icon: '👥'
    },
    {
      label: 'Avg. Session Duration',
      value: basicMetrics.avg_session_duration_seconds 
        ? `${Math.round(basicMetrics.avg_session_duration_seconds / 60 * 10) / 10} mins` 
        : 'N/A',
      icon: '⏱️'
    },
    {
      label: 'Pages/Session',
      value: basicMetrics.avg_pages_per_session 
        ? basicMetrics.avg_pages_per_session.toFixed(1) 
        : 'N/A',
      icon: '📄'
    },
    {
      label: 'Bounce Rate',
      value: basicMetrics.bounce_rate !== undefined 
        ? `${(basicMetrics.bounce_rate * 100).toFixed(1)}%` 
        : 'N/A',
      icon: '↩️'
    }
  ];
  
  // Create metric cards
  metrics.forEach(metric => {
    const metricEl = document.createElement('div');
    metricEl.className = 'metric-card';
    metricEl.innerHTML = `
      <div class="metric-icon">${metric.icon}</div>
      <div class="metric-value">${metric.value}</div>
      <div class="metric-label">${metric.label}</div>
    `;
    summary.appendChild(metricEl);
  });
  
  // Add key insights if available
  if (analysis.insights?.key_findings?.length) {
    const insightsEl = document.createElement('div');
    insightsEl.className = 'insights-section';
    insightsEl.innerHTML = `
      <h3>Key Findings</h3>
      <ul>
        ${analysis.insights.key_findings.map(finding => 
          `<li>${finding}</li>`
        ).join('')}
      </ul>
    `;
    summary.appendChild(insightsEl);
  }
  
  section.appendChild(title);
  section.appendChild(summary);
  return section;
}

// Create metrics section with detailed metrics
function createMetricsSection(analysis) {
  const metrics = analysis.detailed_metrics;
  if (!metrics) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section metrics-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Detailed Metrics';
  title.className = 'section-title';
  
  const grid = document.createElement('div');
  grid.className = 'metrics-grid';
  
  // Add event metrics
  if (metrics.event_analysis?.event_types) {
    Object.entries(metrics.event_analysis.event_types).forEach(([type, count]) => {
      const card = document.createElement('div');
      card.className = 'metric-card';
      card.innerHTML = `
        <div class="metric-value">${count}</div>
        <div class="metric-label">${type.replace(/_/g, ' ')}</div>
      `;
      grid.appendChild(card);
    });
  }
  
  section.appendChild(title);
  section.appendChild(grid);
  return section;
}

// Create funnel analysis section
function createFunnelSection(analysis) {
  const funnel = analysis.detailed_metrics?.funnel_analysis;
  if (!funnel) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section funnel-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Conversion Funnel';
  title.className = 'section-title';
  
  const container = document.createElement('div');
  container.className = 'funnel-container';
  
  // Add each stage of the funnel
  Object.entries(funnel).forEach(([stageName, stageData]) => {
    if (typeof stageData !== 'object') return;
    
    const stageEl = document.createElement('div');
    stageEl.className = 'funnel-stage';
    
    const header = document.createElement('div');
    header.className = 'funnel-header';
    
    const title = document.createElement('div');
    title.className = 'funnel-title';
    title.textContent = stageName.replace(/_/g, ' ');
    
    const conversion = document.createElement('div');
    conversion.className = 'funnel-conversion';
    conversion.textContent = stageData.conversion 
      ? `${(stageData.conversion * 100).toFixed(1)}%` 
      : '';
    
    header.appendChild(title);
    header.appendChild(conversion);
    
    const bar = document.createElement('div');
    bar.className = 'funnel-bar';
    
    const progress = document.createElement('div');
    progress.className = 'funnel-progress';
    progress.style.width = stageData.conversion ? `${stageData.conversion * 100}%` : '0%';
    
    bar.appendChild(progress);
    
    stageEl.appendChild(header);
    stageEl.appendChild(bar);
    container.appendChild(stageEl);
  });
  
  section.appendChild(title);
  section.appendChild(container);
  return section;
}

// Create pages and events section
function createPagesAndEventsSection(analysis) {
  const pages = analysis.detailed_metrics?.page_analysis?.top_pages;
  const events = analysis.detailed_metrics?.event_analysis?.top_event_types;
  
  if (!pages?.length && !events?.length) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section pages-events-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Top Pages & Events';
  title.className = 'section-title';
  
  const content = document.createElement('div');
  content.className = 'pages-events-content';
  
  // Add top pages
  if (pages?.length) {
    const pagesSection = document.createElement('div');
    pagesSection.className = 'data-section';
    pagesSection.innerHTML = `
      <h3>Top Pages</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Page</th>
            <th>Views</th>
          </tr>
        </thead>
        <tbody>
          ${pages.slice(0, 10).map(page => `
            <tr>
              <td>${page.page}</td>
              <td>${page.count}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    content.appendChild(pagesSection);
  }
  
  // Add top events
  if (events?.length) {
    const eventsSection = document.createElement('div');
    eventsSection.className = 'data-section';
    eventsSection.innerHTML = `
      <h3>Top Events</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Event Type</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          ${events.map(event => `
            <tr>
              <td>${event.type}</td>
              <td>${event.count}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    content.appendChild(eventsSection);
  }
  
  section.appendChild(title);
  section.appendChild(content);
  return section;
}

// Create time analysis section
function createTimeAnalysisSection(analysis) {
  const timeData = analysis.detailed_metrics?.time_analysis;
  if (!timeData) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section time-analysis-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Time Analysis';
  title.className = 'section-title';
  
  const content = document.createElement('div');
  content.className = 'time-analysis-content';
  
  // Add hourly distribution
  if (timeData.hourly_distribution) {
    const hours = Object.entries(timeData.hourly_distribution)
      .sort(([a], [b]) => a - b);
    
    if (hours.length > 0) {
      const maxCount = Math.max(...hours.map(([_, count]) => count));
      
      const hourlySection = document.createElement('div');
      hourlySection.className = 'data-section';
      hourlySection.innerHTML = `
        <h3>Hourly Distribution</h3>
        <div class="hourly-chart">
          ${hours.map(([hour, count]) => {
            const height = (count / maxCount * 100) || 0;
            return `
              <div class="hourly-bar-container">
                <div class="hourly-bar" style="height: ${height}%"></div>
                <div class="hour-label">${hour}:00</div>
                <div class="count-label">${count}</div>
              </div>
            `;
          }).join('')}
        </div>
      `;
      content.appendChild(hourlySection);
    }
  }
  
  section.appendChild(title);
  section.appendChild(content);
  return section;
}

// Create session analysis section
function createSessionAnalysisSection(analysis) {
  const sessionData = analysis.detailed_metrics?.session_analysis;
  if (!sessionData?.session_metrics) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section session-analysis-section';
  
  const title = document.createElement('h2');
  title.textContent = 'Session Analysis';
  title.className = 'section-title';
  
  const metrics = [
    {
      label: 'Avg. Session Duration',
      value: sessionData.avg_session_duration 
        ? `${Math.round(sessionData.avg_session_duration / 60 * 10) / 10} mins` 
        : 'N/A',
      icon: '⏱️'
    },
    {
      label: 'Avg. Pages/Session',
      value: sessionData.avg_pages_per_session?.toFixed(1) || 'N/A',
      icon: '📄'
    },
    {
      label: 'Total Sessions',
      value: Object.keys(sessionData.session_metrics).length,
      icon: '🔄'
    }
  ];
  
  const metricsEl = document.createElement('div');
  metricsEl.className = 'metrics-grid';
  
  metrics.forEach(metric => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.innerHTML = `
      <div class="metric-value">${metric.value}</div>
      <div class="metric-label">${metric.label}</div>
    `;
    metricsEl.appendChild(card);
  });
  
  section.appendChild(title);
  section.appendChild(metricsEl);
  return section;
}

function createSparkSummarySection(analysis) {
  const spark = analysis && analysis.spark_summary;
  if (!spark || typeof spark !== 'object') return null;
  const section = document.createElement('div');
  section.className = 'analysis-section spark-summary-section';
  const title = document.createElement('h2');
  title.textContent = 'Spark Summary';
  title.className = 'section-title';
  const grid = document.createElement('div');
  grid.className = 'metrics-grid';
  const cards = [
    { label: 'Total Events', value: spark.total_events ?? 0 },
    { label: 'Total Sessions', value: spark.sessions ?? 0 },
    { label: 'Unique Users', value: spark.unique_users ?? (analysis?.detailed_metrics?.basic_metrics?.unique_users ?? 0) }
  ];
  cards.forEach(item => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.innerHTML = `
      <div class="metric-value">${item.value}</div>
      <div class="metric-label">${item.label}</div>
    `;
    grid.appendChild(card);
  });
  const topPages = Array.isArray(spark.top_pages) ? spark.top_pages : [];
  let pagesEl = null;
  if (topPages.length) {
    pagesEl = document.createElement('div');
    pagesEl.className = 'data-section';
    const rows = topPages.slice(0, 10).map(p => {
      const page = typeof p === 'object' && p !== null ? (p.page ?? p[0]) : '';
      const count = typeof p === 'object' && p !== null ? (p.count ?? p[1]) : '';
      return `<tr><td>${page}</td><td>${count}</td></tr>`;
    }).join('');
    pagesEl.innerHTML = `
      <h3>Top Pages</h3>
      <table class="data-table">
        <thead><tr><th>Page</th><th>Views</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }
  section.appendChild(title);
  section.appendChild(grid);
  if (pagesEl) section.appendChild(pagesEl);
  return section;
}

// Create AI insights and recommendations section
function createAIInsightsSection(analysis) {
  const insights = analysis.insights || {};
  const hasInsights = insights.recommendations?.length || 
                     insights.alerts?.length ||
                     analysis.openrouter_output?.parsed?.recommendations?.length;
  
  if (!hasInsights) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section ai-insights-section';
  
  const title = document.createElement('h2');
  title.textContent = 'AI Insights & Recommendations';
  title.className = 'section-title';
  
  const content = document.createElement('div');
  content.className = 'ai-insights-content';
  
  // Add recommendations
  if (insights.recommendations?.length) {
    const recsEl = document.createElement('div');
    recsEl.className = 'insight-section';
    recsEl.innerHTML = `
      <h3>Recommendations</h3>
      <ul>
        ${insights.recommendations.map(rec => 
          `<li>${rec}</li>`
        ).join('')}
      </ul>
    `;
    content.appendChild(recsEl);
  }
  
  // Add alerts
  if (insights.alerts?.length) {
    const alertsEl = document.createElement('div');
    alertsEl.className = 'insight-section alerts';
    alertsEl.innerHTML = `
      <h3>Alerts</h3>
      <ul>
        ${insights.alerts.map(alert => 
          `<li>⚠️ ${alert}</li>`
        ).join('')}
      </ul>
    `;
    content.appendChild(alertsEl);
  }
  
  // Add OpenRouter recommendations if available
  const openRouterRecs = analysis.openrouter_output?.parsed?.recommendations_for_user;
  if (openRouterRecs?.length) {
    const openRouterEl = document.createElement('div');
    openRouterEl.className = 'insight-section openrouter';
    openRouterEl.innerHTML = `
      <h3>Personalized Recommendations</h3>
      <ul>
        ${openRouterRecs.map(rec => 
          `<li>💡 ${rec}</li>`
        ).join('')}
      </ul>
    `;
    content.appendChild(openRouterEl);
  }
  
  section.appendChild(title);
  section.appendChild(content);
  return section;
}

// Create raw data section
function createRawDataSection(analysis) {
  const section = document.createElement('details');
  section.className = 'raw-data-section';
  section.innerHTML = `
    <summary>View Raw Analysis Data</summary>
    <pre>${JSON.stringify(analysis, null, 2)}</pre>
  `;
  return section;
}

// Add styles
const styles = `
.analysis-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 16px;
}

.analysis-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.section-title {
  color: var(--primary);
  margin-top: 0;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* Summary Section */
.summary-section {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%);
}

.summary-content {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.05);
  padding: 16px;
  border-radius: 8px;
  text-align: center;
  border-left: 3px solid var(--primary);
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.metric-icon {
  font-size: 1.5em;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 1.8em;
  font-weight: 700;
  color: var(--text);
  margin: 8px 0;
}

.metric-label {
  font-size: 0.9em;
  color: var(--text-muted);
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

/* Funnel Section */
.funnel-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.funnel-stage {
  position: relative;
  padding: 12px;
  background: rgba(79, 70, 229, 0.1);
  border-radius: 6px;
  border-left: 3px solid var(--primary);
}

.funnel-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.funnel-title {
  font-weight: 600;
  color: var(--text);
  text-transform: capitalize;
}

.funnel-conversion {
  font-weight: 600;
  color: var(--primary);
}

.funnel-bar {
  height: 8px;
  background: rgba(79, 70, 229, 0.2);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 8px;
}

.funnel-progress {
  height: 100%;
  background: var(--primary);
  border-radius: 4px;
  transition: width 0.5s ease;
}

/* Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 0.9em;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.data-table th {
  background: rgba(0, 0, 0, 0.1);
  font-weight: 600;
  color: var(--text);
}

.data-table tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

/* Hourly Chart */
.hourly-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 200px;
  padding: 20px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
  overflow-x: auto;
}

.hourly-bar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 30px;
}

.hourly-bar {
  width: 20px;
  background: var(--primary);
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
}

.hour-label, .count-label {
  font-size: 0.8em;
  color: var(--text-muted);
  margin-top: 4px;
}

/* Insights & Recommendations */
.insight-section {
  margin-bottom: 20px;
}

.insight-section h3 {
  margin-top: 0;
  margin-bottom: 8px;
  color: var(--primary);
  font-size: 1.1em;
}

.insight-section ul {
  margin: 0;
  padding-left: 20px;
}

.insight-section li {
  margin-bottom: 6px;
  line-height: 1.5;
}

.insight-section.alerts li {
  color: #ef4444;
}

.insight-section.openrouter li {
  color: #10b981;
}

/* Raw Data Section */
.raw-data-section {
  margin-top: 20px;
}

.raw-data-section summary {
  cursor: pointer;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-weight: 500;
  outline: none;
}

.raw-data-section summary:hover {
  background: rgba(255, 255, 255, 0.05);
}

.raw-data-section pre {
  max-height: 400px;
  overflow: auto;
  margin-top: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-size: 0.8em;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Responsive Design */
@media (max-width: 768px) {
  .summary-content,
  .metrics-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .hourly-chart {
    height: 150px;
  }
}

@media (max-width: 480px) {
  .summary-content,
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .analysis-section {
    padding: 12px;
  }
}

/* Error State */
.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  padding: 16px;
  border-radius: 6px;
  border-left: 3px solid #ef4444;
  margin: 16px 0;
}

.error pre {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: auto;
  max-height: 300px;
  font-size: 0.9em;
}
`;

// Create LLM Analysis Section
function createLLMSection(analysis) {
  if (!analysis.openrouter_output) return null;
  
  const section = document.createElement('div');
  section.className = 'analysis-section llm-analysis-section';
  section.id = 'llm-analysis';
  
  const header = document.createElement('h2');
  header.className = 'section-header';
  header.innerHTML = '🤖 AI-Powered Analysis';
  section.appendChild(header);
  
  const llmContainer = document.createElement('div');
  llmContainer.className = 'llm-container';
  
  // Use the new llmDisplay module
  displayLLMAnalysis(analysis.openrouter_output, llmContainer);
  
  section.appendChild(llmContainer);
  return section;
}

// Add styles to the document
const styleElement = document.createElement('style');
styleElement.textContent = styles;
document.head.appendChild(styleElement);
