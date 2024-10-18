import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from abc import ABC, abstractmethod

class AnomalyDetectionEngine:
    def __init__(self, contamination, z_score_threshold, detectors=None):
        self.contamination = contamination
        self.isf_threshold = 0.1
        self.isf_feature_metric = "overalThroughput"
        self.z_score_threshold = z_score_threshold
        self.rolling_window = 5
        self.rolling_correlation_threshold = 0.4
        self.ramp_up_period = None
        self.fixed_load_period = None
        self.output = []
        self.fixed_load_percentage = 60
        self.slope_threshold = 0.015
        self.p_value_threshold = 0.15
        self.anomaly_detectors = detectors if detectors is not None else []

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
        anomaly_started = False
        start_time = None
        end_time = None
        prev_normal_value = None
        post_anomaly_value = None
        anomalies_detected = False
        anomaly_values = []
        buffer_period = 5
        buffer_counter = 0
        current_methods = set()

        for index, row in df.iterrows():
            if 'Anomaly' in str(row[anomaly_cl]) and 'potential saturation point' not in str(row[anomaly_cl]):
                methods = set(row[anomaly_cl].replace('Anomaly: ', '').split(', '))
                current_methods.update(methods)
                if not anomaly_started:
                    anomaly_started = True
                    start_time = index
                    anomalies_detected = True
                    anomaly_values = [row[metric]]
                    if prev_normal_value is None and df.index.get_loc(index) > 0:
                        prev_index = df.index[df.index.get_loc(index) - 1]
                        prev_normal_value = df.at[prev_index, metric]
                else:
                    anomaly_values.append(row[metric])
                end_time = index
                buffer_counter = 0  # Reset buffer counter when an anomaly is found
            else:
                if anomaly_started:
                    buffer_counter += 1
                    if buffer_counter > buffer_period:
                        prev_normal_value = row[metric]
                        self._append_anomaly_result(metric, ', '.join(current_methods), start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values)
                        anomaly_started = False
                        buffer_counter = 0
                        current_methods.clear()
                    else:
                        anomaly_values.append(row[metric])
                else:
                    prev_normal_value = row[metric]

        if anomaly_started:
            self._append_anomaly_result(metric, ', '.join(current_methods), start_time, end_time, prev_normal_value, post_anomaly_value, anomaly_values)

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
        return fixed_load_period, ramp_up_period

    def check_if_fixed_load(self, total_rows, fixed_load_rows):
        fixed_load_percentage = (fixed_load_rows / total_rows) * 100
        return fixed_load_percentage >= self.fixed_load_percentage

class AnomalyDetector(ABC):
    def __init__(self, type):
        self.type = type

    @abstractmethod
    def detect(self, df, metric, engine):
        pass