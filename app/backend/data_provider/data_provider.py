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

# Standard library imports
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional, Type
import logging

# Third-party imports
import pandas as pd
from datetime import datetime
from dateutil import tz

# Local application imports
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.integrations.data_sources.influxdb_v1_8.influxdb_extraction_1_8 import InfluxdbV18
from app.backend.data_provider.data_analysis.anomaly_detection import AnomalyDetectionEngine
from app.backend.integrations.data_sources.base_extraction import DataExtractionBase
from app.backend.data_provider.test_data import BaseTestData, BackendTestData, FrontendTestData, MetricsTable, TestDataFactory
from app.backend.data_provider.data_analysis.constants import METRIC_DISPLAY_NAMES

class DataProvider:
    """
    DataProvider class manages data extraction, transformation, and analysis for performance tests.

    This class serves as a central hub for handling performance test data, providing:
    - Data extraction from various sources (InfluxDB)
    - Data transformation and preprocessing
    - Performance metrics calculation and aggregation
    - Support for both backend and frontend test types
    """

    class_map: Dict[str, Type[DataExtractionBase]] = {
        "influxdb_v2": InfluxdbV2,
        "influxdb_v1.8": InfluxdbV18,
        # Add more data sources as needed
    }

    # Map data source types to test types
    source_to_test_type_map: Dict[str, str] = {
        "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient": "back_end",
        "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient_v1.8": "back_end",
        "sitespeed_influxdb_v2": "front_end",
        "sitespeed_influxdb_v1.8": "front_end",
    }

    def __init__(self, project: Any, source_type: Any, id: str, bucket: str) -> None:
        """
        Initialize DataProvider with project settings and data source configuration.

        Args:
            project: Project configuration object with settings
            source_type: Data source type identifier (e.g., "influxdb_v2")
            id: Identifier for specific data source instance
            bucket: Override for the data source bucket (applied post-initialization)
        """
        self.project = project
        self.source_type = source_type
        self.ds_obj = self.class_map.get(source_type, None)(project=self.project, id=id)

        # Determine the test type based on the source type
        self.test_type = self.source_to_test_type_map.get(self.ds_obj.listener, "back_end")

        # Apply bucket override (optional) in a source-type aware manner
        # For InfluxDB v2, bucket is used in Flux queries and does not affect the client.
        # For InfluxDB 1.8, bucket corresponds to the database on the client.
        if bucket:
            try:
                if source_type == "influxdb_v2":
                    # Simple override of the bucket used in queries
                    setattr(self.ds_obj, "bucket", bucket)
                elif source_type == "influxdb_v1.8":
                    # For classic InfluxDB 1.8, switch the active database on the existing client
                    client = getattr(self.ds_obj, "influxdb_connection", None)
                    if client is not None:
                        try:
                            client.switch_database(bucket)
                        except Exception as er:
                            logging.warning(f"DataProvider: failed to switch InfluxDB 1.8 database to '{bucket}': {er}")
                    setattr(self.ds_obj, "database", bucket)
                else:
                    # Fallback: try to set a generic bucket attribute if present
                    if hasattr(self.ds_obj, "bucket"):
                        setattr(self.ds_obj, "bucket", bucket)
            except Exception as e:
                logging.warning(f"DataProvider: failed to apply bucket override: {e}")

    # Timestamp helper
    def get_current_timestamp(self, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
        """Generate the current timestamp in human-readable form.

        The timezone is taken from the underlying data source object (``ds_obj``),
        which should expose a ``tmz_human`` attribute like the InfluxdbV2 class.
        If the data source does not provide timezone information, UTC is used.

        Args:
            fmt: Optional strftime format string. Defaults to
                 "%Y-%m-%d %H:%M:%S %Z".

        Returns:
            str: Human-readable timestamp in the configured timezone.
        """
        human_tz = getattr(self.ds_obj, "tmz_human", tz.tzutc()) or tz.tzutc()
        now_utc = datetime.now(tz=tz.tzutc())
        return now_utc.astimezone(human_tz).strftime(fmt)

    # Basic data retrieval methods
    def get_test_log(self, test_titles: list[str]):
        """Return tests list.

        If *limit* and/or *offset* are provided and the underlying data-source
        supports them, they will be forwarded to reduce the amount of data
        transferred. Otherwise the full list will be requested and sliced
        in-memory as a graceful fallback.
        """
        return self.ds_obj.get_test_log(test_titles=test_titles)

    def get_tests_titles(self) -> list[str]:
        """Return list of unique test titles from data-source."""
        raw = self.ds_obj.get_tests_titles()
        return [str(r.get("test_title")) for r in raw if r.get("test_title")]

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
    def collect_test_obj(self, test_title: str, test_type: Optional[str] = None) -> BaseTestData:
        """
        Collect and create a test data object for the specified test

        Args:
            test_title: The title/name of the test to collect data for
            test_type: Optional test type override. If not provided, will use the type determined by source_type

        Returns:
            Test data object populated with test data
        """
        # Use provided test_type or default to the one determined by source_type
        effective_test_type = test_type if test_type else self.test_type

        # Create appropriate test data object
        test_obj = TestDataFactory.create_test_data(effective_test_type)

        # Set common data for all test types
        if hasattr(test_obj, 'test_title'):
            test_obj.set_metric('test_title', test_title)
        if hasattr(test_obj, 'start_time_human'):
            test_obj.set_metric('start_time_human', self.ds_obj.get_start_time(test_title=test_title, time_format='human'))
        if hasattr(test_obj, 'end_time_human'):
            test_obj.set_metric('end_time_human', self.ds_obj.get_end_time(test_title=test_title, time_format='human'))
        if hasattr(test_obj, 'start_time_iso'):
            test_obj.set_metric('start_time_iso', self.ds_obj.get_start_time(test_title=test_title, time_format='iso'))
        if hasattr(test_obj, 'end_time_iso'):
            test_obj.set_metric('end_time_iso', self.ds_obj.get_end_time(test_title=test_title, time_format='iso'))
        if hasattr(test_obj, 'start_time_timestamp'):
            test_obj.set_metric('start_time_timestamp', self.ds_obj.get_start_time(test_title=test_title, time_format='timestamp'))
        if hasattr(test_obj, 'end_time_timestamp'):
            test_obj.set_metric('end_time_timestamp', self.ds_obj.get_end_time(test_title=test_title, time_format='timestamp'))
        # Calculate duration
        test_obj.calculate_duration()

        # Set data provider reference in test object for lazy loading
        if hasattr(test_obj, 'data_provider'):
            test_obj.data_provider = self

        # Dispatch to specialized collection methods based on test type
        if effective_test_type == "back_end":
            self._collect_backend_test_data(test_obj)
        elif effective_test_type == "front_end":
            self._collect_frontend_test_data(test_obj)

        if hasattr(test_obj, 'custom_vars'):
            for custom_var in self.ds_obj.custom_vars:
                value = self.ds_obj.get_custom_var(test_title=test_title, custom_var=custom_var, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
                test_obj.append_metric("custom_vars", {"name": custom_var, "value": value})
        return test_obj

    def _collect_backend_test_data(self, test_obj: BackendTestData) -> None:
        """
        Collect data specific to backend tests

        Args:
            test_obj: BackendTestData object to populate
        """
        # Now that error handling is moved to base_extraction.py, we can simplify this method
        # Each method in base_extraction.py now handles errors and provides fallback values

        # Max active users
        value = self.ds_obj.get_max_active_users_stats(
            test_title=test_obj.test_title,
            start=test_obj.start_time_iso,
            end=test_obj.end_time_iso
        )
        test_obj.set_metric('max_active_users', value)

        # Median throughput
        value = self.ds_obj.get_median_throughput_stats(
            test_title=test_obj.test_title,
            start=test_obj.start_time_iso,
            end=test_obj.end_time_iso
        )
        test_obj.set_metric('median_throughput', value)

        # Median response time
        value = self.ds_obj.get_median_response_time_stats(
            test_title=test_obj.test_title,
            start=test_obj.start_time_iso,
            end=test_obj.end_time_iso
        )
        test_obj.set_metric('median_response_time_stats', value)

        # 90th percentile response time
        value = self.ds_obj.get_pct90_response_time_stats(
            test_title=test_obj.test_title,
            start=test_obj.start_time_iso,
            end=test_obj.end_time_iso
        )
        test_obj.set_metric('pct90_response_time_stats', value)

        # Error percentage
        value = self.ds_obj.get_errors_pct_stats(
            test_title=test_obj.test_title,
            start=test_obj.start_time_iso,
            end=test_obj.end_time_iso
        )
        test_obj.set_metric('errors_pct_stats', value)


    def _collect_frontend_test_data(self, test_obj: FrontendTestData) -> None:
        """
        Collect data specific to frontend tests

        Args:
            test_obj: FrontendTestData object to populate
        """
        # Get aggregated data table
        pass

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
        """
        Remove rows containing NaN values while gracefully handling fully-missing metrics.

        This function will:
        - Drop any columns that are entirely NaN (e.g., missing metrics) with a warning
        - Drop remaining rows that contain NaN values across the kept columns
        - Raise only if the DataFrame is empty or if all columns are entirely NaN

        Args:
            df: The DataFrame to process

        Returns:
            A DataFrame with NaN rows removed

        Raises:
            ValueError: If the DataFrame is empty or if all columns are completely NaN
        """
        # Check if the DataFrame is empty
        if df.empty:
            raise ValueError("DataFrame is empty - no metrics data available")

        # Check if any columns are completely NaN
        all_nan_columns = df.columns[df.isna().all()].tolist()

        # If all columns are NaN, raise an exception
        if len(all_nan_columns) == len(df.columns):
            raise ValueError(f"All metrics data is missing: {', '.join(all_nan_columns)}")

        # If some columns are completely NaN, log a warning and drop them, continue with remaining columns
        if all_nan_columns:
            logging.warning(
                "Some data was not found with current integration configuration. Please check your configuration. Dropping metrics with no data: %s",
                ", ".join(all_nan_columns)
            )
            df = df.drop(columns=all_nan_columns)

        # If no columns are completely NaN, proceed with normal dropna
        return df.dropna()

    def get_statistics(self, test_title: str, test_obj: BaseTestData = None) -> Dict[str, Any]:
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
        if not test_obj:
            test_obj: BaseTestData = self.collect_test_obj(test_title=test_title)

        aggregated_results = {
            "vu": test_obj.max_active_users,
            "throughput": test_obj.median_throughput,
            "median": test_obj.median_response_time_stats,
            "90pct": test_obj.pct90_response_time_stats,
            "errors": f'{str(test_obj.errors_pct_stats)}%'
        }
        return aggregated_results

    def get_test_details(self, test_title: str, test_obj: BaseTestData = None ) -> Dict[str, str]:
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
        if not test_obj:
            test_obj: BaseTestData = self.collect_test_obj(test_title=test_title)

        test_details = {
            "start_time": test_obj.start_time_human,
            "end_time": test_obj.end_time_human,
            "duration": test_obj.duration
        }
        return test_details

    def _get_test_results(self, test_obj: BaseTestData):
        standard_metrics = self.initialize_metrics()

        # Fetch and merge the data for all standard metrics
        dataframes = {metric: self.fetch_metric(metric, details["func"], test_obj.test_title, test_obj.start_time_iso, test_obj.end_time_iso) for metric, details in standard_metrics.items()}

        # NaN values to 0
        dataframes = {metric: self.df_nan_to_zero(df) for metric, df in dataframes.items()}

        merged_df = self.merge_dataframes(dataframes)

        merged_df = self.df_delete_nan_rows(merged_df)
        return merged_df, standard_metrics

    def get_ml_analysis_to_test_obj(self, test_obj: BaseTestData):
        """
        Perform machine learning analysis on test data to detect anomalies and patterns.

        Args:
            test_obj: TestData object containing test information and metrics

        Returns:
            metrics: Dictionary containing analyzed metrics and their characteristics
        """
        # If ML analysis is already present, do not run it again
        if test_obj.ml_anomalies is not None:
            return test_obj.ml_metrics

        merged_df, standard_metrics = self._get_test_results(test_obj=test_obj)

        # Initialize engine with detectors
        self.anomaly_detection_engine = AnomalyDetectionEngine(
            params={}  # You can pass custom parameters here
        )

        # Analyze the data periods
        metrics, is_fixed_load, analysis_output = self.anomaly_detection_engine.analyze_test_data(
            merged_df=merged_df,
            standard_metrics=standard_metrics,
            data_provider=self,
            test_obj=test_obj
        )

        if is_fixed_load:
            test_obj.test_type = "fixed load"
        else:
            test_obj.test_type = "ramp up"

        ml_html_summary, performance_status = self.anomaly_detection_engine.create_html_summary(test_obj.test_type, analysis_output)
        ml_summary = self.anomaly_detection_engine.create_text_summary(test_obj.test_type, analysis_output)

        test_obj.ml_anomalies = analysis_output
        test_obj.ml_html_summary = ml_html_summary
        test_obj.ml_summary = ml_summary
        test_obj.performance_status = performance_status
        test_obj.ml_metrics = metrics

        return metrics



    # Main analysis method
    def collect_test_data_for_report_page(self, test_title: str) -> Tuple[Dict, List, Dict, Dict, Dict, str, bool]:
        """
        Comprehensive test data collection and analysis for report generation.

        This method orchestrates the entire data collection and analysis process:
        1. Collects basic test information and metrics
        2. Performs ML analysis for anomaly detection
        3. Gathers detailed response time metrics per request
        4. Compiles statistics and test details

        Args:
            test_title: Name/identifier of the test to analyze
        """
        test_obj: BaseTestData = self.collect_test_obj(test_title=test_title)

        metrics = self.get_ml_analysis_to_test_obj(test_obj=test_obj)

        # Collect overall anomaly windows from the anomaly detection engine for
        # visualization (e.g. shaded bands on charts).
        overall_anomaly_windows: Dict[str, List[Dict[str, str]]] = {}
        engine = getattr(self, "anomaly_detection_engine", None)
        if engine is not None:
            overall_list = getattr(engine, "overall_anomalies", []) or []
            for oa in overall_list:
                metric = oa.get("metric")
                start_time = oa.get("start_time")
                end_time = oa.get("end_time")
                if not metric or start_time is None or end_time is None:
                    continue
                try:
                    start_iso = pd.to_datetime(start_time).isoformat()
                except Exception:
                    start_iso = str(start_time)
                try:
                    end_iso = pd.to_datetime(end_time).isoformat()
                except Exception:
                    end_iso = str(end_time)
                overall_anomaly_windows.setdefault(metric, []).append(
                    {"start": start_iso, "end": end_iso}
                )

        # Fetch additional response time per request data
        avgResponseTimePerReq = self._get_per_req_series(test_obj, 'rt_avg', test_title, test_obj.start_time_iso, test_obj.end_time_iso)
        metrics["avgResponseTimePerReq"] = self.transform_to_json(avgResponseTimePerReq)

        medianRespTimePerReq = self._get_per_req_series(test_obj, 'rt_median', test_title, test_obj.start_time_iso, test_obj.end_time_iso)
        metrics["medianResponseTimePerReq"] = self.transform_to_json(medianRespTimePerReq)

        pctRespTimePerReq = self._get_per_req_series(test_obj, 'rt_p90', test_title, test_obj.start_time_iso, test_obj.end_time_iso)
        metrics["pctResponseTimePerReq"] = self.transform_to_json(pctRespTimePerReq)

        throughputPerReq = self._get_per_req_series(test_obj, 'rps', test_title, test_obj.start_time_iso, test_obj.end_time_iso)
        metrics["throughputPerReq"] = self.transform_to_json(throughputPerReq)

        # Collect the aggregated table data (backend tests only)
        is_backend = getattr(test_obj, 'test_type', None) == 'back_end'
        if is_backend:
            metrics_table: MetricsTable = test_obj.get_table('aggregated_data')
            if metrics_table:
                test_obj.aggregated_table = metrics_table.format_metrics()



        # Collect the outputs
        statistics = self.get_statistics(test_title=test_title, test_obj=test_obj)
        test_details = self.get_test_details(test_title=test_title, test_obj=test_obj)
        return (
            metrics,
            test_obj.ml_anomalies,
            statistics,
            test_details,
            test_obj.aggregated_table,
            test_obj.ml_html_summary,
            test_obj.performance_status,
            overall_anomaly_windows,
        )

    def _get_per_req_series(self, test_obj: BaseTestData, key: str, test_title: str, start: str, end: str):
        cache_key = (key, start, end)
        cache = getattr(test_obj, '_per_req_cache', None)
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        if key == 'rps':
            data = self.ds_obj.get_throughput_per_req(test_title=test_title, start=start, end=end)
        elif key == 'rt_avg':
            data = self.ds_obj.get_average_response_time_per_req(test_title=test_title, start=start, end=end)
        elif key == 'rt_median':
            data = self.ds_obj.get_median_response_time_per_req(test_title=test_title, start=start, end=end)
        elif key == 'rt_p90':
            data = self.ds_obj.get_pct90_response_time_per_req(test_title=test_title, start=start, end=end)
        else:
            data = None
        if cache is not None:
            cache[cache_key] = data
        return data

    def build_per_transaction_long_frame(self, test_obj: BaseTestData, sampling_interval_sec: int = 5, per_txn_rt_metrics: list[str] | None = None) -> None:
        test_title = test_obj.test_title
        start = test_obj.start_time_iso
        end = test_obj.end_time_iso

        if per_txn_rt_metrics is None:
            per_txn_rt_metrics = ['median', 'avg', 'p90']
        rps_per_req = self._get_per_req_series(test_obj, 'rps', test_title, start, end)
        rt_series = {}
        if 'avg' in per_txn_rt_metrics:
            rt_series['avg'] = self._get_per_req_series(test_obj, 'rt_avg', test_title, start, end)
        if 'median' in per_txn_rt_metrics:
            rt_series['median'] = self._get_per_req_series(test_obj, 'rt_median', test_title, start, end)
        if 'p90' in per_txn_rt_metrics or 'pct90' in per_txn_rt_metrics:
            rt_series['p90'] = self._get_per_req_series(test_obj, 'rt_p90', test_title, start, end)

        # Build lookup by transaction
        rps_map = {entry.get('transaction') or entry.get('name'): entry.get('data') for entry in (rps_per_req or [])}
        rt_maps = {k: {e.get('transaction') or e.get('name'): e.get('data') for e in (v or [])} for k, v in rt_series.items()}
        all_rt_txns = set().union(*[set(m.keys()) for m in rt_maps.values()]) if rt_maps else set()
        all_txns = sorted(set(rps_map.keys()) | all_rt_txns)
        if 'all' in all_txns:
            all_txns.remove('all')
        if not all_txns:
            test_obj.per_txn_df_long = None
            return

        merged_df, standard_metrics = self._get_test_results(test_obj=test_obj)
        engine = AnomalyDetectionEngine(params={})
        fixed_load_period, _, _ = engine.filter_ramp_up_and_down_periods(df=merged_df.copy(), metric="overalUsers")
        fixed_index = fixed_load_period.index
        fixed_start = fixed_index.min() if len(fixed_index) else None
        fixed_end = fixed_index.max() if len(fixed_index) else None

        frames = []
        rule = f"{int(sampling_interval_sec)}s"
        for txn in all_txns:
            df_rps = rps_map.get(txn)
            parts = []
            if df_rps is not None and not df_rps.empty:
                sr = df_rps['value'].resample(rule).mean().ffill().rename('rps')
                parts.append(sr)
            for k, m in rt_maps.items():
                df_rt = m.get(txn)
                if df_rt is not None and not df_rt.empty:
                    col = 'rt_ms_median' if k == 'median' else ('rt_ms_avg' if k == 'avg' else 'rt_ms_p90')
                    sr = df_rt['value'].resample(rule).mean().ffill().rename(col)
                    parts.append(sr)
            if not parts:
                continue
            df = pd.concat(parts, axis=1)
            df['transaction'] = txn
            frames.append(df.reset_index().rename(columns={'index': 'timestamp'}))

        if not frames:
            test_obj.per_txn_df_long = None
            return

        long_df = pd.concat(frames, axis=0, ignore_index=True)

        # Convert timestamps to UTC
        try:
            long_df['timestamp'] = pd.to_datetime(long_df['timestamp']).dt.tz_convert('UTC')
        except Exception:
            long_df['timestamp'] = pd.to_datetime(long_df['timestamp'], utc=True)

        if 'rps' in long_df.columns:
            overall = long_df.groupby('timestamp')['rps'].sum(min_count=1).rename('overall_rps')
            long_df = long_df.merge(overall.reset_index(), on='timestamp', how='left')
        else:
            long_df['overall_rps'] = pd.NA

        if 'error_rate' not in long_df.columns:
            long_df['error_rate'] = pd.NA

        if fixed_start is not None and fixed_end is not None:
            long_df = long_df[(long_df['timestamp'] >= fixed_start) & (long_df['timestamp'] <= fixed_end)]

        cols = ['timestamp', 'transaction', 'rt_ms', 'rt_ms_avg', 'rt_ms_median', 'rt_ms_p90', 'error_rate', 'rps', 'overall_rps']
        final_cols = [c for c in cols if c in long_df.columns] + [c for c in long_df.columns if c not in cols]
        long_df = long_df[final_cols].sort_values(['timestamp', 'transaction']).reset_index(drop=True)

        test_obj.per_txn_df_long = long_df

    # Transaction Status Evaluation Methods
    def _get_all_transactions(self, test_obj: BaseTestData) -> List[str]:
        """Get all unique transaction names from various data sources.

        Args:
            test_obj: Test data object

        Returns:
            List of unique transaction names including 'all' if NFRs with scope='all' exist
        """
        transactions = set()

        # Check test type to determine where to look for transactions
        is_backend = getattr(test_obj, 'test_type', None) == 'back_end'
        is_frontend = getattr(test_obj, 'test_type', None) == 'front_end'

        if is_backend:
            # Get transactions from aggregated_data table (backend tests)
            try:
                agg_table = test_obj.get_table('aggregated_data')
                if agg_table and hasattr(agg_table, 'metrics'):
                    for metric in agg_table.metrics:
                        if metric.scope and metric.scope != 'unknown':
                            transactions.add(metric.scope)
            except Exception as e:
                logging.debug(f"Could not get transactions from aggregated_data: {e}")

            # Get transactions from per-transaction ML data (backend tests with ML)
            try:
                per_txn_events = getattr(test_obj, 'per_txn_events_raw', None)
                if per_txn_events:
                    for event in per_txn_events:
                        txn = event.get('transaction')
                        if txn:
                            transactions.add(txn)
            except Exception as e:
                logging.debug(f"Could not get transactions from ML events: {e}")

        if is_frontend or not transactions:
            # Scan all available tables (frontend tests or fallback)
            # Frontend tests store pages in individual tables without an aggregated_data table
            try:
                all_tables = test_obj.get_all_tables()
                for table_name, table in all_tables.items():
                    # Skip overview_data as it contains test-level summaries, not per-page metrics
                    if table_name == 'overview_data':
                        continue
                    if hasattr(table, 'metrics'):
                        for metric in table.metrics:
                            if metric.scope and metric.scope != 'unknown':
                                transactions.add(metric.scope)
            except Exception as e:
                logging.debug(f"Could not get transactions from all tables: {e}")

        #  Exclude 'all' scope from transaction status table
        # The 'all' scope is used for global NFRs but is not an actual transaction
        # and won't have per-transaction ML data, so it's not useful in the status table
        transactions.discard('all')

        return sorted(list(transactions))

    def _extract_ml_anomaly_details(self, transaction: str, test_obj: BaseTestData) -> List[Dict[str, Any]]:
        """Extract ML anomaly details with direction and magnitude for a transaction.

        Args:
            transaction: Transaction name
            test_obj: Test data object

        Returns:
            List of anomaly detail dictionaries
        """
        details = []

        # Get per-transaction events
        per_txn_events = getattr(test_obj, 'per_txn_events_raw', None)
        if not per_txn_events:
            return details

        # Filter events for this transaction
        txn_events = [e for e in per_txn_events if e.get('transaction') == transaction]

        for event in txn_events:
            window_info = event.get('window', {})
            metrics_list= event.get('metrics', [])
            direction = event.get('direction', 'unknown')

            # Get window details from per_txn_windows if available
            per_txn_windows = getattr(test_obj, 'per_txn_windows', {})
            windows_by_metric = {}

            if per_txn_windows:
                txn_data = per_txn_windows.get('by_txn', {}).get(transaction, {})
                windows_by_metric = txn_data.get('windows_by_metric', {})

            for metric_info in metrics_list:
                metric_name = metric_info.get('name')
                if not metric_name:
                    continue

                detail = {
                    'metric': metric_name,
                    'direction': direction,
                    'window_start': window_info.get('start'),
                    'window_end': window_info.get('end')
                }

                # Try to get quantitative data from original windows
                metric_windows = windows_by_metric.get(metric_name, [])
                if metric_windows and len(metric_windows) > 0:
                    # Take the first window (most significant)
                    window_data = metric_windows[0]
                    detail.update({
                        'baseline': window_data.get('baseline'),
                        'significant_value': window_data.get('significant_value'),
                        'delta_abs': window_data.get('delta_abs'),
                        'min': window_data.get('min'),
                        'max': window_data.get('max'),
                        'mean': window_data.get('mean')
                    })

                details.append(detail)

        return details

    def _evaluate_transaction_status(
        self,
        transaction: str,
        test_obj: BaseTestData,
        config: 'TransactionStatusConfig' = None
    ) -> 'TransactionStatus':
        """Evaluate the status of a single transaction based on NFR, baseline, and ML checks.

        Args:
            transaction: Transaction name
            test_obj: Test data object
            config: Optional configuration for status evaluation

        Returns:
            TransactionStatus object
        """
        from app.backend.data_provider.test_data import (
            TransactionStatus,
            TransactionStatusConfig,
            NFRStatus
        )

        if config is None:
            config = TransactionStatusConfig()

        reasons = []
        nfr_status_val = 'NOT_EVALUATED'
        nfr_failures = []
        baseline_status_val = 'NOT_AVAILABLE'
        baseline_regressions = []
        ml_status_val = 'NOT_EVALUATED'
        ml_events = []

        # Collect all metrics for this transaction
        transaction_metrics = []
        try:
            all_tables = test_obj.get_all_tables()
            for table in all_tables.values():
                if hasattr(table, 'metrics'):
                    txn_metrics = [m for m in table.metrics if m.scope == transaction]
                    transaction_metrics.extend(txn_metrics)
        except Exception as e:
            logging.warning(f"Could not collect metrics for transaction '{transaction}': {e}")

        # Check 1: NFR Validation
        if config.nfr_enabled:
            failed_nfrs = [m for m in transaction_metrics if m.nfr_status == NFRStatus.FAILED]
            if failed_nfrs:
                nfr_status_val = 'FAILED'
                for m in failed_nfrs:
                    nfr_failures.append(f"{m.name}")
                    # Build detailed message with threshold info
                    if m.nfr_threshold is not None and m.nfr_operation:
                        reasons.append(
                            f"NFR: {m.name} failed "
                            f"(actual: {m.value:.2f}, expected: {m.nfr_operation} {m.nfr_threshold:.2f})"
                        )
                    else:
                        reasons.append(f"NFR: {m.name} failed")
            elif any(m.nfr_status == NFRStatus.PASSED for m in transaction_metrics):
                nfr_status_val = 'PASSED'

        # Check 2: Baseline Regression
        if config.baseline_enabled:
            warning_threshold = config.baseline_warning_threshold_pct
            failed_threshold = config.baseline_failed_threshold_pct

            regressions_found = []
            for m in transaction_metrics:
                if (m.baseline is not None and
                    m.difference_pct is not None and
                    m.difference_pct >= warning_threshold):
                    regressions_found.append(m)
                    baseline_regressions.append({
                        'metric': m.name,
                        'baseline': m.baseline,
                        'current': m.value,
                        'delta_pct': m.difference_pct
                    })

            if regressions_found:
                baseline_status_val = 'FAILED'
                # Build list of regression details
                regression_details = []
                for m in regressions_found:
                    severity = "critical" if m.difference_pct >= failed_threshold else "moderate"
                    metric_display = METRIC_DISPLAY_NAMES.get(m.name, m.name)
                    regression_details.append(f"{metric_display} +{m.difference_pct:.1f}% ({severity})")
                # Combine all regressions into a single reason with commas
                reasons.append(f"Regression: {', '.join(regression_details)}")
            elif any(m.baseline is not None for m in transaction_metrics):
                baseline_status_val = 'PASSED'

        # Check 3: ML Anomalies
        if config.ml_enabled:
            ml_details = self._extract_ml_anomaly_details(transaction, test_obj)

            if ml_details:
                ml_status_val = 'FAILED'
                ml_events = ml_details

                # Group anomalies by base metric
                from collections import defaultdict
                metric_groups = defaultdict(list)

                for detail in ml_details:
                    metric_name = detail.get('metric')
                    # Extract base metric name (e.g., "rt_ms" from "rt_ms_median")
                    base_metric = None
                    if metric_name:
                        # Check if this is a derived metric (contains underscore variations)
                        if metric_name in ['rt_ms_median', 'rt_ms_avg', 'rt_ms_p90']:
                            base_metric = 'rt_ms'
                        elif metric_name == 'rps':
                            # RPS (throughput) is a standalone metric
                            base_metric = 'rps'
                        elif metric_name == 'error_rate':
                            # Error rate is a standalone metric
                            base_metric = 'error_rate'
                        else:
                            base_metric = metric_name

                        metric_groups[base_metric].append(detail)

                # Build user-friendly messages grouped by base metric
                for base_metric, details_list in metric_groups.items():
                    base_display = METRIC_DISPLAY_NAMES.get(base_metric, base_metric)

                    if len(details_list) == 1:
                        # Single anomaly - show detailed info with statistic type
                        detail = details_list[0]
                        metric_name = detail.get('metric')
                        direction = detail.get('direction')
                        baseline = detail.get('baseline')
                        sig_val = detail.get('significant_value')

                        # Get the statistic type (median, avg, p90)
                        stat_type = None
                        if metric_name and '_' in metric_name:
                            parts = metric_name.split('_')
                            if parts[-1] in ['median', 'avg', 'p90']:
                                stat_type = parts[-1]
                                if stat_type == 'p90':
                                    stat_type = '90th percentile'

                        if baseline is not None and sig_val is not None and direction:
                            delta = abs(sig_val - baseline)
                            delta_pct = (delta / baseline * 100) if baseline > 0 else 0
                            action = "increased" if direction == 'increase' else "decreased"
                            stat_suffix = f" ({stat_type})" if stat_type else ""
                            reasons.append(
                                f"ML: {base_display}{stat_suffix} {action} from {baseline:.1f} to {sig_val:.1f} ({delta_pct:+.1f}%)"
                            )
                        else:
                            # Show count format for consistency with multiple anomalies
                            stat_suffix = f" ({stat_type})" if stat_type else ""
                            anomaly_word = "anomaly" if len(details_list) == 1 else "anomalies"
                            reasons.append(f"ML: {base_display}{stat_suffix} ({len(details_list)} {anomaly_word})")
                    else:
                        # Multiple anomalies for same base metric - show count and list statistics
                        # Extract statistic types
                        stat_types = []
                        for detail in details_list:
                            metric_name = detail.get('metric')
                            if metric_name and '_' in metric_name:
                                parts = metric_name.split('_')
                                if parts[-1] in ['median', 'avg', 'p90']:
                                    stat = parts[-1]
                                    if stat == 'p90':
                                        stat = '90th percentile'
                                    stat_types.append(stat)

                        if stat_types:
                            stats_str = '/'.join(stat_types)
                            reasons.append(
                                f"ML: {base_display} ({len(details_list)} anomalies: {stats_str} were affected)"
                            )
                        else:
                            reasons.append(
                                f"ML: {base_display} ({len(details_list)} anomalies detected)"
                            )
            else:
                # Check if ML analysis was performed
                if hasattr(test_obj, 'ml_anomalies') and test_obj.ml_anomalies is not None:
                    ml_status_val = 'PASSED'

        # Determine final status based on severity
        if reasons:
            has_nfr_failures = nfr_status_val == 'FAILED'

            # Find maximum regression percentage
            max_regression_pct = 0
            for reg in baseline_regressions:
                if reg['delta_pct'] > max_regression_pct:
                    max_regression_pct = reg['delta_pct']

            # Determine status
            if has_nfr_failures:
                final_status = "FAILED"
            elif max_regression_pct >= config.baseline_failed_threshold_pct:
                final_status = "FAILED"
            elif max_regression_pct >= config.baseline_warning_threshold_pct:
                final_status = "WARNING"
            else:
                # Has ML anomalies but no critical failures or major regressions
                final_status = "WARNING" if any('ML' in r for r in reasons) else "FAILED"
        else:
            final_status = "PASSED"

        return TransactionStatus(
            transaction=transaction,
            status=final_status,
            reasons=reasons,
            nfr_status=nfr_status_val,
            nfr_failures=nfr_failures,
            baseline_status=baseline_status_val,
            baseline_regressions=baseline_regressions,
            ml_status=ml_status_val,
            ml_events=ml_events
        )

    def build_transaction_status_table(
        self,
        test_obj: BaseTestData,
        config: 'TransactionStatusConfig' = None
    ) -> 'TransactionStatusTable':
        """Build a complete transaction status table from all available data sources.

        Args:
            test_obj: Test data object
            config: Optional configuration for status evaluation

        Returns:
            TransactionStatusTable with status for all transactions
        """
        from app.backend.data_provider.test_data import TransactionStatusTable

        table = TransactionStatusTable()

        # Get all unique transactions
        transactions = self._get_all_transactions(test_obj)

        if not transactions:
            logging.warning("No transactions found for status table")
            return table

        # Evaluate each transaction
        for txn in transactions:
            try:
                status_obj = self._evaluate_transaction_status(
                    transaction=txn,
                    test_obj=test_obj,
                    config=config
                )
                table.add_status(status_obj)
            except Exception as e:
                logging.error(f"Failed to evaluate status for transaction '{txn}': {e}")
                # Add NOT_EVALUATED status for this transaction
                from app.backend.data_provider.test_data import TransactionStatus
                table.add_status(TransactionStatus(
                    transaction=txn,
                    status='NOT_EVALUATED',
                    reasons=[f"Error during evaluation: {str(e)}"]
                ))

        return table
