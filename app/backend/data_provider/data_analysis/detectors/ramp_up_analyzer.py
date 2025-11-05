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
from typing import Literal, Callable

class RampUpPeriodAnalyzer(BaseDetector):
    """
    Analyzes performance data to detect ramp-up periods and potential system saturation points.
    Identifies where system performance begins to degrade under increasing load.
    """
    def __init__(self, threshold_condition: Callable, base_metric: str):
        """
        Initialize the analyzer with detection parameters.

        Args:
            threshold_condition: Function that evaluates if correlation crosses threshold
            base_metric: Reference metric to correlate against (typically 'users')
        """
        self._type = 'ramp_up'
        self._name = 'Ramp-Up Analysis'
        self.threshold_condition = threshold_condition
        self.base_metric = base_metric

    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        """Returns the analyzer type identifier."""
        return self._type

    @property
    def name(self) -> str:
        """Returns the human-readable name of the analyzer."""
        return self._name

    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        """
        Analyzes the data to detect potential system saturation points during ramp-up.

        Args:
            df: Input DataFrame containing performance metrics
            metric: Name of the metric to analyze
            engine: Analysis engine providing configuration and output handling

        Returns:
            DataFrame with added anomaly detection results
        """
        df = df.copy()

        anomaly_col = f'{metric}_anomaly'
        if anomaly_col not in df.columns:
            df[anomaly_col] = 'Normal'

        if df is not None:
            # Calculate rolling correlation between metric and base_metric (e.g., response time vs users)
            df['rolling_correlation'] = df[metric].rolling(window=engine.rolling_window).corr(df[self.base_metric])

            # Track potential tipping point using consecutive threshold violations
            tipping_point = False
            count = 0
            tipping_point_rt = None
            tipping_point_index = None
            n_eff = int(pd.Series(df['rolling_correlation']).count())
            frac = float(getattr(engine, 'ramp_up_required_breaches_fraction', 0.15))
            min_breaches = int(getattr(engine, 'ramp_up_required_breaches_min', 3))
            max_breaches = int(getattr(engine, 'ramp_up_required_breaches_max', 5))
            required_breaches = min(max_breaches, max(min_breaches, int(frac * n_eff))) if n_eff > 0 else max_breaches

            # Iterate through correlations to find sustained threshold violations
            for i in range(len(df)):
                corr_val = df['rolling_correlation'].iloc[i]
                if pd.notna(corr_val) and self.threshold_condition(corr_val):
                    count += 1
                    # Store first violation point as potential tipping point
                    if count == 1 and i > 0:
                        tipping_point_rt = df.iloc[i - 1]
                        tipping_point_index = df.index[i - 1]
                    # Consider tipping point confirmed after 5 consecutive violations
                    if count >= required_breaches:
                        tipping_point = True
                        break
                else:
                    count = 0
                    tipping_point_rt = None
                    tipping_point_index = None

            # Record analysis results
            if tipping_point:
                engine.add_output(
                    status='failed',
                    method='rolling_correlation',
                    description=f"Tipping point was reached at load of {str(int(tipping_point_rt[metric]))} requests per second according to throughput analysis.",
                    value=int(tipping_point_rt[metric])
                )
                df.loc[tipping_point_index, anomaly_col] = 'Anomaly: potential saturation point'
            else:
                engine.add_output(
                    status='passed',
                    method='rolling_correlation',
                    description='Users ramped up successfully.',
                    value=None
                )

        # Clean up temporary analysis columns
        df = engine.delete_columns(df=df.copy(), columns=['rolling_correlation'])
        return df
