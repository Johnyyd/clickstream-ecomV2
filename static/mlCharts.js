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

// Create ALS Recommendations Chart
window.MLCharts.createALSChart = function(container, data) {
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <div class="chart-title">📊 ALS Model Performance</div>
        <canvas id="alsChart"></canvas>
    `;
    container.appendChild(chartDiv);
    
    destroyChart('alsChart');
    
    const ctx = document.getElementById('alsChart').getContext('2d');
    chartInstances['alsChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['RMSE', 'Users', 'Products', 'Interactions'],
            datasets: [{
                label: 'ALS Statistics',
                data: [
                    data.rmse || 0,
                    data.model_info?.total_users || 0,
                    data.model_info?.total_products || 0,
                    (data.model_info?.total_interactions || 0) / 1000 // Scale down for visibility
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
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            let value = context.parsed.y;
                            if (label === 'Interactions') {
                                value = value * 1000; // Restore original scale
                            }
                            return label + ': ' + value.toLocaleString();
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create K-Means Clustering Chart
window.MLCharts.createKMeansChart = function(container, data) {
    if (!data.cluster_stats) return;
    
    const clusters = Object.keys(data.cluster_stats);
    const clusterData = clusters.map(c => data.cluster_stats[c]);
    
    // Stats Grid
    const statsDiv = document.createElement('div');
    statsDiv.className = 'ml-stats-grid';
    statsDiv.innerHTML = `
        <div class="ml-stat-box">
            <div class="label">👥 Total Users</div>
            <div class="value">${data.total_users || 0}</div>
        </div>
        <div class="ml-stat-box">
            <div class="label">🎯 Clusters</div>
            <div class="value">${data.num_clusters || 0}</div>
        </div>
        <div class="ml-stat-box">
            <div class="label">📊 Silhouette</div>
            <div class="value">${data.silhouette_score || 0}</div>
        </div>
    `;
    container.appendChild(statsDiv);
    
    // Cluster comparison chart
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `
        <div class="chart-title">📊 Cluster Comparison</div>
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
                    borderWidth: 2
                },
                {
                    label: 'Avg Events',
                    data: clusterData.map(c => c.avg_events),
                    backgroundColor: 'rgba(46, 204, 113, 0.7)',
                    borderColor: 'rgb(46, 204, 113)',
                    borderWidth: 2
                },
                {
                    label: 'Conversion Rate',
                    data: clusterData.map(c => c.avg_conversion * 100),
                    backgroundColor: 'rgba(155, 89, 182, 0.7)',
                    borderColor: 'rgb(155, 89, 182)',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Cluster details grid
    const clusterGrid = document.createElement('div');
    clusterGrid.className = 'cluster-grid';
    clusters.forEach(clusterId => {
        const cluster = data.cluster_stats[clusterId];
        clusterGrid.innerHTML += `
            <div class="cluster-card">
                <h5>🎯 Cluster ${clusterId}</h5>
                <div class="cluster-stat">
                    <span class="label">Users:</span>
                    <span class="value">${cluster.user_count}</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">Avg Events:</span>
                    <span class="value">${cluster.avg_events.toFixed(2)}</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">Conversion:</span>
                    <span class="value">${(cluster.avg_conversion * 100).toFixed(2)}%</span>
                </div>
                <div class="cluster-stat">
                    <span class="label">Cart Rate:</span>
                    <span class="value">${(cluster.avg_cart_rate * 100).toFixed(2)}%</span>
                </div>
            </div>
        `;
    });
    container.appendChild(clusterGrid);
}

// Create SEO Traffic Chart
window.MLCharts.createSEOChart = function(container, data) {
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
window.MLCharts.createConversionChart = function(container, data) {
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
window.MLCharts.createRetentionChart = function(container, data) {
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
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Cleanup all charts
window.MLCharts.cleanupAllCharts = function() {
    Object.keys(chartInstances).forEach(chartId => {
        destroyChart(chartId);
    });
}
