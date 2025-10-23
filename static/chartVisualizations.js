/**
 * Chart Visualizations for Analytics Dashboard
 * 
 * Provides reusable chart components:
 * - Bounce Rate Gauge
 * - Conversion Funnel
 * - User Segmentation
 * - Daily Distribution
 * - Time Series Line Chart
 */

/**
 * Render Bounce Rate as a circular gauge
 * @param {number} bounceRate - Bounce rate (0 to 1)
 * @param {object} options - Optional configuration
 * @returns {string} HTML string
 */
export function renderBounceRateGauge(bounceRate, options = {}) {
    const percentage = (bounceRate * 100).toFixed(1);
    const size = options.size || 120;
    const radius = (size - 20) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = bounceRate * circumference;
    
    // Color based on bounce rate
    const color = bounceRate < 0.02 ? '#10b981' :  // Green (excellent)
                  bounceRate < 0.05 ? '#3b82f6' :  // Blue (good)
                  bounceRate < 0.10 ? '#f59e0b' :  // Yellow (fair)
                  '#ef4444';  // Red (poor)
    
    const status = bounceRate < 0.02 ? 'Excellent' :
                   bounceRate < 0.05 ? 'Good' :
                   bounceRate < 0.10 ? 'Fair' :
                   'Needs Improvement';
    
    return `
        <div class="bounce-gauge" style="text-align: center;">
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                <!-- Background circle -->
                <circle 
                    cx="${size/2}" cy="${size/2}" r="${radius}"
                    fill="none" 
                    stroke="rgba(255,255,255,0.1)" 
                    stroke-width="10"/>
                
                <!-- Progress circle -->
                <circle 
                    cx="${size/2}" cy="${size/2}" r="${radius}"
                    fill="none" 
                    stroke="${color}" 
                    stroke-width="10"
                    stroke-dasharray="${progress} ${circumference}"
                    stroke-linecap="round"
                    transform="rotate(-90 ${size/2} ${size/2})"
                    style="transition: stroke-dasharray 1s ease;"/>
                
                <!-- Center text -->
                <text 
                    x="${size/2}" y="${size/2 - 10}" 
                    text-anchor="middle" 
                    dominant-baseline="middle" 
                    font-size="24" 
                    font-weight="700"
                    fill="${color}">
                    ${percentage}%
                </text>
                <text 
                    x="${size/2}" y="${size/2 + 15}" 
                    text-anchor="middle" 
                    font-size="10" 
                    fill="var(--muted)">
                    ${status}
                </text>
            </svg>
            <div style="margin-top: 8px; color: var(--muted); font-size: 12px;">
                Bounce Rate
            </div>
        </div>
    `;
}

/**
 * Render Conversion Funnel as horizontal bars
 * @param {object} funnels - Funnel data from analysis
 * @returns {string} HTML string
 */
export function renderConversionFunnel(funnels) {
    // Define funnel stages
    const stages = [
        {
            name: 'Home',
            count: funnels.home_to_product?.home || 0,
            color: '#3b82f6'
        },
        {
            name: 'Product View',
            count: funnels.home_to_product?.product || 0,
            color: '#10b981',
            conversion: funnels.home_to_product?.conversion
        },
        {
            name: 'Checkout',
            count: funnels.home_to_checkout?.checkout || 0,
            color: '#f59e0b',
            conversion: funnels.home_to_checkout?.conversion
        }
    ];
    
    // Calculate percentages relative to first stage
    const maxCount = stages[0].count || 1;
    stages.forEach(stage => {
        stage.percentage = (stage.count / maxCount * 100).toFixed(1);
    });
    
    let html = '<div class="funnel-chart" style="width: 100%; max-width: 600px; margin: 0 auto;">';
    
    stages.forEach((stage, i) => {
        const width = stage.percentage;
        const dropoff = i > 0 ? (stages[i-1].percentage - stage.percentage) : 0;
        
        html += `
            <div class="funnel-stage" style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; color: var(--muted);">
                    <span>${stage.name}</span>
                    <span>${stage.count.toLocaleString()} (${width}%)</span>
                </div>
                <div style="position: relative;">
                    <div class="funnel-bar" 
                         style="width: ${width}%; 
                                height: 40px; 
                                background: ${stage.color}; 
                                border-radius: 6px;
                                transition: all 0.5s ease;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                color: white;
                                font-weight: 600;">
                        ${stage.conversion ? `${(stage.conversion * 100).toFixed(1)}% conversion` : ''}
                    </div>
                </div>
                ${dropoff > 0 ? `
                    <div style="margin-top: 4px; font-size: 11px; color: #ef4444;">
                        ↓ ${dropoff}% drop-off
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

/**
 * Render User Segmentation from K-Means clusters
 * @param {array} segments - Array of cluster data
 * @returns {string} HTML string
 */
export function renderUserSegmentation(segments) {
    if (!segments || segments.length === 0) {
        return '<p style="color: var(--muted);">No segmentation data available</p>';
    }
    
    const colors = [
        '#3b82f6', // Blue
        '#10b981', // Green
        '#f59e0b', // Yellow
        '#ef4444', // Red
        '#8b5cf6', // Purple
        '#06b6d4', // Cyan
        '#ec4899'  // Pink
    ];
    
    let html = '<div class="segments-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">';
    
    segments.forEach((seg, i) => {
        const color = colors[i % colors.length];
        const clusterName = seg.cluster_name || `Cluster ${seg.cluster_id || i}`;
        
        html += `
            <div class="segment-card" 
                 style="background: rgba(255,255,255,0.05); 
                        padding: 16px; 
                        border-radius: 8px;
                        border-left: 4px solid ${color};
                        transition: transform 0.2s, box-shadow 0.2s;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <h4 style="margin: 0; color: ${color}; font-size: 16px;">
                        ${clusterName}
                    </h4>
                    <span style="background: ${color}; 
                                 color: white; 
                                 padding: 2px 8px; 
                                 border-radius: 12px; 
                                 font-size: 11px; 
                                 font-weight: 600;">
                        ${seg.users || 0} users
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div class="segment-metric">
                        <div style="font-size: 11px; color: var(--muted); margin-bottom: 4px;">Avg Events</div>
                        <div style="font-size: 20px; font-weight: 700; color: var(--text);">
                            ${(seg.avg_events || 0).toFixed(1)}
                        </div>
                    </div>
                    <div class="segment-metric">
                        <div style="font-size: 11px; color: var(--muted); margin-bottom: 4px;">Conversion</div>
                        <div style="font-size: 20px; font-weight: 700; color: ${color};">
                            ${((seg.avg_conversion || 0) * 100).toFixed(1)}%
                        </div>
                    </div>
                </div>
                ${seg.description ? `
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 12px; color: var(--muted);">
                        ${seg.description}
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

/**
 * Render Daily Distribution as column chart
 * @param {object} dailyData - {date: count, ...}
 * @returns {string} HTML string
 */
export function renderDailyDistribution(dailyData) {
    if (!dailyData || Object.keys(dailyData).length === 0) {
        return '<p style="color: var(--muted);">No daily data available</p>';
    }
    
    const dates = Object.keys(dailyData).sort();
    const counts = dates.map(d => dailyData[d]);
    const maxCount = Math.max(...counts, 1);
    
    const width = 800;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 60, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const barWidth = Math.max(8, chartWidth / dates.length - 4);
    
    let svg = `<svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" class="daily-chart">`;
    
    // Y-axis labels
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight * i / 5);
        const value = Math.round(maxCount * (1 - i / 5));
        svg += `
            <line x1="${padding.left - 5}" y1="${y}" x2="${padding.left}" y2="${y}" 
                  stroke="var(--border)" stroke-width="1"/>
            <text x="${padding.left - 10}" y="${y}" 
                  text-anchor="end" dominant-baseline="middle" 
                  font-size="10" fill="var(--muted)">
                ${value.toLocaleString()}
            </text>
        `;
    }
    
    // Bars with hover effect
    dates.forEach((date, i) => {
        const count = counts[i];
        const barHeight = (count / maxCount) * chartHeight;
        const x = padding.left + (i * (chartWidth / dates.length)) + (chartWidth / dates.length - barWidth) / 2;
        const y = padding.top + chartHeight - barHeight;
        
        const dateObj = new Date(date);
        const label = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        svg += `
            <g class="bar-group" data-date="${date}" data-count="${count}">
                <rect x="${x}" y="${y}" 
                      width="${barWidth}" height="${barHeight}"
                      fill="#3b82f6" opacity="0.8" rx="4"
                      style="cursor: pointer; transition: opacity 0.2s;"
                      onmouseover="this.setAttribute('opacity', '1')"
                      onmouseout="this.setAttribute('opacity', '0.8')">
                    <title>${label}: ${count.toLocaleString()} events</title>
                </rect>
            </g>
        `;
    });
    
    // X-axis labels (show every N days to avoid crowding)
    const labelFreq = Math.ceil(dates.length / 10);
    dates.forEach((date, i) => {
        if (i % labelFreq === 0 || i === dates.length - 1) {
            const x = padding.left + (i * (chartWidth / dates.length)) + (chartWidth / dates.length) / 2;
            const dateObj = new Date(date);
            const label = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            
            svg += `
                <text x="${x}" y="${height - padding.bottom + 20}" 
                      text-anchor="middle" font-size="10" fill="var(--muted)">
                    ${label}
                </text>
            `;
        }
    });
    
    // Axis lines
    svg += `
        <line x1="${padding.left}" y1="${padding.top}" 
              x2="${padding.left}" y2="${padding.top + chartHeight}" 
              stroke="var(--border)" stroke-width="2"/>
        <line x1="${padding.left}" y1="${padding.top + chartHeight}" 
              x2="${width - padding.right}" y2="${padding.top + chartHeight}" 
              stroke="var(--border)" stroke-width="2"/>
    `;
    
    svg += '</svg>';
    return svg;
}

/**
 * Render Time Series Line Chart
 * @param {object} data - {timestamp: value, ...} or array of {x, y}
 * @param {object} options - Chart configuration
 * @returns {string} HTML string
 */
export function renderTimeSeriesChart(data, options = {}) {
    const {
        width = 800,
        height = 300,
        color = '#3b82f6',
        fillOpacity = 0.1,
        showDots = true,
        yLabel = 'Value'
    } = options;
    
    // Convert data to array format
    let dataPoints = [];
    if (Array.isArray(data)) {
        dataPoints = data;
    } else {
        dataPoints = Object.entries(data).map(([x, y]) => ({ x: new Date(x), y }));
    }
    
    if (dataPoints.length === 0) {
        return '<p style="color: var(--muted);">No time series data available</p>';
    }
    
    dataPoints.sort((a, b) => new Date(a.x) - new Date(b.x));
    
    const padding = { top: 20, right: 20, bottom: 60, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    const yValues = dataPoints.map(d => d.y);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const yRange = maxY - minY || 1;
    
    // Scale functions
    const scaleX = (i) => padding.left + (i / (dataPoints.length - 1)) * chartWidth;
    const scaleY = (y) => padding.top + chartHeight - ((y - minY) / yRange) * chartHeight;
    
    // Generate path
    let pathData = '';
    dataPoints.forEach((d, i) => {
        const x = scaleX(i);
        const y = scaleY(d.y);
        pathData += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });
    
    // Area fill path
    const areaPath = pathData + 
        ` L ${scaleX(dataPoints.length - 1)} ${padding.top + chartHeight}` +
        ` L ${scaleX(0)} ${padding.top + chartHeight} Z`;
    
    let svg = `<svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">`;
    
    // Y-axis
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (chartHeight * i / 5);
        const value = maxY - (yRange * i / 5);
        svg += `
            <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" 
                  stroke="var(--border)" stroke-width="1" opacity="0.5"/>
            <text x="${padding.left - 10}" y="${y}" 
                  text-anchor="end" dominant-baseline="middle" 
                  font-size="10" fill="var(--muted)">
                ${value.toFixed(0)}
            </text>
        `;
    }
    
    // Area fill
    svg += `<path d="${areaPath}" fill="${color}" opacity="${fillOpacity}"/>`;
    
    // Line
    svg += `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>`;
    
    // Data points
    if (showDots) {
        dataPoints.forEach((d, i) => {
            const x = scaleX(i);
            const y = scaleY(d.y);
            const label = d.x instanceof Date ? d.x.toLocaleString() : d.x;
            
            svg += `
                <circle cx="${x}" cy="${y}" r="4" fill="${color}" opacity="0.8"
                        style="cursor: pointer;"
                        onmouseover="this.setAttribute('r', '6')"
                        onmouseout="this.setAttribute('r', '4')">
                    <title>${label}: ${d.y}</title>
                </circle>
            `;
        });
    }
    
    svg += '</svg>';
    return svg;
}

/**
 * Add CSS for chart components
 */
export const chartStyles = `
<style>
.bounce-gauge svg {
    filter: drop-shadow(0 2px 8px rgba(0,0,0,0.15));
}

.funnel-bar:hover {
    transform: scaleX(1.02);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.segment-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.daily-chart .bar-group:hover rect {
    filter: brightness(1.2);
}

@media (max-width: 768px) {
    .segments-grid {
        grid-template-columns: 1fr !important;
    }
    
    .funnel-chart {
        max-width: 100% !important;
    }
}
</style>
`;
