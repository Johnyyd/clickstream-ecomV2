/**
 * Comprehensive Analytics UI Handler
 * Handles all new analytics endpoints and displays results
 */

(function () {
    'use strict';

    const token = localStorage.getItem('token');
    // Persistence keys for analytics
    const ANALYTICS_KEYS = {
        seo: 'analytics:seo',
        cart: 'analytics:cart',
        retention: 'analytics:retention',
        journey: 'analytics:journey',
        recommendations: 'analytics:recommendations',
        comprehensive: 'analytics:comprehensive'
    };

    // Save analytics result to localStorage with timestamp
    function saveAnalytics(moduleName, data) {
        try {
            const payload = { ts: Date.now(), data };
            const key = ANALYTICS_KEYS[moduleName];
            if (key) localStorage.setItem(key, JSON.stringify(payload));
        } catch (e) {
            console.warn('Failed to save analytics to localStorage', e);
        }
    }

    // Load analytics result from localStorage
    function loadAnalytics(moduleName) {
        try {
            const key = ANALYTICS_KEYS[moduleName];
            if (!key) return null;
            const raw = localStorage.getItem(key);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            return parsed && parsed.data ? parsed.data : null;
        } catch (e) {
            console.warn('Failed to load analytics from localStorage', e);
            return null;
        }
    }

    // Clear all stored analytics data
    function clearStoredAnalytics() {
        Object.values(ANALYTICS_KEYS).forEach(k => localStorage.removeItem(k));
    }

    // Detect hard-reload key combos (Ctrl+Shift+R or Ctrl+F5) before the reload occurs.
    // On detection we set a short-lived sessionStorage flag so the next load can clear stored analytics.
    window.addEventListener('keydown', (e) => {
        // e.key may be 'R' or 'F5'
        const isCtrl = e.ctrlKey || e.metaKey;
        const isShift = e.shiftKey;
        const key = (e.key || '').toLowerCase();

        // Ctrl+Shift+R (Chrome/Edge) or Ctrl+F5 (some browsers)
        if (isCtrl && isShift && key === 'r') {
            sessionStorage.setItem('clearOnLoad', '1');
            // allow reload to proceed
        }
        if (isCtrl && !isShift && key === 'f5') {
            // treat Ctrl+F5 as hard reload
            sessionStorage.setItem('clearOnLoad', '1');
        }
    }, { passive: true });

    // On page load, if the 'clearOnLoad' flag is set, clear stored analytics and remove the flag.
    function handleClearOnLoadFlag() {
        try {
            const flag = sessionStorage.getItem('clearOnLoad');
            if (flag) {
                clearStoredAnalytics();
                sessionStorage.removeItem('clearOnLoad');
                console.log('Cleared persisted analytics due to hard reload flag');
            }
        } catch (e) {
            console.warn('Error handling clearOnLoad flag', e);
        }
    }

    // Load any stored analytics into the UI (called on DOMContentLoaded)
    function loadStoredAnalyticsToUI() {
        try {
            // If comprehensive result exists, prefer to render it (it contains modules)
            const comprehensive = loadAnalytics('comprehensive');
            if (comprehensive && comprehensive.results) {
                show('comprehensiveResults');
                const res = comprehensive.results;
                if (res.seo) {
                    show('seoResults');
                    displayTrafficBySource(res.seo.traffic_by_source || [], res.seo);
                    displayLandingPages(res.seo.landing_pages || []);
                    displayConversionBySource(res.seo.conversion_by_source || []);
                    displayHourlyTraffic(res.seo.hourly_traffic || []);
                }
                if (res.cart) {
                    show('cartResults');
                    displayAbandonment(res.cart);
                }
                if (res.retention) {
                    show('retentionResults');
                    displayRetention(res.retention);
                }
                if (res.journey) {
                    show('journeyResults');
                    displayJourney(res.journey);
                }
                return;
            }

            // Otherwise load per-module stored results
            const seo = loadAnalytics('seo');
            if (seo) {
                show('comprehensiveResults');
                show('seoResults');
                displayTrafficBySource(seo.traffic_by_source || [], seo);
                displayLandingPages(seo.landing_pages || []);
                displayConversionBySource(seo.conversion_by_source || []);
                displayHourlyTraffic(seo.hourly_traffic || []);
            }

            const cart = loadAnalytics('cart');
            if (cart) {
                show('comprehensiveResults');
                show('cartResults');
                displayAbandonment(cart);
            }

            const retention = loadAnalytics('retention');
            if (retention) {
                show('comprehensiveResults');
                show('retentionResults');
                displayRetention(retention);
            }

            const journey = loadAnalytics('journey');
            if (journey) {
                show('comprehensiveResults');
                show('journeyResults');
                displayJourney(journey);
            }

            const recs = loadAnalytics('recommendations');
            if (recs) {
                show('comprehensiveResults');
                show('recommendationsResults');
                displayRecommendations(recs);
            }
        } catch (e) {
            console.warn('Failed to load stored analytics to UI', e);
        }
    }

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

        // Subtab switching
        const subtabButtons = document.querySelectorAll('.subtab-btn');
        subtabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Get parent section
                const parentSection = btn.closest('.analytics-section');
                if (!parentSection) return;

                // Remove active from all subtabs in this section
                parentSection.querySelectorAll('.subtab-btn').forEach(b => b.classList.remove('active'));
                parentSection.querySelectorAll('.subtab-content').forEach(c => c.classList.remove('active'));

                // Add active to clicked button
                btn.classList.add('active');

                // Show corresponding content
                const subtabId = btn.getAttribute('data-subtab');
                const subtabContent = document.getElementById(subtabId);
                if (subtabContent) {
                    subtabContent.classList.add('active');
                }
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
            const uname = (document.getElementById('analyticsUsername')?.value || '').trim();
            const url = uname ? `/api/analytics/seo?username=${encodeURIComponent(uname)}` : '/api/analytics/seo';
            const result = await fetchAPI(url);

            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }

            show('comprehensiveResults');
            switchToTab('seoResults');

            // Traffic by Source with Chart
            displayTrafficBySource(result.traffic_by_source || [], result);

            // Landing Pages
            displayLandingPages(result.landing_pages || []);

            // Conversion by Source
            displayConversionBySource(result.conversion_by_source || []);

            // Hourly Traffic
            displayHourlyTraffic(result.hourly_traffic || []);

            showStatus('✅ SEO Analysis Complete');
            // Persist SEO results so they survive a normal reload (F5)
            saveAnalytics('seo', result);
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }

    function displayTrafficBySource(data, fullResult) {
        const container = document.getElementById('trafficBySource');

        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <p class="empty-message">No traffic data available yet</p>
                    <p style="font-size: 0.9em; color: #7f8c8d;">Run SEO analysis to see traffic sources</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h4>📊 Traffic by Source / Nguồn lưu lượng</h4>
            <div id="seoChartContainer"></div>
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

        // Render SEO chart if available
        if (window.MLCharts && window.MLCharts.createSEOChart && fullResult) {
            const chartContainer = document.getElementById('seoChartContainer');
            if (chartContainer) {
                window.MLCharts.createSEOChart(chartContainer, fullResult);
            }
        }
    }

    function displayLandingPages(data) {
        const container = document.getElementById('landingPages');
        container.innerHTML = `
            <h4>🎯 Top Landing Pages / Trang đích hàng đầu</h4>
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
            <h4>💰 Conversion by Source / Chuyển đổi theo nguồn</h4>
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
            <h4>⏰ Peak Traffic Hours / Giờ cao điểm</h4>
            <div class="chart-container">
                ${Object.keys(byHour).sort((a, b) => parseInt(a) - parseInt(b)).map(hour => {
            const total = byHour[hour].reduce((sum, r) => sum + r.sessions, 0);
            const maxSessions = Math.max(...Object.values(byHour).map(h => h.reduce((s, r) => s + r.sessions, 0)));
            const width = (total / maxSessions * 100).toFixed(1);
            return `
                        <div class="bar-chart-row" scrollbar-x="true">
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
            const uname = (document.getElementById('analyticsUsername')?.value || '').trim();
            const url = uname ? `/api/analytics/cart-abandonment?username=${encodeURIComponent(uname)}` : '/api/analytics/cart-abandonment';
            const result = await fetchAPI(url);

            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }

            show('comprehensiveResults');
            switchToTab('cartResults');

            displayAbandonment(result);

            showStatus('✅ Cart Analysis Complete');
            // Persist Cart results
            saveAnalytics('cart', result);
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }

    function displayAbandonment(data) {
        // Abandonment Rate
        document.getElementById('abandonmentRate').innerHTML = `
            <h4>📉 Abandonment Overview / Tổng quan hủy đơn</h4>
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
            <h4>💵 Cart Value Analysis / Phân tích giá trị giỏ hàng</h4>
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
            <h4>🎯 Most Abandoned Products / Sản phẩm bị bỏ lại nhiều nhất</h4>
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
            const uname = (document.getElementById('analyticsUsername')?.value || '').trim();
            const url = uname ? `/api/analytics/retention?username=${encodeURIComponent(uname)}` : '/api/analytics/retention';
            const result = await fetchAPI(url);

            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }

            show('comprehensiveResults');
            switchToTab('retentionResults');

            displayRetention(result);

            showStatus('✅ Retention Analysis Complete');
            // Persist Retention results
            saveAnalytics('retention', result);
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }

    function displayRetention(data) {
        // Cohort Table
        document.getElementById('cohortTable').innerHTML = `
            <h4>📅 Cohort Analysis / Phân tích dữ liệu tổ hợp</h4>
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
            <h4>📊 Average Retention / Tỷ lệ giữ chân trung bình</h4>
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
            <h4>👥 User Segments / Phân khúc người dùng</h4>
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
            const uname = (document.getElementById('analyticsUsername')?.value || '').trim();
            const url = uname ? `/api/analytics/customer-journey?username=${encodeURIComponent(uname)}` : '/api/analytics/customer-journey';
            const result = await fetchAPI(url);

            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                return;
            }

            show('comprehensiveResults');
            switchToTab('journeyResults');

            displayJourney(result);

            showStatus('✅ Journey Analysis Complete');
            // Persist Journey results
            saveAnalytics('journey', result);
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
        }
    }

    function displayJourney(data) {
        // Conversion Paths
        document.getElementById('conversionPaths').innerHTML = `
            <h4>✅ Successful Conversion Paths / Lộ trình chuyển đổi thành công</h4>
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
            <h4>⚠️ Common Drop-off Points / Điểm rời bỏ phổ biến</h4>
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
            <h4>📊 Path Statistics / Thống kê lộ trình</h4>
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
            <h4>🔄 Common Page Sequences / Chuỗi trang phổ biến</h4>
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
        const container = document.getElementById('alsRecommendations');

        try {
            lastRefreshModule = 'recommendations'; // Track last used module

            // Show loading state
            showStatus('⭐ Getting Recommendations...');
            container.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Loading Product Recommendations...</p>
                    <p style="font-size: 0.9em; color: #7f8c8d; margin-top: 10px;">This may take a few seconds</p>
                </div>
            `;

            // Prefer input username, fallback to current user from /api/me
            let username = (document.getElementById('analyticsUsername')?.value || '').trim();
            if (!username) {
                const me = await fetchAPI('/api/me');
                username = me.username;
            }
            const result = await fetchAPI(`/api/analytics/recommendations/${encodeURIComponent(username)}`);

            if (result.error) {
                showStatus(`❌ Error: ${result.error}`, true);
                displayRecommendations(result); // Show error state
                return;
            }

            show('comprehensiveResults');
            switchToTab('recommendationsResults');

            displayRecommendations(result);

            showStatus('✅ Recommendations Generated');
            showToast('✅ Product recommendations loaded successfully');
            // Persist recommendations for reload
            saveAnalytics('recommendations', result);
        } catch (error) {
            showStatus(`❌ ${error.message}`, true);
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <p class="error-message">Failed to load recommendations</p>
                    <p style="color: #7f8c8d;">${error.message}</p>
                    <button class="analytics-btn" onclick="location.reload()">Retry</button>
                </div>
            `;
        }
    }

    function displayRecommendations(data) {
        const container = document.getElementById('alsRecommendations');

        // Handle errors
        if (data.error) {
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <p class="error-message">${data.error}</p>
                    ${data.suggestions ? `
                        <div class="suggestions">
                            <h5>Suggestions:</h5>
                            <ul>
                                ${data.suggestions.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
            return;
        }

        // Admin view - show sample recommendations from all users
        if (data.admin_view) {
            const sampleRecs = data.sample_recommendations || [];

            container.innerHTML = `
                <div class="admin-banner">
                    <h4>👑 Admin View: Product Recommendations</h4>
                    <p style="color: #667eea; font-weight: 500;">${data.message || 'Showing recommendations for all users'}</p>
                </div>
                
                <div class="model-info-card">
                    <p><strong>Algorithm:</strong> ${data.algorithm || 'ALS Collaborative Filtering'}</p>
                    <p><strong>RMSE:</strong> ${data.rmse || 'N/A'}</p>
                    <p><strong>Total Users with Recommendations:</strong> ${data.total_users_with_recs || 0}</p>
                    <p><strong>Model Info:</strong> ${data.model_info?.total_users || 0} users, ${data.model_info?.total_products || 0} products, ${data.model_info?.total_interactions?.toLocaleString() || 0} interactions</p>
                </div>
                
                <div id="alsChartContainer"></div>
                
                <h5 style="margin-top: 20px;">📋 Sample Recommendations (Top ${sampleRecs.length} Users)</h5>
                ${sampleRecs.length === 0 ? `
                    <div class="empty-state">
                        <p>No sample recommendations available</p>
                    </div>
                ` : `
                    <div class="user-recommendations-list">
                        ${sampleRecs.map((userRec, idx) => `
                            <div class="user-recommendation-section">
                                <h6>User ${idx + 1} (ID: ${userRec.user_id.substring(0, 8)}...)</h6>
                                <div class="recommendations-grid">
                                    ${(userRec.recommendations || []).map(rec => `
                                        <div class="recommendation-card">
                                            <h5>${rec.product_name || 'Unknown Product'}</h5>
                                            <p><strong>Category:</strong> ${rec.category || 'N/A'}</p>
                                            <p><strong>Price:</strong> $${rec.price || 0}</p>
                                            <p><strong>Predicted Score:</strong> <span class="badge good">${rec.predicted_rating || 0}</span></p>
                                            <p class="reason">${rec.reason || ''}</p>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}
            `;

            // Render ALS chart if MLCharts is available
            if (window.MLCharts && window.MLCharts.createALSChart) {
                const chartContainer = document.getElementById('alsChartContainer');
                if (chartContainer) {
                    window.MLCharts.createALSChart(chartContainer, data);
                }
            }

            return;
        }

        // Regular user view
        const recommendations = data.recommendations || [];

        if (recommendations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⭐</div>
                    <p class="empty-message">No recommendations available yet</p>
                    <p style="font-size: 0.9em; color: #7f8c8d;">More product interactions are needed to generate recommendations</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <h4>⭐ Personalized Recommendations</h4>
            <div class="model-info-card">
                <p><strong>Algorithm:</strong> ${data.algorithm || 'ALS'}</p>
                <p><strong>RMSE:</strong> ${data.rmse || 'N/A'}</p>
                <p><strong>User:</strong> ${data.user || 'Current User'}</p>
                ${data.model_info ? `
                    <p><strong>Model:</strong> ${data.model_info.total_users} users, ${data.model_info.total_products} products</p>
                ` : ''}
            </div>
            <div class="recommendations-grid">
                ${recommendations.map(rec => `
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
            const uname = (document.getElementById('analyticsUsername')?.value || '').trim();
            const result = await fetchAPI('/api/analytics/comprehensive', {
                method: 'POST',
                body: JSON.stringify({
                    modules: ['seo', 'cart', 'retention', 'journey'],
                    username: uname || null
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
            // Persist comprehensive result
            saveAnalytics('comprehensive', result);
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
                switch (lastRefreshModule) {
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
            // Handle hard-reload flag and restore any stored analytics before wiring UI
            handleClearOnLoadFlag();
            loadStoredAnalyticsToUI();
            initTabSwitching();
            setupEventListeners();
        });
    } else {
        handleClearOnLoadFlag();
        loadStoredAnalyticsToUI();
        initTabSwitching();
        setupEventListeners();
    }

})();
