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

# THIS IS DEMO CODE!!!
from app.backend.integrations.influxdb.influxdb       import Influxdb
from app.backend.analysis.stats_ml_analysis           import PerformanceAnalysis

import pandas as pd

class DataPreparation():
    def __init__(self, project):
        self.project        = project
        self.influxdb_obj   = Influxdb(project=self.project).connect_to_influxdb()
        self.analysis       = ""
    
    def process_data(self, result):
        """Process the data fetched from InfluxDB into a DataFrame."""
        records = []
        for table in result:
            for record in table.records:
                records.append((record.get_time(), record.get_value()))

        df = pd.DataFrame(records, columns=['timestamp', 'value'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def merge_data(self, throughput_df, users_df, rt_df):
        """Merge throughput data with concurrent users data and an additional DataFrame."""
        # Merge throughput_df and users_df
        df = pd.merge(throughput_df, users_df, left_index=True, right_index=True, suffixes=('_throughput', '_users'))
        # Rename columns in rt_df to avoid conflicts
        rt_df_renamed = rt_df.add_suffix('_rt')
        # Merge the result with rt_df_renamed
        df = pd.merge(df, rt_df_renamed, left_index=True, right_index=True)
        return df
    
    def get_test_data(self, test_title):
        current_start_time      = self.influxdb_obj.get_start_time(test_title)
        current_end_time        = self.influxdb_obj.get_end_time(test_title)
        
        result_throughput       = self.influxdb_obj.get_rps(run_id=test_title, start=current_start_time, end=current_end_time)
        throughput_df           = self.process_data(result_throughput)

        result_users            = self.influxdb_obj.get_active_threads(run_id=test_title, start=current_start_time, end=current_end_time)
        users_df                = self.process_data(result_users)

        result_rt               = self.influxdb_obj.get_response_time(run_id=test_title, start=current_start_time, end=current_end_time)
        rt_df                   = self.process_data(result_rt)

        df = self.merge_data(throughput_df, users_df, rt_df)

        df = df.rename(columns={'value_throughput': 'throughput',
                                    'value_users': 'users',
                                    'value_rt': 'rt'})
        
        # Initialize the PerformanceAnalysis class
        analysis = PerformanceAnalysis(
                contamination=0.01, 
                z_score_threshold=4,
                throughput_metric="throughput",
                users_metric="users",
                rt_metric="rt"
                )
        
         # Perform analysis
        fixed_load_period, ramp_up_period = analysis.filter_ramp_up_and_down_periods(df=df.copy())
        # Analyze ramp-up period
        ramp_up_period = analysis.analyze_ramp_up(df=ramp_up_period)
        if analysis.check_if_fixed_load(total_rows=len(df), fixed_load_rows=len(fixed_load_period)):
            for column in df.columns:
                fixed_load_period = analysis.detect_anomalies_isolation_forest(df = fixed_load_period, metric=column)
                fixed_load_period = analysis.detect_anomalies_z_score(df = fixed_load_period, metric=column)
                analysis.is_metric_stable(df = fixed_load_period.copy(), metric=column)
        
        for col in ['throughput_anomaly', 'users_anomaly', 'rt_anomaly']:
            if col not in ramp_up_period.columns:
                ramp_up_period[col] = 'Normal'
            if col not in fixed_load_period.columns:
                fixed_load_period[col] = 'Normal'

        # Combine the DataFrames
        combined_df = pd.concat([ramp_up_period, fixed_load_period], axis=0)
        self.analysis = analysis.output
        return combined_df