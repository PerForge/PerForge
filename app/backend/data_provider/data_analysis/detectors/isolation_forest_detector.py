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

from .base import BaseDetector
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Literal

class IsolationForestDetector(BaseDetector):
    """
    Anomaly detection using Isolation Forest algorithm.
    Capable of detecting anomalies in both fixed load and ramp up test scenarios.
    """
    def __init__(self):
        # Initialize detector type and name
        self._type = 'fixed_load'
        self._name = 'Isolation Forest'

    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type

    @property
    def name(self) -> str:
        return self._name

    def _validate_anomalies(self, df: pd.DataFrame, metric: str, anomaly_column: str, threshold: float = 0.1) -> pd.DataFrame:
        """
        Validate anomalies using median-based threshold approach.

        Args:
            df (pd.DataFrame): DataFrame containing the data
            metric (str): Name of the metric being analyzed
            anomaly_column (str): Name of the column containing anomaly flags
            threshold (float): Threshold for relative deviation from median (default: 0.2 or 20%)

        Returns:
            pd.DataFrame: DataFrame with validated anomaly flags
        """
        df = df.copy()
        median_value = df[metric].median()

        for idx in df.index:
            if df.at[idx, anomaly_column] == -1:
                current_value = df.at[idx, metric]
                deviation = abs(current_value - median_value) / median_value

                # If deviation is less than threshold, mark as normal
                if deviation < threshold:
                    df.at[idx, anomaly_column] = 1

        return df

    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        """
        Detect anomalies in time series data using Isolation Forest.

        Args:
            df (pd.DataFrame): Input dataframe containing time series data
            metric (str): Name of the primary metric to analyze
            engine: Analysis engine instance providing configuration and utility methods

        Returns:
            pd.DataFrame: DataFrame with added anomaly detection results
        """
        df = df.copy()

        # Determine which features are actually available in the DataFrame
        candidate_features = [metric]
        if engine.isf_feature_metric != metric:
            candidate_features.append(engine.isf_feature_metric)
        available_features = [f for f in candidate_features if f in df.columns]

        # If no expected features are available, return with default 'Normal' anomaly column
        if not available_features:
            result = df.copy()
            result[f'{metric}_anomaly'] = 'Normal'
            return result

        # Separate rows: keep only rows that have no NaNs in the used features
        non_missing_rows = df.dropna(subset=available_features).copy()
        missing_rows = df[~df.index.isin(non_missing_rows.index)].copy()

        if not non_missing_rows.empty and (metric in non_missing_rows.columns):
            # Prepare and normalize features for Isolation Forest
            scaler = StandardScaler()
            normalized_features = scaler.fit_transform(non_missing_rows[available_features])

            # Train Isolation Forest and get anomaly scores
            iso_forest = IsolationForest(contamination=engine.contamination, random_state=42)
            iso_forest.fit(normalized_features)
            anomaly_scores = iso_forest.decision_function(normalized_features)

            # Convert scores to binary labels (-1: anomaly, 1: normal)
            non_missing_rows.loc[:, f'{metric}_anomaly_isf'] = np.where(anomaly_scores < engine.isf_threshold, -1, 1)

            # Validate anomalies only if primary metric exists
            non_missing_rows = self._validate_anomalies(
                df=non_missing_rows,
                metric=metric,
                anomaly_column=f'{metric}_anomaly_isf'
            )

            # Ensure endpoints are marked as normal points
            non_missing_rows.iloc[0, non_missing_rows.columns.get_loc(f'{metric}_anomaly_isf')] = 1
            non_missing_rows.iloc[-1, non_missing_rows.columns.get_loc(f'{metric}_anomaly_isf')] = 1

            # Update anomaly status based on detection results
            non_missing_rows = engine.update_anomaly_status(df=non_missing_rows, metric=metric, anomaly_metric=f'{metric}_anomaly_isf', method='isf')

        # Combine processed rows with missing rows and sort by index
        combined_df = pd.concat([non_missing_rows, missing_rows], axis=0).sort_index()

        # Ensure anomaly column exists and default to 'Normal' where missing
        if f'{metric}_anomaly' not in combined_df.columns:
            combined_df[f'{metric}_anomaly'] = 'Normal'
        else:
            combined_df.loc[:, f'{metric}_anomaly'] = combined_df.loc[:, f'{metric}_anomaly'].fillna('Normal')

        # Clean up temporary columns if present
        if f'{metric}_anomaly_isf' in combined_df.columns:
            engine.delete_columns(df=combined_df, columns=[f'{metric}_anomaly_isf'])
        return combined_df
