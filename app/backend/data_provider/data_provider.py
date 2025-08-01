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

# Third-party imports
import pandas as pd
from datetime import datetime
from dateutil import tz
from cachetools import TTLCache, cached

# Local application imports
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.data_provider.data_analysis.anomaly_detection import AnomalyDetectionEngine
from app.backend.integrations.data_sources.base_extraction import DataExtractionBase
from app.backend.data_provider.test_data import BaseTestData, BackendTestData, FrontendTestData, MetricsTable, TestDataFactory

class DataProvider:
    _titles_cache = TTLCache(maxsize=1000, ttl=60)
    """
    DataProvider class manages data extraction, transformation, and analysis for performance tests.

    This class serves as a central hub for handling performance test data, providing:
    - Data extraction from various sources (InfluxDB, TimeScaleDB)
    - Data transformation and preprocessing
    - Performance metrics calculation and aggregation
    - Support for both backend and frontend test types
    """

    class_map: Dict[str, Type[DataExtractionBase]] = {
        "influxdb_v2": InfluxdbV2
        # Add more data sources as needed
    }

    # Map data source types to test types
    source_to_test_type_map: Dict[str, str] = {
        "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient": "back_end",
        "sitespeed_influxdb_v2": "front_end",
    }

    def __init__(self, project: Any, source_type: Any, id: Optional[str] = None) -> None:
        """
        Initialize DataProvider with project settings and data source configuration.

        Args:
            project: Project configuration object with settings
            source_type: Data source type identifier (e.g., "influxdb_v2", "timescaledb")
            id: Optional identifier for specific data source instance
        """
        self.project = project
        self.source_type = source_type
        self.ds_obj = self.class_map.get(source_type, None)(project=self.project, id=id)

        # Determine the test type based on the source type
        self.test_type = self.source_to_test_type_map.get(self.ds_obj.listener, "back_end")

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
    def get_test_log(self, limit: int | None = None, offset: int | None = None, sort_by: str | None = None, sort_dir: str = 'asc'):
        """Return tests list.

        If *limit* and/or *offset* are provided and the underlying data-source
        supports them, they will be forwarded to reduce the amount of data
        transferred. Otherwise the full list will be requested and sliced
        in-memory as a graceful fallback.
        """
        return self.ds_obj.get_test_log(limit=limit, offset=offset or 0, sort_by=sort_by, sort_dir=sort_dir)

    @cached(_titles_cache)
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
        Selectively remove rows containing NaN values and raise exceptions for problematic data.

        Args:
            df: The DataFrame to process

        Returns:
            A DataFrame with NaN rows removed

        Raises:
            ValueError: If all columns are completely NaN or if some metrics are missing
        """
        # Check if the DataFrame is empty
        if df.empty:
            raise ValueError("DataFrame is empty - no metrics data available")

        # Check if any columns are completely NaN
        all_nan_columns = df.columns[df.isna().all()].tolist()

        # If all columns are NaN, raise an exception
        if len(all_nan_columns) == len(df.columns):
            raise ValueError(f"All metrics data is missing: {', '.join(all_nan_columns)}")

        # If some columns are completely NaN, log a warning but continue with remaining columns
        if all_nan_columns:
            # Raise an exception with information about which metrics are missing
            raise ValueError(f"Some metrics data is completely missing: {', '.join(all_nan_columns)}")

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
            return

        merged_df, standard_metrics = self._get_test_results(test_obj=test_obj)

        # Initialize engine with detectors
        self.anomaly_detection_engine = AnomalyDetectionEngine(
            params={}  # You can pass custom parameters here
        )

        # Analyze the data periods
        metrics, is_fixed_load, analysis_output = self.anomaly_detection_engine.analyze_test_data(merged_df=merged_df, standard_metrics=standard_metrics)

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

        # Fetch additional response time per request data
        avgResponseTimePerReq = self.ds_obj.get_average_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["avgResponseTimePerReq"] = self.transform_to_json(avgResponseTimePerReq)

        medianRespTimePerReq = self.ds_obj.get_median_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["medianResponseTimePerReq"] = self.transform_to_json(medianRespTimePerReq)

        pctRespTimePerReq = self.ds_obj.get_pct90_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["pctResponseTimePerReq"] = self.transform_to_json(pctRespTimePerReq)

        # Collect the aggregated table data
        metrics_table: MetricsTable = test_obj.get_table('aggregated_data')
        if metrics_table:
            test_obj.aggregated_table = metrics_table.format_metrics()

        # Collect the outputs
        statistics = self.get_statistics(test_title=test_title, test_obj=test_obj)
        test_details = self.get_test_details(test_title=test_title, test_obj=test_obj)
        return metrics, test_obj.ml_anomalies, statistics, test_details, test_obj.aggregated_table, test_obj.ml_html_summary, test_obj.performance_status
