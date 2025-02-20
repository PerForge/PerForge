from .base import BaseDetector
import pandas as pd
import numpy as np
from scipy import stats
from typing import Literal

class ZScoreDetector(BaseDetector):
    def __init__(self):
        self._type = 'fixed_load'
        self._name = 'Z-Score'
    
    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type
        
    @property
    def name(self) -> str:
        return self._name

    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        df = df.copy()
        df[f'{metric}_z_score'] = (df[metric] - df[metric].mean()) / df[metric].std()
        df[f'{metric}_anomaly_z_score'] = df[f'{metric}_z_score'].apply(lambda x: -1 if abs(x) > engine.z_score_threshold else 1)

        # Ensure the first and last points are not detected as anomalies
        df.iloc[0, df.columns.get_loc(f'{metric}_anomaly_z_score')] = 1
        df.iloc[-1, df.columns.get_loc(f'{metric}_anomaly_z_score')] = 1

        df = engine.update_anomaly_status(df=df, metric=metric, anomaly_metric=f'{metric}_anomaly_z_score', method='z_score')
        engine.delete_columns(df=df, columns=[f'{metric}_anomaly_z_score', f'{metric}_z_score'])
        # engine.collect_anomalies(df=df, metric=metric, anomaly_cl=f'{metric}_anomaly', period="fixed-load", method="z_score")
        return df