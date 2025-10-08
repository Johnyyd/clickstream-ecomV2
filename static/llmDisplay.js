// llmDisplay.js - Hiển thị kết quả phân tích LLM với charts và UI đẹp

/**
 * Hiển thị đầy đủ kết quả LLM analysis
 */
export function displayLLMAnalysis(llmOutput, container) {
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    if (!llmOutput || llmOutput.status !== 'ok') {
        displayLLMError(llmOutput, container);
        return;
    }
    
    const parsed = llmOutput.parsed;
    if (!parsed) {
        container.innerHTML = '<div class="error">No parsed LLM data available</div>';
        return;
    }

    // Normalize top-level parsed fields to expected types (arrays/objects)
    normalizeParsed(parsed);
    
    // If model returned truncated output (finish_reason=length), surface a banner
    if (llmOutput.truncated) {
        const warn = document.createElement('div');
        warn.className = 'llm-truncated-warning';
        warn.innerHTML = `\n            <p>⚠️ LLM output was truncated (model signaled length). Some sections may be incomplete.</p>\n        `;
        container.appendChild(warn);
    }
    
    // Create sections
    const sections = [
        createExecutiveSummary(parsed),
        createKPIsSection(parsed),
        createKeyInsights(parsed),
        createTrafficInsights(parsed),
        createConversionAnalysis(parsed),
        createRecommendations(parsed),
        createDecisions(parsed),
        createNextActions(parsed),
        createRiskAlerts(parsed),
        createUserRecommendations(parsed),
        createProductRecommendations(parsed),
        createRawData(llmOutput)
    ];
    
    sections.forEach(section => {
        if (section) container.appendChild(section);
    });
}

function displayLLMError(llmOutput, container) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'llm-error';
    
    let errorMessage = 'LLM analysis failed';
    if (llmOutput?.error) {
        errorMessage = llmOutput.error;
    } else if (llmOutput?.auto_renewal_failed) {
        errorMessage = `Auto-renewal failed: ${llmOutput.auto_renewal_error}`;
    }
    
    errorDiv.innerHTML = `
        <h3>⚠️ LLM Analysis Error</h3>
        <p>${errorMessage}</p>
        ${llmOutput?.auto_renewed ? '<p class="success">✅ API key was auto-renewed</p>' : ''}
    `;
    
    container.appendChild(errorDiv);
}

function createExecutiveSummary(parsed) {
    const section = document.createElement('div');
    section.className = 'llm-section executive-summary';
    
    section.innerHTML = `
        <h2>📊 Executive Summary</h2>
        <div class="summary-content">
            <p>${parsed.executive_summary || 'No summary available'}</p>
        </div>
    `;
    
    return section;
}

function createKPIsSection(parsed) {
    if (!parsed.kpis) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section kpis-section';
    
    const kpis = parsed.kpis;
    
    section.innerHTML = `
        <h2>📈 Key Performance Indicators</h2>
        <div class="kpis-grid">
            <div class="kpi-card">
                <div class="kpi-value">${formatNumber(kpis.total_events)}</div>
                <div class="kpi-label">Total Events</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">${formatNumber(kpis.total_sessions)}</div>
                <div class="kpi-label">Total Sessions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">${formatPercent(kpis.bounce_rate)}</div>
                <div class="kpi-label">Bounce Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">${formatDuration(kpis.avg_session_duration_seconds)}</div>
                <div class="kpi-label">Avg Session Duration</div>
            </div>
        </div>
    `;
    
    return section;
}

function createKeyInsights(parsed) {
    if (!parsed.key_insights || parsed.key_insights.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section insights-section';
    
    const insightsList = parsed.key_insights.map((insight, idx) => 
        `<li class="insight-item">
            <span class="insight-number">${idx + 1}</span>
            <span class="insight-text">${safeString(insight)}</span>
        </li>`
    ).join('');
    
    section.innerHTML = `
        <h2>💡 Key Insights</h2>
        <ul class="insights-list">${insightsList}</ul>
    `;
    
    return section;
}

function createTrafficInsights(parsed) {
    if (!parsed.traffic_insights) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section traffic-section';
    
    const ti = parsed.traffic_insights || {};
    
    section.innerHTML = `
        <h2>🚦 Traffic Insights</h2>
        <div class="traffic-grid">
            ${createSubSection('Peak Hours', ti.peak_hours)}
            ${createSubSection('User Behavior Patterns', ti.user_behavior_patterns)}
            ${createSubSection('Popular Categories', ti.popular_categories)}
        </div>
    `;
    
    return section;
}

function createConversionAnalysis(parsed) {
    if (!parsed.conversion_analysis) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section conversion-section';
    
    const ca = parsed.conversion_analysis || {};
    
    section.innerHTML = `
        <h2>🎯 Conversion Analysis</h2>
        <div class="conversion-grid">
            ${createSubSection('Funnel Performance', ca.funnel_performance, 'success')}
            ${createSubSection('Drop-off Points', ca.drop_off_points, 'warning')}
            ${createSubSection('Optimization Opportunities', ca.optimization_opportunities, 'info')}
        </div>
    `;
    
    return section;
}

function createRecommendations(parsed) {
    if (!parsed.recommendations || parsed.recommendations.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section recommendations-section';
    
    const recsList = parsed.recommendations.map((rec, idx) => 
        `<li class="recommendation-item">
            <span class="rec-icon">✓</span>
            <span class="rec-text">${safeString(rec)}</span>
        </li>
    `).join('');
    
    section.innerHTML = `
        <h2>🎯 Business Recommendations</h2>
        <ul class="recommendations-list">${recsList}</ul>
    `;
    
    return section;
}

function createDecisions(parsed) {
    if (!parsed.decisions || parsed.decisions.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section decisions-section';
    
    const decisionsList = parsed.decisions.map((decision, idx) => 
        `<li class="decision-item">
            <span class="decision-number">${idx + 1}</span>
            <span class="decision-text">${safeString(decision)}</span>
        </li>`
    ).join('');
    
    section.innerHTML = `
        <h2>⚡ Strategic Decisions</h2>
        <ul class="decisions-list">${decisionsList}</ul>
    `;
    
    return section;
}

function createNextActions(parsed) {
    if (!parsed.next_best_actions || parsed.next_best_actions.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section actions-section';
    
    const actionsList = parsed.next_best_actions.map((action, idx) => 
        `<li class="action-item">
            <input type="checkbox" id="action-${idx}" class="action-checkbox">
            <label for="action-${idx}" class="action-text">${safeString(action)}</label>
        </li>`
    ).join('');
    
    section.innerHTML = `
        <h2>📋 Next Best Actions (7 days)</h2>
        <ul class="actions-list">${actionsList}</ul>
    `;
    
    return section;
}

function createRiskAlerts(parsed) {
    if (!parsed.risk_alerts || parsed.risk_alerts.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section risks-section';
    
    const risksList = parsed.risk_alerts.map(risk => 
        `<li class="risk-item">
            <span class="risk-icon">⚠️</span>
            <span class="risk-text">${safeString(risk)}</span>
        </li>
    `).join('');
    
    section.innerHTML = `
        <h2>⚠️ Risk Alerts</h2>
        <ul class="risks-list">${risksList}</ul>
    `;
    
    return section;
}

function createUserRecommendations(parsed) {
    if (!parsed.recommendations_for_user || parsed.recommendations_for_user.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section user-recs-section';
    
    const recsList = parsed.recommendations_for_user.map(rec => 
        `<li class="user-rec-item">${safeString(rec)}</li>`
    ).join('');
    
    section.innerHTML = `
        <h2>👤 User Recommendations</h2>
        <ul class="user-recs-list">${recsList}</ul>
    `;
    
    return section;
}

function createProductRecommendations(parsed) {
    if (!parsed.recommendations_for_user_products || parsed.recommendations_for_user_products.length === 0) return null;
    
    const section = document.createElement('div');
    section.className = 'llm-section products-section';
    
    const productCards = parsed.recommendations_for_user_products.map(product => {
        const name = safeString(product.name || product.title || 'Unnamed Product');
        const reason = safeString(product.reason || product.reasoning || 'No reason provided');
        const pid = safeString(product.product_id || product.id || '');
        return `<div class="product-card">
            <div class="product-name">${name}</div>
            <div class="product-reason">${reason}</div>
            ${pid ? `<a href="/p/${pid}" class="product-link">View Product →</a>` : ''}
        </div>`
    }).join('');
    
    section.innerHTML = `
        <h2>🛍️ Recommended Products</h2>
        <div class="products-grid">${productCards}</div>
    `;
    
    return section;
}

function createRawData(llmOutput) {
    const section = document.createElement('details');
    section.className = 'llm-section raw-section';
    
    section.innerHTML = `
        <summary>🔍 Raw LLM Response</summary>
        <pre class="raw-json">${JSON.stringify(llmOutput, null, 2)}</pre>
    `;
    
    return section;
}

function createSubSection(title, items, type = 'default') {
    // Accept strings, single objects, or arrays. Normalize to array.
    const arr = ensureArray(items);
    if (arr.length === 0) return '';

    const itemsList = arr.map(item => {
        if (typeof item === 'string' || typeof item === 'number') {
            return `<li class="subsection-item ${type}">${safeString(item)}</li>`;
        }
        // If item is an object, try to render meaningful fields
        if (item && typeof item === 'object') {
            // If it has a title/name, show that plus optional detail
            const titleText = safeString(item.title || item.name || JSON.stringify(item));
            const detail = item.reason || item.detail || item.description || '';
            return `<li class="subsection-item ${type}"><strong>${titleText}</strong>${detail ? ` — ${safeString(detail)}` : ''}</li>`;
        }
        return `<li class="subsection-item ${type}">${safeString(item)}</li>`;
    }).join('');

    return `
        <div class="subsection">
            <h3>${title}</h3>
            <ul>${itemsList}</ul>
        </div>
    `;
}

// Utility functions
function formatNumber(num) {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString();
}

function formatPercent(num) {
    if (num === null || num === undefined) return 'N/A';
    return `${(num * 100).toFixed(1)}%`;
}

function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
}

// Helpers: ensureArray converts strings/single objects into arrays; safeString guards against objects
function ensureArray(v) {
    if (v === null || v === undefined) return [];
    if (Array.isArray(v)) return v;
    // If it's a string that contains newlines or bullet points, split it
    if (typeof v === 'string') {
        const parts = v.split(/\r?\n|\n\s*-\s+|\n\s*\d+\.|;\s*/).map(s => s.trim()).filter(Boolean);
        return parts.length > 1 ? parts : [v];
    }
    return [v];
}

function safeString(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'string') return v;
    try {
        return String(v);
    } catch (err) {
        return JSON.stringify(v);
    }
}

function normalizeParsed(parsed) {
    // Normalize common list fields to arrays
    const listFields = [
        'key_insights', 'recommendations', 'decisions', 'next_best_actions', 'risk_alerts',
        'recommendations_for_user', 'recommendations_for_user_products'
    ];
    listFields.forEach(f => {
        if (parsed[f] && !Array.isArray(parsed[f])) {
            // If it's an object with numeric keys, convert to array
            if (typeof parsed[f] === 'object') {
                parsed[f] = Object.values(parsed[f]);
            } else {
                parsed[f] = [parsed[f]];
            }
        }
    });

    // Ensure nested objects exist
    parsed.traffic_insights = parsed.traffic_insights || {};
    parsed.conversion_analysis = parsed.conversion_analysis || {};
}
