from .base import BaseDetector
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Literal

class IsolationForestDetector(BaseDetector):
    def __init__(self):
        self._type = 'fixed_load'
        self._name = 'Isolation Forest'
    
    @property
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        return self._type
        
    @property
    def name(self) -> str:
        return self._name
    
    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        df = df.copy()
        df_with_features = engine.add_rolling_features(df=df.copy(), metric=metric, is_mean=True, is_std=True)
        
        # Check if the second metric is different from the primary metric
        if engine.isf_feature_metric != metric:
            df_with_features = engine.add_rolling_features(df=df_with_features, metric=engine.isf_feature_metric, is_mean=True, is_std=True)
        
        missing_rows = df_with_features[df_with_features.isna().any(axis=1)].copy()
        non_missing_rows = df_with_features.dropna().copy()

        if not non_missing_rows.empty:
            # Normalize the features
            scaler = StandardScaler()
            features = [metric, f'{metric}_rolling_mean', f'{metric}_rolling_std']
            
            # Add the second metric's features if it is different from the primary metric
            if engine.isf_feature_metric != metric:
                features.extend([engine.isf_feature_metric, f'{engine.isf_feature_metric}_rolling_mean', f'{engine.isf_feature_metric}_rolling_std'])
            
            normalized_features = scaler.fit_transform(non_missing_rows[features])

            # Fit the Isolation Forest on the normalized features
            iso_forest = IsolationForest(contamination=engine.contamination, random_state=42)
            iso_forest.fit(normalized_features)
            anomaly_scores = iso_forest.decision_function(normalized_features)
            
            # Mark anomalies as -1 and normal points as 1 using np.where
            non_missing_rows.loc[:, f'{metric}_anomaly_isf'] = np.where(anomaly_scores < engine.isf_threshold, -1, 1)
            # Ensure the first and last points are always marked as "Normal" before combining
            non_missing_rows.iloc[0, non_missing_rows.columns.get_loc(f'{metric}_anomaly_isf')] = 1
            non_missing_rows.iloc[-1, non_missing_rows.columns.get_loc(f'{metric}_anomaly_isf')] = 1
            non_missing_rows = engine.update_anomaly_status(df=non_missing_rows, metric=metric, anomaly_metric=f'{metric}_anomaly_isf', method='isf')

        combined_df = pd.concat([non_missing_rows, missing_rows], axis=0).sort_index()
        combined_df.loc[:, f'{metric}_anomaly'] = combined_df.loc[:, f'{metric}_anomaly'].fillna('Normal')
        
        # Delete the columns related to the second metric if it was added
        columns_to_delete = [f'{metric}_anomaly_isf', f'{metric}_rolling_mean', f'{metric}_rolling_std']
        if engine.isf_feature_metric != metric:
            columns_to_delete.extend([f'{engine.isf_feature_metric}_rolling_mean', f'{engine.isf_feature_metric}_rolling_std'])
        
        engine.delete_columns(df=combined_df, columns=columns_to_delete)
        # engine.collect_anomalies(df=combined_df, metric=metric, anomaly_cl=f'{metric}_anomaly', period="fixed-load", method="isf")
        return combined_df
