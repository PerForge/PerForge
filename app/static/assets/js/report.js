// page-scripts.js

async function fetchAndDisplayTestData(testTitle, sourceType, id, bucket) {
    const loadingScreen = document.getElementById('loading-screen');
    const loadingMessage = document.getElementById('loading-message');

    // Show the loading screen
    showLoadingScreen(loadingScreen, loadingMessage);

    try {
        const data = await fetchData(testTitle, sourceType, id, bucket);
        handleFetchedData(data);
        // Hide the loading screen
        hideLoadingScreen(loadingScreen);
    } catch (error) {
        console.error('Error fetching data:', error);
        hideLoadingScreen(loadingScreen);
        // Show error message to the user
        showFlashMessage('Failed to load report data. Please try again.', 'error');
    }
}

async function fetchData(testTitle, sourceType, id, bucket) {
    try {
        const response = await apiClient.reports.getReportData(testTitle, sourceType, id, bucket);
        return response.data;
    } catch (error) {
        console.error('API error:', error);
        throw error;
    }
}

function showLoadingScreen(loadingScreen, loadingMessage) {
    loadingScreen.style.display = 'flex';
    loadingMessage.innerText = 'Preparing your tests data';
}

function hideLoadingScreen(loadingScreen) {
    loadingScreen.style.display = 'none';
}

function handleFetchedData(data) {
    const {
        data: chartData,
        styling,
        layout: layoutConfig,
        analysis: analysisData,
        statistics,
        test_details: testDetails,
        aggregated_table: aggregatedTable,
        summary,
        performance_status
    } = data;

    updateTestDetails(testDetails);
    updatePerformanceCard(summary, performance_status);
    updateCards(statistics);
    updateTable(aggregatedTable);
    updateAnalysisTable(analysisData);
    createGraphs(chartData, styling, layoutConfig);
    renderAnalysisInsights(analysisData);
    // Ensure newly created charts match the current theme
    if (typeof updateAllPlotlyChartsTheme === 'function') {
        updateAllPlotlyChartsTheme();
    }

    // Equalize chart panel heights after charts & insights are rendered
    queueEqualizeChartCards();

    // Attach event listeners after rows are inserted
    if (aggregatedTable && aggregatedTable.length > 0) {
        initializeListJs();
    }
    addDropdownEventListeners(chartData, styling, layoutConfig);
}

// --- Render per-graph insights below charts ---
function renderAnalysisInsights(analysisData) {
    try {
        const containers = {
            throughput: document.getElementById('throughputInsights'),
            response: document.getElementById('responseTimeInsights'),
            errors: document.getElementById('errorsInsights')
        };

        Object.values(containers).forEach(el => { if (el) el.innerHTML = ''; });
        if (!Array.isArray(analysisData) || analysisData.length === 0) return;

        const toBadge = (status) => {
            switch ((status || '').toLowerCase()) {
                case 'passed': return 'badge badge-success';
                case 'warning': return 'badge badge-warning';
                case 'info': return 'badge badge-primary';
                default: return 'badge badge-failure';
            }
        };

        const targetFor = ({ description = '', method = '' }) => {
            const d = String(description).toLowerCase();
            const m = String(method).toLowerCase();
            // Throughput & Users bucket
            if (d.includes('overalthroughput') || d.includes('throughput') || d.includes('users') || m.includes('ramp')) return 'throughput';
            // Response time bucket
            if (d.includes('avgresponsetime') || d.includes('medianresponsetime') || d.includes('90pct') || d.includes('response time')) return 'response';
            // Errors bucket
            if (d.includes('overalerrors') || d.includes('error')) return 'errors';
            // Fallback: response time (most analyses concern timings)
            return 'response';
        };

        // Group items by target first, so we can add a single title per box
        const grouped = { throughput: [], response: [], errors: [] };
        analysisData.forEach(item => {
            grouped[targetFor(item)].push(item);
        });

        Object.entries(grouped).forEach(([key, items]) => {
            if (!items.length) return;
            const host = containers[key];
            if (!host) return;
            const title = document.createElement('div');
            title.className = 'insights-title';
            title.textContent = 'Insights';
            host.appendChild(title);

            const MAX_ITEMS = 4;
            const visibleItems = items.slice(0, MAX_ITEMS);

            visibleItems.forEach(item => {
                const badgeClass = toBadge(item.status);
                const node = document.createElement('div');
                node.className = 'insight-item';
                node.innerHTML = `
                    <span class="${badgeClass}">${item.status}</span>
                    <div class="insight-copy">
                        <div class="desc">${item.description}</div>
                    </div>
                `;
                host.appendChild(node);
            });

            if (items.length > 0) {
                const more = document.createElement('div');
                more.className = 'insight-more';
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'insight-btn';
                btn.textContent = 'View all insights';
                btn.addEventListener('click', () => {
                    const analysisCard = document.querySelector('#analysis-table')?.closest('.card');
                    if (analysisCard) {
                        analysisCard.style.display = 'block';
                        analysisCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
                more.appendChild(btn);
                host.appendChild(more);
            }
        });
    } catch (e) {
        console.warn('Failed to render insights:', e);
    }
}

function updateTestDetails(testDetails) {
    document.getElementById('startTimeDetail').innerText = testDetails.start_time;
    document.getElementById('endTimeDetail').innerText = testDetails.end_time;
    document.getElementById('durationDetail').innerText = testDetails.duration;
}

function updatePerformanceCard(summary, performanceStatus) {
    const card = document.getElementById('performanceCard') || document.querySelector('.card[style*="border-left"]');
    if (!card) return;
    const summaryElement = document.getElementById('summaryCard') || card.querySelector('#summaryCard');

    const color = performanceStatus ? '#02d051' : '#ffc107';

    card.style.borderLeft = `4px solid ${color}`;
    if (summaryElement) {
        summaryElement.innerHTML = summary; // Changed from textContent to innerHTML
    }
}

function updateCards(statistics) {
    document.getElementById('vuCard').innerText = statistics.vu;
    document.getElementById('throughputCard').innerText = statistics.throughput;
    document.getElementById('medianCard').innerText = statistics.median;
    document.getElementById('pct90Card').innerText = statistics['90pct'];
    document.getElementById('errorsCard').innerText = statistics.errors;
}

function updateTable(aggregatedTable) {
    const tableContainer = document.querySelector('#aggregated-table');
    if (!tableContainer) return; // Exit if the table container doesn't exist

    const tbody = tableContainer.querySelector('.list');
    const dataComponentCard = tableContainer.closest('.card'); // Find the closest parent with class 'card'

    // Clear previous content
    tbody.innerHTML = '';

    // Check if aggregatedTable is null or empty
    if (!aggregatedTable || aggregatedTable.length === 0) {
        // Hide the table's parent card container if there's no data
        if (dataComponentCard) {
            dataComponentCard.style.display = 'none';
        }
        return; // Exit the function
    }

    // If there is data, ensure the container is visible
    if (dataComponentCard) {
        dataComponentCard.style.display = 'block';
    }

    aggregatedTable.forEach(stat => {
        const row = `
        <tr class="stat-row" data-transaction="${stat.transaction}">
            <th class="label">
                <button class="dropdown-btn btn btn-primary" data-target="chart-${stat.transaction}">˅</button>
                ${stat.transaction}
            </th>
            <th class="count">${stat.count ?? 'N/A'}</th>
            <th class="avg">${stat.avg ?? 'N/A'}</th>
            <th class="pct50">${stat.pct50 ?? 'N/A'}</th>
            <th class="pct75">${stat.pct75 ?? 'N/A'}</th>
            <th class="pct90">${stat.pct90 ?? 'N/A'}</th>
            <th class="rpm">${typeof stat.rpm === 'number' ? stat.rpm.toFixed(2) : 'N/A'}</th>
            <th class="errors">${typeof stat.errors === 'number' ? stat.errors.toFixed(2) : 'N/A'}</th>
            <th class="stddev">${stat.stddev ?? 'N/A'}</th>
        </tr>
        <tr class="graph-container" id="graph-${stat.transaction}" style="display: none;" data-transaction="${stat.transaction}">
            <td colspan="9">
                <div class="transaction-charts-row">
                    <div class="chart" id="chart-${stat.transaction}-throughput" style="height: 300px;"></div>
                    <div class="chart" id="chart-${stat.transaction}" style="height: 300px;"></div>
                </div>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

function updateAnalysisTable(analysisData) {
    const tableContainer = document.querySelector('#analysis-table');
    if (!tableContainer) return;

    const tbody = tableContainer.querySelector('.list');
    const cardContainer = tableContainer.closest('.card');

    tbody.innerHTML = '';

    if (!analysisData || analysisData.length === 0) {
        if (cardContainer) {
            cardContainer.style.display = 'none';
        }
        return;
    }

    if (cardContainer) {
        cardContainer.style.display = 'block';
    }

    analysisData.forEach(analysis => {
        const badgeClass = getBadgeClass(analysis.status);

        const row = `
        <tr>
            <td class="status"><span class="badge ${badgeClass}">${analysis.status}</span></td>
            <td class="method">${analysis.method}</td>
            <td class="description">${analysis.description}</td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

function getBadgeClass(status) {
    switch (status) {
        case 'passed':
            return 'badge-success';
        case 'failed':
            return 'badge-failure';
        default:
            return 'badge-primary';
    }
}

function initializeListJs() {
    const options = {
        valueNames: ['label', 'count', 'avg', 'pct50', 'pct75', 'pct90', 'rpm', 'errors', 'stddev']
    };

    const tableList = new List('aggregated-table', options);
    tableList.on('updated', adjustGraphPosition);
}

function adjustGraphPosition() {
    const rows = Array.from(document.querySelectorAll('.stat-row'));
    const parent = rows[0].parentNode;

    rows.forEach(statRow => {
        const transaction = statRow.dataset.transaction;
        const graphRow = document.getElementById(`graph-${transaction}`);

        if (graphRow) {
            parent.insertBefore(graphRow, statRow.nextSibling);
        }
    });
}

function addDropdownEventListeners(chartData, styling, layoutConfig) {
    document.querySelectorAll('.dropdown-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const parentRow = this.closest('.stat-row');
            const transaction = parentRow.dataset.transaction;
            const graphRow = document.getElementById(`graph-${transaction}`);

            if (!graphRow) {
                console.error(`Graph row not found for transaction: ${transaction}`);
                return;
            }

            if (graphRow.style.display === 'none' || !graphRow.style.display) {
                graphRow.style.display = 'table-row';
                this.innerHTML = '^';
                drawGraph(chartData, styling, layoutConfig, transaction, `chart-${transaction}`);
            } else {
                graphRow.style.display = 'none';
                this.innerHTML = '˅';
            }
        });
    });
}

function drawGraph(chartData, styling, layoutConfig, transactionName, chartElementId) {
    const avgTransactionData = chartData.avgResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const medianTransactionData = chartData.medianResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const pctTransactionData = chartData.pctResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const throughputTransactionData = chartData.throughputPerReq?.find(transaction => transaction.name === transactionName);

    const avgArr = avgTransactionData?.data || [];
    const medianArr = medianTransactionData?.data || [];
    const pctArr = pctTransactionData?.data || [];
    const throughputArr = throughputTransactionData?.data || [];

    // Choose timestamps source from first available series
    const base = avgArr.length ? avgArr : (medianArr.length ? medianArr : (pctArr.length ? pctArr : (throughputArr.length ? throughputArr : [])));
    if (!base.length) {
        console.warn(`No transaction data available for: ${transactionName}`);
        return;
    }

    const timestamps = base.map(d => new Date(d.timestamp));

    const metrics = [];
    if (avgArr.length) {
        metrics.push({
            name: 'Avg Response Time',
            data: avgArr.map(d => d.value),
            anomalies: avgArr.map(d => d.anomaly !== 'Normal'),
            anomalyMessages: avgArr.map(d => d.anomaly),
            color: 'rgba(2, 208, 81, 0.8)',
            yAxisUnit: 'ms'
        });
    }
    if (medianArr.length) {
        metrics.push({
            name: 'Median Response Time',
            data: medianArr.map(d => d.value),
            anomalies: medianArr.map(d => d.anomaly !== 'Normal'),
            anomalyMessages: medianArr.map(d => d.anomaly),
            color: 'rgba(23, 100, 254, 0.8)',
            yAxisUnit: 'ms'
        });
    }
    if (pctArr.length) {
        metrics.push({
            name: 'Pct90 Response Time',
            data: pctArr.map(d => d.value),
            anomalies: pctArr.map(d => d.anomaly !== 'Normal'),
            anomalyMessages: pctArr.map(d => d.anomaly),
            color: 'rgba(245, 165, 100, 1)',
            yAxisUnit: 'ms'
        });
    }

    if (!metrics.length) {
        console.warn(`No metrics to plot for transaction: ${transactionName}`);
        return;
    }

    createGraph(chartElementId, `Response Time - ${transactionName}`, timestamps, metrics, styling, layoutConfig);

    // Draw throughput under the response time chart if available
    if (throughputArr.length) {
        const thrTimestamps = throughputArr.map(d => new Date(d.timestamp));
        const thrMetrics = [{
            name: 'Throughput',
            data: throughputArr.map(d => d.value),
            anomalies: throughputArr.map(d => d.anomaly !== 'Normal'),
            anomalyMessages: throughputArr.map(d => d.anomaly),
            color: 'rgba(31, 119, 180, 1)',
            yAxisUnit: 'r/s'
        }];
        createGraph(`${chartElementId}-throughput`, `Throughput - ${transactionName}`, thrTimestamps, thrMetrics, styling, layoutConfig);
    }
    // Apply theme to the lazily created chart as well
    if (typeof updateAllPlotlyChartsTheme === 'function') {
        updateAllPlotlyChartsTheme();
    }

    // Ensure Plotly recalculates sizes after flex layout is applied
    try {
        if (typeof Plotly !== 'undefined') {
            const respEl = document.getElementById(chartElementId);
            const thrEl = document.getElementById(`${chartElementId}-throughput`);
            requestAnimationFrame(() => {
                if (thrEl) { try { Plotly.Plots.resize(thrEl); } catch (e) {} }
                if (respEl) { try { Plotly.Plots.resize(respEl); } catch (e) {} }
            });
        }
    } catch (e) { /* no-op */ }
}

function createGraphs(chartData, styling, layoutConfig) {
    const overalAvg = chartData.overalAvgResponseTime?.data || [];
    const overalMedian = chartData.overalMedianResponseTime?.data || [];
    const overalPct90 = chartData.overal90PctResponseTime?.data || [];
    const overalThroughput = chartData.overalThroughput?.data || [];
    const overalUsers = chartData.overalUsers?.data || [];
    const overalErrors = chartData.overalErrors?.data || [];

    // Choose timestamps source from first available series
    const base = overalAvg.length ? overalAvg : (overalMedian.length ? overalMedian : (overalPct90.length ? overalPct90 : (overalThroughput.length ? overalThroughput : (overalUsers.length ? overalUsers : overalErrors))));
    if (!base || !base.length) {
        console.warn('No overall time series available to plot');
        return;
    }
    const timestamps = base.map(d => new Date(d.timestamp));

    const throughput = overalThroughput.map(d => d.value);
    const throughputAnomalies = overalThroughput.map(d => d.anomaly !== 'Normal');
    const throughputAnomalyMessages = overalThroughput.map(d => d.anomaly);
    const users = overalUsers.map(d => d.value);

    const responseTimeMetrics = [];
    if (overalAvg.length) {
        responseTimeMetrics.push({ name: 'Avg Response Time', data: overalAvg.map(d => d.value), anomalies: overalAvg.map(d => d.anomaly !== 'Normal'), anomalyMessages: overalAvg.map(d => d.anomaly), color: 'rgba(2, 208, 81, 0.8)', yAxisUnit: 'ms' });
    }
    if (overalMedian.length) {
        responseTimeMetrics.push({ name: 'Median Response Time', data: overalMedian.map(d => d.value), anomalies: overalMedian.map(d => d.anomaly !== 'Normal'), anomalyMessages: overalMedian.map(d => d.anomaly), color: 'rgba(23, 100, 254, 0.8)', yAxisUnit: 'ms' });
    }
    if (overalPct90.length) {
        responseTimeMetrics.push({ name: '90Pct Response Time', data: overalPct90.map(d => d.value), anomalies: overalPct90.map(d => d.anomaly !== 'Normal'), anomalyMessages: overalPct90.map(d => d.anomaly), color: 'rgba(245, 165, 100, 1)', yAxisUnit: 'ms' });
    }

    // Plot throughput/users only if we have at least one of them
    const throughputUsersMetrics = [];
    // Draw Users first (right axis), then Throughput on top so it remains visible even when values overlap
    if (users.length) throughputUsersMetrics.push({ name: 'Users', data: users, anomalies: [], anomalyMessages: [], color: 'rgba(0, 155, 162, 0.8)', yAxisUnit: 'vu', useRightYAxis: true });
    if (throughput.length) throughputUsersMetrics.push({ name: 'Throughput', data: throughput, anomalies: throughputAnomalies, anomalyMessages: throughputAnomalyMessages, color: 'rgba(31, 119, 180, 1)', yAxisUnit: 'r/s' });
    if (throughputUsersMetrics.length) {
        createGraph('throughputChart', 'Throughput and Users', timestamps, throughputUsersMetrics, styling, layoutConfig);
    }

    if (responseTimeMetrics.length) {
        createGraph('responseTimeChart', 'Response Time', timestamps, responseTimeMetrics, styling, layoutConfig);
    }

    const errors = overalErrors.map(d => d.value);
    if (errors.length) {
        createGraph('overalErrors', 'Errors', timestamps, [
            { name: 'Errors', data: errors, anomalies: [], anomalyMessages: [], color: 'rgba(255, 8, 8, 0.8)', yAxisUnit: 'er' }
        ], styling, layoutConfig);
    }

    // Render scatter only if the element exists on the page
    const scatterEl = document.getElementById('responseTimeScatterChart');
    if (scatterEl && Array.isArray(chartData.avgResponseTimePerReq) && chartData.avgResponseTimePerReq.length) {
        createScatterChartForResponseTimes(chartData.avgResponseTimePerReq, 'responseTimeScatterChart', styling, layoutConfig);
    }
}

// === Theme utilities for Plotly charts ===
function getCurrentThemeColors() {
    const styles = getComputedStyle(document.body || document.documentElement);
    const textColor = (styles.getPropertyValue('--text-main-color') || '').trim() || '#ced4da';
    const gridColor = (styles.getPropertyValue('--border-main-color') || '').trim() || '#343a40';
    // Use transparent paper/plot backgrounds so charts blend with card/container in all themes
    const paperBg = 'rgba(0,0,0,0)';
    const plotBg = 'rgba(0,0,0,0)';
    const hoverBg = (styles.getPropertyValue('--bs-background-dark') || '').trim() || '#18171a';
    return { textColor, gridColor, paperBg, plotBg, hoverBg };
}

function updateAllPlotlyChartsTheme() {
    if (typeof Plotly === 'undefined') return;
    const { textColor, gridColor, paperBg, plotBg, hoverBg } = getCurrentThemeColors();

    const layoutUpdate = {
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        'title.font.color': textColor,
        'xaxis.tickfont.color': textColor,
        'xaxis.color': textColor,
        'xaxis.gridcolor': gridColor,
        'yaxis.tickfont.color': textColor,
        'yaxis.color': textColor,
        'yaxis.gridcolor': gridColor,
        'yaxis2.tickfont.color': textColor,
        'yaxis2.color': textColor,
        'legend.font.color': textColor,
        'hoverlabel.bgcolor': hoverBg,
        'hoverlabel.font.color': textColor
    };

    document.querySelectorAll('.js-plotly-plot').forEach((el) => {
        try { Plotly.relayout(el, layoutUpdate); } catch (e) { /* no-op */ }
    });
}

// Listen for theme change broadcasts from the theme switcher
document.addEventListener('theme:changed', () => {
    updateAllPlotlyChartsTheme();
});

// Also try once on DOM ready (in case charts already exist)
document.addEventListener('DOMContentLoaded', () => {
    updateAllPlotlyChartsTheme();
});

// === Equal-height utilities for the two chart panels ===
function debounce(fn, wait = 150) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(null, args), wait);
    };
}

function equalizeChartCards() {
    try {
        const row = document.querySelector('.start-section.equal-height');
        if (!row) return;
        const cards = row.querySelectorAll('.chart-card');
        if (!cards || cards.length < 2) return;

        // Reset any previous min-height
        cards.forEach(c => c.style.minHeight = '');

        // Only equalize when two columns are side-by-side (lg and up)
        const isTwoCols = window.innerWidth >= 992; // lg breakpoint
        if (!isTwoCols) return;

        const max = Array.from(cards).reduce((m, c) => {
            const h = c.getBoundingClientRect().height;
            return Math.max(m, h || 0);
        }, 0);
        if (max > 0 && isFinite(max)) {
            const h = Math.ceil(max) + 'px';
            cards.forEach(c => { c.style.minHeight = h; });
        }
    } catch (e) {
        // no-op: don't break page if equalization fails
    }
}

// Queue equalization after the browser paints (helps after Plotly renders)
const queueEqualizeChartCards = (() => {
    let rafId = 0;
    return () => {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => setTimeout(equalizeChartCards, 0));
    };
})();

// Re-run on resize and theme changes
const equalizeOnResize = debounce(() => queueEqualizeChartCards(), 150);
window.addEventListener('resize', equalizeOnResize);
document.addEventListener('theme:changed', queueEqualizeChartCards);
document.addEventListener('DOMContentLoaded', queueEqualizeChartCards);

function createGraph(divId, title, labels, metrics, styling, layoutConfig) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        console.warn(`No metrics provided for graph: ${title}`);
        return;
    }

    const safeLayoutConfig = layoutConfig || {};
    const themeColors = (typeof getCurrentThemeColors === 'function') ? getCurrentThemeColors() : {};
    const paperBg = themeColors.paperBg || 'rgba(0,0,0,0)';
    const plotBg = themeColors.plotBg || 'rgba(0,0,0,0)';

    const traces = metrics.map(metric => {
        return {
            x: labels,
            y: metric.data,
            mode: 'lines+markers',
            name: metric.name,
            marker: {
                color: (metric.anomalies.length > 0 ? metric.anomalies : metric.data.map(() => false)).map(anomaly => anomaly ? styling.marker_color_anomaly : styling.marker_color_normal),
                size: (metric.anomalies.length > 0 ? metric.anomalies : metric.data.map(() => false)).map(anomaly => anomaly ? styling.marker_size : 0)
            },
            text: (metric.anomalyMessages.length > 0 ? metric.anomalyMessages : metric.data.map(() => '')).map((msg, index) => metric.anomalies[index] ? msg : ''),
            hoverinfo: 'x+y+text',
            line: { shape: styling.line_shape, width: styling.line_width, color: metric.color },
            yaxis: metric.useRightYAxis ? 'y2' : 'y'
        };
    });

    const firstLeft = metrics.find(metric => !metric.useRightYAxis) || metrics[0];
    const leftYAxisColor = firstLeft?.color || (styling?.axis_font_color || '#888');
    const rightYAxisCandidate = metrics.find(metric => metric.useRightYAxis) || firstLeft;
    const rightYAxisColor = rightYAxisCandidate?.color || leftYAxisColor;

    const layout = {
        // Allow external layoutConfig but ensure our critical props (title/axes) are preserved
        ...safeLayoutConfig,
        title: {
            text: title,
            font: {
                color: styling.title_font_color,
                family: styling.font_family,
                size: styling.title_size
            },
            y: 0.95,
            x: 0.5
        },
        margin: { t: 60, r: 70, l: 60, b: 50 },
        paper_bgcolor: paperBg,
        plot_bgcolor: plotBg,
        xaxis: {
            tickfont: {
                color: styling.axis_font_color,
                family: styling.font_family,
                size: styling.xaxis_tickfont_size
            },
            color: styling.axis_font_color,
            gridcolor: styling.gridcolor,
            automargin: true
        },
        yaxis: {
            tickfont: {
                color: leftYAxisColor,
                family: styling.font_family,
                size: styling.yaxis_tickfont_size
            },
            color: leftYAxisColor,
            ticksuffix: ` ${firstLeft?.yAxisUnit || ''}`,
            zeroline: false,
            gridcolor: styling.gridcolor,
            rangemode: 'tozero', // Ensure Y-axis starts at 0
            automargin: true
        },
        yaxis2: {
            tickfont: {
                color: rightYAxisColor,
                family: styling.font_family,
                size: styling.yaxis_tickfont_size
            },
            color: rightYAxisColor,
            ticksuffix: ` ${rightYAxisCandidate?.yAxisUnit || ''}`,
            zeroline: false,
            overlaying: 'y',
            side: 'right',
            showgrid: false,
            rangemode: "tozero", // Ensure secondary Y-axis starts at 0
            automargin: true
        },
        hoverlabel: {
            bgcolor: styling.hover_bgcolor,
            bordercolor: styling.hover_bordercolor,
            font: {
                color: styling.hover_font_color,
                family: styling.font_family
            }
        },
        legend: {
            orientation: 'h',
            x: 0,
            y: -0.2,
            xanchor: 'left',
            yanchor: 'top',
            traceorder: 'normal',
            bgcolor: paperBg
        }
    };

    Plotly.newPlot(divId, traces, layout, { responsive: true, useResizeHandler: true });
}

// Updated createScatterChartForResponseTimes function to include styling and layoutConfig as parameters
function createScatterChartForResponseTimes(avgResponseTimePerReq, elementId, styling, layoutConfig) {
    const timestamps = [];
    const values = [];

    avgResponseTimePerReq.forEach(transaction => {
        transaction.data.forEach(record => {
            timestamps.push(new Date(record.timestamp));
            values.push(record.value);
        });
    });

    const trace1 = {
        x: timestamps,
        y: values,
        mode: 'markers',
        type: 'scatter',
        marker: {
            size: 2, // Smaller dots
            color: styling.marker_color_normal
        },
    };

    const layout = {
        title: {
            text: 'Response Time Scatter Chart',
            font: {
                color: styling.title_font_color,
                family: styling.font_family,
                size: styling.title_size
            }
        },
        paper_bgcolor: styling.paper_bgcolor,
        plot_bgcolor: styling.plot_bgcolor,
        xaxis: {
            tickfont: {
                color: styling.axis_font_color,
                family: styling.font_family,
                size: styling.xaxis_tickfont_size
            },
            color: styling.axis_font_color,
            gridcolor: styling.gridcolor
        },
        yaxis: {
            tickfont: {
                color: styling.marker_color_normal,
                family: styling.font_family,
                size: styling.yaxis_tickfont_size,
            },
            color: styling.axis_font_color,
            gridcolor: styling.gridcolor,
            zeroline: false
        },
        hoverlabel: {
            bgcolor: styling.hover_bgcolor,
            bordercolor: styling.hover_bordercolor,
            font: {
                color: styling.hover_font_color,
                family: styling.font_family,
            },
        },
        legend: {
            orientation: 'h',
            x: 0,
            y: -0.2,
            xanchor: 'left',
            yanchor: 'top'
        },
        ...layoutConfig
    };

    Plotly.newPlot(elementId, [trace1], layout, { responsive: true, useResizeHandler: true });
}
