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
