// page-scripts.js

async function fetchAndDisplayTestData(testTitle, sourceType, id) {
    const loadingScreen = document.getElementById('loading-screen');
    const loadingMessage = document.getElementById('loading-message');

    // Show the loading screen
    showLoadingScreen(loadingScreen, loadingMessage);

    try {
        const data = await fetchData(testTitle, sourceType, id);
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

async function fetchData(testTitle, sourceType, id) {
    try {
        const response = await apiClient.reports.getReportData(testTitle, sourceType, id);
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

    // Attach event listeners after rows are inserted
    if (aggregatedTable && aggregatedTable.length > 0) {
        initializeListJs();
    }
    addDropdownEventListeners(chartData, styling, layoutConfig);
}

function updateTestDetails(testDetails) {
    document.getElementById('startTimeDetail').innerText = testDetails.start_time;
    document.getElementById('endTimeDetail').innerText = testDetails.end_time;
    document.getElementById('durationDetail').innerText = testDetails.duration;
}

function updatePerformanceCard(summary, performanceStatus) {
    const card = document.querySelector('.card[style*="border-left"]');
    const summaryElement = card.querySelector('#summaryCard');

    const color = performanceStatus ? '#02d051' : '#ffc107';

    card.style.borderLeft = `4px solid ${color}`;
    summaryElement.innerHTML = summary; // Changed from textContent to innerHTML
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
                <div class="chart" id="chart-${stat.transaction}" style="height: 300px;"></div>
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

    const avgArr = avgTransactionData?.data || [];
    const medianArr = medianTransactionData?.data || [];
    const pctArr = pctTransactionData?.data || [];

    // Choose timestamps source from first available series
    const base = avgArr.length ? avgArr : (medianArr.length ? medianArr : (pctArr.length ? pctArr : []));
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
    if (throughput.length) throughputUsersMetrics.push({ name: 'Throughput', data: throughput, anomalies: throughputAnomalies, anomalyMessages: throughputAnomalyMessages, color: 'rgba(31, 119, 180, 1)', yAxisUnit: 'r/s' });
    if (users.length) throughputUsersMetrics.push({ name: 'Users', data: users, anomalies: [], anomalyMessages: [], color: 'rgba(0, 155, 162, 0.8)', yAxisUnit: 'vu', useRightYAxis: true });
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

    if (Array.isArray(chartData.avgResponseTimePerReq) && chartData.avgResponseTimePerReq.length) {
        createScatterChartForResponseTimes(chartData.avgResponseTimePerReq, 'responseTimeScatterChart', styling, layoutConfig);
    }
}

function createGraph(divId, title, labels, metrics, styling, layoutConfig) {
    if (!Array.isArray(metrics) || metrics.length === 0) {
        console.warn(`No metrics provided for graph: ${title}`);
        return;
    }

    const safeLayoutConfig = layoutConfig || {};

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
        title: {
            text: title,
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
                color: leftYAxisColor,
                family: styling.font_family,
                size: styling.yaxis_tickfont_size
            },
            color: leftYAxisColor,
            ticksuffix: ` ${firstLeft?.yAxisUnit || ''}`,
            zeroline: false,
            gridcolor: styling.gridcolor,
            rangemode: 'tozero' // Ensure Y-axis starts at 0
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
            rangemode: "tozero" // Ensure secondary Y-axis starts at 0
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
            yanchor: 'top'
        },
        ...safeLayoutConfig // Spread the layout configuration safely
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
