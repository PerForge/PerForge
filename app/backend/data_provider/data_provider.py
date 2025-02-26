# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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

from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.data_provider.data_analysis.anomaly_detection import AnomalyDetectionEngine
from app.backend.data_provider.data_analysis.detectors import (
    IsolationForestDetector,
    ZScoreDetector,
    MetricStabilityDetector,
    RampUpPeriodAnalyzer
)
from app.backend.integrations.data_sources.timescaledb.timescaledb_extraction import TimeScaleDB

import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

class DataProvider:
    """
    DataProvider class manages data extraction, transformation, and analysis for performance tests.

    This class serves as a bridge between data sources (like InfluxDB) and the application,
    providing methods to fetch, analyze, and format performance test data. It includes
    functionality for anomaly detection, trend analysis, and performance metrics aggregation.

    Attributes:
        class_map (Dict[str, Any]): Mapping of data source types to their implementation classes
        project: Project configuration object
        ds_obj: Data source object instance
        test_type (Optional[str]): Type of the test (fixed load or ramp up)
        Various time and metric attributes for caching test data
    """

    class_map = {
        "influxdb_v2": InfluxdbV2,
        "timescaledb": TimeScaleDB
    }

    def __init__(self, project: Any, source_type: Any, id: Optional[str] = None) -> None:
        """
        Initialize the DataProvider with project settings and optional ID.

        Args:
            project: Project configuration object
            source_type: Type of the data source (e.g. InfluxDB, TimeScaleDB)
            id: Optional identifier for the data source
        """
        self.project = project
        self.ds_obj = self.class_map.get(source_type, None)(project=self.project, id=id)
        # Initialize cache attributes
        self.start_time_human = None
        self.end_time_human = None
        self.start_time_iso = None
        self.end_time_iso = None
        self.start_time_timestamp = None
        self.end_time_timestamp = None
        self.test_name = None
        self.test_type = None
        self.duration = None
        self.max_active_users = None
        self.median_throughput = None
        self.median_response_time_stats = None
        self.pct90_response_time_stats = None
        self.errors_pct_stats = None

    # Basic data retrieval methods
    def get_test_log(self) -> Dict[str, Any]:
        """Retrieve test log data from the database."""
        return self.ds_obj.get_test_log()

    def get_response_time_data(self) -> None:
        """Retrieve response time data (placeholder)."""
        pass

    def get_throughput_data(self) -> None:
        """Retrieve throughput data (placeholder)."""
        pass

    def get_vusers_data(self) -> None:
        """Retrieve virtual users data (placeholder)."""
        pass

    def get_errors_data(self) -> None:
        """Retrieve errors data (placeholder)."""
        pass

    # Data collection and caching methods
    def collect_test_data(self, test_title: str) -> None:
        """
        Collect and cache all test-related data.

        Args:
            test_title: The title/name of the test to collect data for
        """
        if not self.start_time_human:
            self.start_time_human = self.ds_obj.get_start_time(test_title=test_title, time_format='human')
        if not self.end_time_human:
            self.end_time_human = self.ds_obj.get_end_time(test_title=test_title, time_format='human')
        if not self.start_time_iso:
            self.start_time_iso = self.ds_obj.get_start_time(test_title=test_title, time_format='iso')
        if not self.end_time_iso:
            self.end_time_iso = self.ds_obj.get_end_time(test_title=test_title, time_format='iso')
        if not self.start_time_timestamp:
            self.start_time_timestamp = self.ds_obj.get_start_time(test_title=test_title, time_format='timestamp')
        if not self.end_time_timestamp:
            self.end_time_timestamp = self.ds_obj.get_end_time(test_title=test_title, time_format='timestamp')
        if not self.test_name:
            self.test_name = self.ds_obj.get_test_name(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)
        if not self.duration:
            self.duration = str(int((self.end_time_timestamp - self.start_time_timestamp) / 1000))
        if not self.max_active_users:
            self.max_active_users = self.ds_obj.get_max_active_users_stats(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)
        if not self.median_throughput:
            self.median_throughput = self.ds_obj.get_median_throughput_stats(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)
        if not self.median_response_time_stats:
            self.median_response_time_stats = self.ds_obj.get_median_response_time_stats(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)
        if not self.pct90_response_time_stats:
            self.pct90_response_time_stats = self.ds_obj.get_pct90_response_time_stats(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)
        if not self.errors_pct_stats:
            self.errors_pct_stats = self.ds_obj.get_errors_pct_stats(test_title=test_title, start=self.start_time_iso, end=self.end_time_iso)

    # Metric initialization and configuration
    def initialize_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize and return the standard metrics configuration.

        Returns:
            Dictionary containing metric configurations with their functions and analysis settings
        """
        return {
            "overalThroughput": {"func": self.ds_obj.get_rps, "name": "Throughput", "analysis": True},
            "overalUsers": {"func": self.ds_obj.get_active_threads, "name": "Users", "analysis": False},
            "overalAvgResponseTime": {"func": self.ds_obj.get_average_response_time, "name": "Avg Response Time", "analysis": True},
            "overalMedianResponseTime": {"func": self.ds_obj.get_median_response_time, "name": "Median Response Time", "analysis": True},
            "overal90PctResponseTime": {"func": self.ds_obj.get_pct90_response_time, "name": "90th Percentile Response Time", "analysis": True},
            "overalErrors": {"func": self.ds_obj.get_error_count, "name": "Errors", "analysis": False}
        }

    # Data transformation methods
    def transform_to_json(self, result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform time series data to JSON format.

        Args:
            result: List of dictionaries with transaction data

        Returns:
            List of dictionaries with formatted data points
        """
        grouped_records = defaultdict(list)

        for entry in result:
            transaction = entry['transaction']
            df = entry['data']

            for timestamp, row in df.iterrows():
                value = row['value']
                grouped_records[transaction].append({
                    'timestamp': timestamp.isoformat(),
                    'value': value,
                    'anomaly': 'Normal'
                })

        json_result = [{'name': transaction, 'data': data} for transaction, data in grouped_records.items()]

        return json_result

    def fetch_metric(self, metric: str, func: Any, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch a specific metric using the provided function.

        Args:
            metric: Name of the metric
            func: Function to fetch the data
            test_title: Test title/name
            start: Start time in ISO format
            end: End time in ISO format

        Returns:
            DataFrame with renamed value column
        """
        result = func(test_title=test_title, start=start, end=end)
        return result.rename(columns={'value': metric})

    # DataFrame manipulation methods
    def merge_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge multiple DataFrames into a single DataFrame.

        Args:
            dataframes: Dictionary of DataFrames to merge

        Returns:
            Merged DataFrame sorted by index
        """
        merged_df = pd.concat(dataframes.values(), axis=1)
        return merged_df.sort_index()

    def df_nan_to_zero(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replace NaN values with 0."""
        return df.fillna(0)

    def df_delete_nan_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows containing NaN values."""
        return df.dropna()

    # Analysis methods
    def analyze_data_periods(self, merged_df: pd.DataFrame, test_title: str,
                           start: str, end: str) -> Tuple[pd.DataFrame, pd.DataFrame, bool]:
        """
        Analyze test data periods for anomalies and patterns.

        Args:
            merged_df: DataFrame containing all metrics
            test_title: Test title/name
            start: Start time in ISO format
            end: End time in ISO format

        Returns:
            Tuple containing ramp-up period data, fixed-load period data, and is_fixed_load flag
        """
        fixed_load_period, ramp_up_period = self.engine.filter_ramp_up_and_down_periods(df=merged_df.copy(), metric="overalUsers")

        ramp_up_period = self.engine.detect_anomalies(ramp_up_period, metric="overalThroughput", period_type='ramp_up')

        is_fixed_load = self.engine.check_if_fixed_load(total_rows=len(merged_df), fixed_load_rows=len(fixed_load_period))
        if is_fixed_load:
            self.test_type = "fixed load"
            for metric in self.initialize_metrics():
                if self.initialize_metrics()[metric]['analysis']:
                    fixed_load_period = self.engine.detect_anomalies(fixed_load_period, metric=metric, period_type='fixed_load')
        else:
            self.test_type = "ramp up"

        return ramp_up_period, fixed_load_period, is_fixed_load

    def prepare_final_result(self, merged_df: pd.DataFrame, standart_metrics: Dict[str, Dict[str, Any]]):
        """
        Prepare the final result dictionary from the merged DataFrame.
        :param merged_df: The merged DataFrame containing the data.
        :param standart_metrics: The dictionary containing the standard metrics configuration.
        :return: The final result dictionary.
        """
        result = {}

        for col in merged_df.columns:
            if '_anomaly' not in col:
                anomaly_col = col + '_anomaly'

                result[col] = {
                    'name': standart_metrics[col]['name'],
                    'data': []
                }

                for timestamp, row in merged_df.iterrows():
                    anomaly_value = row[anomaly_col] if anomaly_col in row and pd.notna(row[anomaly_col]) else 'Normal'
                    value = row[col] if pd.notna(row[col]) else 0.0
                    result[col]['data'].append({
                        'timestamp': timestamp.isoformat(),
                        'value': value,
                        'anomaly': anomaly_value
                    })

        return result

    def create_html_summary(self, test_type: str, analysis_output: List[Dict[str, Any]]) -> Tuple[str, bool]:
        """
        Create HTML summary of test analysis results.

        Args:
            test_type: Type of the test (fixed load or ramp up)
            analysis_output: List of analysis results

        Returns:
            Tuple containing HTML formatted summary and performance status
        """
        # Count failed checks and group anomalies by metric
        failed_checks = [x for x in analysis_output if x['status'] == 'failed']
        metric_anomaly_counts = defaultdict(int)
        trend_issues = []
        ramp_up_status = None
        saturation_point = None
        performance_status = True  # Start with assumption that performance is good

        for check in analysis_output:
            if check['method'] == 'rolling_correlation':
                if 'Tipping point was reached' in check.get('description', ''):
                    saturation_point = check.get('value')
                else:
                    ramp_up_status = check['status'] == 'passed'
            elif check['status'] == 'failed':
                performance_status = False  # Any failed check means we have issues
                if check['method'] == 'TrendAnalysis':
                    trend_issues.append(check['description'])
                elif 'An anomaly was detected in' in check['description']:
                    metric = check['description'].split('in ')[1].split(' from')[0]
                    metric_anomaly_counts[metric] += 1

        # Generate HTML summary
        html_parts = []

        # Test type and overall status
        html_parts.append(f"<p>Test type: <strong>{test_type}</strong></p>")

        # Ramp-up analysis
        if test_type.lower() == "ramp up":
            if saturation_point:
                html_parts.append(f"<p>🎯 System saturation detected at: <strong>{saturation_point}</strong> requests per second</p>")
        elif ramp_up_status is not None:
            status_icon = "✅" if ramp_up_status else "❌"
            html_parts.append(f"<p>{status_icon} Ramp-up period: {'successful' if ramp_up_status else 'issues detected'}</p>")

        # Trend analysis
        if trend_issues:
            html_parts.append("<div class='trend-analysis'>")
            html_parts.append("<h4>📈 Trend Analysis Issues:</h4>")
            html_parts.append("<ul>")
            for issue in trend_issues:
                html_parts.append(f"<li>{issue}</li>")
            html_parts.append("</ul>")
            html_parts.append("</div>")

        # Anomalies summary
        if metric_anomaly_counts:
            html_parts.append("<div class='anomalies'>")
            html_parts.append("<h4>⚠️ Anomalies Detected:</h4>")
            html_parts.append("<ul>")
            for metric, count in metric_anomaly_counts.items():
                html_parts.append(
                    f"<li><strong>{metric}</strong>: "
                    f"{count} {'anomaly' if count == 1 else 'anomalies'}</li>"
                )
            html_parts.append("</ul>")
            html_parts.append("</div>")

        if not failed_checks:
            html_parts.append("<p>✅ No issues were detected during the test execution.</p>")

        return "\n".join(html_parts), performance_status

    def get_aggregated_metrics(self, test_title: str) -> Dict[str, Any]:
        """
        Retrieve aggregated metrics from the test data.

        This method collects key performance metrics including:
        - Maximum number of virtual users (VU)
        - Median throughput
        - Median response time
        - 90th percentile response time
        - Error percentage

        Args:
            test_title: The title/name of the test to analyze

        Returns:
            Dictionary containing aggregated metrics with their values
        """
        self.collect_test_data(test_title=test_title)

        aggregated_results = {
            "vu": self.max_active_users,
            "throughput": self.median_throughput,
            "median": self.median_response_time_stats,
            "90pct": self.pct90_response_time_stats,
            "errors": f'{str(self.errors_pct_stats)}%'
        }
        return aggregated_results

    def get_test_details(self, test_title: str) -> Dict[str, str]:
        """
        Retrieve basic test execution details.

        This method collects basic test information including:
        - Start time (human readable)
        - End time (human readable)
        - Test duration in seconds

        Args:
            test_title: The title/name of the test

        Returns:
            Dictionary containing test execution details
        """
        self.collect_test_data(test_title=test_title)

        test_details = {
            "start_time": self.start_time_human,
            "end_time": self.end_time_human,
            "duration": self.duration
        }
        return test_details

    # Main analysis method
    def get_test_results_and_analyze(self, test_title: str) -> Tuple[Dict, List, Dict, Dict, Dict, str, bool]:
        """
        Main method to retrieve and analyze test results.

        Args:
            test_title: The title/name of the test to analyze

        Returns:
            Tuple containing:
            - result: Processed test data
            - analysis_output: Raw analysis results
            - aggregated_results: Aggregated metrics
            - test_details: Basic test information
            - statistics: Statistical analysis
            - summary: HTML formatted summary
            - performance_status: Boolean indicating if there are performance issues
        """
        # Initialize detectors with configuration
        detectors = [
            IsolationForestDetector(),
            ZScoreDetector(),
            MetricStabilityDetector(),
            RampUpPeriodAnalyzer(
                threshold_condition=lambda x: x < self.engine.rolling_correlation_threshold,
                base_metric="overalUsers"
            )
        ]

        # Initialize engine with detectors
        self.engine = AnomalyDetectionEngine(
            params={},  # You can pass custom parameters here
            detectors=detectors
        )

        current_start_time = self.ds_obj.get_start_time(test_title=test_title, time_format='iso')
        current_end_time = self.ds_obj.get_end_time(test_title=test_title, time_format='iso')

        standart_metrics = self.initialize_metrics()

        # Fetch and merge the data for all standard metrics
        dataframes = {metric: self.fetch_metric(metric, details["func"], test_title, current_start_time, current_end_time) for metric, details in standart_metrics.items()}

        # NaN values to 0
        dataframes = {metric: self.df_nan_to_zero(df) for metric, df in dataframes.items()}

        merged_df = self.merge_dataframes(dataframes)

        merged_df = self.df_delete_nan_rows(merged_df)

        # Analyze the data periods
        ramp_up_period, fixed_load_period, is_fixed_load = self.analyze_data_periods(merged_df, test_title, current_start_time, current_end_time)

        missing_columns = set(fixed_load_period.columns) - set(ramp_up_period.columns)
        for col in missing_columns:
            ramp_up_period[col] = 'Normal'

        # Merge ramp-up and fixed-load periods back into a single DataFrame
        merged_df = pd.concat([ramp_up_period, fixed_load_period], axis=0)

        # Prepare the final result
        result = self.prepare_final_result(merged_df, standart_metrics)

        # Fetch additional response time per request data
        avgResponseTimePerReq = self.ds_obj.get_average_response_time_per_req(test_title=test_title, start=current_start_time, end=current_end_time)
        result["avgResponseTimePerReq"] = self.transform_to_json(avgResponseTimePerReq)

        medianRespTimePerReq = self.ds_obj.get_median_response_time_per_req(test_title=test_title, start=current_start_time, end=current_end_time)
        result["medianResponseTimePerReq"] = self.transform_to_json(medianRespTimePerReq)

        pctRespTimePerReq = self.ds_obj.get_pct90_response_time_per_req(test_title=test_title, start=current_start_time, end=current_end_time)
        result["pctResponseTimePerReq"] = self.transform_to_json(pctRespTimePerReq)

        if is_fixed_load:
            self.engine.process_anomalies(merged_df)

        # Collect the outputs
        analysis_output = self.engine.output
        aggregated_results = self.get_aggregated_metrics(test_title=test_title)
        test_details = self.get_test_details(test_title=test_title)
        statistics = self.ds_obj.get_aggregated_table(test_title=test_title, start=current_start_time, end=current_end_time)
        summary, performance_status = self.create_html_summary(self.test_type, analysis_output)
        return result, analysis_output, aggregated_results, test_details, statistics, summary, performance_status