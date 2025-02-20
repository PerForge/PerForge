from .base import BaseDetector
import pandas as pd
from typing import Literal
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import adfuller
import ruptures as rpt
import numpy as np
import pandas as pd

class MetricStabilityDetector(BaseDetector):
    def __init__(self):
        self._type = 'fixed_load'
        self._name = 'Stability'
        
    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type
        
    @property
    def name(self) -> str:
        return self._name
    
    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")

        df = df.copy()
        df['time_seconds'] = (df.index - df.index[0]).total_seconds()
        X = df['time_seconds'].values.reshape(-1, 1)
        y = df[metric].values
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]

        if np.var(y) < 1e-6:
            engine.add_output(
                status='passed',
                method='LinearRegression',
                description=f'{metric} was stable during the test (constant data).',
                value=None
            )
            return df.drop(columns=['time_seconds'])

        result = adfuller(df[metric])
        p_value = result[1]

        algo = rpt.Binseg(model="l2").fit(y)

        if abs(slope) < engine.slope_threshold and p_value < engine.p_value_threshold:
            engine.add_output(
                status='passed',
                method='LinearRegression',
                description=f'{metric} was stable during the test.',
                value=slope
            )
        elif slope > engine.slope_threshold:
            engine.add_output(
                status='failed',
                method='LinearRegression',
                description=f'{metric} was not stable during the test (potential increase).',
                value=slope
            )
        else:
            engine.add_output(
                status='failed',
                method='LinearRegression',
                description=f'{metric} was not stable during the test (potential degradation).',
                value=slope
            )
        
        return df.drop(columns=['time_seconds'])
