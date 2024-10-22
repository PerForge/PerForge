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
from app.backend.data_provider.data_analysis.detectors import IsolationForestDetector, ZScoreDetector, MetricStabilityDetector, RampUpPeriodAnalyzer

import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any

class DataProvider:
    
    class_map = {
        "influxdb_v2": InfluxdbV2
    }
    
    def __init__(self, project, id = None):
        self.project = project
        self.ds_obj  = self.class_map.get("influxdb_v2", None)(project=self.project, id=id) #"influxdb_v2" should be passed dynamically
        # Initialize the AnomalyDetectionEngine
        self.start_time_human     = None
        self.end_time_human       = None
        self.start_time_iso       = None
        self.end_time_iso         = None
        self.start_time_timestamp = None
        self.end_time_timestamp   = None
        self.test_name            = None
        self.duration             = None
        self.max_active_users     = None
        self.median_throughput    = None
        self.median_response_time_stats = None
        self.pct90_response_time_stats  = None
        self.errors_pct_stats     = None

    def get_test_log(self):
        """
        Retrieve test log data from the database.
        """
        result = self.ds_obj.get_test_log()
        return result

    def get_response_time_data(self):
        """
        Retrieve response time data from the internal database.
        """
        pass

    def get_throughput_data(self):
        """
        Retrieve throughput data from the internal database.
        """
        pass

    def get_vusers_data(self):
        """
        Retrieve virtual users (vusers) data from the internal database.
        """
        pass

    def get_errors_data(self):
        """
        Retrieve errors data from the internal database.
        """
        pass
    
    def collect_test_data(self, test_title: str):
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
            
    def get_aggregated_metrics(self, test_title: str):
        """
        Retrieve aggregated metrics from the internal database.
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
    
    def get_test_details(self, test_title: str):
        """
        Retrieve test details from the internal database.
        """
        self.collect_test_data(test_title=test_title)
        
        test_details = {
            "start_time": self.start_time_human,
            "end_time": self.end_time_human,
            "duration": self.duration
        }
        return test_details
     
    def transform_to_json(self, result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform the output of get_average_response_time_per_req to a JSON format.
        :param result: List of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        :return: JSON-friendly list of dictionaries.
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
    
    def fetch_metric(self, metric: str, func, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch a specific metric using the provided function and rename the value column.
        :param metric: The metric name to be used for renaming the value column.
        :param func: The function to fetch the data.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A DataFrame with the renamed value column.
        """
        result = func(test_title=test_title, start=start, end=end)
        return result.rename(columns={'value': metric})

    def initialize_metrics(self):
        """
        Initialize and return the standard metrics configuration.
        :return: A dictionary containing the standard metrics configuration.
        """
        return {
            "overalThroughput": {"func": self.ds_obj.get_rps, "name": "Throughput", "analysis": True},
            "overalUsers": {"func": self.ds_obj.get_active_threads, "name": "Users", "analysis": False},
            "overalAvgResponseTime": {"func": self.ds_obj.get_average_response_time, "name": "Avg Response Time", "analysis": True},
            "overalMedianResponseTime": {"func": self.ds_obj.get_median_response_time, "name": "Median Response Time", "analysis": True},
            "overal90PctResponseTime": {"func": self.ds_obj.get_pct90_response_time, "name": "90th Percentile Response Time", "analysis": True},
            "overalErrors": {"func": self.ds_obj.get_error_count, "name": "Errors", "analysis": False}
        }

    def merge_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge multiple DataFrames into a single DataFrame sorted by index.
        :param dataframes: A dictionary of DataFrames to merge.
        :return: A merged DataFrame sorted by index.
        """
        merged_df = pd.concat(dataframes.values(), axis=1)
        return merged_df.sort_index()

    def analyze_data_periods(self, merged_df: pd.DataFrame, test_title: str, start: str, end: str):
        """
        Analyze the ramp-up and fixed-load periods in the data.
        :param merged_df: The merged DataFrame containing the data.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The ramp-up period, fixed-load period, and a boolean indicating if the test is a fixed load.
        """
        fixed_load_period, ramp_up_period = self.engine.filter_ramp_up_and_down_periods(df=merged_df.copy(), metric="overalUsers")

        ramp_up_period = self.engine.detect_anomalies(ramp_up_period, metric="overalThroughput", period_type='ramp_up')

        is_fixed_load = self.engine.check_if_fixed_load(total_rows=len(merged_df), fixed_load_rows=len(fixed_load_period))
        if is_fixed_load:
            for metric in self.initialize_metrics():
                if self.initialize_metrics()[metric]['analysis']:
                    fixed_load_period = self.engine.detect_anomalies(fixed_load_period, metric=metric, period_type='fixed_load')

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
    
    # def generate_summary(self):
        
    
    def get_test_results_and_analyze(self, test_title: str):
        """
        Retrieve test results from the internal database and perform analysis.
        :param test_title: The title of the test.
        :return: A tuple containing the result, analysis output, aggregated results, test details, statistics, and llm_response.
        """
        self.engine  = AnomalyDetectionEngine(
            {},
            detectors=[
                IsolationForestDetector(),
                ZScoreDetector(),
                MetricStabilityDetector(),
                RampUpPeriodAnalyzer(threshold_condition=lambda x: x < self.engine.rolling_correlation_threshold, base_metric="overalUsers")
            ]
        )
        
        current_start_time = self.ds_obj.get_start_time(test_title=test_title, time_format='iso')
        current_end_time = self.ds_obj.get_end_time(test_title=test_title, time_format='iso')

        standart_metrics = self.initialize_metrics()

        # Fetch and merge the data for all standard metrics
        dataframes = {metric: self.fetch_metric(metric, details["func"], test_title, current_start_time, current_end_time) for metric, details in standart_metrics.items()}
        merged_df = self.merge_dataframes(dataframes)
        
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
        summary = ""
        return result, analysis_output, aggregated_results, test_details, statistics, summary