// page-scripts.js

async function fetchAndDisplayTestData(testTitle) {
    const loadingScreen = document.getElementById('loading-screen');
    const loadingMessage = document.getElementById('loading-message');

    // Show the loading screen
    showLoadingScreen(loadingScreen, loadingMessage);

    try {
        const data = await fetchData(testTitle);
        handleFetchedData(data);
        // Hide the loading screen
        hideLoadingScreen(loadingScreen);
    } catch (error) {
        console.error('Error fetching data:', error);
        hideLoadingScreen(loadingScreen);
    }
}

function showLoadingScreen(loadingScreen, loadingMessage) {
    loadingScreen.style.display = 'flex'; 
    loadingMessage.innerText = 'Preparing your tests data'; 
}

function hideLoadingScreen(loadingScreen) {
    loadingScreen.style.display = 'none';
}

async function fetchData(testTitle) {
    const response = await fetch(`/api/data?test_title=${encodeURIComponent(testTitle)}`);
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }
    return response.json();
}

function handleFetchedData(data) {
    const {
        data: chartData,
        styling,
        layout: layoutConfig,
        analysis: analysisData,
        aggregated_results: aggregatedResults,
        test_details: testDetails,
        statistics,
        summary,
        performance_status
    } = data;

    updateTestDetails(testDetails);
    updatePerformanceCard(summary, performance_status);
    updateCards(aggregatedResults);
    updateTable(statistics);
    updateAnalysisTable(analysisData);
    createGraphs(chartData, styling, layoutConfig);

    // Attach event listeners after rows are inserted
    initializeListJs();
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

function updateCards(aggregatedResults) {
    document.getElementById('vuCard').innerText = aggregatedResults.vu;
    document.getElementById('throughputCard').innerText = aggregatedResults.throughput;
    document.getElementById('medianCard').innerText = aggregatedResults.median;
    document.getElementById('pct90Card').innerText = aggregatedResults['90pct'];
    document.getElementById('errorsCard').innerText = aggregatedResults.errors;
}

function updateTable(statistics) {
    const tbody = document.querySelector('#aggregated-table .list');
    tbody.innerHTML = '';

    statistics.forEach(stat => {
        const row = `
        <tr class="stat-row" data-transaction="${stat.transaction}">
            <th class="label">
                <button class="dropdown-btn btn btn-primary" data-target="chart-${stat.transaction}">˅</button>
                ${stat.transaction}
            </th>
            <th class="count">${stat.count}</th>
            <th class="avg">${stat.avg}</th>
            <th class="pct50">${stat.pct50}</th>
            <th class="pct75">${stat.pct75}</th>
            <th class="pct90">${stat.pct90}</th>
            <th class="rpm">${stat.rpm.toFixed(2)}</th>
            <th class="errors">${stat.errors.toFixed(2)}</th>
            <th class="stddev">${stat.stddev}</th>
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
    const tbody = document.querySelector('#analysis-table .list');
    tbody.innerHTML = ''; 

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
    const avgTransactionData = chartData.avgResponseTimePerReq.find(transaction => transaction.name === transactionName);
    const medianTransactionData = chartData.medianResponseTimePerReq.find(transaction => transaction.name === transactionName);
    const pctTransactionData = chartData.pctResponseTimePerReq.find(transaction => transaction.name === transactionName);

    if (!avgTransactionData || !medianTransactionData || !pctTransactionData) {
        console.error(`Transaction data not found for: ${transactionName}`);
        return;
    }

    const timestamps = avgTransactionData.data.map(d => new Date(d.timestamp));
    const avgValues = avgTransactionData.data.map(d => d.value);
    const avgAnomalies = avgTransactionData.data.map(d => d.anomaly !== 'Normal');
    const avgAnomalyMessages = avgTransactionData.data.map(d => d.anomaly);

    const medianValues = medianTransactionData.data.map(d => d.value);
    const medianAnomalies = medianTransactionData.data.map(d => d.anomaly !== 'Normal');
    const medianAnomalyMessages = medianTransactionData.data.map(d => d.anomaly);

    const pctValues = pctTransactionData.data.map(d => d.value);
    const pctAnomalies = pctTransactionData.data.map(d => d.anomaly !== 'Normal');
    const pctAnomalyMessages = pctTransactionData.data.map(d => d.anomaly);

    createGraph(chartElementId, `Response Time - ${transactionName}`, timestamps, [
        {
            name: 'Avg Response Time',
            data: avgValues,
            anomalies: avgAnomalies,
            anomalyMessages: avgAnomalyMessages,
            color: 'rgba(2, 208, 81, 0.8)',
            yAxisUnit: 'ms'
        },
        {
            name: 'Median Response Time',
            data: medianValues,
            anomalies: medianAnomalies,
            anomalyMessages: medianAnomalyMessages,
            color: 'rgba(23, 100, 254, 0.8)',
            yAxisUnit: 'ms'
        },
        {
            name: 'Pct90 Response Time',
            data: pctValues,
            anomalies: pctAnomalies,
            anomalyMessages: pctAnomalyMessages,
            color: 'rgba(245, 165, 100, 1)',
            yAxisUnit: 'ms'
        }
    ],
        styling, layoutConfig);
}

function createGraphs(chartData, styling, layoutConfig) {
    const timestamps = chartData.overalAvgResponseTime.data.map(d => new Date(d.timestamp));

    const avgResponseTime = chartData.overalAvgResponseTime.data.map(d => d.value);
    const avgResponseTimeAnomalies = chartData.overalAvgResponseTime.data.map(d => d.anomaly !== 'Normal');
    const avgResponseTimeAnomalyMessages = chartData.overalAvgResponseTime.data.map(d => d.anomaly);

    const medianResponseTime = chartData.overalMedianResponseTime.data.map(d => d.value);
    const medianResponseTimeAnomalies = chartData.overalMedianResponseTime.data.map(d => d.anomaly !== 'Normal');
    const medianResponseTimeAnomalyMessages = chartData.overalMedianResponseTime.data.map(d => d.anomaly);

    const pctResponseTime = chartData.overal90PctResponseTime.data.map(d => d.value);
    const pctResponseTimeAnomalies = chartData.overal90PctResponseTime.data.map(d => d.anomaly !== 'Normal');
    const pctResponseTimeAnomalyMessages = chartData.overal90PctResponseTime.data.map(d => d.anomaly);

    const throughput = chartData.overalThroughput.data.map(d => d.value);
    const throughputAnomalies = chartData.overalThroughput.data.map(d => d.anomaly !== 'Normal');
    const throughputAnomalyMessages = chartData.overalThroughput.data.map(d => d.anomaly);

    const users = chartData.overalUsers.data.map(d => d.value);

    const errors = chartData.overalErrors.data.map(d => d.value);

    createGraph('throughputChart', 'Throughput and Users', timestamps, [
        { name: 'Throughput', data: throughput, anomalies: throughputAnomalies, anomalyMessages: throughputAnomalyMessages, color: 'rgba(31, 119, 180, 1)', yAxisUnit: 'r/s' },
        { name: 'Users', data: users, anomalies: [], anomalyMessages: [], color: 'rgba(0, 155, 162, 0.8)', yAxisUnit: 'vu', useRightYAxis: true }
    ], styling, layoutConfig);

    createGraph('responseTimeChart', 'Response Time', timestamps, [
        { name: 'Avg Response Time', data: avgResponseTime, anomalies: avgResponseTimeAnomalies, anomalyMessages: avgResponseTimeAnomalyMessages, color: 'rgba(2, 208, 81, 0.8)', yAxisUnit: 'ms' },
        { name: 'Median Response Time', data: medianResponseTime, anomalies: medianResponseTimeAnomalies, anomalyMessages: medianResponseTimeAnomalyMessages, color: 'rgba(23, 100, 254, 0.8)', yAxisUnit: 'ms' },
        { name: '90Pct Response Time', data: pctResponseTime, anomalies: pctResponseTimeAnomalies, anomalyMessages: pctResponseTimeAnomalyMessages, color: 'rgba(245, 165, 100, 1)', yAxisUnit: 'ms' }
    ], styling, layoutConfig);

    createGraph('overalErrors', 'Errors', timestamps, [
        { name: 'Errors', data: errors, anomalies: [], anomalyMessages: [], color: 'rgba(255, 8, 8, 0.8)', yAxisUnit: 'er' }
    ], styling, layoutConfig);

    createScatterChartForResponseTimes(chartData.avgResponseTimePerReq, 'responseTimeScatterChart', styling, layoutConfig);
}

function createGraph(divId, title, labels, metrics, styling, layoutConfig) {
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

    const leftYAxisColor = metrics.find(metric => !metric.useRightYAxis).color;
    const rightYAxisColor = metrics.find(metric => metric.useRightYAxis)?.color || leftYAxisColor;

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
            ticksuffix: ` ${metrics.find(metric => !metric.useRightYAxis).yAxisUnit}`, 
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
            ticksuffix: ` ${metrics.find(metric => metric.useRightYAxis)?.yAxisUnit || ''}`, 
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
        ...layoutConfig // Spread the layout configuration
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