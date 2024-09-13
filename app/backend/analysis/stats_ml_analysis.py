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

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import ruptures as rpt
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression


class PerformanceAnalysis:
    def __init__(self, contamination, z_score_threshold, throughput_metric, users_metric, rt_metric):
        self.contamination = contamination
        self.z_score_threshold = z_score_threshold
        self.rolling_window = 5
        self.rolling_correlation_threshold = 0.5
        self.ramp_up_period = None
        self.fixed_load_period = None
        self.output = []
        self.throughput_metric = throughput_metric
        self.users_metric = users_metric
        self.rt_metric = rt_metric
        self.fixed_load_percentage = 60
        self.slope_threshold = 0.015  # Adjusted threshold for the slope to be more sensitive
        self.p_value_threshold = 0.15  # Adjusted significance level for ADF test

    def add_rolling_features(self, df, metric, is_mean=True, is_std=True):
        """Add rolling mean and rolling standard deviation as features."""
        if is_mean:
            df[f'{metric}_rolling_mean'] = df[metric].rolling(window=self.rolling_window).mean()
        if is_std:
            df[f'{metric}_rolling_std'] = df[metric].rolling(window=self.rolling_window).std()
        return df

    def normalize_columns(self, df, columns):
        """Normalize specified columns in the DataFrame."""
        scaler = MinMaxScaler()
        df[columns] = scaler.fit_transform(df[columns])
        return df

    def delete_columns(self, df, columns):
        """Delete specified columns from the DataFrame."""
        df.drop(columns=columns, inplace=True)
        return df

    def collect_anomalies(self, df, metric, anomaly_cl, period, method):
        """Collect anomalies for further analysis."""
        anomaly_started = False
        start_time = None
        end_time = None
        prev_normal_value = None
        post_anomaly_value = None
        anomalies_detected = False
        anomaly_values = []  # To track values within an anomaly sequence

        for index, row in df.iterrows():
            if 'Anomaly' in row[anomaly_cl]:
                if not anomaly_started:  # Start of an anomaly sequence
                    anomaly_started = True
                    start_time = index  # Use index as timestamp
                    anomalies_detected = True
                    anomaly_values = [row[metric]]  # Initialize with the first anomaly value
                    if prev_normal_value is None and df.index.get_loc(index) > 0:  # Handle anomaly at the start
                        prev_index = df.index[df.index.get_loc(index) - 1]
                        prev_normal_value = df.at[prev_index, metric]
                else:
                    anomaly_values.append(row[metric])  # Add value to the list
                end_time = index  # Use index as timestamp
            else:
                if anomaly_started:  # End of an anomaly sequence
                    self._append_anomaly_result(df, metric, period, method, start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values)
                    anomaly_started = False
                    prev_normal_value = row[metric]  # Reset for the next sequence
                else:
                    prev_normal_value = row[metric]  # Update the last normal value before anomaly

        # Handle anomaly at the end
        if anomaly_started:
            self._append_anomaly_result(df, metric, period, method, start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values)

        if not anomalies_detected:
            self.output.append({
                'status': 'passed',
                'method': method,
                'description': f'No anomalies detected in {metric}',
                'value': None
            })

    def _append_anomaly_result(self, df, metric, period, method, start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values):
        """Helper function to append anomaly results to the output."""
        mean_value = np.mean([val for val in [prev_normal_value, post_anomaly_value] if val is not None])
        description = f"An anomaly was detected in {metric} from {start_time} to {end_time}, with the metric "
        if mean_value < np.max(anomaly_values):
            description += f"increasing to {np.max(anomaly_values):.6f}."
        else:
            description += f"dropping to {np.min(anomaly_values):.6f}."
        self.output.append({
            'status': 'failed',
            'method': method,
            'description': description,
            'value': np.max(anomaly_values) if mean_value < np.max(anomaly_values) else np.min(anomaly_values)
        })

    def update_anomaly_status(self, df, metric, anomaly_metric, method):
        """Update the anomaly status in the DataFrame."""
        anomaly_col = f'{metric}_anomaly'
        anomaly_method_col = anomaly_metric
        df = df.copy()

        # Check if anomaly_col exists, if not, create it with empty strings
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

    def detect_anomalies_isolation_forest(self, df, metric):
        """Detect anomalies in the data using Isolation Forest."""
        df = df.copy()
        df_with_features = self.add_rolling_features(df=df.copy(), metric=metric, is_mean=True, is_std=True)

        # Separate rows with missing values
        missing_rows = df_with_features[df_with_features.isna().any(axis=1)]
        non_missing_rows = df_with_features.dropna()

        if not non_missing_rows.empty:
            iso_forest = IsolationForest(contamination=self.contamination, random_state=42)
            non_missing_rows.loc[:, f'{metric}_anomaly_isf'] = iso_forest.fit_predict(non_missing_rows[[metric, f'{metric}_rolling_mean', f'{metric}_rolling_std']])
            non_missing_rows = self.update_anomaly_status(df=non_missing_rows, metric=metric, anomaly_metric=f'{metric}_anomaly_isf', method='isf')

        # Combine the non-missing rows with the original DataFrame
        combined_df = pd.concat([non_missing_rows, missing_rows], axis=0).sort_index()

        # Fill NaN values in the anomaly column with 'Normal'
        combined_df.loc[:, f'{metric}_anomaly'].fillna('Normal', inplace=True)

        # Delete rolling feature columns from the combined DataFrame
        self.delete_columns(df=combined_df, columns=[f'{metric}_anomaly_isf', f'{metric}_rolling_mean', f'{metric}_rolling_std'])

        self.collect_anomalies(df=combined_df, metric=metric, anomaly_cl=f'{metric}_anomaly', period="fixed-load", method="isolation_forest")
        return combined_df

    def detect_anomalies_z_score(self, df, metric):
        """Detect anomalies in the data using Z-score."""
        df = df.copy()
        df[f'{metric}_z_score'] = (df[metric] - df[metric].mean()) / df[metric].std()
        df[f'{metric}_anomaly_z_score'] = df[f'{metric}_z_score'].apply(lambda x: -1 if abs(x) > self.z_score_threshold else 1)
        df = self.update_anomaly_status(df=df, metric=metric, anomaly_metric=f'{metric}_anomaly_z_score', method='z_score')
        self.delete_columns(df=df, columns=[f'{metric}_anomaly_z_score', f'{metric}_z_score'])
        self.collect_anomalies(df=df, metric=metric, anomaly_cl=f'{metric}_anomaly', period="fixed-load", method="z_score")
        return df

    def is_metric_stable(self, df, metric):
        """Check if the metric is stable using linear regression and ADF test."""
        # Ensure the DataFrame index is a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")

        # Convert the datetime index to seconds since the start of the time series
        df['time_seconds'] = (df.index - df.index[0]).total_seconds()

        # Fit a linear regression model to the metric
        X = df['time_seconds'].values.reshape(-1, 1)  # Ensure X is 2-dimensional
        y = df[metric].values
        model = LinearRegression().fit(X, y)

        # Evaluate the slope of the trend line
        slope = model.coef_[0]

        # Check if the metric data has sufficient variance
        if np.var(y) < 1e-6:  # Adjust the threshold as needed
            self.output.append({
                'status': 'passed',
                'method': 'LinearRegression',
                'description': f'{metric} was stable during the test (constant data).',
                'value': None
            })
            return

        # Perform the Augmented Dickey-Fuller (ADF) test
        result = adfuller(df[metric])
        p_value = result[1]

        # Detect change points
        algo = rpt.Binseg(model="l2").fit(y)

        if abs(slope) < self.slope_threshold and p_value < self.p_value_threshold:
            self.output.append({
                'status': 'passed',
                'method': 'LinearRegression',
                'description': f'{metric} was stable during the test.',
                'value': slope
            })
        elif slope > self.slope_threshold:
            self.output.append({
                'status': 'failed',
                'method': 'LinearRegression',
                'description': f'{metric} was not stable during the test (potential increase).',
                'value': slope
            })
        else:
            self.output.append({
                'status': 'failed',
                'method': 'LinearRegression',
                'description': f'{metric} was not stable during the test (potential degradation).',
                'value': slope
            })

    def filter_ramp_up_and_down_periods(self, df):
        """Filter out the ramp-up and ramp-down periods where the number of users is changing."""
        df['is_ramp_up_down'] = df[self.users_metric].diff().fillna(0).apply(
            lambda x: 'Ramp-up' if x > 0 else ('Ramp-down' if x < 0 else 'Stable')
        )
        # Set the first data point to 'Ramp-up' by default
        df.iloc[0, df.columns.get_loc('is_ramp_up_down')] = 'Ramp-up'
        fixed_load_period = df[df['is_ramp_up_down'] == 'Stable']
        fixed_load_period = self.delete_columns(df=fixed_load_period.copy(), columns=["is_ramp_up_down"])
        ramp_up_period = df[df['is_ramp_up_down'] == 'Ramp-up']
        ramp_up_period = self.delete_columns(df=ramp_up_period.copy(), columns=["is_ramp_up_down"])
        return fixed_load_period, ramp_up_period

    def check_if_fixed_load(self, total_rows, fixed_load_rows):
        """Determine if the test type is 'fixed load' or 'ramp-up'."""
        # Calculate the percentage of rows that belong to the fixed load period
        fixed_load_percentage = (fixed_load_rows / total_rows) * 100

        # Determine the test type based on the 80% threshold
        return fixed_load_percentage >= self.fixed_load_percentage

    def analyze_ramp_up_period(self, df, value_column, threshold_condition):
        """Analyze the ramp-up period for correlation between a given value and users."""
        df = df.copy()

        # Ensure the anomaly column exists with default value 'Normal'
        anomaly_col = f'{value_column}_anomaly'
        if anomaly_col not in df.columns:
            df[anomaly_col] = 'Normal'

        if df is not None:
            # Calculate rolling correlation
            df['rolling_correlation'] = df[value_column].rolling(window=self.rolling_window).apply(
                lambda x: x.corr(df[self.users_metric])
            )

            # Identify tipping points where rolling correlation meets the threshold condition at least 5 times in a sequence
            tipping_point = False
            count = 0
            tipping_point_rt = None
            tipping_point_index = None

            for i in range(len(df)):
                if threshold_condition(df['rolling_correlation'].iloc[i]):
                    count += 1
                    if count == 1 and i > 0:
                        # Save the throughput value before the first occurrence in the sequence
                        tipping_point_rt = df.iloc[i - 1]
                        tipping_point_index = df.index[i - 1]
                    if count >= 5:
                        tipping_point = True
                        break
                else:
                    count = 0
                    tipping_point_rt = None
                    tipping_point_index = None

            # Check if there are any tipping points
            if tipping_point:
                self.output.append({
                    'status': 'failed',
                    'method': 'rolling_correlation',
                    'description': f"Tipping point was reached at load of {str(tipping_point_rt[value_column])} requests per second according to throughput analysis.",
                    'value': tipping_point_rt[value_column]
                })
                # Update the anomaly column
                df.loc[tipping_point_index, anomaly_col] = 'Anomaly: potential saturation point'
            else:
                self.output.append({
                    'status': 'passed',
                    'method': 'rolling_correlation',
                    'description': 'Users ramped up successfully.',
                    'value': None
                })

        df = self.delete_columns(df=df.copy(), columns=['rolling_correlation'])
        return df

    def analyze_ramp_up_period_tr(self, df):
        """Analyze the ramp-up period for throughput."""
        return self.analyze_ramp_up_period(df, self.throughput_metric, lambda x: x < self.rolling_correlation_threshold)

    def analyze_ramp_up_period_rt(self, df):
        """Analyze the ramp-up period for response time."""
        return self.analyze_ramp_up_period(df, self.rt_metric, lambda x: x > self.rolling_correlation_threshold)

    def analyze_ramp_up(self, df):
        """Analyze the ramp-up period for both throughput and response time."""
        new_df = self.analyze_ramp_up_period_tr(df=df)
        return new_df