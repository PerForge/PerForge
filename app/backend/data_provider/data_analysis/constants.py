OVERALL_METRIC_KEYS: list[str] = [
    'overalAvgResponseTime',
    'overalMedianResponseTime',
    'overal90PctResponseTime',
    'overalThroughput',
]

OVERALL_METRIC_DISPLAY: dict[str, str] = {
    'overalAvgResponseTime': 'Average response time',
    'overalMedianResponseTime': 'Median response time',
    'overal90PctResponseTime': '90th percentile response time',
    'overalThroughput': 'Throughput',
}

COL_OVERALL_THROUGHPUT: str = 'overalThroughput'
COL_OVERALL_USERS: str = 'overalUsers'

COL_TXN: str = 'transaction'
COL_TXN_RPS: str = 'rps'
COL_OVERALL_RPS: str = 'overall_rps'
COL_ERR_RATE: str = 'error_rate'

RT_TXN_METRICS: list[str] = ['rt_ms_median', 'rt_ms_avg', 'rt_ms_p90', 'rt_ms']

# Human-readable metric names for transaction status reasons
METRIC_DISPLAY_NAMES: dict[str, str] = {
    'rt_ms': 'Response Time',
    'rt_ms_median': 'Response Time (median)',
    'rt_ms_avg': 'Response Time (avg)',
    'rt_ms_p90': 'Response Time (90th percentile)',
    'error_rate': 'Error Rate',
    'rps': 'Requests per Second',
    'overall_rps': 'Overall RPS',
    'stddev': 'Standard Deviation',
    'pct90': '90th Percentile',
    'avg': 'Average',
    'median': 'Median',
}

ANOMALY_SUFFIX: str = '_anomaly'
