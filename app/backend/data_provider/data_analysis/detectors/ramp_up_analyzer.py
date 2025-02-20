from .base import BaseDetector
import pandas as pd
from typing import Literal, Callable

class RampUpPeriodAnalyzer(BaseDetector):
    def __init__(self, threshold_condition: Callable, base_metric: str):
        self._type = 'ramp_up'
        self._name = 'Ramp-Up Analysis'
        self.threshold_condition = threshold_condition
        self.base_metric = base_metric
    
    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type
        
    @property
    def name(self) -> str:
        return self._name
    
    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        df = df.copy()
        anomaly_col = f'{metric}_anomaly'
        if anomaly_col not in df.columns:
            df[anomaly_col] = 'Normal'

        if df is not None:
            df['rolling_correlation'] = df[metric].rolling(window=engine.rolling_window).apply(
                lambda x: x.corr(df[self.base_metric])
            )

            tipping_point = False
            count = 0
            tipping_point_rt = None
            tipping_point_index = None

            for i in range(len(df)):
                if self.threshold_condition(df['rolling_correlation'].iloc[i]):
                    count += 1
                    if count == 1 and i > 0:
                        tipping_point_rt = df.iloc[i - 1]
                        tipping_point_index = df.index[i - 1]
                    if count >= 5:
                        tipping_point = True
                        break
                else:
                    count = 0
                    tipping_point_rt = None
                    tipping_point_index = None

            if tipping_point:
                engine.add_output(
                    status='failed',
                    method='rolling_correlation',
                    description=f"Tipping point was reached at load of {str(tipping_point_rt[metric])} requests per second according to throughput analysis.",
                    value=tipping_point_rt[metric]
                )
                df.loc[tipping_point_index, anomaly_col] = 'Anomaly: potential saturation point'
            else:
                engine.add_output(
                    status='passed',
                    method='rolling_correlation',
                    description='Users ramped up successfully.',
                    value=None
                )
        df = engine.delete_columns(df=df.copy(), columns=['rolling_correlation'])
        return df