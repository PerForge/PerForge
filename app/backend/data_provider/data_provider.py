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
from app.backend.integrations.data_sources.base_extraction import DataExtractionBase
from app.backend.integrations.data_sources.timescaledb.timescaledb_extraction import TimeScaleDB
from app.backend.data_provider.test import Test

import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional, Type

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

    class_map: Dict[str, Type[DataExtractionBase]] = {
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

    # Basic data retrieval methods
    def get_test_log(self) -> Dict[str, Any]:
        """Retrieve test log data from the database."""
        return self.ds_obj.get_test_log()
    
    def get_aggregated_table(self, test_title: str, start_time: str, end_time: str):
        return self.ds_obj.get_aggregated_table(test_title, start_time, end_time)

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
    def collect_test_obj(self, test_title: str) -> None:
        """
        Collect and cache all test-related data.

        Args:
            test_title: The title/name of the test to collect data for
        """
        test_obj = Test()
        
        if not test_obj.test_title:
            test_obj.test_title = test_title      
        if not test_obj.start_time_human:
            test_obj.start_time_human = self.ds_obj.get_start_time(test_title=test_title, time_format='human')
        if not test_obj.end_time_human:
            test_obj.end_time_human = self.ds_obj.get_end_time(test_title=test_title, time_format='human')
        if not test_obj.start_time_iso:
            test_obj.start_time_iso = self.ds_obj.get_start_time(test_title=test_title, time_format='iso')
        if not test_obj.end_time_iso:
            test_obj.end_time_iso = self.ds_obj.get_end_time(test_title=test_title, time_format='iso')
        if not test_obj.start_time_timestamp:
            test_obj.start_time_timestamp = self.ds_obj.get_start_time(test_title=test_title, time_format='timestamp')
        if not test_obj.end_time_timestamp:
            test_obj.end_time_timestamp = self.ds_obj.get_end_time(test_title=test_title, time_format='timestamp')
        if not test_obj.application:
            test_obj.application = self.ds_obj.get_application(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        if not test_obj.duration:
            test_obj.calculate_duration()
        if not test_obj.max_active_users:
            test_obj.max_active_users = self.ds_obj.get_max_active_users_stats(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        if not test_obj.median_throughput:
            test_obj.median_throughput = self.ds_obj.get_median_throughput_stats(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        if not test_obj.median_response_time_stats:
            test_obj.median_response_time_stats = self.ds_obj.get_median_response_time_stats(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        if not test_obj.pct90_response_time_stats:
            test_obj.pct90_response_time_stats = self.ds_obj.get_pct90_response_time_stats(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        if not test_obj.errors_pct_stats:
            test_obj.errors_pct_stats = self.ds_obj.get_errors_pct_stats(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
            
        return test_obj

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

    def get_statistics(self, test_title: str, test_obj: Test = None) -> Dict[str, Any]:
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
            test_obj: Test = self.collect_test_obj(test_title=test_title)

        aggregated_results = {
            "vu": test_obj.max_active_users,
            "throughput": test_obj.median_throughput,
            "median": test_obj.median_response_time_stats,
            "90pct": test_obj.pct90_response_time_stats,
            "errors": f'{str(test_obj.errors_pct_stats)}%'
        }
        return aggregated_results

    def get_test_details(self, test_title: str, test_obj: Test = None ) -> Dict[str, str]:
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
            test_obj: Test = self.collect_test_obj(test_title=test_title)

        test_details = {
            "start_time": test_obj.start_time_human,
            "end_time": test_obj.end_time_human,
            "duration": test_obj.duration
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
        test_obj: Test = self.collect_test_obj(test_title=test_title)

        # Initialize engine with detectors
        self.anomaly_detection_engine = AnomalyDetectionEngine(
            params={}  # You can pass custom parameters here
        )

        standard_metrics = self.initialize_metrics()

        # Fetch and merge the data for all standard metrics
        dataframes = {metric: self.fetch_metric(metric, details["func"], test_title, test_obj.start_time_iso, test_obj.end_time_iso) for metric, details in standard_metrics.items()}

        # NaN values to 0
        dataframes = {metric: self.df_nan_to_zero(df) for metric, df in dataframes.items()}

        merged_df = self.merge_dataframes(dataframes)

        merged_df = self.df_delete_nan_rows(merged_df)

        # Analyze the data periods
        metrics, summary, performance_status, is_fixed_load = self.anomaly_detection_engine.analyze_test_data(merged_df=merged_df, standard_metrics=standard_metrics)
        
        if is_fixed_load:
            test_obj.test_type = "fixed load"
        else:
            test_obj.test_type = "ramp up"

        # Fetch additional response time per request data
        avgResponseTimePerReq = self.ds_obj.get_average_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["avgResponseTimePerReq"] = self.transform_to_json(avgResponseTimePerReq)

        medianRespTimePerReq = self.ds_obj.get_median_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["medianResponseTimePerReq"] = self.transform_to_json(medianRespTimePerReq)

        pctRespTimePerReq = self.ds_obj.get_pct90_response_time_per_req(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        metrics["pctResponseTimePerReq"] = self.transform_to_json(pctRespTimePerReq)
        
        # Collect the outputs
        analysis_output = self.anomaly_detection_engine.output
        statistics = self.get_statistics(test_title=test_title, test_obj=test_obj)
        test_details = self.get_test_details(test_title=test_title, test_obj=test_obj)
        aggregated_table = self.ds_obj.get_aggregated_table(test_title=test_title, start=test_obj.start_time_iso, end=test_obj.end_time_iso)
        return metrics, analysis_output, statistics, test_details, aggregated_table, summary, performance_status