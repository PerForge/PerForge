from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller
import ruptures as rpt
import numpy as np
import pandas as pd
from app.backend.data_provider.data_analysis.anomaly_detection import AnomalyDetector

class IsolationForestDetector(AnomalyDetector):
    def __init__(self):
        super().__init__(type='fixed_load')

    def detect(self, df, metric, engine):
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

class ZScoreDetector(AnomalyDetector):
    def __init__(self):
        super().__init__(type='fixed_load')

    def detect(self, df, metric, engine):
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

class MetricStabilityDetector(AnomalyDetector):
    def __init__(self):
        super().__init__(type='fixed_load')

    def detect(self, df, metric, engine):
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")

        df = df.copy()
        df['time_seconds'] = (df.index - df.index[0]).total_seconds()
        X = df['time_seconds'].values.reshape(-1, 1)
        y = df[metric].values
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]

        if np.var(y) < 1e-6:
            engine.output.append({
                'status': 'passed',
                'method': 'LinearRegression',
                'description': f'{metric} was stable during the test (constant data).',
                'value': None
            })
            return df.drop(columns=['time_seconds'])

        result = adfuller(df[metric])
        p_value = result[1]

        algo = rpt.Binseg(model="l2").fit(y)

        if abs(slope) < engine.slope_threshold and p_value < engine.p_value_threshold:
            engine.output.append({
                'status': 'passed',
                'method': 'LinearRegression',
                'description': f'{metric} was stable during the test.',
                'value': slope
            })
        elif slope > engine.slope_threshold:
            engine.output.append({
                'status': 'failed',
                'method': 'LinearRegression',
                'description': f'{metric} was not stable during the test (potential increase).',
                'value': slope
            })
        else:
            engine.output.append({
                'status': 'failed',
                'method': 'LinearRegression',
                'description': f'{metric} was not stable during the test (potential degradation).',
                'value': slope
            })
        
        return df.drop(columns=['time_seconds'])

class RampUpPeriodAnalyzer(AnomalyDetector):
    def __init__(self, threshold_condition, base_metric):
        super().__init__(type='ramp_up')
        self.threshold_condition = threshold_condition
        self.base_metric = base_metric

    def detect(self, df, metric, engine):
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
                engine.output.append({
                    'status': 'failed',
                    'method': 'rolling_correlation',
                    'description': f"Tipping point was reached at load of {str(tipping_point_rt[metric])} requests per second according to throughput analysis.",
                    'value': tipping_point_rt[metric]
                })
                df.loc[tipping_point_index, anomaly_col] = 'Anomaly: potential saturation point'
            else:
                engine.output.append({
                    'status': 'passed',
                    'method': 'rolling_correlation',
                    'description': 'Users ramped up successfully.',
                    'value': None
                })
        df = engine.delete_columns(df=df.copy(), columns=['rolling_correlation'])
        return df