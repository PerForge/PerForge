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

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import List, Dict, Any, Literal, Tuple, Optional
import logging
from app.backend.errors import ErrorMessages
from collections import defaultdict
from app.backend.data_provider.data_analysis.detectors import (
    IsolationForestDetector,
    ZScoreDetector,
    MetricStabilityDetector,
    RampUpPeriodAnalyzer
)
from app.backend.data_provider.data_analysis.constants import OVERALL_METRIC_KEYS, OVERALL_METRIC_DISPLAY, COL_TXN_RPS, COL_OVERALL_RPS, COL_ERR_RATE
from app.backend.components.settings.settings_defaults import get_defaults_for_category
from app.backend.components.settings.settings_service import SettingsService

class AnomalyDetectionEngine:
    """
    A class for detecting anomalies in time-series data.

    This engine supports multiple detection methods and can process various metrics
    to identify anomalous behavior in the data.
    """
    def __init__(self, params: Dict[str, Any] = None, project_id: Optional[int] = None):
        """
        Initialize the Anomaly Detection Engine

        Args:
            params: Configuration parameters for the engine (optional, overrides project settings)
            project_id: Project ID for loading project-specific settings (optional)
        """
        self.output = []
        # Internal store for overall metric anomalies (per window), to be
        # enriched with per-transaction attribution before final output is built.
        self.overall_anomalies: List[Dict[str, Any]] = []

        # Load default parameters from centralized settings_defaults.py
        # This is the single source of truth for default values
        ml_defaults_metadata = get_defaults_for_category('ml_analysis')
        default_params = {key: config['value'] for key, config in ml_defaults_metadata.items()}

        # If project_id is provided, load project-specific settings from database
        if project_id is not None:
            try:
                project_settings = SettingsService.get_project_settings(project_id, 'ml_analysis')
                # Merge project settings into defaults (project settings override defaults)
                default_params = {**default_params, **project_settings}
                logging.debug(f"Loaded ML analysis settings for project {project_id}")
            except Exception as e:
                logging.warning(f"Failed to load ML settings for project {project_id}, using defaults: {e}")

        # Ensure params is a dict
        if params is None:
            params = {}

        # Validate and update parameters (explicit params override everything)
        self._validate_and_set_params(params, default_params)

        self.detectors = [
            IsolationForestDetector(),
            ZScoreDetector(),
            MetricStabilityDetector(),
            RampUpPeriodAnalyzer(
                threshold_condition=lambda x: x < self.rolling_correlation_threshold,
                base_metric=self.ramp_up_base_metric
            )
        ]
        self.anomaly_detectors = self.detectors if self.detectors is not None else []

    def _validate_and_set_params(self, params: Dict[str, Any], default_params: Dict[str, Any]):
        if not isinstance(params, dict):
            logging.warning(ErrorMessages.ER00072.value)
            params = {}

        for key in params:
            if key not in default_params:
                logging.error(ErrorMessages.ER00073.value.format(key))

        final_params = {**default_params, **params}
        for key, value in final_params.items():
            setattr(self, key, value)

    def add_anomaly_detector(self, detector):
        self.anomaly_detectors.append(detector)

    def remove_anomaly_detector(self, detector):
        self.anomaly_detectors.remove(detector)

    def add_rolling_features(self, df, metric, is_mean=True, is_std=True):
        if is_mean:
            df[f'{metric}_rolling_mean'] = df[metric].rolling(window=self.rolling_window).mean()
        if is_std:
            df[f'{metric}_rolling_std'] = df[metric].rolling(window=self.rolling_window).std()
        return df

    def normalize_columns(self, df, columns):
        scaler = MinMaxScaler()
        df[columns] = scaler.fit_transform(df[columns])
        return df

    def normalize_metric(self, df, metric: str):
        """
        Normalize a specific metric column by setting min=0 and max=1

        Args:
            df: Input DataFrame or numpy array
            metric: Name of the column (for DataFrame) or None (for numpy array)

        Returns:
            DataFrame or numpy array with normalized values (min=0, max=1)
        """
        if isinstance(df, pd.DataFrame):
            if metric not in df.columns:
                logging.error(f"Column {metric} not found in DataFrame")
                return df

            if df.empty or df[metric].dropna().empty:
                logging.debug(f"No data available to normalize for metric {metric}")
                return df

            df = df.copy()
            max_val = df[metric].max()
            df[metric] = df[metric] / max_val if max_val != 0 else df[metric]
            return df

        elif isinstance(df, np.ndarray):
            if df.size == 0:
                logging.debug("No data available to normalize for numpy array metric input")
                return df
            max_val = np.max(df)
            return df / max_val if max_val != 0 else df
        else:
            logging.error(f"Input type {type(df)} not supported. Must be DataFrame or numpy array")
            return df

    def delete_columns(self, df, columns):
        df.drop(columns=columns, inplace=True)
        return df

    def add_output(self, status: Literal['passed', 'failed'], method: str, description: str, value: Any = None):
        """
        Add a new output entry to the anomaly detection results

        Args:
            status: Status of the anomaly (must be either 'passed' or 'failed')
            method: Name of the detection method
            description: Description of the anomaly or result
            value: Optional value associated with the result
        """
        self.output.append({
            'status': status,
            'method': method,
            'description': description,
            'value': value
        })
    def process_anomalies(self, merged_df):
        # Iterate over the columns to find metric and anomaly columns
        for col in merged_df.columns:
            if col.endswith('_anomaly'):
                # Identify the corresponding metric column
                metric_col = col.replace('_anomaly', '')
                if metric_col in merged_df.columns:
                    # Call the collect_anomalies function
                    self.collect_anomalies(merged_df, metric_col, col)

    def _has_overall_anomalies(self, fixed_load_period: pd.DataFrame) -> bool:
        """Return True if any overall anomaly windows have been recorded.

        The argument ``fixed_load_period`` is kept for compatibility but is no
        longer inspected. This helper now simply checks whether
        ``self.overall_anomalies`` contains any entries, which are populated by
        ``collect_anomalies`` via ``_record_overall_anomaly_window``.
        """
        try:
            anomalies = getattr(self, 'overall_anomalies', [])
            return bool(anomalies)
        except Exception:
            return False

    def _record_overall_anomaly_window(self, metric: str, start_time, end_time, baseline_value: float, summary: Dict[str, Any]) -> None:
        """Record an overall-metric anomaly window for later enrichment.

        This helper creates an internal anomaly entry capturing the
        window, direction, and significant value. It does not modify
        self.output; that will be built in a later step.
        """
        try:
            direction = summary.get('direction')
            significant_value = summary.get('significant_value', baseline_value)
        except Exception:
            direction = None
            significant_value = baseline_value
        try:
            anomaly = {
                'id': len(self.overall_anomalies),
                'metric': metric,
                'start_time': start_time,
                'end_time': end_time,
                'direction': direction,
                'significant_value': significant_value,
                'baseline': baseline_value,
                'summary': summary,
                'transactions': [],
            }
            self.overall_anomalies.append(anomaly)
        except Exception:
            # Fail silently; this helper must not break anomaly collection.
            pass

    def _summarize_anomaly_window(self, baseline_value: float, values: List[float]) -> Dict[str, Any]:
        """Summarize a single anomaly window.

        Given a baseline reference value and a list of observed values within the
        anomaly window, determine whether the anomaly is an increase or decrease,
        compute min/max/mean, and the absolute delta from baseline.
        """
        if values is None or len(values) == 0:
            return {
                'baseline': float(baseline_value) if baseline_value is not None else 0.0,
                'min': float(baseline_value) if baseline_value is not None else 0.0,
                'max': float(baseline_value) if baseline_value is not None else 0.0,
                'mean': float(baseline_value) if baseline_value is not None else 0.0,
                'direction': 'increase',
                'significant_value': float(baseline_value) if baseline_value is not None else 0.0,
                'delta_abs': 0.0,
            }

        # filter out NaNs
        arr = np.array(values, dtype=float)
        arr = arr[~np.isnan(arr)]
        if arr.size == 0:
            return {
                'baseline': float(baseline_value) if baseline_value is not None else 0.0,
                'min': float(baseline_value) if baseline_value is not None else 0.0,
                'max': float(baseline_value) if baseline_value is not None else 0.0,
                'mean': float(baseline_value) if baseline_value is not None else 0.0,
                'direction': 'increase',
                'significant_value': float(baseline_value) if baseline_value is not None else 0.0,
                'delta_abs': 0.0,
            }

        baseline = float(baseline_value) if baseline_value is not None else float(arr[0])
        v_min = float(np.min(arr))
        v_max = float(np.max(arr))
        v_mean = float(np.mean(arr))

        delta_up = v_max - baseline
        delta_down = baseline - v_min
        if delta_up >= delta_down:
            direction = 'increase'
            significant_value = v_max
            delta_abs = max(0.0, float(delta_up))
        else:
            direction = 'decrease'
            significant_value = v_min
            delta_abs = max(0.0, float(delta_down))

        return {
            'baseline': baseline,
            'min': v_min,
            'max': v_max,
            'mean': v_mean,
            'direction': direction,
            'significant_value': significant_value,
            'delta_abs': delta_abs,
        }

    def collect_anomalies(self, df, metric, anomaly_cl):
        """Collect anomaly windows for a metric.

        This new implementation:
        - Derives a boolean anomaly flag column from ``anomaly_cl``.
        - Uses ``_extract_anomaly_windows`` to find contiguous windows.
        - Records each window via ``_record_overall_anomaly_window``.

        It does *not* write anything to ``self.output``; later steps will
        be responsible for building user-facing output from the recorded
        windows.
        """
        try:
            df_idx = df.copy()
            if 'timestamp' in df_idx.columns and df_idx.index.name != 'timestamp':
                df_idx = df_idx.set_index('timestamp')
        except Exception:
            df_idx = df.copy()

        if anomaly_cl in df_idx.columns:
            flags = df_idx[anomaly_cl].apply(
                lambda v: isinstance(v, str)
                and 'Anomaly' in str(v)
                and 'potential saturation point' not in str(v)
            )
        else:
            flags = pd.Series(False, index=df_idx.index)

        df_idx[f'{metric}_anomaly_flag'] = flags.astype(bool)

        cols = [c for c in [metric, f'{metric}_anomaly_flag'] if c in df_idx.columns]
        if cols:
            df_for_windows = df_idx[cols]
        else:
            df_for_windows = df_idx[[f'{metric}_anomaly_flag']]

        windows = self._extract_anomaly_windows(df_for_windows, metric)

        for w in windows:
            try:
                start_raw = w.get('start')
                end_raw = w.get('end')
                start_time = pd.to_datetime(start_raw) if start_raw is not None else None
                end_time = pd.to_datetime(end_raw) if end_raw is not None else None
                baseline_value = w.get('baseline')
                summary = w
                self._record_overall_anomaly_window(metric, start_time, end_time, baseline_value, summary)
            except Exception:
                # Recording windows must not break overall processing.
                continue

    def update_anomaly_status(self, df, metric, anomaly_metric, method):
        anomaly_col = f'{metric}_anomaly'
        anomaly_method_col = anomaly_metric
        df = df.copy()

        if anomaly_col not in df.columns:
            df[anomaly_col] = ""

        def check_and_update(row):
            if row[anomaly_method_col] == -1:
                if 'Anomaly' in str(row[anomaly_col]):
                    if method not in str(row[anomaly_col]):
                        return f"{row[anomaly_col]}, {method}"
                    else:
                        return row[anomaly_col]
                else:
                    return f"Anomaly: {method}"
            else:
                if 'Anomaly' in str(row[anomaly_col]):
                    return row[anomaly_col]
                else:
                    return "Normal"

        df[anomaly_col] = df.apply(check_and_update, axis=1)
        return df

    def filter_contextual_anomalies(self, df: pd.DataFrame, metric: str, method_flag_col: str) -> pd.DataFrame:
        """
        Validate candidate anomalies against local neighborhood median.

        If abs(x_i - median(neighbors)) <= context_median_pct * |median(neighbors)|,
        then the point is reclassified as normal (1) in method_flag_col.

        Neighbors are up to `context_median_window` points before and after, excluding the point itself.

        Args:
            df: DataFrame with the metric and method_flag_col (-1 for anomaly, 1 for normal)
            metric: Metric column name
            method_flag_col: Per-method anomaly flag column

        Returns:
            Updated DataFrame with filtered method_flag_col
        """
        if not getattr(self, 'context_median_enabled', True):
            return df
        if metric not in df.columns or method_flag_col not in df.columns:
            return df
        df = df.copy()
        window = int(getattr(self, 'context_median_window', 20))
        pct = float(getattr(self, 'context_median_pct', 0.15))

        values = df[metric].to_numpy()
        n = len(df)

        # Only evaluate indices flagged as anomalies by the method
        flags = df[method_flag_col].to_numpy(copy=True)

        for i in range(n):
            if flags[i] != -1:
                continue

            start = max(0, i - window)
            end = min(n, i + window + 1)

            # neighbors excluding the current point
            prev_vals = values[start:i]
            next_vals = values[i + 1:end]

            if prev_vals.size == 0 and next_vals.size == 0:
                continue

            neighbors = np.concatenate([prev_vals, next_vals]) if prev_vals.size and next_vals.size else (
                prev_vals if prev_vals.size else next_vals
            )

            # Remove NaNs
            neighbors = neighbors[~np.isnan(neighbors)]
            if neighbors.size == 0:
                continue

            neighbor_median = float(np.median(neighbors))
            # Use current point magnitude as denominator to match "15% of metric"
            denom = max(abs(float(values[i])), 1e-12)
            diff = abs(float(values[i]) - neighbor_median)

            if diff <= pct * denom:
                # Reclassify as normal
                df.iloc[i, df.columns.get_loc(method_flag_col)] = 1

        return df

    def detect_anomalies(self, df, metric, period_type):
        for detector in self.anomaly_detectors:
            if detector.type == period_type:
                df = detector.detect(df, metric, self)
        return df

    def filter_ramp_up_and_down_periods(self, df, metric):
        df['is_ramp_up_down'] = df[metric].diff().fillna(0).apply(
            lambda x: 'Ramp-up' if x > 0 else ('Ramp-down' if x < 0 else 'Stable')
        )
        df.iloc[0, df.columns.get_loc('is_ramp_up_down')] = 'Ramp-up'
        fixed_load_period = df[df['is_ramp_up_down'] == 'Stable']
        fixed_load_period = self.delete_columns(df=fixed_load_period.copy(), columns=["is_ramp_up_down"])
        ramp_up_period = df[df['is_ramp_up_down'] == 'Ramp-up']
        ramp_up_period = self.delete_columns(df=ramp_up_period.copy(), columns=["is_ramp_up_down"])
        is_fixed_load = self.check_if_fixed_load(total_rows=len(df), fixed_load_rows=len(fixed_load_period))
        return fixed_load_period, ramp_up_period, is_fixed_load

    def check_if_fixed_load(self, total_rows, fixed_load_rows):
        fixed_load_percentage = (fixed_load_rows / total_rows) * 100
        return fixed_load_percentage >= self.fixed_load_percentage

    def prepare_final_metrics(self, merged_df: pd.DataFrame, standard_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare the final result dictionary from the merged DataFrame.
        """
        metrics = {}

        # Ensure chronological ordering before iterating; chart libraries expect
        # x-values to be sorted or they will draw backtracking lines.
        sorted_df = merged_df.sort_index()

        for col in sorted_df.columns:
            if '_anomaly' not in col:
                anomaly_col = col + '_anomaly'

                metrics[col] = {
                    'name': standard_metrics[col]['name'],
                    'data': []
                }

                for timestamp, row in sorted_df.iterrows():
                    anomaly_value = row[anomaly_col] if anomaly_col in row and pd.notna(row[anomaly_col]) else 'Normal'
                    value = row[col] if pd.notna(row[col]) else 0.0
                    metrics[col]['data'].append({
                        'timestamp': timestamp.isoformat(),
                        'value': value,
                        'anomaly': anomaly_value
                    })

        return metrics

    def _analyze_results(self, analysis_output: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the test results and return a dictionary of findings.
        """
        failed_checks = [x for x in analysis_output if x['status'] == 'failed']
        metric_anomaly_counts = defaultdict(int)
        trend_issues = []
        ramp_up_status = None
        saturation_point = None
        performance_status = not failed_checks

        for check in analysis_output:
            if check['method'] == 'rolling_correlation':
                if 'Tipping point was reached' in check.get('description', ''):
                    saturation_point = check.get('value')
                else:
                    ramp_up_status = check['status'] == 'passed'
            elif check['status'] == 'failed':
                if check['method'] == 'TrendAnalysis':
                    trend_issues.append(check['description'])
                elif 'An anomaly was detected in' in check['description']:
                    metric = check['description'].split('in ')[1].split(' from')[0]
                    metric_anomaly_counts[metric] += 1

        return {
            'failed_checks': failed_checks,
            'metric_anomaly_counts': metric_anomaly_counts,
            'trend_issues': trend_issues,
            'ramp_up_status': ramp_up_status,
            'saturation_point': saturation_point,
            'performance_status': performance_status
        }

    def create_text_summary(self, test_type: str, analysis_output: List[Dict[str, Any]]) -> str:
        """
        Create a plain-text summary of test analysis results.
        """
        results = self._analyze_results(analysis_output)
        metric_anomaly_counts = results['metric_anomaly_counts']
        trend_issues = results['trend_issues']
        ramp_up_status = results['ramp_up_status']
        saturation_point = results['saturation_point']
        failed_checks = results['failed_checks']

        text_parts = []
        text_parts.append(f"Test type: {test_type}")

        if test_type.lower() == "ramp up":
            if saturation_point:
                text_parts.append(f"- System saturation detected at: {saturation_point} requests per second")
        elif ramp_up_status is not None:
            status_text = 'successful' if ramp_up_status else 'issues detected'
            text_parts.append(f"- Ramp-up period: {status_text}")

        if trend_issues:
            text_parts.append("\nTrend Analysis Issues:")
            for issue in trend_issues:
                text_parts.append(f"  - {issue}")

        if metric_anomaly_counts:
            text_parts.append("\nAnomalies Detected:")
            for metric, count in metric_anomaly_counts.items():
                plural = 'anomaly' if count == 1 else 'anomalies'
                text_parts.append(f"  - {metric}: {count} {plural}")

        if not failed_checks:
            text_parts.append("\nNo issues were detected during the test execution.")

        return "\n".join(text_parts)

    def create_html_summary(self, test_type: str, analysis_output: List[Dict[str, Any]]) -> Tuple[str, bool]:
        """
        Create HTML summary of test analysis results.
        """
        results = self._analyze_results(analysis_output)
        metric_anomaly_counts = results['metric_anomaly_counts']
        trend_issues = results['trend_issues']
        ramp_up_status = results['ramp_up_status']
        saturation_point = results['saturation_point']
        failed_checks = results['failed_checks']
        performance_status = results['performance_status']

        html_parts = []
        html_parts.append(f"<p>Test type: <strong>{test_type}</strong></p>")

        if test_type.lower() == "ramp up":
            if saturation_point:
                html_parts.append(f"<p>🎯 System saturation detected at: <strong>{saturation_point}</strong> requests per second</p>")
        elif ramp_up_status is not None:
            status_icon = "✅" if ramp_up_status else "❌"
            html_parts.append(f"<p>{status_icon} Ramp-up period: {'successful' if ramp_up_status else 'issues detected'}</p>")

        if trend_issues:
            html_parts.extend([
                "<div class='trend-analysis'>",
                "<h4>📈 Trend Analysis Issues:</h4>",
                "<ul>",
                *[f"<li>{issue}</li>" for issue in trend_issues],
                "</ul>",
                "</div>"
            ])

        if metric_anomaly_counts:
            html_parts.extend([
                "<div class='anomalies'>",
                "<h4>⚠️ Anomalies Detected:</h4>",
                "<ul>",
                *[f"<li><strong>{metric}</strong>: {count} {'anomaly' if count == 1 else 'anomalies'}</li>"
                  for metric, count in metric_anomaly_counts.items()],
                "</ul>",
                "</div>"
            ])

        if not failed_checks:
            html_parts.append("<p>✅ No issues were detected during the test execution.</p>")

        return "\n".join(html_parts), performance_status

    def analyze_test_data(self, merged_df: pd.DataFrame, standard_metrics: Dict[str, Dict[str, Any]], data_provider=None, test_obj=None):
        """
        Analyze test data and prepare results.

        Args:
            merged_df: DataFrame containing all metrics
            standard_metrics: Dictionary of standard metrics configuration

        Returns:
            Tuple containing:
            - Processed test data
            - Analysis output
            - HTML summary
            - Performance status
        """
        # Analyze data periods
        fixed_load_period, ramp_up_period, is_fixed_load = self.filter_ramp_up_and_down_periods(df=merged_df.copy(), metric="overalUsers")

        # Only analyze ramp-up throughput if the metric exists
        if 'overalThroughput' in ramp_up_period.columns:
            ramp_up_period = self.detect_anomalies(ramp_up_period, metric="overalThroughput", period_type='ramp_up')
        else:
            logging.warning("Skipping ramp-up anomaly detection: 'overalThroughput' metric not available")

        if is_fixed_load:
            for metric in standard_metrics:
                if standard_metrics[metric]['analysis']:
                    # Only detect anomalies if the metric exists in the DataFrame
                    if metric in fixed_load_period.columns:
                        fixed_load_period = self.detect_anomalies(
                            fixed_load_period,
                            metric=metric,
                            period_type='fixed_load'
                        )
                    else:
                        logging.warning(f"Skipping anomaly detection for '{metric}': metric not available in data")
            try:
                self.fixed_load_period_annotated = fixed_load_period.copy()
            except Exception:
                self.fixed_load_period_annotated = fixed_load_period

        # Ensure columns match between periods
        missing_columns = set(fixed_load_period.columns) - set(ramp_up_period.columns)
        for col in missing_columns:
            ramp_up_period[col] = 'Normal'

        # Merge periods and prepare results
        merged_df = pd.concat([ramp_up_period, fixed_load_period], axis=0)
        metrics = self.prepare_final_metrics(merged_df, standard_metrics)

        has_any_overall_anomaly = False
        if is_fixed_load:
            # For gating and attribution we only consider anomalies detected
            # in the fixed-load period, not during ramp-up.
            self.process_anomalies(fixed_load_period)
            has_any_overall_anomaly = self._has_overall_anomalies(fixed_load_period)

        self._run_per_transaction_pipeline(
            is_fixed_load=is_fixed_load,
            has_any_overall_anomaly=has_any_overall_anomaly,
            data_provider=data_provider,
            test_obj=test_obj
        )

        # Build user-facing overall anomaly entries (including any
        # per-transaction contributions) from the internal windows.
        self._build_output_from_overall_anomalies()

        return metrics, is_fixed_load, self.output

    def _run_per_transaction_pipeline(self, *, is_fixed_load: bool, has_any_overall_anomaly: bool, data_provider=None, test_obj=None) -> None:
        try:
            # Respect project setting for per-transaction analysis. If disabled,
            # skip the entire per-transaction pipeline.
            if not getattr(self, 'per_txn_analysis_enabled', True):
                logging.debug("Per-transaction analysis disabled by settings; skipping per-transaction pipeline.")
                return

            if is_fixed_load and has_any_overall_anomaly and data_provider is not None and test_obj is not None:
                try:
                    data_provider.build_per_transaction_long_frame(test_obj=test_obj, sampling_interval_sec=30)
                except Exception as e:
                    logging.warning(f"Failed to build per-transaction long frame: {e}")

                try:
                    if getattr(self, 'anomaly_detectors', None) is not None and getattr(test_obj, 'per_txn_df_long', None) is not None:
                        sel = self.select_transactions_for_analysis(
                            test_obj.per_txn_df_long,
                            metrics=None,
                            txn_col='transaction',
                            rps_col='rps',
                            overall_rps_col='overall_rps'
                        )
                        setattr(test_obj, 'per_txn_selection', sel)
                        setattr(test_obj, 'per_txn_df_long_selected', sel.get('df_long_selected'))
                except Exception as e:
                    logging.warning(f"Per-transaction selection failed: {e}")

                try:
                    if getattr(test_obj, 'per_txn_df_long_selected', None) is not None:
                        det = self.detect_and_window_per_transaction(
                            test_obj.per_txn_df_long_selected,
                            metrics=None,
                            txn_col='transaction'
                        )
                        setattr(test_obj, 'per_txn_windows', det.get('by_txn'))
                        setattr(test_obj, 'per_txn_df_long_annotated', det.get('annotated'))
                except Exception as e:
                    logging.warning(f"Per-transaction detection/windowing failed: {e}")

                try:
                    if getattr(test_obj, 'per_txn_windows', None) is not None:
                        merged_txn = self.merge_and_score_per_transaction(
                            {'by_txn': getattr(test_obj, 'per_txn_windows'), 'annotated': getattr(test_obj, 'per_txn_df_long_annotated')},
                            txn_col='transaction'
                        )
                        setattr(test_obj, 'per_txn_merged_windows', merged_txn.get('by_txn'))
                        setattr(test_obj, 'per_txn_events_raw', merged_txn.get('events'))
                        try:
                            dataset = self.build_transaction_events_dataset(
                                dataset_id='ev_txn_anomalies',
                                name='Transaction anomalies',
                                events=merged_txn.get('events')
                            )
                            setattr(test_obj, 'per_txn_events_dataset', dataset)
                        except Exception as ie:
                            logging.warning(f"Building per-transaction events dataset failed: {ie}")
                except Exception as e:
                    logging.warning(f"Per-transaction merge/score failed: {e}")

                try:
                    if getattr(test_obj, 'per_txn_merged_windows', None) is not None:
                        per_txn_bundle = {
                            'by_txn': getattr(test_obj, 'per_txn_merged_windows'),
                            'annotated': getattr(test_obj, 'per_txn_df_long_annotated')
                        }
                        attribution = self.attribute_overall_to_transactions(
                            overall_metrics=OVERALL_METRIC_KEYS,
                            per_txn=per_txn_bundle,
                            txn_col='transaction',
                            top_n=None
                        )
                        setattr(test_obj, 'overall_txn_attribution', attribution)
                except Exception as e:
                    logging.warning(f"Overall→transaction attribution failed: {e}")
        except Exception as e:
            logging.warning(f"Per-transaction pipeline failed: {e}")

    def select_transactions_for_analysis(self, df_long: pd.DataFrame, metrics: List[str] = None, txn_col: str = 'transaction', rps_col: str = 'rps', overall_rps_col: str = 'overall_rps') -> Dict[str, Any]:
        if df_long is None or df_long.empty:
            result = {
                'selected_transactions': [],
                'selection': {
                    'cumulative_share': 0.0,
                    'total_txns': 0,
                    'after_points_txns': 0,
                    'selected_count': 0
                },
                'df_long_selected': df_long
            }
            self.transaction_selection = result
            return result
        txns = df_long[txn_col].dropna().unique().tolist()
        total_txns = len(txns)
        if total_txns == 0:
            result = {
                'selected_transactions': [],
                'selection': {
                    'cumulative_share': 0.0,
                    'total_txns': 0,
                    'after_points_txns': 0,
                    'selected_count': 0
                },
                'df_long_selected': df_long.head(0).copy()
            }
            self.transaction_selection = result
            return result
        g = df_long.groupby(txn_col, dropna=True)
        recs = []
        for txn, sub in g:
            points = len(sub)
            mean_rps = pd.to_numeric(sub.get(rps_col), errors='coerce').mean()
            mean_overall = pd.to_numeric(sub.get(overall_rps_col), errors='coerce').mean()
            denom = float(mean_overall) if pd.notna(mean_overall) and float(mean_overall) > 0 else 0.0
            share = float(mean_rps) / denom if denom > 0 else 0.0
            recs.append((txn, points, share))
        cand = pd.DataFrame(recs, columns=['transaction', 'points', 'share'])
        min_points = int(getattr(self, 'per_txn_min_points', 6))
        after_points = cand[cand['points'] >= min_points]
        if after_points.empty:
            top1 = cand.sort_values('share', ascending=False).head(1)
            selected = top1['transaction'].tolist()
            cumulative_share = float(top1['share'].sum()) if not top1.empty else 0.0
        else:
            after_points = after_points.sort_values('share', ascending=False)
            coverage = float(getattr(self, 'per_txn_coverage', 0.8))
            max_k = int(getattr(self, 'per_txn_max_k', 50))

            # If we have <= max_k transactions, select all of them (no 80% cutoff)
            # The 80% coverage rule only applies when we have more than max_k transactions
            if len(after_points) <= max_k:
                selected_df = after_points
            else:
                # We have more than max_k transactions - apply 80% coverage rule
                cum = after_points['share'].cumsum()
                if (cum >= coverage).any():
                    upto = after_points.index.get_loc((cum >= coverage).idxmax()) + 1
                    selected_df = after_points.iloc[:upto]
                else:
                    selected_df = after_points
                # Cap at max_k
                if len(selected_df) > max_k:
                    selected_df = selected_df.iloc[:max_k]

            selected = selected_df['transaction'].tolist()
            cumulative_share = float(selected_df['share'].sum()) if not selected_df.empty else 0.0
        result = {
            'selected_transactions': selected,
            'selection': {
                'cumulative_share': cumulative_share,
                'total_txns': total_txns,
                'after_points_txns': int((cand['points'] >= min_points).sum()),
                'selected_count': len(selected)
            }
        }
        df_sel = df_long[df_long[txn_col].isin(selected)].copy() if selected else df_long.head(0).copy()
        result['df_long_selected'] = df_sel
        self.transaction_selection = result
        return result

    def _detect_group(self, g: pd.DataFrame, metric: str) -> pd.DataFrame:
        if metric in g.columns:
            cols = ["timestamp", metric]
            for extra in (COL_TXN_RPS, COL_OVERALL_RPS, COL_ERR_RATE):
                if extra in g.columns and extra not in cols:
                    cols.append(extra)
            df = g[cols].copy()
        else:
            df = g[["timestamp"]].copy()
        if metric not in g.columns or df.empty:
            df.set_index('timestamp', inplace=True)
            df[f'{metric}_anomaly_flag'] = False
            return df
        df.set_index('timestamp', inplace=True)
        # For per-transaction analysis, run anomaly detectors only (exclude trend/stability)
        original_detectors = self.anomaly_detectors
        try:
            self.anomaly_detectors = [d for d in original_detectors if d.__class__.__name__ != 'MetricStabilityDetector']
            df = self.detect_anomalies(df, metric=metric, period_type='fixed_load')
        finally:
            self.anomaly_detectors = original_detectors
        col = f'{metric}_anomaly'
        if col in df.columns:
            flags = df[col].apply(lambda v: isinstance(v, str) and 'Anomaly' in v and 'potential saturation point' not in str(v))
        else:
            flags = pd.Series(False, index=df.index)
        df[f'{metric}_anomaly_flag'] = flags.astype(bool)
        return df

    def _extract_anomaly_windows(self, df_idx: pd.DataFrame, metric: str) -> List[Dict[str, Any]]:
        if df_idx.empty or f'{metric}_anomaly_flag' not in df_idx.columns:
            return []
        flags = df_idx[f'{metric}_anomaly_flag'].to_numpy()
        ts = df_idx.index.to_numpy()
        n = len(flags)
        if n == 0:
            return []
        max_gap = int(getattr(self, 'merge_gap_samples', 1))
        windows = []
        in_win = False
        start_i = None
        gap = 0
        last_true_i = None
        for i in range(n):
            if flags[i]:
                if not in_win:
                    in_win = True
                    start_i = i
                    gap = 0
                last_true_i = i
                gap = 0
            else:
                if in_win:
                    gap += 1
                    if gap > max_gap:
                        end_i = last_true_i if last_true_i is not None else i - 1
                        if start_i is not None and end_i is not None and end_i >= start_i:
                            windows.append((start_i, end_i))
                        in_win = False
                        start_i = None
                        gap = 0
        if in_win and start_i is not None:
            end_i = last_true_i if last_true_i is not None else n - 1
            if end_i >= start_i:
                windows.append((start_i, end_i))

        # Prepare metric series if available for window summarization
        vals = None
        if metric in df_idx.columns:
            try:
                vals = pd.to_numeric(df_idx[metric], errors='coerce')
            except Exception:
                vals = None

        result = []
        for s_i, e_i in windows:
            ts_start = ts[s_i]
            ts_end = ts[e_i]
            try:
                duration_sec = float((pd.Timestamp(ts_end) - pd.Timestamp(ts_start)).total_seconds())
            except Exception:
                duration_sec = float(e_i - s_i)

            window_payload = {
                'start': pd.Timestamp(ts_start).isoformat() if hasattr(pd.Timestamp(ts_start), 'isoformat') else str(ts_start),
                'end': pd.Timestamp(ts_end).isoformat() if hasattr(pd.Timestamp(ts_end), 'isoformat') else str(ts_end),
                'durationSec': duration_sec,
                'points': int(e_i - s_i + 1),
                'metric': metric
            }

            # Attach direction / min / max / mean / delta_abs when we have metric values
            if vals is not None:
                try:
                    # Use a simple pre-window baseline from previous points
                    k = int(getattr(self, 'baseline_window', 5))
                except Exception:
                    k = 5
                pre_start = max(0, s_i - k)
                pre_vals = vals.iloc[pre_start:s_i]
                if pre_vals.notna().any():
                    baseline_value = float(pre_vals.median())
                else:
                    cur_val = vals.iloc[s_i] if s_i < len(vals) else np.nan
                    baseline_value = float(cur_val) if not np.isnan(cur_val) else None
                win_vals = vals.iloc[s_i:e_i + 1]
                summary = self._summarize_anomaly_window(baseline_value, win_vals.tolist())
                window_payload.update(summary)

            result.append(window_payload)
        return result

    def detect_and_window_per_transaction(self, df_long_selected: pd.DataFrame, metrics: List[str] = None, txn_col: str = 'transaction') -> Dict[str, Any]:
        if df_long_selected is None or df_long_selected.empty:
            self.transaction_windows = {'by_txn': {}, 'annotated': df_long_selected}
            return self.transaction_windows
        df = df_long_selected.copy()

        # If no explicit metrics list is provided, fall back to project settings
        # (per_txn_metrics). If settings are missing or invalid, use the
        # historical default metric set.
        if metrics is None:
            configured_metrics = getattr(self, 'per_txn_metrics', None)
            if isinstance(configured_metrics, (list, tuple)):
                try:
                    metrics = [str(m) for m in configured_metrics]
                except Exception:
                    metrics = ['rt_ms_median', 'rt_ms_avg', 'rt_ms_p90', 'error_rate', 'rps']
            else:
                metrics = ['rt_ms_median', 'rt_ms_avg', 'rt_ms_p90', 'error_rate', 'rps']

        m_present = [m for m in metrics if m in df.columns]
        by_txn = {}
        annotated_parts = []
        for txn, g in df.groupby(txn_col, dropna=True):
            g = g.sort_values('timestamp').copy()
            g_idx = g.set_index('timestamp')
            windows_by_metric = {}
            for metric in m_present:
                det_df = self._detect_group(g, metric)
                # align detected flags back to group timestamps
                flags = det_df.get(f'{metric}_anomaly_flag', pd.Series(False, index=det_df.index))
                # merge flags into g_idx
                aligned_flags = flags.reindex(g_idx.index, method=None, fill_value=False)
                aligned_flags = aligned_flags.astype(bool)
                g_idx[f'{metric}_anomaly_flag'] = aligned_flags
                windows = self._extract_anomaly_windows(g_idx[[c for c in [metric, f'{metric}_anomaly_flag'] if c in g_idx.columns]], metric)
                if windows:
                    windows_by_metric[metric] = windows
            by_txn[txn] = {'windows_by_metric': windows_by_metric}
            annotated_parts.append(g_idx.reset_index())
        annotated = pd.concat(annotated_parts, axis=0, ignore_index=True).sort_values(['timestamp', txn_col])
        self.transaction_windows = {'by_txn': by_txn, 'annotated': annotated}
        return self.transaction_windows

    def _merge_windows_across_metrics(self, windows_by_metric: Dict[str, List[Dict[str, Any]]], sample_seconds: float, merge_gap_samples: int) -> List[Dict[str, Any]]:
        # Flatten windows across metrics
        all_wins = []
        for metric, wins in windows_by_metric.items():
            for w in wins:
                try:
                    s = pd.to_datetime(w['start'])
                    e = pd.to_datetime(w['end'])
                except Exception:
                    s = pd.Timestamp(w['start'])
                    e = pd.Timestamp(w['end'])
                all_wins.append({
                    'start': s,
                    'end': e,
                    'metric': metric,
                    'direction': w.get('direction')
                })
        if not all_wins:
            return []
        all_wins.sort(key=lambda x: x['start'])
        tol = float(max(0, merge_gap_samples)) * float(sample_seconds)
        merged = []
        # maintain current cluster
        cur = None
        for w in all_wins:
            if cur is None:
                cur = {
                    'start': w['start'],
                    'end': w['end'],
                    'metrics': {w['metric']: {'count': 1, 'direction': w.get('direction')}}
                }
                continue
            gap_sec = (w['start'] - cur['end']).total_seconds()
            if gap_sec <= tol and (w['start'] <= cur['end'] or gap_sec <= tol):
                # extend cluster
                if w['end'] > cur['end']:
                    cur['end'] = w['end']
                entry = cur['metrics'].setdefault(w['metric'], {'count': 0, 'direction': None})
                entry['count'] += 1
                if w.get('direction') is not None:
                    entry['direction'] = w.get('direction')
            else:
                merged.append(cur)
                cur = {
                    'start': w['start'],
                    'end': w['end'],
                    'metrics': {w['metric']: {'count': 1, 'direction': w.get('direction')}}
                }
        if cur is not None:
            merged.append(cur)
        return merged

    def _severity_label(self, score: float) -> str:
        s = float(max(0.0, min(1.0, score)))
        if s >= getattr(self, 'severity_critical', 0.60):
            return 'critical'
        if s >= getattr(self, 'severity_high', 0.40):
            return 'high'
        if s >= getattr(self, 'severity_medium', 0.25):
            return 'medium'
        if s >= getattr(self, 'severity_low', 0.10):
            return 'low'
        return 'none'

    def merge_and_score_per_transaction(self, transaction_windows: Dict[str, Any], txn_col: str = 'transaction') -> Dict[str, Any]:
        if not transaction_windows or 'by_txn' not in transaction_windows or 'annotated' not in transaction_windows:
            self.transaction_merged = {}
            self.transaction_events = []
            return {'by_txn': {}, 'events': []}
        annotated = transaction_windows['annotated']
        by_txn = transaction_windows['by_txn']
        merged_by_txn: Dict[str, Any] = {}
        events: List[Dict[str, Any]] = []
        # per transaction processing
        for txn, data in by_txn.items():
            g = annotated[annotated[txn_col] == txn].copy()
            g = g.sort_values('timestamp')
            g_idx = g.set_index('timestamp')
            # derive sample seconds from index
            try:
                diffs = g_idx.index.to_series().diff().dropna().dt.total_seconds()
                sample_seconds = float(diffs.median()) if len(diffs) else 5.0
            except Exception:
                sample_seconds = 5.0
            mg = int(getattr(self, 'merge_gap_samples', 1))
            merged_windows = self._merge_windows_across_metrics(data.get('windows_by_metric', {}), sample_seconds, mg)
            merged_by_txn[txn] = merged_windows
            # score each merged window
            for w in merged_windows:
                w_start = w['start']
                w_end = w['end']
                # compute weight within window
                try:
                    slice_df = g_idx[(g_idx.index >= w_start) & (g_idx.index <= w_end)]
                except Exception:
                    slice_df = g_idx
                mean_rps = float(pd.to_numeric(slice_df.get('rps'), errors='coerce').mean()) if 'rps' in slice_df.columns else 0.0
                mean_overall = float(pd.to_numeric(slice_df.get('overall_rps'), errors='coerce').mean()) if 'overall_rps' in slice_df.columns else 0.0
                weight = (mean_rps / mean_overall) if (mean_overall and mean_overall > 0) else 0.0
                # aggregate metric contributions for this window (names only)
                metrics_list = []
                for m_name in w.get('metrics', {}).keys():
                    metrics_list.append({'name': m_name})

                # choose window-level direction from merged metrics (propagated from _summarize_anomaly_window)
                direction = None
                for m_name, meta in w.get('metrics', {}).items():
                    d = None
                    if isinstance(meta, dict):
                        d = meta.get('direction')
                    if d is not None:
                        direction = d
                        break

                # impact: depend only on transaction load share
                duration_sec = max(0.0, float((w_end - w_start).total_seconds()))
                impact = float(weight)
                events.append({
                    'transaction': txn,
                    'window': {'start': w_start.isoformat(), 'end': w_end.isoformat(), 'durationSec': duration_sec},
                    'metrics': metrics_list,
                    'volume': {'mean_rps': mean_rps, 'share': weight},
                    'direction': direction,
                    'impact': impact
                })
        # sort events by impact desc
        events.sort(key=lambda e: e.get('impact', 0.0), reverse=True)
        self.transaction_merged = merged_by_txn
        self.transaction_events = events
        return {'by_txn': merged_by_txn, 'events': events}

    def _extract_windows_from_anomaly_col(self, df_idx: pd.DataFrame, metric: str) -> List[Dict[str, Any]]:
        col = f"{metric}_anomaly"
        if df_idx is None or df_idx.empty or col not in df_idx.columns:
            return []
        flags = df_idx[col].apply(lambda v: isinstance(v, str) and 'Anomaly' in v and 'potential saturation point' not in str(v)).to_numpy()
        ts = df_idx.index.to_numpy()
        n = len(flags)
        if n == 0:
            return []
        max_gap = int(getattr(self, 'merge_gap_samples', 1))
        windows = []
        in_win = False
        start_i = None
        gap = 0
        last_true_i = None
        for i in range(n):
            if flags[i]:
                if not in_win:
                    in_win = True
                    start_i = i
                    gap = 0
                last_true_i = i
                gap = 0
            else:
                if in_win:
                    gap += 1
                    if gap > max_gap:
                        end_i = last_true_i if last_true_i is not None else i - 1
                        if start_i is not None and end_i is not None and end_i >= start_i:
                            windows.append((start_i, end_i))
                        in_win = False
                        start_i = None
                        gap = 0
        if in_win and start_i is not None:
            end_i = last_true_i if last_true_i is not None else n - 1
            if end_i >= start_i:
                windows.append((start_i, end_i))
        result: List[Dict[str, Any]] = []
        for s_i, e_i in windows:
            ts_start = ts[s_i]
            ts_end = ts[e_i]
            try:
                duration_sec = float((pd.Timestamp(ts_end) - pd.Timestamp(ts_start)).total_seconds())
            except Exception:
                duration_sec = float(e_i - s_i)
            result.append({
                'metric': metric,
                'start': pd.Timestamp(ts_start),
                'end': pd.Timestamp(ts_end),
                'durationSec': duration_sec
            })
        return result

    def attribute_overall_to_transactions(self, overall_metrics: List[str], per_txn: Dict[str, Any], txn_col: str = 'transaction', top_n: Optional[int] = None) -> Dict[str, Any]:
        # If there is no per-transaction data or no overall anomalies, nothing to do.
        overall_list = getattr(self, 'overall_anomalies', [])
        if not per_txn or not overall_list:
            self.overall_txn_attribution = {'by_metric': {}}
            return self.overall_txn_attribution

        merged_by_txn = per_txn.get('by_txn', {}) if isinstance(per_txn, dict) else {}
        annotated_txn = per_txn.get('annotated') if isinstance(per_txn, dict) else None
        result_by_metric: Dict[str, Any] = {}

        # Initialise per-metric containers
        for m in overall_metrics:
            result_by_metric[m] = []

        for oa in overall_list:
            m = oa.get('metric')
            if m not in overall_metrics:
                continue
            o_start = oa.get('start_time')
            o_end = oa.get('end_time')
            if o_start is None or o_end is None:
                continue
            try:
                o_start_ts = pd.to_datetime(o_start)
                o_end_ts = pd.to_datetime(o_end)
            except Exception:
                continue

            # Prepare container for this anomaly's transaction contributions
            if 'transactions' not in oa or oa['transactions'] is None:
                oa['transactions'] = []

            for txn, clusters in merged_by_txn.items():
                if not clusters:
                    continue
                best_overlap = 0.0
                best_metrics = None
                best_window = None
                for c in clusters:
                    c_start = c.get('start')
                    c_end = c.get('end')
                    if c_start is None or c_end is None:
                        continue
                    try:
                        c_start_ts = pd.to_datetime(c_start)
                        c_end_ts = pd.to_datetime(c_end)
                    except Exception:
                        continue
                    # overlap between overall anomaly window and txn cluster
                    s = max(o_start_ts, c_start_ts)
                    e = min(o_end_ts, c_end_ts)
                    overlap = (e - s).total_seconds() if e > s else 0.0
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_metrics = c.get('metrics', {})
                        best_window = (s, e)
                if best_overlap <= 0.0 or best_window is None:
                    continue

                # Compute transaction share within the overlapping window
                share = 0.0
                if annotated_txn is not None and not annotated_txn.empty:
                    g = annotated_txn[annotated_txn[txn_col] == txn].copy()
                    if not g.empty:
                        g_idx = g.set_index('timestamp')
                        try:
                            slice_df = g_idx[(g_idx.index >= best_window[0]) & (g_idx.index <= best_window[1])]
                        except Exception:
                            slice_df = g_idx
                        mean_rps = float(pd.to_numeric(slice_df.get('rps'), errors='coerce').mean()) if 'rps' in slice_df.columns else 0.0
                        mean_overall = float(pd.to_numeric(slice_df.get('overall_rps'), errors='coerce').mean()) if 'overall_rps' in slice_df.columns else 0.0
                        if mean_overall and mean_overall > 0:
                            share = mean_rps / mean_overall

                # Choose anomaly direction from the best_metrics (if any)
                direction = None
                if best_metrics:
                    for m_name, meta in best_metrics.items():
                        d = None
                        if isinstance(meta, dict):
                            d = meta.get('direction')
                        if d is not None:
                            direction = d
                            break

                # For throughput metrics (RPS), align per-transaction direction with overall direction
                # to avoid logical contradictions (e.g., overall "decrease" with per-txn "increase")
                overall_direction = oa.get('direction')
                if m in ['overalThroughput', 'rps'] and overall_direction and direction:
                    if overall_direction != direction:
                        # Per-transaction direction contradicts overall - align it
                        direction = overall_direction

                duration_sec = best_overlap
                impact = float(share)
                contrib = {
                    'overall_metric': m,
                    'overall_window': {
                        'start': o_start_ts.isoformat(),
                        'end': o_end_ts.isoformat()
                    },
                    'transaction': txn,
                    'overlapWindow': {
                        'start': best_window[0].isoformat(),
                        'end': best_window[1].isoformat(),
                        'durationSec': duration_sec
                    },
                    'direction': direction,
                    'share': share,
                    'impact': impact
                }

                # Attach to per-metric summary and to the anomaly itself
                result_by_metric[m].append(contrib)
                oa['transactions'].append({
                    'transaction': txn,
                    'direction': direction,
                    'share': share,
                    'impact': impact,
                    'overlapWindow': contrib['overlapWindow'],
                })

        # Rank and optionally truncate per metric
        for m, contribs in result_by_metric.items():
            contribs.sort(key=lambda x: x.get('impact', 0.0), reverse=True)
            if top_n and top_n > 0:
                result_by_metric[m] = contribs[:top_n]

        self.overall_txn_attribution = {'by_metric': result_by_metric}
        return self.overall_txn_attribution

    def _build_output_from_overall_anomalies(self, top_txn: int = 5) -> None:
        """Append overall anomaly entries to ``self.output`` from ``self.overall_anomalies``.

        The base description follows the legacy pattern used in the old
        ``collect_anomalies`` implementation. If per-transaction contributions
        were attached via ``attribute_overall_to_transactions``, an additional
        sentence is appended listing the top contributing transactions.
        """

        def _format_time_range(start, end):
            try:
                start_ts = pd.to_datetime(start)
                end_ts = pd.to_datetime(end)
            except Exception:
                return f"{start}–{end}"

            # Check if start and end are the same
            if start_ts == end_ts:
                return f"at {start_ts.strftime('%I:%M:%S %p')}"

            start_date = start_ts.strftime('%Y-%m-%d')
            end_date = end_ts.strftime('%Y-%m-%d')
            if start_date == end_date:
                return f"{start_ts.strftime('%I:%M:%S %p')}–{end_ts.strftime('%I:%M:%S %p')}"
            return f"{start_ts.strftime('%Y-%m-%d %I:%M:%S %p')}–{end_ts.strftime('%Y-%m-%d %I:%M:%S %p')}"

        overall_list = getattr(self, 'overall_anomalies', [])
        if not overall_list:
            return

        for oa in overall_list:
            metric = oa.get('metric')
            start_time = oa.get('start_time')
            end_time = oa.get('end_time')
            direction = oa.get('direction') or 'increase'
            significant_value = oa.get('significant_value')

            if start_time is None or end_time is None or metric is None:
                continue

            try:
                value_str = f"{float(significant_value):.2f}" if significant_value is not None else "N/A"
            except Exception:
                value_str = str(significant_value)

            time_range_str = _format_time_range(start_time, end_time)
            metric_label = OVERALL_METRIC_DISPLAY.get(metric, metric)

            # Adjust description format based on whether time_range_str starts with "at"
            if time_range_str.startswith("at "):
                # Single timestamp: "Median response time at 23:32:30 decreased to 20.00."
                base_desc = (
                    f"{metric_label} {time_range_str} "
                    f"{'increased' if direction == 'increase' else 'decreased'} "
                    f"to {value_str}."
                )
            else:
                # Time range: "Median response time 23:32:30–23:32:35: decreased to 20.00."
                base_desc = (
                    f"{metric_label} {time_range_str}: "
                    f"{'increased' if direction == 'increase' else 'decreased'} "
                    f"to {value_str}."
                )

            desc = base_desc
            txns = oa.get('transactions') or []
            if txns:
                # Sort by impact (load share) and take top N
                txns_sorted = sorted(txns, key=lambda t: t.get('impact', 0.0), reverse=True)
                if top_txn and top_txn > 0:
                    txns_sorted = txns_sorted[:top_txn]
                parts = []
                for t in txns_sorted:
                    name = t.get('transaction') or 'unknown'
                    direction_txn = t.get('direction') or 'unknown'
                    parts.append(f"{name} ({direction_txn})")
                if parts:
                    desc = f"{base_desc} Likely contributing transactions: " + ", ".join(parts) + "."

            # For now, method is generic; detectors contributing are encoded in
            # the anomaly columns that produced the windows.
            self.output.append({
                'status': 'failed',
                'method': 'AnomalyDetection',
                'description': desc,
                'value': significant_value
            })

    def build_transaction_events_dataset(self, dataset_id: str = 'ev_txn_anomalies', name: str = 'Transaction anomalies', events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        ev = events if events is not None else getattr(self, 'transaction_events', None)
        if not ev:
            dataset = {'id': dataset_id, 'type': 'events', 'name': name, 'events': []}
            self.transaction_events_dataset = dataset
            return dataset
        payload = []
        for e in ev:
            txn = e.get('transaction')
            window = e.get('window') or {}
            t = window.get('start')
            volume = e.get('volume') or {}
            share = volume.get('share', 0.0)
            metrics = e.get('metrics') or []
            payload.append({
                't': t,
                'type': 'transaction_anomaly',
                'meta': {
                    'transaction': txn,
                    'window': window,
                    'metrics': metrics,
                    'volume': volume,
                    'impact': e.get('impact'),
                }
            })
        dataset = {'id': dataset_id, 'type': 'events', 'name': name, 'events': payload}
        self.transaction_events_dataset = dataset
        return dataset
