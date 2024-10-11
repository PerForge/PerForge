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

from app.backend.integrations.influxdb.influxdb import Influxdb
from app.backend.data_provider.data_analysis.anomaly_detection import AnomalyDetectionEngine
from app.backend.data_provider.data_analysis.detectors import IsolationForestDetector, ZScoreDetector, MetricStabilityDetector, RampUpPeriodAnalyzer

import pandas as pd
from collections import defaultdict

class DataProvider:
    def __init__(self, project):
        self.project        = project
        self.influxdb_obj   = Influxdb(project=self.project).connect_to_influxdb()
        # Initialize the AnomalyDetectionEngine
        self.engine = AnomalyDetectionEngine(
            contamination=0.001, 
            z_score_threshold=4,
            detectors=[
                IsolationForestDetector(),
                ZScoreDetector(),
                MetricStabilityDetector(),
                RampUpPeriodAnalyzer(threshold_condition=lambda x: x < self.engine.rolling_correlation_threshold, base_metric="overalUsers")
            ]
        )

    def get_test_log(self):
        """
        Retrieve test log data from the internal database.
        """
        pass

    def get_test_results_and_analyze(self, test_title):
        """
        Retrieve test results from the internal database and perform analysis.
        """
        def process_data(result):
            records = []
            for table in result:
                for record in table.records:
                    records.append((record.get_time(), record.get_value()))

            df = pd.DataFrame(records, columns=['timestamp', 'value'])
            df.set_index('timestamp', inplace=True)
            return df 
        
        def process_data_req(result):
            grouped_records = defaultdict(list)
            
            for table in result:
                for record in table.records:
                    timestamp = record.get_time()
                    value = record.get_value()
                    transaction = record.values.get('transaction', 'default')  # Use 'default' if no transaction
                    
                    grouped_records[transaction].append({
                        'timestamp': timestamp.isoformat(),
                        'value': value,
                        "anomaly": "Normal"
                    })
            
            json_result = []
            for transaction, data in grouped_records.items():
                json_result.append({
                    'name': transaction,
                    'data': data
                })
            
            return json_result
        
        current_start_time      = self.influxdb_obj.get_start_time(test_title)
        current_end_time        = self.influxdb_obj.get_end_time(test_title)

        standart_metrics = {
            "overalThroughput": {
                "func": self.influxdb_obj.get_rps,
                "name": "Throughput",
                "analysis": True
            },
            "overalUsers": {
                "func": self.influxdb_obj.get_active_threads,
                "name": "Users",
                "analysis": False
            },
            "overalAvgResponseTime": {
                "func": self.influxdb_obj.get_response_time,
                "name": "Avg Response Time",
                "analysis": True
            },
            "overalMedianResponseTime": {
                "func": self.influxdb_obj.get_response_time_median,
                "name": "Median Response Time",
                "analysis": True
            },
            "overal90PctResponseTime": {
                "func": self.influxdb_obj.get_response_time_pct,
                "name": "90th Percentile Response Time",
                "analysis": True
            },
            "overalErrors": {
                "func": self.influxdb_obj.get_errors,
                "name": "Errors",
                "analysis": False
            }
        }

        dataframes = {}
        for metric, details in standart_metrics.items():
            func = details["func"]
            result = func(run_id=test_title, start=current_start_time, end=current_end_time)
            df = process_data(result)
            df = df.rename(columns={'value': metric})
            dataframes[metric] = df
        
        merged_df = pd.concat(dataframes.values(), axis=1) 

        # Filter ramp-up and fixed-load periods
        fixed_load_period, ramp_up_period = self.engine.filter_ramp_up_and_down_periods(df=merged_df.copy(), metric="overalUsers")

        # Analyze ramp-up period
        ramp_up_period = self.engine.detect_anomalies(ramp_up_period, metric="overalThroughput", period_type='ramp_up')

        # Check if the test is a fixed load
        if self.engine.check_if_fixed_load(total_rows=len(merged_df), fixed_load_rows=len(fixed_load_period)):
            for metric in standart_metrics:
                if standart_metrics[metric]['analysis']:
                   fixed_load_period = self.engine.detect_anomalies(fixed_load_period, metric=metric, period_type='fixed_load')

        missing_columns = set(fixed_load_period.columns) - set(ramp_up_period.columns)

        # Add missing columns with default value 'Normal'
        for col in missing_columns:
            ramp_up_period[col] = 'Normal'

        # Merge the DataFrames
        merged_df = pd.concat([ramp_up_period, fixed_load_period], axis=0)
        # Initialize the result dictionary
        result = {}

        # Iterate over each column in the DataFrame
        for col in merged_df.columns:
            if '_anomaly' not in col:
                # Get the anomaly column name
                anomaly_col = col + '_anomaly'
                
                # Create the dictionary for the current column
                result[col] = {
                    'name': standart_metrics[col]['name'],
                    'data': []
                }
                
                # Populate the data list with timestamp, value, and anomaly
                for timestamp, row in merged_df.iterrows():
                    anomaly_value = row[anomaly_col] if anomaly_col in row and pd.notna(row[anomaly_col])  else 'Normal'
                    value = row[col] if pd.notna(row[col]) else 0.0
                    result[col]['data'].append({
                        'timestamp': timestamp.isoformat(),
                        'value': value,
                        'anomaly': anomaly_value
                    })

        avgResponseTimePerReq = self.influxdb_obj.get_response_time_per_req(run_id=test_title, start=current_start_time, end=current_end_time)
        avgResponseTimePerReq_data = process_data_req(avgResponseTimePerReq)

        result["avgResponseTimePerReq"] = avgResponseTimePerReq_data

        medianRespTimePerReq = self.influxdb_obj.get_response_time_per_req_median(run_id=test_title, start=current_start_time, end=current_end_time)
        medianRespTimePerReq_data = process_data_req(medianRespTimePerReq)

        result["medianResponseTimePerReq"] = medianRespTimePerReq_data

        pctRespTimePerReq = self.influxdb_obj.get_response_time_per_req_pct(run_id=test_title, start=current_start_time, end=current_end_time)
        pctRespTimePerReq_data = process_data_req(pctRespTimePerReq)

        result["pctResponseTimePerReq"] = pctRespTimePerReq_data

        self.engine.process_anomalies(merged_df)
        
        # Output the analysis results
        analysis_output = self.engine.output

        aggregated_results = self.get_aggregated_metrics()

        test_details = self.get_test_details()

        statistics = self.influxdb_obj.get_aggregated_table(run_id=test_title, start=current_start_time, end=current_end_time)

        prompt = f''''''
        llm_response = ""

        return result, analysis_output, aggregated_results, test_details, statistics, llm_response

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

    def get_aggregated_metrics(self):
        """
        Retrieve aggregated metrics from the internal database.
        """
        aggregated_results = {
            "vu": 100,
            "throughput": 75.5,
            "median": 1.25,
            "90pct": 3.67,
            "errors": 13
        }
        return aggregated_results
    
    def get_test_details(self):
        """
        Retrieve test details from the internal database.
        """
        test_details = {
            "start_time": "30. 9. 2024, 10:26:39",
            "end_time": "30. 9. 2024, 11:26:28",
            "duration": "59.8 min"
        }
        return test_details

    def get_dynamic_metric_by_name(self, metric_name):
        """
        Retrieve a dynamic metric by its name from the internal database.
        
        :param metric_name: The name of the dynamic metric to retrieve.
        """
        pass

    def get_available_dynamic_metrics(self):
        """
        Retrieve a list of available dynamic metrics from the internal database.
        """
        pass

    def check_internal_data_up_to_date(self):
        """
        Check if the internal data is up to date.
        """
        pass

    def trigger_external_data_check(self):
        """
        Trigger a check to see if there is any data from external data sources.
        """
        pass