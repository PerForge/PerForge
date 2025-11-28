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
        performance_status,
        overall_anomaly_windows: overallAnomalyWindows,
        per_transaction_anomaly_windows: perTransactionAnomalyWindows,
        timezone
    } = data;

    updateTestDetails(testDetails);
    updatePerformanceCard(summary, performance_status);
    updateCards(statistics);
    updateTable(aggregatedTable);
    updateAnalysisTable(analysisData);
    createGraphs(chartData, styling, layoutConfig, overallAnomalyWindows || {}, timezone);
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
    addDropdownEventListeners(chartData, styling, layoutConfig, perTransactionAnomalyWindows || {}, timezone);
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

function addDropdownEventListeners(chartData, styling, layoutConfig, perTransactionAnomalyWindows, timezone) {
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
                drawGraph(chartData, styling, layoutConfig, transaction, `chart-${transaction}`, perTransactionAnomalyWindows, timezone);
            } else {
                graphRow.style.display = 'none';
                this.innerHTML = '˅';
            }
        });
    });
}

function drawGraph(chartData, styling, layoutConfig, transactionName, chartElementId, perTransactionAnomalyWindows, timezone) {
    const avgTransactionData = chartData.avgResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const medianTransactionData = chartData.medianResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const pctTransactionData = chartData.pctResponseTimePerReq?.find(transaction => transaction.name === transactionName);
    const throughputTransactionData = chartData.throughputPerReq?.find(transaction => transaction.name === transactionName);

    const avgArr = avgTransactionData?.data || [];
    const medianArr = medianTransactionData?.data || [];
    const pctArr = pctTransactionData?.data || [];
    const throughputArr = throughputTransactionData?.data || [];

    // Get anomaly windows for this specific transaction
    const transactionWindows = (perTransactionAnomalyWindows && perTransactionAnomalyWindows[transactionName]) || {};

    // Choose timestamps source from first available series
    const base = avgArr.length ? avgArr : (medianArr.length ? medianArr : (pctArr.length ? pctArr : (throughputArr.length ? throughputArr : [])));
    if (!base.length) {
        console.warn(`No transaction data available for: ${transactionName}`);
        return;
    }

    const timestamps = base.map(d => parseTimestamp(d.timestamp, timezone));

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

    // Merge anomaly windows for response time metrics
    const rtWindows = [];
    ['rt_ms_avg', 'rt_ms_median', 'rt_ms_p90'].forEach(metricKey => {
        const wins = transactionWindows[metricKey];
        if (Array.isArray(wins)) {
            rtWindows.push(...wins);
        }
    });

    createGraph(chartElementId, `Response Time - ${transactionName}`, timestamps, metrics, styling, layoutConfig, rtWindows, timezone);

    // Draw throughput under the response time chart if available
    if (throughputArr.length) {
        const thrTimestamps = throughputArr.map(d => parseTimestamp(d.timestamp, timezone));
        const thrMetrics = [{
            name: 'Throughput',
            data: throughputArr.map(d => d.value),
            anomalies: throughputArr.map(d => d.anomaly !== 'Normal'),
            anomalyMessages: throughputArr.map(d => d.anomaly),
            color: 'rgba(31, 119, 180, 1)',
            yAxisUnit: 'r/s'
        }];
        // Get throughput anomaly windows for this transaction
        const thrWindows = transactionWindows['rps'] || [];
        createGraph(`${chartElementId}-throughput`, `Throughput - ${transactionName}`, thrTimestamps, thrMetrics, styling, layoutConfig, thrWindows, timezone);
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
                if (thrEl) { try { Plotly.Plots.resize(thrEl); } catch (e) { } }
                if (respEl) { try { Plotly.Plots.resize(respEl); } catch (e) { } }
            });
        }
    } catch (e) { /* no-op */ }
}

function createGraphs(chartData, styling, layoutConfig, overallAnomalyWindows, timezone) {
    const overalAvg = chartData.overalAvgResponseTime?.data || [];
    const overalMedian = chartData.overalMedianResponseTime?.data || [];
    const overalPct90 = chartData.overal90PctResponseTime?.data || [];
    const overalThroughput = chartData.overalThroughput?.data || [];
    const overalUsers = chartData.overalUsers?.data || [];
    const overalErrors = chartData.overalErrors?.data || [];

    const anomalyWindowsByMetric = overallAnomalyWindows || {};

    // Choose timestamps source from first available series
    const base = overalAvg.length ? overalAvg : (overalMedian.length ? overalMedian : (overalPct90.length ? overalPct90 : (overalThroughput.length ? overalThroughput : (overalUsers.length ? overalUsers : overalErrors))));
    if (!base || !base.length) {
        console.warn('No overall time series available to plot');
        return;
    }
    const timestamps = base.map(d => parseTimestamp(d.timestamp, timezone));

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
        const thrWindows = anomalyWindowsByMetric['overalThroughput'] || [];
        createGraph('throughputChart', 'Throughput and Users', timestamps, throughputUsersMetrics, styling, layoutConfig, thrWindows, timezone);
    }

    if (responseTimeMetrics.length) {
        // Union anomaly windows across response-time overall metrics
        const rtWindows = [];
        ['overalAvgResponseTime', 'overalMedianResponseTime', 'overal90PctResponseTime'].forEach(key => {
            const wins = anomalyWindowsByMetric[key];
            if (Array.isArray(wins)) {
                rtWindows.push(...wins);
            }
        });
        createGraph('responseTimeChart', 'Response Time', timestamps, responseTimeMetrics, styling, layoutConfig, rtWindows, timezone);
    }

    const errors = overalErrors.map(d => d.value);
    if (errors.length) {
        const errWindows = anomalyWindowsByMetric['overalErrors'] || [];
        createGraph('overalErrors', 'Errors', timestamps, [
            { name: 'Errors', data: errors, anomalies: [], anomalyMessages: [], color: 'rgba(255, 8, 8, 0.8)', yAxisUnit: 'er' }
        ], styling, layoutConfig, errWindows, timezone);
    }

    // Render scatter only if the element exists on the page
    const scatterEl = document.getElementById('responseTimeScatterChart');
    if (scatterEl && Array.isArray(chartData.avgResponseTimePerReq) && chartData.avgResponseTimePerReq.length) {
        createScatterChartForResponseTimes(chartData.avgResponseTimePerReq, 'responseTimeScatterChart', styling, layoutConfig, timezone);
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

function createGraph(divId, title, labels, metrics, styling, layoutConfig, anomalyWindows, timezone) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        console.warn(`No metrics provided for graph: ${title}`);
        return;
    }

    const safeLayoutConfig = layoutConfig || {};
    const themeColors = (typeof getCurrentThemeColors === 'function') ? getCurrentThemeColors() : {};
    const paperBg = themeColors.paperBg || 'rgba(0,0,0,0)';
    const plotBg = themeColors.plotBg || 'rgba(0,0,0,0)';
    const bodyEl = document.body || document.documentElement;
    const isLightTheme = (bodyEl && bodyEl.classList && bodyEl.classList.contains('light-theme'))
        || (typeof localStorage !== 'undefined' && localStorage.getItem('theme') === 'light');
    const anomalyFillColor = isLightTheme
        ? 'rgba(231, 14, 36, 0.25)'   // softer band for light theme
        : 'rgba(231, 14, 36, 0.25)';  // slightly stronger band for dark theme

    // Build standard line traces (no per-point anomaly dots)
    const traces = metrics.map(metric => {
        return {
            x: labels,
            y: metric.data,
            mode: 'lines',
            name: metric.name,
            line: { shape: styling.line_shape, width: styling.line_width, color: metric.color },
            yaxis: metric.useRightYAxis ? 'y2' : 'y',
            cliponaxis: false
        };
    });

    const anomalyShapes = [];
    const hasExplicitWindows = Array.isArray(anomalyWindows) && anomalyWindows.length > 0;

    if (hasExplicitWindows) {
        // Use explicit windows from backend (overall anomaly windows).
        // Normalize to Date objects and merge overlapping/adjacent windows
        // so that overlapping anomalies render as a single continuous band.
        const normalized = anomalyWindows
            .map(win => {
                if (!win) return null;
                const rawStart = win.start || win.x0;
                const rawEnd = win.end || win.x1;
                if (!rawStart || !rawEnd) return null;
                const s = parseTimestamp(rawStart, timezone);
                const e = parseTimestamp(rawEnd, timezone);
                if (!isFinite(s.getTime()) || !isFinite(e.getTime())) return null;
                return s <= e ? { start: s, end: e } : { start: e, end: s };
            })
            .filter(w => w !== null)
            .sort((a, b) => a.start - b.start);

        const merged = [];
        normalized.forEach(win => {
            if (!merged.length) {
                merged.push({ start: win.start, end: win.end });
                return;
            }
            const last = merged[merged.length - 1];
            if (win.start <= last.end) {
                // Overlapping or touching: extend the last window
                if (win.end > last.end) last.end = win.end;
            } else {
                merged.push({ start: win.start, end: win.end });
            }
        });

        // First expand point anomalies, keeping track of vertical line markers,
        // then merge the expanded rectangles so that they do not visually overlap.
        const expandedWindows = [];
        merged.forEach(win => {
            let x0 = win.start;
            let x1 = win.end;

            // Check if this is a point-in-time anomaly (where start === end)
            const isPointAnomaly = x0.getTime() === x1.getTime();

            if (isPointAnomaly) {
                // Expand the window by 2 minutes on each side for visibility
                const minWidthMs = 2 * 60 * 1000; // 2 minutes in milliseconds
                x0 = new Date(x0.getTime() - minWidthMs);
                x1 = new Date(x1.getTime() + minWidthMs);

                // Add a vertical line marker at the exact anomaly point for emphasis
                anomalyShapes.push({
                    type: 'line',
                    xref: 'x',
                    yref: 'paper',
                    x0: win.start,
                    x1: win.start,
                    y0: 0,
                    y1: 1,
                    line: {
                        color: 'rgba(231, 14, 36, 0.8)',
                        width: 2,
                        dash: 'dot'
                    }
                });
            }

            expandedWindows.push({ start: x0, end: x1 });
        });

        // Merge expanded rectangles to avoid overlapping shaded bands
        expandedWindows.sort((a, b) => a.start - b.start);
        const rectWindows = [];
        expandedWindows.forEach(win => {
            if (!rectWindows.length) {
                rectWindows.push({ start: win.start, end: win.end });
                return;
            }
            const last = rectWindows[rectWindows.length - 1];
            if (win.start <= last.end) {
                if (win.end > last.end) {
                    last.end = win.end;
                }
            } else {
                rectWindows.push({ start: win.start, end: win.end });
            }
        });

        rectWindows.forEach(win => {
            anomalyShapes.push({
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: win.start,
                x1: win.end,
                y0: 0,
                y1: 1,
                fillcolor: anomalyFillColor,
                line: { width: 0 }
            });
        });
    } else {
        // Fall back to per-point anomaly flags (used by per-transaction charts)
        const anomalyFlags = (labels || []).map((_, idx) =>
            metrics.some(metric => Array.isArray(metric.anomalies) && metric.anomalies[idx])
        );

        let inRun = false;
        let startIdx = 0;
        anomalyFlags.forEach((flag, idx) => {
            if (flag && !inRun) {
                inRun = true;
                startIdx = idx;
            } else if (!flag && inRun) {
                inRun = false;
                const endIdx = idx - 1;
                if (endIdx >= startIdx && labels[startIdx] != null && labels[endIdx] != null) {
                    let x0 = labels[startIdx];
                    let x1 = labels[endIdx];
                    // If only a single anomalous point, expand band to neighbor interval
                    if (startIdx === endIdx) {
                        const prev = startIdx > 0 ? labels[startIdx - 1] : null;
                        const next = endIdx < labels.length - 1 ? labels[endIdx + 1] : null;
                        if (prev && next) {
                            x0 = prev;
                            x1 = next;
                        } else if (prev) {
                            x0 = prev;
                        } else if (next) {
                            x1 = next;
                        }
                    }
                    anomalyShapes.push({
                        type: 'rect',
                        xref: 'x',
                        yref: 'paper',
                        x0: x0,
                        x1: x1,
                        y0: 0,
                        y1: 1,
                        fillcolor: anomalyFillColor,
                        line: { width: 0 }
                    });
                }
            }
        });
        if (inRun && labels.length > 0 && labels[startIdx] != null && labels[labels.length - 1] != null) {
            let x0 = labels[startIdx];
            let x1 = labels[labels.length - 1];
            if (startIdx === labels.length - 1 && labels.length > 1) {
                // Single anomalous point at the very end: extend band back to previous timestamp
                x0 = labels[labels.length - 2];
            }
            anomalyShapes.push({
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: x0,
                x1: x1,
                y0: 0,
                y1: 1,
                fillcolor: anomalyFillColor,
                line: { width: 0 }
            });
        }
    }

    const firstLeft = metrics.find(metric => !metric.useRightYAxis) || metrics[0];
    const leftYAxisColor = firstLeft?.color || (styling?.axis_font_color || '#888');
    const rightYAxisCandidate = metrics.find(metric => metric.useRightYAxis) || firstLeft;
    const rightYAxisColor = rightYAxisCandidate?.color || leftYAxisColor;

    // Calculate x-axis range with padding to prevent clipping
    let xaxisRange = null;
    if (labels && labels.length > 0) {
        // Convert labels to timestamps if they are Date objects
        const times = labels.map(l => l instanceof Date ? l.getTime() : new Date(l).getTime()).filter(t => !isNaN(t));
        if (times.length > 0) {
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);
            const duration = maxTime - minTime;

            // Add 5% padding on each side, or default to 1 minute if single point
            const padding = duration > 0 ? duration * 0.03 : 60000;

            xaxisRange = [new Date(minTime - padding), new Date(maxTime + padding)];
        }
    }

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
            automargin: true,
            tickformat: '%I:%M %p',  // 12-hour format without seconds
            range: xaxisRange, // Apply calculated range with padding
            autorange: false   // Explicitly disable autorange
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
        },
        shapes: [
            ...((safeLayoutConfig && Array.isArray(safeLayoutConfig.shapes)) ? safeLayoutConfig.shapes : []),
            ...anomalyShapes
        ]
    };

    Plotly.newPlot(divId, traces, layout, { responsive: true, useResizeHandler: true });
}

// Updated createScatterChartForResponseTimes function to include styling and layoutConfig as parameters
function createScatterChartForResponseTimes(avgResponseTimePerReq, elementId, styling, layoutConfig, timezone) {
    const timestamps = [];
    const values = [];

    avgResponseTimePerReq.forEach(transaction => {
        transaction.data.forEach(record => {
            timestamps.push(parseTimestamp(record.timestamp, timezone));
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
            gridcolor: styling.gridcolor,
            tickformat: '%I:%M %p'  // 12-hour format without seconds
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

function parseTimestamp(timestamp, timezone) {
    if (!timestamp) return null;
    // If a timezone is provided, treat the timestamp as local time
    // by stripping the timezone offset (including 'Z') from the ISO string.
    if (timezone) {
        // Remove the timezone offset (e.g., +03:00, -03:00, or Z) from the end of the string
        // This regex matches +HH:MM, -HH:MM, or Z at the end of the string
        const localIso = timestamp.replace(/([+-]\d{2}:\d{2}|Z)$/, '');
        return new Date(localIso);
    }
    return new Date(timestamp);
}
