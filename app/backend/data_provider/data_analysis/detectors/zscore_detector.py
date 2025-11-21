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
from typing import Literal

class ZScoreDetector(BaseDetector):
    """
    Anomaly detector using Z-Score method combined with median validation.
    Detects outliers based on both statistical deviation (Z-Score) and
    median-based threshold validation.
    """
    def __init__(self):
        self._type = 'fixed_load'
        self._name = 'Z-Score'

    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type

    @property
    def name(self) -> str:
        return self._name

    def validate_with_median(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        """
        Validates data points against the median value.

        Args:
            df: Input DataFrame containing the metric
            metric: Name of the metric column to validate

        Returns:
            DataFrame with added median validation column
        """
        median = df[metric].median()
        threshold = 0.10  # 10% threshold for median deviation

        def is_anomaly(value):
            # Calculate percentage difference from median
            diff_percentage = abs(value - median) / median
            return -1 if diff_percentage > threshold else 1

        df[f'{metric}_median_valid'] = df[metric].apply(is_anomaly)
        return df

    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        """
        Detects anomalies using combined Z-Score and median validation approach.

        Args:
            df: Input DataFrame containing the metric
            metric: Name of the metric column to analyze
            engine: Analysis engine providing configuration and utility methods

        Returns:
            DataFrame with detected anomalies
        """
        df = df.copy()

        # Guard: skip if the metric column is missing
        if metric not in df.columns:
            return df

        series = df[metric].dropna()

        # Guard: if not enough data points or zero standard deviation, default to Normal
        if len(series) < 3 or series.std() == 0 or pd.isna(series.std()):
            df[f'{metric}_anomaly_z_score'] = 1
            df = engine.update_anomaly_status(
                df=df,
                metric=metric,
                anomaly_metric=f'{metric}_anomaly_z_score',
                method='z_score'
            )
            engine.delete_columns(
                df=df,
                columns=[f'{metric}_anomaly_z_score']
            )
            return df

        # Step 1: Z-Score calculation and anomaly detection
        df[f'{metric}_z_score'] = (df[metric] - df[metric].mean()) / df[metric].std()
        df[f'{metric}_anomaly_z_score'] = df[f'{metric}_z_score'].apply(
            lambda x: -1 if abs(x) > engine.z_score_threshold else 1
        )

        # Step 2: Apply median-based validation
        df = self.validate_with_median(df, metric)

        # Step 3: Combine both detection methods
        # Point is anomalous only if both methods agree
        df[f'{metric}_anomaly_z_score'] = df.apply(
            lambda row: -1 if row[f'{metric}_anomaly_z_score'] == -1 and
                            row[f'{metric}_median_valid'] == -1 else 1,
            axis=1
        )

        # Step 3.5: Apply contextual validator (20 before/after median, 15% of current metric)
        df = engine.filter_contextual_anomalies(
            df,
            metric,
            f'{metric}_anomaly_z_score'
        )

        # Step 4: Ensure endpoints are not marked as anomalies
        df.iloc[0, df.columns.get_loc(f'{metric}_anomaly_z_score')] = 1
        df.iloc[-1, df.columns.get_loc(f'{metric}_anomaly_z_score')] = 1

        # Step 5: Update final anomaly status and cleanup
        df = engine.update_anomaly_status(
            df=df,
            metric=metric,
            anomaly_metric=f'{metric}_anomaly_z_score',
            method='z_score'
        )
        engine.delete_columns(
            df=df,
            columns=[f'{metric}_anomaly_z_score', f'{metric}_z_score', f'{metric}_median_valid']
        )
        return df
