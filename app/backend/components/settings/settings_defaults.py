# Copyright Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Default settings definitions for PerForge projects.

Each setting includes:
- value: The default value
- type: Data type (int, float, bool, string, list, dict)
- description: Human-readable description
- min/max: Optional constraints for numeric types
- options: Optional list of valid options for string/list types
"""

from typing import Dict, Any


ML_ANALYSIS_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # Isolation Forest Settings
    'contamination': {
        'value': 0.001,
        'type': 'float',
        'min': 0.0001,
        'max': 0.5,
        'description': 'The expected proportion of outliers (anomalies) in the dataset. This parameter controls the sensitivity of the Isolation Forest algorithm. Lower values (e.g., 0.001) imply that anomalies are rare, resulting in stricter detection where fewer points are flagged. Higher values (e.g., 0.1) assume anomalies are more common.'
    },
    'isf_threshold': {
        'value': 0.1,
        'type': 'float',
        'min': -1.0,
        'max': 1.0,
        'description': 'The decision function threshold for classifying a data point as an anomaly. The Isolation Forest algorithm assigns an anomaly score to each point; points with scores lower than this threshold are classified as anomalies. Adjusting this value shifts the boundary between normal and anomalous behavior.'
    },
    'isf_feature_metric': {
        'value': 'overalThroughput',
        'type': 'string',
        'options': ['overalThroughput', 'overalUsers'],
        'description': 'The primary performance metric used for Isolation Forest multi-dimensional analysis. This metric serves as the main feature for detecting anomalies. "overalThroughput" focuses on system capacity, while "overalUsers" focuses on load concurrency.'
    },
    'isf_validation_threshold': {
        'value': 0.1,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The threshold for relative deviation from the median used to validate Isolation Forest anomalies. If the deviation of a flagged point is less than this threshold, it is reclassified as normal. This helps reduce false positives for minor fluctuations.'
    },

    # Z-Score Detection
    'z_score_threshold': {
        'value': 3,
        'type': 'float',
        'min': 1.0,
        'max': 10.0,
        'description': 'The number of standard deviations from the mean required to classify a data point as an anomaly. A higher threshold (e.g., 3.0) makes the detection less sensitive, flagging only extreme outliers. A lower threshold (e.g., 2.0) is more sensitive but may increase false positives.'
    },
    'z_score_median_validation_threshold': {
        'value': 0.1,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The threshold for relative deviation from the median used to validate Z-Score anomalies. A point is considered anomalous only if it fails both the Z-Score test AND deviates from the median by more than this percentage.'
    },

    # Rolling Analysis
    'rolling_window': {
        'value': 5,
        'type': 'int',
        'min': 2,
        'max': 20,
        'description': 'The size of the moving window (in number of samples) used for calculating rolling statistics such as mean, variance, and correlation. A larger window smooths out short-term fluctuations but may delay the detection of rapid changes. A smaller window is more responsive but noisier.'
    },
    'rolling_correlation_threshold': {
        'value': 0.4,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum correlation coefficient required between the load metric (e.g., Users) and the performance metric (e.g., Throughput) to consider the system stable. Values below this threshold suggest a loss of linearity, potentially indicating saturation or performance degradation.'
    },

    # Ramp-Up Detection
    'ramp_up_required_breaches_min': {
        'value': 3,
        'type': 'int',
        'min': 1,
        'max': 10,
        'description': 'The minimum number of consecutive data points that must breach the anomaly threshold to confirm a "tipping point" or significant performance shift. This prevents single transient spikes from triggering false alarms.'
    },
    'ramp_up_required_breaches_max': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'The maximum number of consecutive breaches considered when dynamically calculating the tipping point requirement. This caps the dynamic adjustment logic, ensuring the system doesn\'t wait too long to flag an issue.'
    },
    'ramp_up_required_breaches_fraction': {
        'value': 0.15,
        'type': 'float',
        'min': 0.01,
        'max': 0.5,
        'description': 'The fraction of total data points in the dataset used to dynamically calculate the required number of breaches. The actual required breaches will be calculated based on dataset size but clamped between the min and max values.'
    },
    'ramp_up_base_metric': {
        'value': 'overalUsers',
        'type': 'string',
        'options': ['overalUsers', 'overalThroughput'],
        'description': 'The base metric used as the independent variable for correlation analysis during ramp-up. Typically "overalUsers" (load), it is correlated against performance metrics to detect when the system stops scaling linearly with load.'
    },

    # Load Detection
    'fixed_load_percentage': {
        'value': 60,
        'type': 'int',
        'min': 50,
        'max': 100,
        'description': 'The percentage of total data points where the user count must remain stable (within a small margin) for the test to be classified as a "Fixed Load" test. This classification affects which anomaly detection algorithms are applied.'
    },

    # Metric Stability Analysis
    'slope_threshold': {
        'value': 1.000,
        'type': 'float',
        'min': 0.0,
        'max': 10.0,
        'description': 'The threshold for the slope of the linear regression line fitted to the metric data. Absolute slope values exceeding this threshold indicate a significant upward or downward trend (instability), whereas lower values indicate a steady state.'
    },
    'p_value_threshold': {
        'value': 0.05,
        'type': 'float',
        'min': 0.01,
        'max': 0.2,
        'description': 'The significance level (alpha) for statistical hypothesis testing (e.g., Mann-Kendall trend test). A p-value below this threshold allows us to reject the null hypothesis (stability) and conclude that a statistically significant trend exists.'
    },
    'numpy_var_threshold': {
        'value': 0.003,
        'type': 'float',
        'min': 0.0,
        'max': 0.1,
        'description': 'The variance threshold for determining metric stability. Variance measures how spread out the data points are. Values below this threshold indicate low variability (stable performance), while higher values suggest instability or noise.'
    },
    'cv_threshold': {
        'value': 0.07,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The Coefficient of Variation (CV) threshold, calculated as the standard deviation divided by the mean. This normalized measure of dispersion helps compare volatility across metrics with different scales. Higher values indicate higher relative volatility.'
    },

    # Context Filtering
    'context_median_window': {
        'value': 10,
        'type': 'int',
        'min': 3,
        'max': 50,
        'description': 'The window size (number of samples before and after a point) used to calculate the local median context. This local context helps differentiate between global anomalies and local fluctuations relative to immediate neighbors.'
    },
    'context_median_pct': {
        'value': 0.15,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The percentage deviation from the local context median allowed before a point is flagged as a false positive. If an anomaly is within this percentage of its local neighbors, it is suppressed (considered noise rather than a true anomaly).'
    },
    'context_median_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enables the "Contextual Median" filter, a post-processing step that removes false positive anomalies which are statistically similar to their immediate neighbors, improving detection precision.'
    },

    # Severity Thresholds
    'severity_critical': {
        'value': 0.60,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum impact score required to classify an anomaly as "Critical".'
    },
    'severity_high': {
        'value': 0.40,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum impact score required to classify an anomaly as "High".'
    },
    'severity_medium': {
        'value': 0.25,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum impact score required to classify an anomaly as "Medium".'
    },
    'severity_low': {
        'value': 0.10,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum impact score required to classify an anomaly as "Low".'
    },

    # Stability Analysis
    'stability_outlier_z_score': {
        'value': 3.0,
        'type': 'float',
        'min': 1.0,
        'max': 10.0,
        'description': 'The Z-score threshold used to identify and remove outliers before performing stability analysis.'
    },
    'stability_min_points': {
        'value': 3,
        'type': 'int',
        'min': 2,
        'max': 20,
        'description': 'The minimum number of data points required to perform stability analysis on a metric.'
    },
    'baseline_window': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'The number of data points preceding an anomaly window used to calculate the baseline value for comparison.'
    },

    # Merging & Grouping
    'merge_gap_samples': {
        'value': 4,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'The maximum gap (in number of samples) allowed between two distinct anomaly periods to merge them into a single continuous event. If anomalies occur close together (within this gap), they are treated as one prolonged performance issue.'
    },

    # Per-Transaction Analysis
    'per_txn_coverage': {
        'value': 0.8,
        'type': 'float',
        'min': 0.1,
        'max': 1.0,
        'description': 'The target cumulative traffic coverage for selecting transactions to analyze. For example, 0.8 means the system will select the top volume transactions that explicitly account for 80% of the total traffic, ignoring low-volume noise.'
    },
    'per_txn_max_k': {
        'value': 50,
        'type': 'int',
        'min': 1,
        'max': 200,
        'description': 'The maximum absolute number of unique transactions to analyze, regardless of the coverage target. This prevents performance bottlenecks in cases with thousands of unique low-volume transactions.'
    },
    'per_txn_min_points': {
        'value': 6,
        'type': 'int',
        'min': 3,
        'max': 20,
        'description': 'The minimum number of data points a transaction must have to be eligible for analysis. Transactions with insufficient data are skipped to ensure statistical validity.'
    },
    'per_txn_analysis_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Master switch to enable or disable granular, per-transaction anomaly detection. When enabled, the system analyzes individual transaction endpoints in addition to global system metrics. This value affects the scope of anomaly detection.'
    },
    'per_txn_metrics': {
        'value': ['rt_ms_median', 'rt_ms_avg', 'rt_ms_p90', 'error_rate', 'rps'],
        'type': 'list',
        'description': 'The list of specific performance metrics to be analyzed for each transaction. Common metrics include response times (avg, median, p90), error rates, and throughput (RPS). This value affects the type of performance issues detected in transactions.'
    },
}


TRANSACTION_STATUS_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # NFR Checking
    'nfr_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enables the validation of Non-Functional Requirements (NFRs) as part of the transaction status evaluation. If enabled, transactions failing NFR checks (e.g., response time limits) will be marked accordingly. This value affects the inclusion of NFRs in transaction status evaluation.'
    },

    # Baseline Comparison
    'baseline_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enables automatic comparison against a baseline (previous successful test run). This detects performance regressions by comparing current metrics with historical data. This value affects the detection of performance regressions.'
    },
    'baseline_warning_threshold_pct': {
        'value': 10.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'The percentage deviation from the baseline metric that triggers a "WARNING" status. For example, if current response time is 15% higher than baseline and this is set to 10%, it flags a warning. This value affects the sensitivity of baseline comparison.'
    },
    'baseline_failed_threshold_pct': {
        'value': 20.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'The percentage deviation from the baseline metric that triggers a "FAILED" status. Deviations exceeding this threshold indicate a severe regression requiring immediate attention. This value affects the severity of baseline comparison.'
    },
    'baseline_metrics_to_check': {
        'value': ['avg', 'pct50', 'pct90', 'errors'],
        'type': 'list',
        'description': 'The list of metrics to compare against the baseline. For backend tests, this typically includes aggregation stats like "avg", "pct50", "pct90", "errors". For frontend tests, use web vitals like "FCP", "LCP", "TTFB". This value affects the scope of baseline comparison.'
    },

    # ML Anomaly Detection
    'ml_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enables the inclusion of Machine Learning-based anomaly detection results in the final transaction status. If enabled, detected anomalies can degrade the transaction status to Warning or Failed. This value affects the inclusion of ML anomalies in transaction status evaluation.'
    },
    'ml_min_impact': {
        'value': 0.0,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'The minimum "impact score" (weighted by traffic share) required for an ML-detected anomaly to affect the transaction status. Anomalies in low-traffic transactions (below this impact threshold) will be logged but won\'t fail the test. This value affects the sensitivity of ML anomaly detection.'
    }
}


DATA_QUERY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # Backend Listener Query Settings
    'backend_query_granularity_seconds': {
        'value': 30,
        'type': 'int',
        'min': 1,
        'max': 300,
        'description': 'Time granularity (in seconds) for aggregating backend listener metrics in time-series queries. This controls the resolution of data points in charts and statistics. Lower values provide finer detail but may increase query time and data volume. Default is 30 seconds.'
    }
}


REPORTING_TABLE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'aggregated_table_columns': {
        'value': ['avg:Avg RT', 'errors:Errors', 'pct50:P50', 'pct75:P75', 'pct90:P90', 'count:Count', 'rpm:RPM', 'stddev:Std Dev'],
        'type': 'list',
        'description': 'Columns to include in the aggregated data table. Format: metric_key:Display Name (e.g. avg:Avg RT, pct90:P90). Controls which columns appear and their header labels. Available metrics: avg, errors, pct50, pct75, pct90, count, rpm, stddev.'
    },
    'aggregated_table_split_baseline': {
        'value': False,
        'type': 'bool',
        'description': 'When enabled and a baseline test is present, each metric is split into two separate columns (baseline and current) instead of the combined "baseline → current" format.'
    },
    'aggregated_table_current_label': {
        'value': 'Current',
        'type': 'string',
        'description': 'Label suffix for current test columns when split baseline mode is enabled. Result: "Avg RT (Current)".'
    },
    'aggregated_table_baseline_label': {
        'value': 'Baseline',
        'type': 'string',
        'description': 'Label suffix for baseline test columns when split baseline mode is enabled. Result: "Avg RT (Baseline)".'
    },
    'aggregated_table_show_diff': {
        'value': False,
        'type': 'bool',
        'description': 'When enabled and a baseline test is present, adds an absolute difference column after each metric: current minus baseline. Result column name: "Avg RT (Diff)".'
    },
    'aggregated_table_diff_label': {
        'value': 'Diff',
        'type': 'string',
        'description': 'Suffix label for absolute difference columns. Example result: "Avg RT (Diff)".'
    },
    'aggregated_table_show_diff_pct': {
        'value': False,
        'type': 'bool',
        'description': 'When enabled and a baseline test is present, adds a percentage difference column after each metric. Result column name: "Avg RT (Diff %)".'
    },
    'aggregated_table_diff_pct_label': {
        'value': 'Diff %',
        'type': 'string',
        'description': 'Suffix label for percentage difference columns. Example result: "Avg RT (Diff %)".'
    },
    'aggregated_table_highlight_enabled': {
        'value': False,
        'type': 'bool',
        'description': 'When enabled, cells in the aggregated data table are highlighted green for improved metrics and red for degraded metrics relative to the baseline. Requires a baseline test to be selected. Uses the improved/degraded threshold settings below.'
    },
    'aggregated_table_highlight_improved_threshold_pct': {
        'value': 5.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage improvement relative to baseline required for a cell to be highlighted green. For example, 5.0 means the metric must have improved by at least 5% compared to baseline. Applies to "lower is better" metrics (e.g. response time) when the value decreases, and to "higher is better" metrics (e.g. RPM) when the value increases.'
    },
    'aggregated_table_highlight_degraded_threshold_pct': {
        'value': 5.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage degradation relative to baseline required for a cell to be highlighted red. For example, 5.0 means the metric must have degraded by at least 5% compared to baseline. Applies to "lower is better" metrics (e.g. response time) when the value increases, and to "higher is better" metrics (e.g. RPM) when the value decreases.'
    },
    'aggregated_table_highlight_higher_is_better_metrics': {
        'value': ['rpm', 'count'],
        'type': 'list',
        'description': 'List of metric keys where a higher value is considered an improvement (e.g. rpm, count). For these metrics the green/red highlighting direction is inverted: green when the value increases, red when it decreases. All other metrics are treated as "lower is better" (e.g. response time, errors).'
    },
    'top_slowest_count': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 50,
        'description': 'Number of top slowest transactions to include in the ${top_slowest_requests} template variable. The variable inserts a pre-sorted table of the N transactions with the highest value for the chosen metric.'
    },
    'top_slowest_metric': {
        'value': 'pct90',
        'type': 'string',
        'options': ['avg', 'pct50', 'pct75', 'pct90', 'pct95', 'pct99', 'max'],
        'description': 'Metric used to rank transactions for the ${top_slowest_requests} variable. Transactions are sorted descending by this metric and the top N are returned.'
    },
    'top_slowest_exclude_all': {
        'value': True,
        'type': 'bool',
        'description': 'When enabled, rows whose transaction name is an aggregate total (e.g. "all", "Total", "ALL") are excluded from the ${top_slowest_requests} variable so that only individual transactions are ranked.'
    },
    'top_slowest_frontend_table': {
        'value': 'timings_fully_loaded',
        'type': 'string',
        'options': ['timings_fully_loaded', 'timings_page_timings', 'timings_main_document', 'google_web_vitals', 'cpu_long_tasks'],
        'description': 'Table to source data from for the ${top_slowest_requests} variable when running a frontend (SiteSpeed) test.'
    },
    'top_slowest_frontend_metric': {
        'value': 'fullyLoaded',
        'type': 'string',
        'options': [
            'fullyLoaded',
            'LCP', 'FCP', 'CLS', 'FID', 'TBT', 'TTFB',
            'domInteractive', 'domContentLoadedTime', 'loadTime',
            'dns', 'connect', 'serverResponseTime', 'pageDownloadTime',
            'durations', 'lastLongTask', 'totalBlockingTime', 'totalDuration'
        ],
        'description': (
            'Metric to sort by for ${top_slowest_requests} in frontend tests. '
            'Must match a column in the chosen table. '
            'timings_fully_loaded → fullyLoaded. '
            'google_web_vitals → LCP, FCP, CLS, FID, TBT, TTFB. '
            'timings_page_timings → domInteractive, domContentLoadedTime, loadTime. '
            'timings_main_document → dns, connect, serverResponseTime, pageDownloadTime. '
            'cpu_long_tasks → durations, lastLongTask, totalBlockingTime, totalDuration.'
        )
    },
    'top_degraded_count': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 50,
        'description': 'Number of top degraded transactions to include in the ${top_degraded_requests} template variable. Only available when a comparison (baseline) test is selected.'
    },
    'top_degraded_metric': {
        'value': 'pct90',
        'type': 'string',
        'options': ['avg', 'pct50', 'pct75', 'pct90', 'pct95', 'pct99', 'max'],
        'description': 'Metric used to rank and display degradation for the ${top_degraded_requests} variable. The output table shows Current <metric>, Baseline <metric>, Diff, and Diff % columns for this metric only.'
    },
    'top_degraded_exclude_all': {
        'value': True,
        'type': 'bool',
        'description': 'When enabled, aggregate-total rows (e.g. "all", "Total") are excluded from the ${top_degraded_requests} variable so only individual transactions are ranked.'
    },
    'top_degraded_min_pct': {
        'value': 0.0,
        'type': 'float',
        'min': 0.0,
        'description': 'Minimum degradation percentage required for a transaction to appear in ${top_degraded_requests}. Set to 0 to include any positive degradation; set to e.g. 10 to show only transactions that regressed by at least 10%.'
    },
    'top_degraded_sort_by': {
        'value': 'diff_pct',
        'type': 'string',
        'options': ['diff_pct', 'diff'],
        'description': 'Column to sort degraded transactions by. "diff_pct" sorts by relative percentage change (recommended — normalises across transactions with different baseline values). "diff" sorts by absolute difference.'
    },
    'top_degraded_frontend_table': {
        'value': 'timings_fully_loaded',
        'type': 'string',
        'options': ['timings_fully_loaded', 'timings_page_timings', 'timings_main_document', 'google_web_vitals', 'cpu_long_tasks'],
        'description': 'Table to source data from for the ${top_degraded_requests} variable when running a frontend (SiteSpeed) test.'
    },
    'top_degraded_frontend_metric': {
        'value': 'fullyLoaded',
        'type': 'string',
        'options': [
            'fullyLoaded',
            'LCP', 'FCP', 'CLS', 'FID', 'TBT', 'TTFB',
            'domInteractive', 'domContentLoadedTime', 'loadTime',
            'dns', 'connect', 'serverResponseTime', 'pageDownloadTime',
            'durations', 'lastLongTask', 'totalBlockingTime', 'totalDuration'
        ],
        'description': (
            'Metric to rank and display for ${top_degraded_requests} in frontend tests. '
            'Must match a column in the chosen table. '
            'timings_fully_loaded → fullyLoaded. '
            'google_web_vitals → LCP, FCP, CLS, FID, TBT, TTFB. '
            'timings_page_timings → domInteractive, domContentLoadedTime, loadTime. '
            'timings_main_document → dns, connect, serverResponseTime, pageDownloadTime. '
            'cpu_long_tasks → durations, lastLongTask, totalBlockingTime, totalDuration.'
        )
    },
    'overview_table_backend_metrics': {
        'value': [
            'Average:Average RT',
            'Median:Median RT',
            '75%-tile:P75',
            '90%-tile:P90',
            'Total requests:Requests',
            'RPS:RPS',
            'Error %:Error %'
        ],
        'type': 'list',
        'description': (
            'Rows to include in the ${overview_data_table_} for backend tests. '
            'Format: Metric Name:Display Label (e.g. "Average:Avg RT", "Error %:Errors"). '
            'Controls which summary rows appear and their display labels. '
            'Available metrics: Average, Median, 75%-tile, 90%-tile, Total requests, RPS, Error %. '
            'Leave empty to show all rows with their original names.'
        )
    },
    'overview_table_frontend_metrics': {
        'value': [
            'FCP:FCP',
            'LCP:LCP',
            'Fully Loaded:Fully Loaded',
            'TTFB:TTFB',
            'Total Transfer Size (KB):Transfer Size (KB)',
            'Total Requests:Requests',
            'Third-Party Requests:3rd Party Requests',
            'Transfer Size for JavaScript (KB):JS Size (KB)',
            'Transfer Size for CSS (KB):CSS Size (KB)',
            'Transfer Size for Image (KB):Image Size (KB)'
        ],
        'type': 'list',
        'description': (
            'Rows to include in the ${overview_data_table_} for frontend (SiteSpeed) tests. '
            'Format: Metric Name:Display Label (e.g. "FCP:FCP", "Fully Loaded:Fully Loaded"). '
            'Controls which summary rows appear and their display labels. '
            'Available metrics: FCP, LCP, Fully Loaded, TTFB, Total Transfer Size (KB), Total Requests, '
            'Third-Party Requests, Transfer Size for JavaScript (KB), Transfer Size for CSS (KB), Transfer Size for Image (KB). '
            'Leave empty to show all rows with their original names.'
        )
    },
    'skip_empty_internal_graphs': {
        'value': False,
        'type': 'bool',
        'description': 'When enabled, internal graph panels (Errors, Response Time, Throughput) are replaced with a short informational message instead of an empty chart image when the test data contains no values for that panel.',
    },
}


def get_all_defaults() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Get all default settings organized by category.

    Returns:
        Dictionary with categories as keys and their settings as values
    """
    return {
        'ml_analysis': ML_ANALYSIS_DEFAULTS,
        'transaction_status': TRANSACTION_STATUS_DEFAULTS,
        'data_query': DATA_QUERY_DEFAULTS,
        'reporting_table': REPORTING_TABLE_DEFAULTS
    }


def get_flat_defaults() -> Dict[str, Any]:
    """
    Get all default settings as a flat dictionary (category.key -> value).

    Returns:
        Flattened dictionary of default values
    """
    flat = {}
    for category, settings in get_all_defaults().items():
        for key, config in settings.items():
            flat[f"{category}.{key}"] = config['value']
    return flat


def get_defaults_for_category(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Get default settings for a specific category.

    Args:
        category: Category name ('ml_analysis', 'transaction_status')

    Returns:
        Dictionary of settings for the category
    """
    all_defaults = get_all_defaults()
    return all_defaults.get(category, {})

