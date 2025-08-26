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
from sklearn.linear_model import LinearRegression
import numpy as np
from scipy import stats

class MetricStabilityDetector(BaseDetector):
    """
    Detector for analyzing metric stability in performance tests.

    This detector evaluates metrics for:
    - Constant behavior (very low variance)
    - Stability (acceptable variation without significant trend)
    - Trends (increasing or decreasing patterns)
    - Instability (high variation with or without trends)
    """

    def __init__(self):
        self._type = 'fixed_load'
        self._name = 'Stability'

    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type

    @property
    def name(self) -> str:
        return self._name

    def _remove_outliers(self, data: np.ndarray) -> np.ndarray:
        """
        Remove statistical outliers using z-score method.

        Args:
            data: Input numpy array of metric values

        Returns:
            Numpy array with outliers removed (|z-score| < 3)
        """
        z_scores = stats.zscore(data)
        return data[np.abs(z_scores) < 3]

    def _get_trend_description(self, slope: float, cv: float, p_value: float, p_threshold: float, cv_threshold: float) -> str:
        """
        Determine the trend description based on statistical analysis.

        Args:
            slope: Coefficient from linear regression
            cv: Coefficient of variation
            p_value: Statistical significance of the slope
            p_threshold: Threshold for statistical significance (typically 0.05)
            cv_threshold: Threshold for coefficient of variation

        Returns:
            String describing the trend: "unstable", "noisy but stable",
            "constant increase/decrease", or "unstable increasing/decreasing"
        """
        # Consider slope significant if p-value < 0.05
        has_significant_trend = p_value < p_threshold

        if not has_significant_trend:
            return "unstable" if cv >= cv_threshold else "noisy but stable"

        if slope > 0:
            return "constant increase" if cv < cv_threshold else "unstable increasing"
        else:
            return "constant decrease" if cv < cv_threshold else "unstable decreasing"

    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        """
        Analyze metric stability and trends in the time series data.

        The method performs the following analyses:
        1. Outlier removal using z-scores
        2. Variance check for constant behavior
        3. Coefficient of variation calculation
        4. Linear regression for trend detection
        5. Statistical significance testing of the trend

        Args:
            df: DataFrame with DatetimeIndex and metric values
            metric: Name of the metric column to analyze
            engine: Analysis engine providing configuration and output handling

        Returns:
            Original DataFrame (modifications are handled via engine outputs)

        Raises:
            ValueError: If DataFrame index is not DatetimeIndex
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")

        df = df.copy()
        # Guard: skip if the metric column is missing
        if metric not in df.columns:
            return df

        series = df[metric].dropna()
        # Guard: insufficient data points
        if len(series) < 3:
            return df

        y = series.values

        # Step 1: Remove statistical outliers for cleaner analysis
        cleaned_data = self._remove_outliers(y)
        cleaned_data = engine.normalize_metric(cleaned_data, metric)

        # Step 2: Check for constant behavior
        if np.var(cleaned_data, ddof=1) < engine.numpy_var_threshold:
            engine.add_output(
                status='passed',
                method='TrendAnalysis',
                description=f'Metric {metric} is constant throughout the test.',
                value=None
            )
            return df

        # Step 3: Calculate variation metrics
        cv = np.std(cleaned_data) / np.mean(cleaned_data)

        # Step 4: Perform linear regression for trend analysis
        X = np.arange(len(cleaned_data)).reshape(-1, 1)
        model = LinearRegression().fit(X, cleaned_data)
        slope = model.coef_[0]

        # Step 5: Calculate statistical significance of the trend
        n = len(cleaned_data)
        mse = np.sum((cleaned_data - model.predict(X)) ** 2) / (n - 2)
        var_b = mse / np.sum((X - X.mean()) ** 2)
        sd_b = np.sqrt(var_b)
        t_stat = slope / sd_b
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

        # Get trend description with p-value
        trend = self._get_trend_description(slope, cv, p_value, engine.p_value_threshold, engine.cv_threshold)

        if trend == "unstable":
            engine.add_output(
                status='failed',
                method='TrendAnalysis',
                description=f'Metric {metric} shows high variability without a clear trend.',
                value={'slope': slope, 'cv': cv, 'p_value': p_value}
            )
        elif trend == "noisy but stable":
            engine.add_output(
                status='passed',
                method='TrendAnalysis',
                description=f'Metric {metric} shows some variation but remains stable.',
                value={'slope': slope, 'cv': cv, 'p_value': p_value}
            )
        elif trend in ["constant increase", "constant decrease"]:
            engine.add_output(
                status='failed',
                method='TrendAnalysis',
                description=f'Metric {metric} shows a {trend} pattern.',
                value={'slope': slope, 'cv': cv}
            )
        else:
            variations = []
            if cv >= engine.cv_threshold:
                variations.append("high variability")

            engine.add_output(
                status='failed',
                method='TrendAnalysis',
                description=(f'Metric {metric} is unstable with {" and ".join(variations)}. 'f'The overall pattern shows {trend}.'),
                value={'slope': slope, 'cv': cv, 'p_value': p_value}
            )

        return df
