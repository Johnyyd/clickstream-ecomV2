/**
 * ML Algorithm Charts and Visualizations
 * Uses Chart.js to display ML algorithm results
 */

window.MLCharts = window.MLCharts || {};

// Chart instances storage
const chartInstances = {};

// Destroy existing chart if it exists
function destroyChart(chartId) {
    if (chartInstances[chartId]) {
        chartInstances[chartId].destroy();
        delete chartInstances[chartId];
    }
}

// Create ALS Recommendations Chart with Enhanced Metrics
window.MLCharts.createALSChart = function (container, data) {
    // Enhanced metric cards
    const metricsDiv = document.createElement('div');
    metricsDiv.className = 'ml-stats-grid';

    const rmse = data.rmse || 0;
    const totalUsers = data.model_info?.total_users || 0;
    const totalProducts = data.model_info?.total_products || 0;
    const totalInteractions = data.model_info?.total_interactions || 0;

    // Determine RMSE quality
    let rmseQuality = 'poor';
    let rmseText = 'Needs Improvement';
    if (rmse < 0.5) { rmseQuality = 'excellent'; rmseText = 'Excellent'; }
    else if (rmse < 1.0) { rmseQuality = 'good'; rmseText = 'Good'; }
    else if (rmse < 2.0) { rmseQuality = 'fair'; rmseText = 'Fair'; }

    metricsDiv.innerHTML = `
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">📉</span>
                    RMSE Score
                </div>
                <span class="ml-metric-help ml-tooltip" title="Root Mean Square Error">ℹ️
                    <span class="tooltiptext">Root Mean Square Error (RMSE) measures prediction accuracy. Lower values indicate better predictions. <0.5 = Excellent, <1.0 = Good, <2.0 = Fair, ≥2.0 = Poor</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${rmse.toFixed(3)}</span>
                <span class="quality-indicator ${rmseQuality}">
                    ${rmseText}
                </span>
            </div>
            <div class="ml-metric-explanation">
                <strong>Lower is better.</strong> This measures how accurately the model predicts user ratings. An RMSE of ${rmse.toFixed(2)} means predictions are typically off by ±${rmse.toFixed(2)} rating points.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">👥</span>
                    Users Analyzed
                </div>
                <span class="ml-metric-help ml-tooltip" title="Total users in model">ℹ️
                    <span class="tooltiptext">Number of unique users included in the recommendation model. More users generally lead to better recommendations.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${totalUsers.toLocaleString()}</span>
                <span class="ml-metric-unit">users</span>
            </div>
            <div class="ml-metric-explanation">
                The model has learned preferences from <strong>${totalUsers.toLocaleString()} users</strong>.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🛍️</span>
                    Products Covered
                </div>
                <span class="ml-metric-help ml-tooltip" title="Total products in catalog">ℹ️
                    <span class="tooltiptext">Number of unique products the model can recommend. Higher coverage means more diverse recommendations.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${totalProducts.toLocaleString()}</span>
                <span class="ml-metric-unit">products</span>
            </div>
            <div class="ml-metric-explanation">
                Can recommend from a catalog of <strong>${totalProducts.toLocaleString()} products</strong>.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🔗</span>
                    Total Interactions
                </div>
                <span class="ml-metric-help ml-tooltip" title="User-product interactions">ℹ️
                    <span class="tooltiptext">Total number of user-product interactions (views, purchases, ratings) used to train the model. More interactions lead to better recommendations.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(totalInteractions / 1000).toFixed(1)}K</span>
                <span class="ml-metric-unit">interactions</span>
            </div>
            <div class="ml-metric-subvalue">
                ${(totalInteractions / totalUsers).toFixed(1)} interactions per user
            </div>
            <div class="ml-metric-explanation">
                Model trained on <strong>${totalInteractions.toLocaleString()} interactions</strong>.
            </div>
        </div>
    `;
    container.appendChild(metricsDiv);

    // Enhanced chart
    const chartDiv = document.createElement('div');
    chartDiv.className = 'ml-chart-container';
    chartDiv.innerHTML = `
        <div class="ml-chart-title">
            <span>📊</span>
            ALS Model Statistics
        </div>
        <div class="ml-chart-subtitle">
            Overview of the Alternating Least Squares collaborative filtering model performance and coverage
        </div>
        <canvas id="alsChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('alsChart');

    const ctx = document.getElementById('alsChart').getContext('2d');
    chartInstances['alsChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['RMSE', 'Users (100s)', 'Products (100s)', 'Interactions (1000s)'],
            datasets: [{
                label: 'ALS Model Metrics',
                data: [
                    rmse,
                    totalUsers / 100,
                    totalProducts / 100,
                    totalInteractions / 1000
                ],
                backgroundColor: [
                    'rgba(231, 76, 60, 0.7)',
                    'rgba(52, 152, 219, 0.7)',
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(155, 89, 182, 0.7)'
                ],
                borderColor: [
                    'rgb(231, 76, 60)',
                    'rgb(52, 152, 219)',
                    'rgb(46, 204, 113)',
                    'rgb(155, 89, 182)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.95)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function (context) {
                            let label = context.label || '';
                            let value = context.parsed.y;

                            if (label === 'RMSE') {
                                return `RMSE: ${value.toFixed(3)} (${value < 1 ? 'Good' : 'Needs Improvement'})`;
                            } else if (label.includes('Users')) {
                                return `Users: ${(value * 100).toLocaleString()}`;
                            } else if (label.includes('Products')) {
                                return `Products: ${(value * 100).toLocaleString()}`;
                            } else {
                                return `Interactions: ${(value * 1000).toLocaleString()}`;
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Scaled Values',
                        font: {
                            weight: '600'
                        }
                    }
                }
            }
        }
    });
}

// Create K-Means Clustering Chart with Enhanced Metrics
window.MLCharts.createKMeansChart = function (container, data) {
    if (!data.cluster_stats) return;

    const clusters = Object.keys(data.cluster_stats);
    const clusterData = clusters.map(c => data.cluster_stats[c]);

    // Calculate silhouette quality
    const silhouette = data.silhouette_score || 0;
    let qualityClass = 'poor';
    let qualityText = 'Poor';
    if (silhouette > 0.7) { qualityClass = 'excellent'; qualityText = 'Excellent'; }
    else if (silhouette > 0.5) { qualityClass = 'good'; qualityText = 'Good'; }
    else if (silhouette > 0.25) { qualityClass = 'fair'; qualityText = 'Fair'; }

    // Enhanced Stats Grid with Explanations
    const statsDiv = document.createElement('div');
    statsDiv.className = 'ml-stats-grid';
    statsDiv.innerHTML = `
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">👥</span>
                    Total Users
                </div>
                <span class="ml-metric-help ml-tooltip" title="Total number of users analyzed in the clustering">ℹ️
                    <span class="tooltiptext">Total number of unique users included in the clustering analysis. Higher numbers generally lead to more reliable patterns.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(data.total_users || 0).toLocaleString()}</span>
                <span class="ml-metric-unit">users</span>
            </div>
            <div class="ml-metric-explanation">
                This represents the <strong>complete dataset</strong> used for clustering analysis.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🎯</span>
                    Clusters Found
                </div>
                <span class="ml-metric-help ml-tooltip" title="Number of distinct user groups identified">ℹ️
                    <span class="tooltiptext">Number of distinct behavioral groups (clusters) identified by the K-Means algorithm. Each cluster represents users with similar behavior patterns.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${data.num_clusters || 0}</span>
                <span class="ml-metric-unit">groups</span>
            </div>
            <div class="ml-metric-explanation">
                Users are divided into <strong>${data.num_clusters || 0} distinct behavioral segments</strong>.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">📊</span>
                    Silhouette Score
                </div>
                <span class="ml-metric-help ml-tooltip" title="Quality measure of clustering">ℹ️
                    <span class="tooltiptext">Silhouette Score measures clustering quality from -1 to 1. Higher values indicate better-defined clusters. >0.7 = Excellent, >0.5 = Good, >0.25 = Fair, <0.25 = Poor</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${silhouette.toFixed(3)}</span>
                <span class="quality-indicator ${qualityClass}">
                    ${qualityText} Quality
                </span>
            </div>
            <div class="distribution-container">
                <div class="distribution-label">
                    <span>Quality Score</span>
                    <span>${(silhouette * 100).toFixed(1)}%</span>
                </div>
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${silhouette * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                <strong>Higher is better.</strong> This score indicates how well-separated and cohesive the clusters are.
            </div>
        </div>
    `;
    container.appendChild(statsDiv);

    // Cluster comparison chart
    const chartDiv = document.createElement('div');
    chartDiv.className = 'ml-chart-container';
    chartDiv.innerHTML = `
        <div class="ml-chart-title">
            <span>📊</span>
            Cluster Comparison
        </div>
        <div class="ml-chart-subtitle">
            Compare user distribution, engagement levels, and conversion rates across different behavioral segments
        </div>
        <canvas id="kmeansChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('kmeansChart');

    const ctx = document.getElementById('kmeansChart').getContext('2d');
    chartInstances['kmeansChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: clusters.map(c => `Cluster ${c}`),
            datasets: [
                {
                    label: 'Users',
                    data: clusterData.map(c => c.user_count),
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgb(52, 152, 219)',
                    borderWidth: 2,
                    yAxisID: 'y'
                },
                {
                    label: 'Avg Events',
                    data: clusterData.map(c => c.avg_events),
                    backgroundColor: 'rgba(46, 204, 113, 0.7)',
                    borderColor: 'rgb(46, 204, 113)',
                    borderWidth: 2,
                    yAxisID: 'y1'
                },
                {
                    label: 'Conversion Rate (%)',
                    data: clusterData.map(c => c.avg_conversion * 100),
                    backgroundColor: 'rgba(155, 89, 182, 0.7)',
                    borderColor: 'rgb(155, 89, 182)',
                    borderWidth: 2,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.95)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        title: function (context) {
                            return context[0].label;
                        },
                        label: function (context) {
                            let label = context.dataset.label || '';
                            let value = context.parsed.y;

                            if (label.includes('Conversion')) {
                                return `${label}: ${value.toFixed(2)}%`;
                            } else if (label.includes('Events')) {
                                return `${label}: ${value.toFixed(1)} events/user`;
                            } else {
                                return `${label}: ${value} users`;
                            }
                        },
                        afterBody: function (context) {
                            const clusterId = context[0].label.split(' ')[1];
                            const cluster = data.cluster_stats[clusterId];
                            return [
                                '',
                                `Cart Rate: ${(cluster.avg_cart_rate * 100).toFixed(2)}%`,
                                `Engagement: ${cluster.avg_events > 10 ? 'High' : cluster.avg_events > 5 ? 'Medium' : 'Low'}`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Users',
                        font: {
                            weight: '600'
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Average Events',
                        font: {
                            weight: '600'
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                },
                y2: {
                    type: 'linear',
                    display: false,
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // Enhanced cluster details grid
    const clusterGrid = document.createElement('div');
    clusterGrid.className = 'cluster-grid';
    clusterGrid.style.marginTop = '32px';

    clusters.forEach(clusterId => {
        const cluster = data.cluster_stats[clusterId];
        const conversionRate = (cluster.avg_conversion * 100).toFixed(2);
        const cartRate = (cluster.avg_cart_rate * 100).toFixed(2);
        const avgEvents = cluster.avg_events.toFixed(1);

        // Determine cluster characteristics
        let clusterType = '';
        let clusterIcon = '';
        if (cluster.avg_conversion > 0.5) {
            clusterType = 'High-Value Converters';
            clusterIcon = '💎';
        } else if (cluster.avg_events > 10) {
            clusterType = 'Highly Engaged Browsers';
            clusterIcon = '🔥';
        } else if (cluster.avg_cart_rate > 0.3) {
            clusterType = 'Cart Abandoners';
            clusterIcon = '🛒';
        } else {
            clusterType = 'Casual Visitors';
            clusterIcon = '👀';
        }

        clusterGrid.innerHTML += `
            <div class="cluster-card">
                <h5>${clusterIcon} Cluster ${clusterId}</h5>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 12px; font-weight: 600;">
                    ${clusterType}
                </div>
                <div class="cluster-stat">
                    <span class="label">👥 Users:</span>
                    <span class="value">${cluster.user_count.toLocaleString()}</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">📊 Avg Events:</span>
                    <span class="value">${avgEvents}</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">💰 Conversion:</span>
                    <span class="value">${conversionRate}%</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">🛒 Cart Rate:</span>
                    <span class="value">${cartRate}%</span>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0;">
                    <div class="distribution-label">
                        <span style="font-size: 11px;">User Distribution</span>
                        <span style="font-size: 11px;">${((cluster.user_count / data.total_users) * 100).toFixed(1)}%</span>
                    </div>
                    <div class="distribution-bar">
                        <div class="distribution-fill" style="width: ${(cluster.user_count / data.total_users) * 100}%"></div>
                    </div>
                </div>
            </div>
        `;
    });
    container.appendChild(clusterGrid);
}

// Create SEO Traffic Chart
window.MLCharts.createSEOChart = function (container, data) {
    if (!data.traffic_by_source || data.traffic_by_source.length === 0) return;

    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <div class="chart-title">📊 Traffic by Source</div>
        <canvas id="seoChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('seoChart');

    const ctx = document.getElementById('seoChart').getContext('2d');
    chartInstances['seoChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.traffic_by_source.map(s => s.source),
            datasets: [{
                data: data.traffic_by_source.map(s => s.sessions),
                backgroundColor: [
                    'rgba(52, 152, 219, 0.7)',
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(155, 89, 182, 0.7)',
                    'rgba(241, 196, 15, 0.7)',
                    'rgba(231, 76, 60, 0.7)'
                ],
                borderColor: [
                    'rgb(52, 152, 219)',
                    'rgb(46, 204, 113)',
                    'rgb(155, 89, 182)',
                    'rgb(241, 196, 15)',
                    'rgb(231, 76, 60)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Create Conversion Funnel Chart
window.MLCharts.createConversionChart = function (container, data) {
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <div class="chart-title">📊 Conversion Funnel</div>
        <canvas id="conversionChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('conversionChart');

    // Sample funnel data
    const funnelData = [
        { stage: 'Visits', value: 1000 },
        { stage: 'Product Views', value: 750 },
        { stage: 'Add to Cart', value: 400 },
        { stage: 'Checkout', value: 200 },
        { stage: 'Purchase', value: 150 }
    ];

    const ctx = document.getElementById('conversionChart').getContext('2d');
    chartInstances['conversionChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: funnelData.map(f => f.stage),
            datasets: [{
                label: 'Users',
                data: funnelData.map(f => f.value),
                backgroundColor: funnelData.map((_, i) =>
                    `rgba(52, 152, 219, ${1 - i * 0.15})`
                ),
                borderColor: 'rgb(52, 152, 219)',
                borderWidth: 2
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Retention Cohort Heatmap
window.MLCharts.createRetentionChart = function (container, data) {
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <div class="chart-title">📊 Cohort Retention Analysis</div>
        <canvas id="retentionChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('retentionChart');

    // Sample retention data
    const weeks = ['Week 0', 'Week 1', 'Week 2', 'Week 3'];
    const retentionData = [
        [100, 65, 45, 30],
        [100, 70, 50, 35],
        [100, 68, 48, 32],
        [100, 72, 52, 38]
    ];

    const ctx = document.getElementById('retentionChart').getContext('2d');
    chartInstances['retentionChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeks,
            datasets: retentionData.map((cohort, i) => ({
                label: `Cohort ${i + 1}`,
                data: cohort,
                borderColor: `hsl(${i * 90}, 70%, 50%)`,
                backgroundColor: `hsla(${i * 90}, 70%, 50%, 0.1)`,
                borderWidth: 2,
                tension: 0.3
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Create Logistic Regression Chart with Enhanced Metrics
window.MLCharts.createLogisticChart = function (container, data) {
    if (!data || !data.metrics) return;

    const metrics = data.metrics;
    const accuracy = metrics.accuracy || 0;
    const precision = metrics.precision || 0;
    const recall = metrics.recall || 0;
    const f1Score = metrics.f1_score || 0;

    // Determine model quality based on F1 score
    let qualityClass = 'poor';
    let qualityText = 'Needs Improvement';
    if (f1Score > 0.8) { qualityClass = 'excellent'; qualityText = 'Excellent'; }
    else if (f1Score > 0.6) { qualityClass = 'good'; qualityText = 'Good'; }
    else if (f1Score > 0.4) { qualityClass = 'fair'; qualityText = 'Fair'; }

    // Enhanced metric cards
    const metricsDiv = document.createElement('div');
    metricsDiv.className = 'ml-stats-grid';
    metricsDiv.innerHTML = `
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🎯</span>
                    Accuracy
                </div>
                <span class="ml-metric-help ml-tooltip" title="Overall correctness">ℹ️
                    <span class="tooltiptext">Percentage of correct predictions out of all predictions. Good for balanced datasets.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(accuracy * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${accuracy * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                Model correctly predicts <strong>${(accuracy * 100).toFixed(1)}%</strong> of all cases.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🔍</span>
                    Precision
                </div>
                <span class="ml-metric-help ml-tooltip" title="Positive prediction accuracy">ℹ️
                    <span class="tooltiptext">Of all positive predictions, how many were actually correct. High precision = fewer false positives.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(precision * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${precision * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                When predicting "will convert", model is correct <strong>${(precision * 100).toFixed(1)}%</strong> of the time.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">📡</span>
                    Recall
                </div>
                <span class="ml-metric-help ml-tooltip" title="Coverage of actual positives">ℹ️
                    <span class="tooltiptext">Of all actual converters, how many did we correctly identify. High recall = fewer missed opportunities.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(recall * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${recall * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                Model identifies <strong>${(recall * 100).toFixed(1)}%</strong> of all actual converters.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">⚖️</span>
                    F1 Score
                </div>
                <span class="ml-metric-help ml-tooltip" title="Balanced performance metric">ℹ️
                    <span class="tooltiptext">Harmonic mean of Precision and Recall. Best overall metric for model quality. >0.8 = Excellent, >0.6 = Good, >0.4 = Fair</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(f1Score * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
                <span class="quality-indicator ${qualityClass}">
                    ${qualityText}
                </span>
            </div>
            <div class="distribution-container">
                <div class="distribution-label">
                    <span>Model Quality</span>
                    <span>${(f1Score * 100).toFixed(1)}%</span>
                </div>
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${f1Score * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                <strong>Balanced performance score.</strong> Combines precision and recall into a single metric.
            </div>
        </div>
    `;
    container.appendChild(metricsDiv);

    // Performance comparison chart
    const chartDiv = document.createElement('div');
    chartDiv.className = 'ml-chart-container';
    chartDiv.innerHTML = `
        <div class="ml-chart-title">
            <span>📊</span>
            Model Performance Metrics
        </div>
        <div class="ml-chart-subtitle">
            Comparison of key classification metrics for conversion prediction
        </div>
        <canvas id="logisticChart"></canvas>
    `;
    container.appendChild(chartDiv);

    destroyChart('logisticChart');

    const ctx = document.getElementById('logisticChart').getContext('2d');
    chartInstances['logisticChart'] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Accuracy', 'Precision', 'Recall', 'F1 Score'],
            datasets: [{
                label: 'Model Performance',
                data: [accuracy * 100, precision * 100, recall * 100, f1Score * 100],
                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                borderColor: 'rgb(52, 152, 219)',
                borderWidth: 2,
                pointBackgroundColor: 'rgb(52, 152, 219)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(52, 152, 219)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.95)',
                    padding: 12,
                    callbacks: {
                        label: function (context) {
                            return `${context.label}: ${context.parsed.r.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Confusion Matrix if available
    if (data.confusion_matrix) {
        const cm = data.confusion_matrix;
        const cmDiv = document.createElement('div');
        cmDiv.className = 'ml-metric-card';
        cmDiv.style.marginTop = '24px';
        cmDiv.innerHTML = `
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🎲</span>
                    Confusion Matrix
                </div>
                <span class="ml-metric-help ml-tooltip" title="Prediction breakdown">ℹ️
                    <span class="tooltiptext">Shows how predictions compare to actual values. Diagonal = correct predictions, off-diagonal = errors.</span>
                </span>
            </div>
            <div style="overflow-x: auto; margin-top: 16px;">
                <table class="analytics-table" style="width: auto; margin: 0 auto;">
                    <thead>
                        <tr>
                            <th rowspan="2" colspan="2" style="border: none;"></th>
                            <th colspan="2" style="text-align: center;">Predicted</th>
                        </tr>
                        <tr>
                            <th>No Convert</th>
                            <th>Convert</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th rowspan="2" style="vertical-align: middle; writing-mode: vertical-rl; transform: rotate(180deg);">Actual</th>
                            <th>No Convert</th>
                            <td class="good">${cm.true_negative || 0}</td>
                            <td class="warning">${cm.false_positive || 0}</td>
                        </tr>
                        <tr>
                            <th>Convert</th>
                            <td class="warning">${cm.false_negative || 0}</td>
                            <td class="good">${cm.true_positive || 0}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="ml-metric-explanation" style="margin-top: 16px;">
                <strong>Green:</strong> Correct predictions | <strong>Red:</strong> Errors (False Positives/Negatives)
            </div>
        `;
        container.appendChild(cmDiv);
    }
}

// Create Decision Tree Chart with Enhanced Metrics
window.MLCharts.createDecisionTreeChart = function (container, data) {
    if (!data || !data.tree_info) return;

    const treeInfo = data.tree_info;
    const accuracy = data.accuracy || 0;
    const depth = treeInfo.max_depth || 0;
    const nodes = treeInfo.node_count || 0;
    const leaves = treeInfo.leaf_count || 0;

    // Enhanced metric cards
    const metricsDiv = document.createElement('div');
    metricsDiv.className = 'ml-stats-grid';
    metricsDiv.innerHTML = `
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🎯</span>
                    Accuracy
                </div>
                <span class="ml-metric-help ml-tooltip" title="Prediction accuracy">ℹ️
                    <span class="tooltiptext">Percentage of correct predictions made by the decision tree.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(accuracy * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${accuracy * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                Tree correctly predicts <strong>${(accuracy * 100).toFixed(1)}%</strong> of cases.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🌳</span>
                    Tree Depth
                </div>
                <span class="ml-metric-help ml-tooltip" title="Maximum depth">ℹ️
                    <span class="tooltiptext">Maximum number of decisions from root to leaf. Deeper trees can overfit. Typical range: 3-10.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${depth}</span>
                <span class="ml-metric-unit">levels</span>
            </div>
            <div class="ml-metric-explanation">
                Tree makes up to <strong>${depth} sequential decisions</strong> to classify users.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🔢</span>
                    Total Nodes
                </div>
                <span class="ml-metric-help ml-tooltip" title="Decision points">ℹ️
                    <span class="tooltiptext">Total number of decision points in the tree. More nodes = more complex model.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${nodes}</span>
                <span class="ml-metric-unit">nodes</span>
            </div>
            <div class="ml-metric-explanation">
                Tree contains <strong>${nodes} decision points</strong> total.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🍃</span>
                    Leaf Nodes
                </div>
                <span class="ml-metric-help ml-tooltip" title="Final predictions">ℹ️
                    <span class="tooltiptext">Number of final prediction outcomes. Each leaf represents a unique user segment.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${leaves}</span>
                <span class="ml-metric-unit">segments</span>
            </div>
            <div class="ml-metric-explanation">
                Users are classified into <strong>${leaves} distinct segments</strong>.
            </div>
        </div>
    `;
    container.appendChild(metricsDiv);

    // Feature importance chart if available
    if (data.feature_importance && data.feature_importance.length > 0) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'ml-chart-container';
        chartDiv.innerHTML = `
            <div class="ml-chart-title">
                <span>📊</span>
                Feature Importance
            </div>
            <div class="ml-chart-subtitle">
                Which user behaviors most influence conversion predictions
            </div>
            <canvas id="treeChart"></canvas>
        `;
        container.appendChild(chartDiv);

        destroyChart('treeChart');

        const features = data.feature_importance.slice(0, 10); // Top 10
        const ctx = document.getElementById('treeChart').getContext('2d');
        chartInstances['treeChart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: features.map(f => f.feature),
                datasets: [{
                    label: 'Importance Score',
                    data: features.map(f => f.importance * 100),
                    backgroundColor: 'rgba(46, 204, 113, 0.7)',
                    borderColor: 'rgb(46, 204, 113)',
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(44, 62, 80, 0.95)',
                        padding: 12,
                        callbacks: {
                            label: function (context) {
                                return `Importance: ${context.parsed.x.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Importance (%)',
                            font: {
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    }
}

// Create FP-Growth Pattern Chart with Enhanced Metrics
window.MLCharts.createFPGrowthChart = function (container, data) {
    if (!data || !data.patterns) return;

    const patterns = data.patterns || [];
    const totalPatterns = patterns.length;
    const avgSupport = patterns.reduce((sum, p) => sum + (p.support || 0), 0) / totalPatterns || 0;
    const avgConfidence = patterns.reduce((sum, p) => sum + (p.confidence || 0), 0) / totalPatterns || 0;

    // Enhanced metric cards
    const metricsDiv = document.createElement('div');
    metricsDiv.className = 'ml-stats-grid';
    metricsDiv.innerHTML = `
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🔍</span>
                    Patterns Found
                </div>
                <span class="ml-metric-help ml-tooltip" title="Frequent itemsets">ℹ️
                    <span class="tooltiptext">Number of frequent product combinations discovered. These represent common purchase patterns.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${totalPatterns}</span>
                <span class="ml-metric-unit">patterns</span>
            </div>
            <div class="ml-metric-explanation">
                Discovered <strong>${totalPatterns} frequent product combinations</strong>.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">📊</span>
                    Avg Support
                </div>
                <span class="ml-metric-help ml-tooltip" title="Pattern frequency">ℹ️
                    <span class="tooltiptext">Average frequency of patterns. Higher support = more common combinations. Typical range: 0.01-0.1 (1-10%).</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(avgSupport * 100).toFixed(2)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${Math.min(avgSupport * 1000, 100)}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                Patterns appear in <strong>${(avgSupport * 100).toFixed(2)}%</strong> of transactions on average.
            </div>
        </div>
        
        <div class="ml-metric-card">
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">🎯</span>
                    Avg Confidence
                </div>
                <span class="ml-metric-help ml-tooltip" title="Rule strength">ℹ️
                    <span class="tooltiptext">Average confidence of association rules. Higher confidence = stronger product relationships. >70% is considered strong.</span>
                </span>
            </div>
            <div class="ml-metric-value-container">
                <span class="ml-metric-value">${(avgConfidence * 100).toFixed(1)}</span>
                <span class="ml-metric-unit">%</span>
            </div>
            <div class="distribution-container">
                <div class="distribution-bar">
                    <div class="distribution-fill" style="width: ${avgConfidence * 100}%"></div>
                </div>
            </div>
            <div class="ml-metric-explanation">
                Rules are correct <strong>${(avgConfidence * 100).toFixed(1)}%</strong> of the time on average.
            </div>
        </div>
    `;
    container.appendChild(metricsDiv);

    // Top patterns list
    const topPatterns = patterns.slice(0, 10);
    if (topPatterns.length > 0) {
        const patternsDiv = document.createElement('div');
        patternsDiv.className = 'ml-metric-card';
        patternsDiv.style.marginTop = '24px';
        patternsDiv.innerHTML = `
            <div class="ml-metric-header">
                <div class="ml-metric-title">
                    <span class="icon">⭐</span>
                    Top Frequent Patterns
                </div>
                <span class="ml-metric-help ml-tooltip" title="Most common combinations">ℹ️
                    <span class="tooltiptext">Products frequently purchased together. Use these for cross-selling and bundle recommendations.</span>
                </span>
            </div>
            <div style="margin-top: 16px;">
                ${topPatterns.map((pattern, idx) => `
                    <div class="path-item" style="margin-bottom: 12px;">
                        <div class="path-badge">#${idx + 1}</div>
                        <div class="path-text">
                            ${pattern.items ? pattern.items.join(' → ') : 'Pattern ' + (idx + 1)}
                        </div>
                        <div style="min-width: 120px; text-align: right; font-size: 13px;">
                            <div style="color: #3498db; font-weight: 600;">
                                Support: ${(pattern.support * 100).toFixed(2)}%
                            </div>
                            ${pattern.confidence ? `
                                <div style="color: #2ecc71; font-weight: 600;">
                                    Confidence: ${(pattern.confidence * 100).toFixed(1)}%
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        container.appendChild(patternsDiv);
    }
}

// Cleanup all charts
window.MLCharts.cleanupAllCharts = function () {
    Object.keys(chartInstances).forEach(chartId => {
        destroyChart(chartId);
    });
}
