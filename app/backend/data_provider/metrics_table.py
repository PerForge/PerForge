# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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

from typing import Dict, Any, Optional, List

import json

class MetricsTable:
    """
    A class to represent a table of metrics with optional baseline comparison.
    This stores current metrics and optionally baseline metrics and calculated differences.
    """

    def __init__(self, name: str = "", aggregation: str = "median"):
        """
        Initialize a new metrics table.

        Args:
            name: Name of the metrics table
            aggregation: The aggregation type to use ("mean", "median", "p90", etc.)
        """
        self.name = name
        self.aggregation = aggregation
        self.current: List[Dict[str, Any]] = []
        self.baseline: Optional[List[Dict[str, Any]]] = None
        self.diff: Optional[Dict[str, Any]] = None
        self.diff_pct: Optional[Dict[str, Any]] = None

    def set_current_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Set the current metrics values from a list of dictionaries"""
        self.current = metrics

    def set_baseline_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Set the baseline metrics for comparison from a list of dictionaries"""
        self.baseline = metrics
        self._calculate_diff()

    def _calculate_diff(self) -> None:
        """Calculate the difference between current and baseline metrics"""
        if not self.baseline or not self.current:
            return

        # We'll need to adapt our diff calculation to work with lists of dictionaries
        # This requires matching records between current and baseline
        # For now, we'll disable this functionality since it needs a redesign
        self.diff = {}
        self.diff_pct = {}

    def get_metric(self, metric_name: str) -> Any:
        """Get the current value of a specific metric from all records"""
        # Return values from all records that contain this metric
        values = [record.get(metric_name) for record in self.current if metric_name in record]
        return values if values else None

    def get_current_metrics(self) -> List[Dict[str, Any]]:
        """Get all current metrics"""
        return self.current

    def get_baseline_metric(self, metric_name: str) -> Any:
        """Get the baseline value of a specific metric from all records"""
        if self.baseline is None:
            return None
        values = [record.get(metric_name) for record in self.baseline if metric_name in record]
        return values if values else None

    def get_diff_metric(self, metric_name: str) -> Any:
        """Get the difference value of a specific metric"""
        return None if self.diff is None else self.diff.get(metric_name)

    def get_diff_pct_metric(self, metric_name: str) -> Any:
        """Get the percentage difference of a specific metric"""
        return None if self.diff_pct is None else self.diff_pct.get(metric_name)

    def has_baseline(self) -> bool:
        """Check if the table has baseline data"""
        return self.baseline is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the table to a dictionary with all data"""
        result = {
            "current": self.current
        }

        if self.baseline:
            result["baseline"] = self.baseline

        if self.diff:
            result["diff"] = self.diff

        if self.diff_pct:
            result["diff_pct"] = self.diff_pct

        return result

    def __repr__(self) -> str:
        """String representation of the metrics table"""
        has_baseline = "with" if self.baseline else "without"
        return f"MetricsTable({self.name}, {has_baseline} baseline, {len(self.current)} records)"

    def __str__(self) -> str:
        """String representation for template variable replacement

        Returns a JSON string representation of the current metrics data
        for easy consumption by template systems and JavaScript.
        """
        return json.dumps(self.current)
