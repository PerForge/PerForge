# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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
        'description': 'Expected proportion of outliers in the dataset. Lower values mean stricter anomaly detection.'
    },
    'isf_threshold': {
        'value': 0.1,
        'type': 'float',
        'min': -1.0,
        'max': 1.0,
        'description': 'Decision function threshold for anomaly classification. Values below this are considered anomalies.'
    },
    'isf_feature_metric': {
        'value': 'overalThroughput',
        'type': 'string',
        'options': ['overalThroughput', 'overalUsers', 'overalResponseTime'],
        'description': 'Primary metric to use for Isolation Forest multi-dimensional analysis.'
    },

    # Z-Score Detection
    'z_score_threshold': {
        'value': 3,
        'type': 'float',
        'min': 1.0,
        'max': 10.0,
        'description': 'Number of standard deviations from the mean to classify as anomaly. Higher = less sensitive.'
    },

    # Rolling Analysis
    'rolling_window': {
        'value': 5,
        'type': 'int',
        'min': 2,
        'max': 20,
        'description': 'Window size (number of samples) for rolling statistical calculations like mean and correlation.'
    },
    'rolling_correlation_threshold': {
        'value': 0.4,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Correlation threshold for ramp-up saturation detection. Values below this indicate potential issues.'
    },

    # Ramp-Up Detection
    'ramp_up_required_breaches_min': {
        'value': 3,
        'type': 'int',
        'min': 1,
        'max': 10,
        'description': 'Minimum number of consecutive threshold breaches required to confirm a tipping point.'
    },
    'ramp_up_required_breaches_max': {
        'value': 5,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'Maximum number of consecutive threshold breaches to evaluate (cap for dynamic calculation).'
    },
    'ramp_up_required_breaches_fraction': {
        'value': 0.15,
        'type': 'float',
        'min': 0.01,
        'max': 0.5,
        'description': 'Fraction of total data points used to dynamically calculate required breaches (between min and max).'
    },
    'ramp_up_base_metric': {
        'value': 'overalUsers',
        'type': 'string',
        'options': ['overalUsers', 'overalThroughput'],
        'description': 'Base metric to correlate against during ramp-up analysis (typically load indicator).'
    },

    # Load Detection
    'fixed_load_percentage': {
        'value': 60,
        'type': 'int',
        'min': 50,
        'max': 100,
        'description': 'Percentage of data points with stable user count required to classify test as fixed load.'
    },

    # Metric Stability Analysis
    'slope_threshold': {
        'value': 1.000,
        'type': 'float',
        'min': 0.0,
        'max': 10.0,
        'description': 'Linear regression slope threshold for detecting significant upward/downward trends.'
    },
    'p_value_threshold': {
        'value': 0.05,
        'type': 'float',
        'min': 0.01,
        'max': 0.2,
        'description': 'P-value threshold for statistical significance testing (lower = more strict).'
    },
    'numpy_var_threshold': {
        'value': 0.003,
        'type': 'float',
        'min': 0.0,
        'max': 0.1,
        'description': 'Variance threshold for detecting metric stability. Lower variance = more stable.'
    },
    'cv_threshold': {
        'value': 0.07,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Coefficient of variation threshold (std/mean). Higher values indicate more variability.'
    },

    # Context Filtering
    'context_median_window': {
        'value': 10,
        'type': 'int',
        'min': 3,
        'max': 50,
        'description': 'Window size (samples before/after) for calculating contextual median around potential anomalies.'
    },
    'context_median_pct': {
        'value': 0.15,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Percentage deviation from contextual median to filter false positives (0.15 = 15%).'
    },
    'context_median_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable contextual median filtering to reduce false positive anomalies.'
    },

    # Merging & Grouping
    'merge_gap_samples': {
        'value': 4,
        'type': 'int',
        'min': 1,
        'max': 20,
        'description': 'Maximum gap (in samples) between anomaly periods to merge them into a continuous anomaly window.'
    },

    # Per-Transaction Analysis
    'per_txn_coverage': {
        'value': 0.8,
        'type': 'float',
        'min': 0.1,
        'max': 1.0,
        'description': 'Cumulative traffic share coverage for transaction selection (0.8 = select transactions covering 80% of traffic).'
    },
    'per_txn_max_k': {
        'value': 50,
        'type': 'int',
        'min': 1,
        'max': 200,
        'description': 'Maximum number of transactions to analyze individually (cap for coverage-based selection).'
    },
    'per_txn_min_points': {
        'value': 6,
        'type': 'int',
        'min': 3,
        'max': 20,
        'description': 'Minimum number of data points required for a transaction to be included in analysis.'
    }
}


TRANSACTION_STATUS_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # NFR Checking
    'nfr_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable NFR (Non-Functional Requirements) checking for transaction status evaluation.'
    },

    # Baseline Comparison
    'baseline_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable baseline comparison to detect performance regressions against previous test runs.'
    },
    'baseline_warning_threshold_pct': {
        'value': 10.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage deviation from baseline to trigger WARNING status (10-20% = WARNING).'
    },
    'baseline_failed_threshold_pct': {
        'value': 20.0,
        'type': 'float',
        'min': 0.0,
        'max': 100.0,
        'description': 'Percentage deviation from baseline to trigger FAILED status (≥20% = FAILED).'
    },
    'baseline_metrics_to_check': {
        'value': ['rt_ms_avg', 'rt_ms_median', 'rt_ms_p90', 'error_rate'],
        'type': 'list',
        'description': 'List of metrics to evaluate during baseline comparison for regression detection.'
    },

    # ML Anomaly Detection
    'ml_enabled': {
        'value': True,
        'type': 'bool',
        'description': 'Enable ML-based anomaly detection in transaction status evaluation.'
    },
    'ml_min_impact': {
        'value': 0.0,
        'type': 'float',
        'min': 0.0,
        'max': 1.0,
        'description': 'Minimum impact score (traffic share) to consider ML anomalies significant (0.0 = all anomalies considered).'
    }
}


DATA_AGGREGATION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'default_aggregation': {
        'value': 'median',
        'type': 'string',
        'options': ['mean', 'median', 'p90', 'p99'],
        'description': 'Default aggregation method for metrics collection (median is most robust to outliers).'
    }
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
        'data_aggregation': DATA_AGGREGATION_DEFAULTS
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
        category: Category name ('ml_analysis', 'transaction_status', 'data_aggregation')

    Returns:
        Dictionary of settings for the category
    """
    all_defaults = get_all_defaults()
    return all_defaults.get(category, {})
