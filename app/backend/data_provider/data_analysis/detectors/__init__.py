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

"""
Performance test anomaly detectors package.

This package contains various detectors used for analyzing performance test metrics:
- ZScoreDetector: Detects anomalies using Z-score statistical method
- IsolationForestDetector: Uses isolation forest algorithm for anomaly detection
- MetricStabilityDetector: Analyzes metric stability using rolling statistics
- RampUpPeriodAnalyzer: Specialized detector for ramp-up period analysis
"""

from .zscore_detector import ZScoreDetector
from .isolation_forest_detector import IsolationForestDetector
from .metric_stability_detector import MetricStabilityDetector
from .ramp_up_analyzer import RampUpPeriodAnalyzer

__all__ = [
    'ZScoreDetector',
    'MetricStabilityDetector',
    'IsolationForestDetector',
    'RampUpPeriodAnalyzer'
]
