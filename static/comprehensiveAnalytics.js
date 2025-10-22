/**
 * Comprehensive Analytics UI Handler
 * Handles all new analytics endpoints and displays results
 */

(function() {
    'use strict';

    const token = localStorage.getItem('token');
    
    // Utility: Show/hide elements
    function show(el) {
        if (typeof el === 'string') el = document.getElementById(el);
        if (el) el.classList.remove('hidden');
    }
    
    function hide(el) {
        if (typeof el === 'string') el = document.getElementById(el);
        if (el) el.classList.add('hidden');
    }
    
    // Utility: API fetch with auth
    async function fetchAPI(url, options = {}) {
        const headers = options.headers || {};
        headers['Authorization'] = token;
        headers['Content-Type'] = 'application/json';
        
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    }
    
    // Utility: Display status message
    function showStatus(message, isError = false) {
        const output = document.getElementById('output');
        if (output) {
            output.textContent = message;
            output.style.color = isError ? '#e74c3c' : '#27ae60';
        }
    }
    
    // Utility: Show empty state
    function showEmptyState(containerId, message = 'No data available') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <p class="empty-message">${message}</p>
                    <button class="analytics-btn" onclick="window.location.reload()">Refresh Page</button>
                </div>
            `;
        }
    }
    
    // Helper: Switch to specific tab
    function switchToTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.querySelector(`[data-tab="${tabId}"]`)?.classList.add('active');
        document.getElementById(tabId)?.classList.add('active');
    }
    
    // Tab Switching Logic
    function initTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-tab');
                switchToTab(tabId);
            });
        });
    }
    
    // Utility: Show toast notification
    function showToast(message, duration = 3000) {
        // Remove existing toast if any
        const existingToast = document.getElementById('analyticsToast');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.id = 'analyticsToast';
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            animation: slideInUp 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    // Add animation styles
    if (!document.getElementById('toastAnimations')) {
        const style = document.createElement('style');
        style.id = 'toastAnimations';
        style.textContent = `
            @keyframes slideInUp {
                from { transform: translateY(100px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            @keyframes slideOutDown {
                from { transform: translateY(0); opacity: 1; }
                to { transform: translateY(100px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // ===== SEO & Traffic Analysis =====
    async function runSEOAnalysis() {
        try {
            lastRefreshModule = 'seo'; // Track last used module
            showStatus('🔍 Running SEO & Traffic Analysis...');
            const result = await fetchAPI('/api/analytics/seo');
            
            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }
            
            show('comprehensiveResults');
            switchToTab('seoResults');
            
            // Traffic by Source
            displayTrafficBySource(result.traffic_by_source || []);
            
            // Landing Pages
            displayLandingPages(result.landing_pages || []);
            
            // Conversion by Source
            displayConversionBySource(result.conversion_by_source || []);
            
            // Hourly Traffic
            displayHourlyTraffic(result.hourly_traffic || []);
            
            showStatus('✅ SEO Analysis Complete');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    function displayTrafficBySource(data) {
        const container = document.getElementById('trafficBySource');
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <h4>📊 Traffic by Source</h4>
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <p class="empty-message">No traffic data available yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <h4>📊 Traffic by Source</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Sessions</th>
                        <th>Events</th>
                        <th>Users</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(row => `
                        <tr>
                            <td><strong>${row.source}</strong></td>
                            <td>${row.sessions.toLocaleString()}</td>
                            <td>${row.events.toLocaleString()}</td>
                            <td>${row.unique_users.toLocaleString()}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    function displayLandingPages(data) {
        const container = document.getElementById('landingPages');
        container.innerHTML = `
            <h4>🎯 Top Landing Pages</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Page</th>
                        <th>Sessions</th>
                        <th>Avg Events</th>
                        <th>Conversion</th>
                        <th>Bounce Rate</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.slice(0, 10).map(row => `
                        <tr>
                            <td><code>${row.page}</code></td>
                            <td>${row.sessions}</td>
                            <td>${row.avg_events.toFixed(1)}</td>
                            <td class="${row.conversion_rate > 0.1 ? 'good' : ''}">${(row.conversion_rate * 100).toFixed(1)}%</td>
                            <td class="${row.bounce_rate < 0.3 ? 'good' : 'warning'}">${(row.bounce_rate * 100).toFixed(1)}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    function displayConversionBySource(data) {
        const container = document.getElementById('conversionBySource');
        container.innerHTML = `
            <h4>💰 Conversion by Source</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Total Sessions</th>
                        <th>Conversions</th>
                        <th>Rate</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(row => `
                        <tr>
                            <td><strong>${row.source}</strong></td>
                            <td>${row.total_sessions}</td>
                            <td>${row.conversion_sessions}</td>
                            <td class="${row.conversion_rate_pct > 10 ? 'good' : ''}">${row.conversion_rate_pct}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    function displayHourlyTraffic(data) {
        const container = document.getElementById('hourlyTraffic');
        
        // Group by hour
        const byHour = {};
        data.forEach(row => {
            if (!byHour[row.hour]) byHour[row.hour] = [];
            byHour[row.hour].push(row);
        });
        
        container.innerHTML = `
            <h4>⏰ Peak Traffic Hours</h4>
            <div class="chart-container">
                ${Object.keys(byHour).sort((a, b) => parseInt(a) - parseInt(b)).map(hour => {
                    const total = byHour[hour].reduce((sum, r) => sum + r.sessions, 0);
                    const maxSessions = Math.max(...Object.values(byHour).map(h => h.reduce((s, r) => s + r.sessions, 0)));
                    const width = (total / maxSessions * 100).toFixed(1);
                    return `
                        <div class="bar-chart-row">
                            <span class="bar-label">${hour}:00</span>
                            <div class="bar-fill" style="width: ${width}%"></div>
                            <span class="bar-value">${total}</span>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    // ===== Cart Abandonment Analysis =====
    async function runCartAnalysis() {
        try {
            lastRefreshModule = 'cart'; // Track last used module
            showStatus('🛒 Running Cart Abandonment Analysis...');
            const result = await fetchAPI('/api/analytics/cart-abandonment');
            
            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }
            
            show('comprehensiveResults');
            switchToTab('cartResults');
            
            displayAbandonment(result);
            
            showStatus('✅ Cart Analysis Complete');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    function displayAbandonment(data) {
        // Abandonment Rate
        document.getElementById('abandonmentRate').innerHTML = `
            <h4>📉 Abandonment Overview</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">Total Carts</div>
                    <div class="stat-value">${data.total_carts}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Abandoned</div>
                    <div class="stat-value warning">${data.abandoned_carts}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Completed</div>
                    <div class="stat-value good">${data.completed_carts}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Abandonment Rate</div>
                    <div class="stat-value ${data.abandonment_rate > 60 ? 'warning' : ''}">${data.abandonment_rate}%</div>
                </div>
            </div>
        `;
        
        // Cart Value Comparison
        document.getElementById('cartValueComparison').innerHTML = `
            <h4>💵 Cart Value Analysis</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">Avg Abandoned Value</div>
                    <div class="stat-value">$${data.avg_abandoned_value}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Avg Completed Value</div>
                    <div class="stat-value good">$${data.avg_completed_value}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Avg Abandoned Size</div>
                    <div class="stat-value">${data.avg_abandoned_size} items</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Avg Completed Size</div>
                    <div class="stat-value">${data.avg_completed_size} items</div>
                </div>
            </div>
        `;
        
        // Most Abandoned Products
        document.getElementById('abandonedProducts').innerHTML = `
            <h4>🎯 Most Abandoned Products</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Price</th>
                        <th>Abandoned Count</th>
                    </tr>
                </thead>
                <tbody>
                    ${(data.most_abandoned_products || []).map(p => `
                        <tr>
                            <td><strong>${p.product_name}</strong></td>
                            <td>${p.category}</td>
                            <td>$${p.price}</td>
                            <td class="warning">${p.abandoned_count}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    // ===== Retention Analysis =====
    async function runRetentionAnalysis() {
        try {
            lastRefreshModule = 'retention'; // Track last used module
            showStatus('📈 Running Retention Analysis...');
            const result = await fetchAPI('/api/analytics/retention');
            
            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }
            
            show('comprehensiveResults');
            switchToTab('retentionResults');
            
            displayRetention(result);
            
            showStatus('✅ Retention Analysis Complete');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    function displayRetention(data) {
        // Cohort Table
        document.getElementById('cohortTable').innerHTML = `
            <h4>📅 Cohort Analysis</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Cohort</th>
                        <th>Size</th>
                        <th>Week 1</th>
                        <th>Week 2</th>
                        <th>Month 1</th>
                    </tr>
                </thead>
                <tbody>
                    ${(data.cohorts || []).map(c => `
                        <tr>
                            <td><strong>${c.cohort_date}</strong></td>
                            <td>${c.cohort_size}</td>
                            <td class="${c.retention_week1 > 50 ? 'good' : 'warning'}">${c.retention_week1}%</td>
                            <td class="${c.retention_week2 > 40 ? 'good' : 'warning'}">${c.retention_week2}%</td>
                            <td class="${c.retention_month1 > 30 ? 'good' : 'warning'}">${c.retention_month1}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
        
        // Average Retention
        const avg = data.average_retention || {};
        document.getElementById('retentionMetrics').innerHTML = `
            <h4>📊 Average Retention</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">Week 1</div>
                    <div class="stat-value">${avg.week1}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Week 2</div>
                    <div class="stat-value">${avg.week2}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Month 1</div>
                    <div class="stat-value">${avg.month1}%</div>
                </div>
            </div>
        `;
        
        // User Segments
        document.getElementById('userSegments').innerHTML = `
            <h4>👥 User Segments</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Segment</th>
                        <th>User Count</th>
                    </tr>
                </thead>
                <tbody>
                    ${(data.user_segments || []).map(s => `
                        <tr>
                            <td><strong>${s.segment}</strong></td>
                            <td class="${s.segment === 'Active' ? 'good' : s.segment === 'Churned' ? 'warning' : ''}">${s.user_count}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    // ===== Customer Journey Analysis =====
    async function runJourneyAnalysis() {
        try {
            lastRefreshModule = 'journey'; // Track last used module
            showStatus('🗺️ Running Customer Journey Analysis...');
            const result = await fetchAPI('/api/analytics/customer-journey');
            
            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }
            
            show('comprehensiveResults');
            switchToTab('journeyResults');
            
            displayJourney(result);
            
            showStatus('✅ Journey Analysis Complete');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    function displayJourney(data) {
        // Conversion Paths
        document.getElementById('conversionPaths').innerHTML = `
            <h4>✅ Successful Conversion Paths</h4>
            <div class="path-list">
                ${(data.conversion_paths || []).slice(0, 10).map(p => `
                    <div class="path-item">
                        <div class="path-badge">${p.path_length} steps</div>
                        <div class="path-text">${p.path}</div>
                    </div>
                `).join('')}
            </div>
        `;
        
        // Drop-off Points
        document.getElementById('dropoffPoints').innerHTML = `
            <h4>⚠️ Common Drop-off Points</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Page</th>
                        <th>Dropouts</th>
                        <th>Avg Events Before</th>
                    </tr>
                </thead>
                <tbody>
                    ${(data.dropoff_points || []).map(d => `
                        <tr>
                            <td><code>${d.page}</code></td>
                            <td class="warning">${d.dropout_count}</td>
                            <td>${d.avg_events_before}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
        
        // Path Statistics
        const stats = data.path_statistics || {};
        document.getElementById('pathStatistics').innerHTML = `
            <h4>📊 Path Statistics</h4>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">Avg Path Length</div>
                    <div class="stat-value">${stats.avg_path_length}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Min Path</div>
                    <div class="stat-value good">${stats.min_path_length}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Max Path</div>
                    <div class="stat-value">${stats.max_path_length}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Median Path</div>
                    <div class="stat-value">${stats.median_path_length}</div>
                </div>
            </div>
        `;
        
        // Common Sequences
        document.getElementById('commonSequences').innerHTML = `
            <h4>🔄 Common Page Sequences</h4>
            <div class="analytics-table-container">
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Sequence</th>
                        <th>Frequency</th>
                    </tr>
                </thead>
                <tbody>
                    ${(data.common_sequences || []).map(s => `
                        <tr>
                            <td><code>${s.sequence}</code></td>
                            <td>${s.frequency}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    }
    
    // ===== Product Recommendations =====
    async function runRecommendations() {
        try {
            lastRefreshModule = 'recommendations'; // Track last used module
            // Get current username from /api/me
            showStatus('⭐ Getting Recommendations...');
            const me = await fetchAPI('/api/me');
            const username = me.username;
            
            const result = await fetchAPI(`/api/analytics/recommendations/${username}`);
            
            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }
            
            show('comprehensiveResults');
            switchToTab('recommendationsResults');
            
            displayRecommendations(result);
            
            showStatus('✅ Recommendations Generated');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    function displayRecommendations(data) {
        document.getElementById('alsRecommendations').innerHTML = `
            <h4>⭐ Personalized Recommendations</h4>
            <p><strong>Algorithm:</strong> ${data.algorithm || 'ALS'} | <strong>RMSE:</strong> ${data.rmse || 'N/A'}</p>
            <div class="recommendations-grid">
                ${(data.recommendations || []).map(rec => `
                    <div class="recommendation-card">
                        <h5>${rec.product_name}</h5>
                        <p><strong>Category:</strong> ${rec.category}</p>
                        <p><strong>Price:</strong> $${rec.price}</p>
                        <p><strong>Predicted Score:</strong> <span class="badge good">${rec.predicted_rating}</span></p>
                        <p class="reason">${rec.reason}</p>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // ===== Run All Analytics =====
    async function runAllAnalytics() {
        try {
            showStatus('🚀 Running Comprehensive Analytics...');
            
            const result = await fetchAPI('/api/analytics/comprehensive', {
                method: 'POST',
                body: JSON.stringify({
                    modules: ['seo', 'cart', 'retention', 'journey']
                })
            });
            
            show('comprehensiveResults');
            
            // Display each module's results
            if (result.results.seo) {
                show('seoResults');
                displayTrafficBySource(result.results.seo.traffic_by_source || []);
                displayLandingPages(result.results.seo.landing_pages || []);
                displayConversionBySource(result.results.seo.conversion_by_source || []);
                displayHourlyTraffic(result.results.seo.hourly_traffic || []);
            }
            
            if (result.results.cart) {
                show('cartResults');
                displayAbandonment(result.results.cart);
            }
            
            if (result.results.retention) {
                show('retentionResults');
                displayRetention(result.results.retention);
            }
            
            if (result.results.journey) {
                show('journeyResults');
                displayJourney(result.results.journey);
            }
            
            showStatus('✅ All Analytics Complete');
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }
    
    // ===== Event Listeners =====
    document.addEventListener('DOMContentLoaded', () => {
        // Comprehensive Analytics Buttons
        const runAllBtn = document.getElementById('runAllAnalyticsBtn');
        const seoBtn = document.getElementById('seoAnalyticsBtn');
        const cartBtn = document.getElementById('cartAnalyticsBtn');
        const retentionBtn = document.getElementById('retentionAnalyticsBtn');
        const journeyBtn = document.getElementById('journeyAnalyticsBtn');
        const recsBtn = document.getElementById('recommendationsBtn');
        
        if (runAllBtn) runAllBtn.addEventListener('click', runAllAnalytics);
        if (seoBtn) seoBtn.addEventListener('click', runSEOAnalysis);
        if (cartBtn) cartBtn.addEventListener('click', runCartAnalysis);
        if (retentionBtn) retentionBtn.addEventListener('click', runRetentionAnalysis);
        if (journeyBtn) journeyBtn.addEventListener('click', runJourneyAnalysis);
        if (recsBtn) recsBtn.addEventListener('click', runRecommendations);
    });
    
    // ===== Auto-refresh when data is updated =====
    let lastRefreshModule = null;
    let refreshDebounceTimer = null;
    
    window.addEventListener('dataUpdated', (event) => {
        console.log('📊 Data updated, refreshing analytics...', event.detail);
        
        // Show notification
        showToast('🔄 New data detected! Refreshing analytics in 2 seconds...', 2000);
        
        // Clear previous debounce timer
        if (refreshDebounceTimer) {
            clearTimeout(refreshDebounceTimer);
        }
        
        // Debounce refresh to avoid multiple rapid calls
        refreshDebounceTimer = setTimeout(() => {
            // Check which sections are currently visible
            const seoVisible = !document.getElementById('seoResults')?.classList.contains('hidden');
            const cartVisible = !document.getElementById('cartResults')?.classList.contains('hidden');
            const retentionVisible = !document.getElementById('retentionResults')?.classList.contains('hidden');
            const journeyVisible = !document.getElementById('journeyResults')?.classList.contains('hidden');
            const recsVisible = !document.getElementById('recommendationsResults')?.classList.contains('hidden');
            
            let refreshed = false;
            
            // Refresh visible sections
            if (seoVisible) {
                console.log('🔄 Auto-refreshing SEO analytics...');
                runSEOAnalysis();
                refreshed = true;
            }
            if (cartVisible) {
                console.log('🔄 Auto-refreshing Cart analytics...');
                runCartAnalysis();
                refreshed = true;
            }
            if (retentionVisible) {
                console.log('🔄 Auto-refreshing Retention analytics...');
                runRetentionAnalysis();
                refreshed = true;
            }
            if (journeyVisible) {
                console.log('🔄 Auto-refreshing Journey analytics...');
                runJourneyAnalysis();
                refreshed = true;
            }
            if (recsVisible) {
                console.log('🔄 Auto-refreshing Recommendations...');
                runRecommendations();
                refreshed = true;
            }
            
            // If nothing is visible but comprehensive results is, refresh the last used module
            const comprehensiveVisible = !document.getElementById('comprehensiveResults')?.classList.contains('hidden');
            if (comprehensiveVisible && !refreshed && lastRefreshModule) {
                console.log('🔄 Refreshing last used module:', lastRefreshModule);
                switch(lastRefreshModule) {
                    case 'seo': runSEOAnalysis(); break;
                    case 'cart': runCartAnalysis(); break;
                    case 'retention': runRetentionAnalysis(); break;
                    case 'journey': runJourneyAnalysis(); break;
                    case 'recommendations': runRecommendations(); break;
                }
                refreshed = true;
            }
            
            if (refreshed) {
                showToast('✅ Analytics refreshed with latest data!', 2000);
            }
        }, 2000); // Wait 2 seconds after last data update
    });
    
    // Setup Event Listeners
    function setupEventListeners() {
        // Run All Analytics
        const runAllBtn = document.getElementById('runAllAnalyticsBtn');
        if (runAllBtn) {
            runAllBtn.addEventListener('click', async () => {
                show('comprehensiveResults');
                await runSEOAnalysis();
                await runCartAnalysis();
                await runRetentionAnalysis();
                await runJourneyAnalysis();
                await runRecommendations();
            });
        }
        
        // Individual Analytics Buttons
        const seoBtn = document.getElementById('seoAnalyticsBtn');
        if (seoBtn) {
            seoBtn.addEventListener('click', () => {
                show('comprehensiveResults');
                runSEOAnalysis();
            });
        }
        
        const cartBtn = document.getElementById('cartAnalyticsBtn');
        if (cartBtn) {
            cartBtn.addEventListener('click', () => {
                show('comprehensiveResults');
                runCartAnalysis();
            });
        }
        
        const retentionBtn = document.getElementById('retentionAnalyticsBtn');
        if (retentionBtn) {
            retentionBtn.addEventListener('click', () => {
                show('comprehensiveResults');
                runRetentionAnalysis();
            });
        }
        
        const journeyBtn = document.getElementById('journeyAnalyticsBtn');
        if (journeyBtn) {
            journeyBtn.addEventListener('click', () => {
                show('comprehensiveResults');
                runJourneyAnalysis();
            });
        }
        
        const recsBtn = document.getElementById('recommendationsBtn');
        if (recsBtn) {
            recsBtn.addEventListener('click', () => {
                show('comprehensiveResults');
                runRecommendations();
            });
        }
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initTabSwitching();
            setupEventListeners();
        });
    } else {
        initTabSwitching();
        setupEventListeners();
    }
    
})();
