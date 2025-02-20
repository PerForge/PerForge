from abc import ABC, abstractmethod
import pandas as pd
from typing import Literal

class BaseDetector(ABC):
    """Base class for all anomaly detectors"""
    
    @abstractmethod
    def detect(self, df: pd.DataFrame, metric: str, engine) -> pd.DataFrame:
        """
        Detect anomalies in the given dataframe
        
        Args:
            df: Input dataframe with time series data
            metric: Name of the metric to analyze
            engine: Reference to the anomaly detection engine
            
        Returns:
            DataFrame with added anomaly column
        """
        pass
    
    @property
    @abstractmethod
    def type(self) -> Literal['fixed_load', 'ramp_up']:
        """Type of the detector - either 'fixed_load' or 'ramp_up'"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the detector for logging and reporting"""
        pass
