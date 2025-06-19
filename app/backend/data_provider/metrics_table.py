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

    def _sanitize_metrics(self, metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replace None or null values with 0.00 in numeric fields"""
        # If no metrics, return empty list
        if not metrics:
            return []

        result = []
        # First pass: analyze what fields tend to contain numeric values
        numeric_fields = set()
        for metric in metrics:
            for key, value in metric.items():
                if isinstance(value, (int, float)) and value is not None:
                    numeric_fields.add(key)

        # Second pass: replace None values with 0.00 for fields that contained numeric values
        for metric in metrics:
            new_metric = {}
            for key, value in metric.items():
                if value is None or value == "null":
                    if key in numeric_fields:
                        # Replace with 0.00 for fields that contained numeric values elsewhere
                        new_metric[key] = 0.00
                    else:
                        # Keep original value for non-numeric fields
                        new_metric[key] = value
                else:
                    new_metric[key] = value
            result.append(new_metric)
        return result

    def set_current_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Set the current metrics values from a list of dictionaries"""
        self.current = self._sanitize_metrics(metrics)

    def set_baseline_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Set the baseline metrics for comparison from a list of dictionaries"""
        self.baseline = self._sanitize_metrics(metrics)



    def get_metric(self, metric_name: str) -> Any:
        """Get the current value of a specific metric from all records"""
        # Return values from all records that contain this metric
        values = [record.get(metric_name) for record in self.current if metric_name in record]
        return values if values else None

    def get_current_metrics(self) -> List[Dict[str, Any]]:
        """Get all current metrics with float values formatted to 3 decimal places"""
        result = []

        for metric in self.current:
            new_metric = {}

            # Format float values to max 3 decimal places
            for key, value in metric.items():
                if isinstance(value, float):
                    new_metric[key] = f"{value:.2f}"
                else:
                    new_metric[key] = value

            result.append(new_metric)

        return result

    def get_baseline_metric(self, metric_name: str) -> Any:
        """Get the baseline value of a specific metric from all records"""
        if self.baseline is None:
            return None
        values = [record.get(metric_name) for record in self.baseline if metric_name in record]
        return values if values else None



    def get_comparison_metrics(self) -> List[Dict[str, Any]]:
        """
        Get metrics with baseline comparison when available.
        Returns metrics in format: "baseline_value>current_value" when baseline exists,
        otherwise returns just current values.
        """
        if not self.baseline:
            return self.current

        # Create comparison metrics
        result = []

        # Create a mapping of baseline metrics by key (assuming each metric has a unique identifier)
        baseline_map = {self._get_metric_key(item): item for item in self.baseline}

        # For each current metric, find the corresponding baseline metric and format comparison
        for curr in self.current:
            new_metric = curr.copy()  # Start with current metric
            key = self._get_metric_key(curr)

            if key in baseline_map:
                # For each numeric field, replace with baseline>current format
                for field, value in curr.items():
                    if isinstance(value, (int, float)) and field in baseline_map[key]:
                        baseline_value = baseline_map[key][field]

                        # Format float values to max 2 decimal places
                        if baseline_value:
                            baseline_str = f"{float(baseline_value):.2f}"
                        else:
                            baseline_str = "0.00"
                        if value:
                            value_str = f"{float(value):.2f}"
                        else:
                            value_str = "0.00"

                        new_metric[field] = f"{baseline_str} -> {value_str}"

            result.append(new_metric)

        return result

    def has_baseline(self) -> bool:
        """Check if the table has baseline data"""
        return self.baseline is not None

    def _get_metric_key(self, metric: Dict[str, Any]) -> str:
        """
        Generate a unique key for a metric to match baseline with current.
        Assumes metrics have some identifier field like 'page', 'name', etc.
        """
        # Try common identifier fields first
        for key in ['page', 'name', 'id', 'url']:
            if key in metric:
                return str(metric[key])

        # If no identifier found, use a hash of the serialized dict
        # Exclude highly variable fields that shouldn't affect matching
        matching_dict = {k: v for k, v in metric.items() if k not in ['timestamp']}
        return str(hash(frozenset(matching_dict.items())))

    def to_dict(self) -> Dict[str, Any]:
        """Convert the table to a dictionary with all data"""
        result = {
            "current": self.current
        }

        if self.baseline:
            result["baseline"] = self.baseline



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
