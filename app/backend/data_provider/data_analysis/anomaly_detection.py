import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import List, Dict, Any, Literal, Tuple
import logging
from app.backend.errors import ErrorMessages
from collections import defaultdict
from app.backend.data_provider.data_analysis.detectors import (
    IsolationForestDetector,
    ZScoreDetector,
    MetricStabilityDetector,
    RampUpPeriodAnalyzer
)

class AnomalyDetectionEngine:
    """
    A class for detecting anomalies in time-series data.

    This engine supports multiple detection methods and can process various metrics
    to identify anomalous behavior in the data.
    """
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize the Anomaly Detection Engine

        Args:
            params: Configuration parameters for the engine
            detectors: List of detector instances to use
        """
        self.output = []
        # Define default parameters
        default_params = {
            'contamination': 0.001,
            'isf_threshold': 0.1,
            'isf_feature_metric': 'overalThroughput',
            'z_score_threshold': 3,
            'rolling_window': 5,
            'rolling_correlation_threshold': 0.4,
            'fixed_load_percentage': 60,
            'slope_threshold': 1.000,
            'p_value_threshold': 0.05,
            'numpy_var_threshold': 0.003,
            'cv_threshold': 0.07
        }

        # Validate and update parameters
        self._validate_and_set_params(params, default_params)

        self.detectors = [
            IsolationForestDetector(),
            ZScoreDetector(),
            MetricStabilityDetector(),
            RampUpPeriodAnalyzer(
                threshold_condition=lambda x: x < self.rolling_correlation_threshold,
                base_metric="overalUsers"
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

            df = df.copy()
            max_val = df[metric].max()
            df[metric] = df[metric] / max_val if max_val != 0 else df[metric]
            return df

        elif isinstance(df, np.ndarray):
            max_val = np.max(df)
            return df / max_val if max_val != 0 else df
        else:
            logging.error(f"Input type {type(df)} not supported. Must be DataFrame or numpy array")
            return df

    def delete_columns(self, df, columns):
        df.drop(columns=columns, inplace=True)
        return df

    def process_anomalies(self, merged_df):
        # Iterate over the columns to find metric and anomaly columns
        for col in merged_df.columns:
            if col.endswith('_anomaly'):
                # Identify the corresponding metric column
                metric_col = col.replace('_anomaly', '')
                if metric_col in merged_df.columns:
                    # Call the collect_anomalies function
                    self.collect_anomalies(merged_df, metric_col, col)

    def collect_anomalies(self, df, metric, anomaly_cl):
        """
        Collect and analyze anomalies in the time series data.

        Args:
            df (DataFrame): Input dataframe containing time series data
            metric (str): Name of the metric column to analyze
            anomaly_cl (str): Name of the column containing anomaly flags

        The method tracks consecutive anomalies and combines them into single events
        when they occur close to each other (within the buffer_size window).
        """
        def format_time_range(start, end):
            """Format the time range for anomaly description.

            Returns only time if start and end dates are the same,
            otherwise returns full datetime.
            """
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')

            if start_date == end_date:
                return (f"{start.strftime('%H:%M:%S')} to "
                       f"{end.strftime('%H:%M:%S')}")
            else:
                return (f"{start.strftime('%Y-%m-%d %H:%M:%S')} to "
                       f"{end.strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize tracking variables
        anomaly_started = False  # Flag to track if we're currently in an anomaly period
        start_time = None        # Start time of current anomaly
        end_time = None         # End time of current anomaly
        baseline_value = None    # Reference value for comparison
        anomalies_detected = False  # Flag to track if any anomalies were found
        anomaly_values = []      # Values during anomaly period
        buffer_size = 3         # Number of normal points needed to confirm anomaly end
        normal_points_buffer = []  # Buffer for tracking return to normal
        current_methods = set()   # Set of detection methods that identified the anomaly

        def calculate_baseline(series, window=3):
            """Calculate baseline value using rolling mean."""
            return series.rolling(window=window, min_periods=1).mean().iloc[0]

        # Process each data point
        for index, row in df.iterrows():
            current_value = row[metric]
            is_anomaly = 'Anomaly' in str(row[anomaly_cl]) and 'potential saturation point' not in str(row[anomaly_cl])

            if is_anomaly:
                # Extract detection methods from anomaly flag
                methods = set(row[anomaly_cl].replace('Anomaly: ', '').split(', '))
                current_methods.update(methods)

                if not anomaly_started:
                    # Start of new anomaly period
                    anomaly_started = True
                    start_time = index
                    # Calculate baseline from previous normal points
                    prev_idx = df.index.get_loc(index)
                    if prev_idx > 0:
                        prev_values = df[metric].iloc[max(0, prev_idx-3):prev_idx]
                        baseline_value = calculate_baseline(prev_values)
                    else:
                        baseline_value = current_value

                anomaly_values.append(current_value)
                end_time = index
                normal_points_buffer = []  # Reset buffer
                anomalies_detected = True
            else:
                if anomaly_started:
                    # Track potential end of anomaly period
                    normal_points_buffer.append(current_value)
                    if len(normal_points_buffer) >= buffer_size:
                        # Confirm end of anomaly period
                        if anomaly_values:
                            # Calculate anomaly characteristics
                            max_val = max(anomaly_values)
                            min_val = min(anomaly_values)
                            is_increase = max_val > baseline_value
                            significant_value = max_val if is_increase else min_val

                            # Generate description
                            description = (
                                f"An anomaly was detected in {metric} from "
                                f"{format_time_range(start_time, end_time)}, "
                                f"with the metric {'increasing' if is_increase else 'dropping'} "
                                f"to {significant_value:.2f}."
                            )

                            # Record the anomaly
                            self.output.append({
                                'status': 'failed',
                                'method': ', '.join(current_methods),
                                'description': description,
                                'value': significant_value
                            })

                        # Reset tracking variables
                        anomaly_started = False
                        anomaly_values = []
                        current_methods.clear()
                        normal_points_buffer = []

        # Handle case where anomaly continues until end of data
        if anomaly_started and anomaly_values:
            max_val = max(anomaly_values)
            min_val = min(anomaly_values)
            is_increase = max_val > baseline_value
            significant_value = max_val if is_increase else min_val

            description = (
                f"An anomaly was detected in {metric} from "
                f"{format_time_range(start_time, end_time)}, "
                f"with the metric {'increasing' if is_increase else 'dropping'} "
                f"to {significant_value:.2f}."
            )

            self.output.append({
                'status': 'failed',
                'method': ', '.join(current_methods),
                'description': description,
                'value': significant_value
            })

        # Record if no anomalies were detected
        if not anomalies_detected:
            self.output.append({
                'status': 'passed',
                'method': 'N/A',
                'description': f'No anomalies detected in {metric}',
                'value': None
            })

    def _append_anomaly_result(self, metric, method, start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values):
        mean_value = np.mean([val for val in [prev_normal_value, post_anomaly_value] if val is not None])
        description = f"An anomaly was detected in {metric} from {start_time} to {end_time}, with the metric "

        # Round anomaly values to 2 decimal places
        rounded_anomaly_values = [round(val, 2) for val in anomaly_values]

        if mean_value < np.max(anomaly_values):
            description += f"increasing to {np.max(rounded_anomaly_values):.2f}."
        else:
            description += f"dropping to {np.min(rounded_anomaly_values):.2f}."
        self.output.append({
            'status': 'failed',
            'method': method,
            'description': description,
            'value': np.max(rounded_anomaly_values) if mean_value < np.max(rounded_anomaly_values) else np.min(rounded_anomaly_values)
        })

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

        for col in merged_df.columns:
            if '_anomaly' not in col:
                anomaly_col = col + '_anomaly'

                metrics[col] = {
                    'name': standard_metrics[col]['name'],
                    'data': []
                }

                for timestamp, row in merged_df.iterrows():
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

    def analyze_test_data(self, merged_df: pd.DataFrame, standard_metrics: Dict[str, Dict[str, Any]]):
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

        ramp_up_period = self.detect_anomalies(ramp_up_period, metric="overalThroughput", period_type='ramp_up')

        if is_fixed_load:
            for metric in standard_metrics:
                if standard_metrics[metric]['analysis']:
                    fixed_load_period = self.detect_anomalies(
                        fixed_load_period,
                        metric=metric,
                        period_type='fixed_load'
                    )

        # Ensure columns match between periods
        missing_columns = set(fixed_load_period.columns) - set(ramp_up_period.columns)
        for col in missing_columns:
            ramp_up_period[col] = 'Normal'

        # Merge periods and prepare results
        merged_df = pd.concat([ramp_up_period, fixed_load_period], axis=0)
        metrics = self.prepare_final_metrics(merged_df, standard_metrics)

        if is_fixed_load:
            self.process_anomalies(merged_df)

        return metrics, is_fixed_load, self.output