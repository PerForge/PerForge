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

from collections import OrderedDict
from typing import Dict, Any, Optional, List
from .metric import Metric, NFRStatus


class MetricsTable:
    """
    A class to represent a table of metrics using Metric objects with optional baseline comparison.
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
        self.metrics: List[Metric] = []  # Store Metric objects instead of raw dicts
        self.scope_column_name = ""

    def add_metric(self, metric: Metric) -> None:
        """Add a metric object to the table"""
        self.metrics.append(metric)

    def set_metrics_from_data(self, current_data: List[Dict], baseline_data: Optional[List[Dict]] = None):
        """Convert raw data to Metric objects"""
        self.metrics = []
        # Recalculate scope column name for each dataset to avoid stale state
        self.scope_column_name = ""

        # Create baseline lookup
        baseline_map = {}
        if baseline_data:
            for baseline_row in baseline_data:
                key = self._get_row_key(baseline_row)
                baseline_map[key] = baseline_row

        # Create Metric objects
        for current_row in current_data:
            row_key = self._get_row_key(current_row)
            baseline_row = baseline_map.get(row_key, {})

            # Detect scope column per row to avoid relying on dict iteration order
            scope_key = self._detect_scope_key(current_row)
            if not self.scope_column_name and scope_key:
                self.scope_column_name = scope_key
            scope_value = current_row.get(scope_key) if scope_key else None
            if scope_value is None:
                # Fallback to row key if explicit scope is missing
                scope_value = row_key
            else:
                # Normalize to string for consistent grouping keys
                scope_value = str(scope_value)

            # Create metrics for each numeric field (coerce numeric-like strings)
            for field_name, value in current_row.items():
                if field_name in ['page', 'transaction', 'Metric']:
                    continue
                num_value = self._to_number(value)
                if num_value is None:
                    continue

                baseline_value_raw = baseline_row.get(field_name) if baseline_row else None
                baseline_num = self._to_number(baseline_value_raw)

                metric = Metric(
                    name=field_name,
                    value=round(num_value, 2),
                    scope=scope_value,
                    baseline=round(baseline_num, 2) if baseline_num is not None else None
                )
                self.add_metric(metric)

    def _get_row_key(self, row: Dict[str, Any]) -> str:
        """Generate a unique key for a row to match baseline with current"""
        # Try common identifier fields first
        for key in ['page', 'transaction', 'Metric', 'name', 'id', 'url']:
            if key in row:
                return str(row[key])

        # If no identifier found, use a hash of the serialized dict
        # Exclude highly variable fields that shouldn't affect matching
        matching_dict = {k: v for k, v in row.items() if k not in ['timestamp']}
        return str(hash(frozenset(matching_dict.items())))

    def _to_number(self, value: Any) -> Optional[float]:
        """Try to coerce a value to float; return None if not possible."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _detect_scope_key(self, row: Dict[str, Any]) -> Optional[str]:
        """Detect which column should be used as scope for a given row."""
        for key in ['transaction', 'page', 'Metric']:
            if key in row:
                return key
        return None

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

    def get_metrics_by_scope(self, scope: str) -> List[Metric]:
        """Get all metrics for a specific scope (transaction/page)"""
        return [m for m in self.metrics if m.scope == scope]

    def get_metrics_by_name(self, metric_name: str) -> List[Metric]:
        """Get all metrics with a specific name"""
        return [m for m in self.metrics if m.name == metric_name]

    def get_failed_nfr_metrics(self) -> List[Metric]:
        """Get all metrics that failed NFR evaluation"""
        return [m for m in self.metrics if m.nfr_status == NFRStatus.FAILED]

    def format_metrics(self) -> List[Dict[str, Any]]:
        """Format metrics for display with proper formatting of float values"""
        result = []

        # Group metrics by scope
        scope_groups = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        # Create formatted result
        for scope, metrics_dict in scope_groups.items():
            row = {self.scope_column_name: scope}
            for metric_name, metric in metrics_dict.items():
                # Format value to max 2 decimal places if it's a float
                if isinstance(metric.value, float):
                    row[metric_name] = round(metric.value, 2)
                else:
                    row[metric_name] = metric.value
            result.append(row)

        return result

    def format_comparison_metrics(self) -> List[Dict[str, Any]]:
        """Format metrics with baseline->current format

        For metrics with baseline values, shows "baseline -> current" format
        For metrics without baseline values, just shows the current value
        """
        # If no baseline available at all, just return formatted metrics
        if not self.has_baseline():
            return self.format_metrics()

        result = []

        # Group metrics by scope
        scope_groups = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        # Determine how many distinct metric columns exist across the table
        all_metric_names = set()
        for metrics_dict in scope_groups.values():
            all_metric_names.update(metrics_dict.keys())
        # If only one metric column exists, output separate columns for baseline and differences
        if len(all_metric_names) == 1:
            only_metric_name = next(iter(all_metric_names))

            for scope, metrics_dict in scope_groups.items():
                row = {self.scope_column_name: scope}
                metric = metrics_dict.get(only_metric_name)
                if not metric:
                    # No metric present for this scope; fill with zeros
                    row["Current"] = 0.00
                    row["Baseline"] = 0.00
                    row["Diff"] = 0.00
                    row["Diff Pct"] = 0.00
                    result.append(row)
                    continue

                # Current and baseline values (default to 0.00 if None)
                current_val = float(metric.value) if metric.value is not None else 0.00
                baseline_val = float(metric.baseline) if metric.baseline is not None else 0.00

                # Differences
                diff_val = round(current_val - baseline_val, 2)
                diff_pct_val = round((diff_val / baseline_val) * 100, 2) if baseline_val != 0 else 0.00

                # Populate row
                row["Current"] = round(current_val, 2)
                row["Baseline"] = round(baseline_val, 2)
                row["Diff"] = diff_val
                row["Diff Pct"] = diff_pct_val
                result.append(row)
            return result

        # Check if any metric in a scope has baseline data
        has_baseline_by_scope = {}
        for scope, metrics_dict in scope_groups.items():
            has_baseline_by_scope[scope] = any(m.baseline is not None for m in metrics_dict.values())

        # Create comparison rows
        for scope, metrics_dict in scope_groups.items():
            row = {self.scope_column_name: scope}
            # Check if this scope has any baseline metrics
            scope_has_baseline = has_baseline_by_scope[scope]

            for metric_name, metric in metrics_dict.items():
                # If this metric has a baseline value, show comparison
                if metric.baseline is not None:
                    # Format baseline and current values
                    baseline_str = f"{float(metric.baseline):.2f}" if metric.baseline else "0.00"
                    current_str = f"{float(metric.value):.2f}" if metric.value else "0.00"
                    # Use baseline->current format
                    row[metric_name] = f"{baseline_str} -> {current_str}"
                else:
                    # No baseline for this metric
                    if isinstance(metric.value, float):
                        row[metric_name] = f"{metric.value:.2f}"
                    else:
                        row[metric_name] = metric.value
            result.append(row)

        return result

    def format_split_columns_metrics(
        self,
        columns_config: List[tuple],
        current_label: str = 'Current',
        baseline_label: str = 'Baseline',
        show_diff: bool = False,
        diff_label: str = 'Diff',
        show_diff_pct: bool = False,
        diff_pct_label: str = 'Diff %'
    ) -> List[Dict[str, Any]]:
        """Format metrics with baseline and current as separate columns.

        Each metric produces up to four columns in this order:
          "{display_label} ({baseline_label})", "{display_label} ({current_label})",
          optionally "{display_label} ({diff_label})", "{display_label} ({diff_pct_label})".

        Rows are built as OrderedDict to guarantee column order across all integrations.
        When no baseline is available, falls back to _format_metrics_with_config().

        Args:
            columns_config: List of (metric_key, display_label) tuples. If empty, all metrics
                            are included using their original key as the label.
            current_label: Suffix for current test columns.
            baseline_label: Suffix for baseline test columns.
            show_diff: Whether to add an absolute difference column per metric.
            diff_label: Suffix for diff columns.
            show_diff_pct: Whether to add a percentage difference column per metric.
            diff_pct_label: Suffix for diff % columns.

        Returns:
            List of OrderedDict rows with split columns.
        """
        if not self.has_baseline():
            return self._format_metrics_with_config(columns_config)

        # Group by scope
        scope_groups: Dict[str, Dict[str, Any]] = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        # Determine which metrics to include
        if columns_config:
            selected = columns_config
        else:
            seen: Dict[str, str] = {}
            for metrics_dict in scope_groups.values():
                for name in metrics_dict:
                    if name not in seen:
                        seen[name] = name
            selected = [(k, k) for k in seen]

        result = []
        for scope, metrics_dict in scope_groups.items():
            row: OrderedDict = OrderedDict()
            row[self.scope_column_name] = scope
            for metric_key, display_label in selected:
                metric = metrics_dict.get(metric_key)
                current_val = round(float(metric.value), 2) if metric and metric.value is not None else 0.00
                baseline_val = round(float(metric.baseline), 2) if metric and metric.baseline is not None else 0.00
                row[f"{display_label} ({baseline_label})"] = baseline_val
                row[f"{display_label} ({current_label})"] = current_val
                if show_diff:
                    diff_val = round(metric.difference, 2) if metric and metric.difference is not None else 0.00
                    row[f"{display_label} ({diff_label})"] = diff_val
                if show_diff_pct:
                    diff_pct_val = round(metric.difference_pct, 2) if metric and metric.difference_pct is not None else 0.00
                    row[f"{display_label} ({diff_pct_label})"] = diff_pct_val
            result.append(row)
        return result

    def format_comparison_metrics_with_diff(
        self,
        columns_config: List[tuple],
        show_diff: bool = False,
        diff_label: str = 'Diff',
        show_diff_pct: bool = False,
        diff_pct_label: str = 'Diff %'
    ) -> List[Dict[str, Any]]:
        """Format metrics in baseline->current format with optional diff columns.

        Each metric gets a "baseline -> current" string column, followed immediately by
        optional Diff and Diff % columns. Rows are OrderedDict to guarantee Option A ordering
        (all columns for one metric grouped together).

        Falls back to _format_metrics_with_config() when no baseline is present.

        Args:
            columns_config: List of (metric_key, display_label) tuples. If empty, all metrics
                            are included using their original key as the label.
            show_diff: Whether to add an absolute difference column per metric.
            diff_label: Suffix for diff columns.
            show_diff_pct: Whether to add a percentage difference column per metric.
            diff_pct_label: Suffix for diff % columns.

        Returns:
            List of OrderedDict rows.
        """
        if not self.has_baseline():
            return self._format_metrics_with_config(columns_config)

        # Group by scope
        scope_groups: Dict[str, Dict[str, Any]] = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        # Determine which metrics to include
        if columns_config:
            selected = columns_config
        else:
            seen: Dict[str, str] = {}
            for metrics_dict in scope_groups.values():
                for name in metrics_dict:
                    if name not in seen:
                        seen[name] = name
            selected = [(k, k) for k in seen]

        result = []
        for scope, metrics_dict in scope_groups.items():
            row: OrderedDict = OrderedDict()
            row[self.scope_column_name] = scope
            for metric_key, display_label in selected:
                metric = metrics_dict.get(metric_key)
                if metric is not None:
                    if metric.baseline is not None:
                        row[display_label] = f"{float(metric.baseline):.2f} -> {float(metric.value):.2f}"
                    else:
                        row[display_label] = f"{float(metric.value):.2f}" if isinstance(metric.value, float) else metric.value
                    if show_diff:
                        diff_val = round(metric.difference, 2) if metric.difference is not None else 0.00
                        row[f"{display_label} ({diff_label})"] = diff_val
                    if show_diff_pct:
                        diff_pct_val = round(metric.difference_pct, 2) if metric.difference_pct is not None else 0.00
                        row[f"{display_label} ({diff_pct_label})"] = diff_pct_val
            result.append(row)
        return result

    def _format_metrics_with_config(self, columns_config: List[tuple]) -> List[Dict[str, Any]]:
        """Format current metrics with optional column filtering and label renaming (no baseline).

        Args:
            columns_config: List of (metric_key, display_label) tuples. If empty, all metrics
                            are included using their original key as the label.

        Returns:
            List of row dicts.
        """
        scope_groups: Dict[str, Dict[str, Any]] = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        result = []
        for scope, metrics_dict in scope_groups.items():
            row: OrderedDict = OrderedDict()
            row[self.scope_column_name] = scope
            if columns_config:
                for metric_key, display_label in columns_config:
                    metric = metrics_dict.get(metric_key)
                    if metric is not None:
                        row[display_label] = round(float(metric.value), 2) if isinstance(metric.value, float) else metric.value
            else:
                for metric_name, metric in metrics_dict.items():
                    row[metric_name] = round(metric.value, 2) if isinstance(metric.value, float) else metric.value
            result.append(row)
        return result

    def set_baseline_metrics(self, baseline_metrics: List[Metric]) -> None:
        """Set baseline values from a list of Metric objects

        This method updates the current metrics with baseline values from the provided metrics list.
        It matches metrics by name and scope to ensure the correct baseline values are applied.

        Args:
            baseline_metrics: A list of Metric objects containing baseline values
        """
        # Create a lookup dictionary to efficiently match baseline metrics
        baseline_lookup = {}
        for baseline_metric in baseline_metrics:
            # Create a unique key using name and scope
            key = f"{baseline_metric.name}_{baseline_metric.scope or 'unknown'}"
            baseline_lookup[key] = baseline_metric

        # Update current metrics with baseline values
        for metric in self.metrics:
            key = f"{metric.name}_{metric.scope or 'unknown'}"
            if key in baseline_lookup:
                # Set baseline value from matching baseline metric
                metric.baseline = round(baseline_lookup[key].value, 2)
                # Recalculate differences
                if metric.baseline is not None and metric.value is not None:
                    metric.difference = round(metric.value - metric.baseline, 2)
                    if metric.baseline != 0:
                        metric.difference_pct = round((metric.difference / metric.baseline) * 100, 2)
                    else:
                        metric.difference_pct = 0.00

    def has_baseline(self) -> bool:
        """Check if baseline metrics are available"""
        # Check if any metrics have baseline values
        return any(metric.baseline is not None for metric in self.metrics)

    def get_metric(self, metric_name: str) -> Any:
        """Get the current value of a specific metric from all records"""
        # Return values from all records that contain this metric
        values = [record.get(metric_name) for record in self.current if metric_name in record]
        return values if values else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the table to a dictionary with all data"""
        result = {
            "current": self.current
        }
        if self.baseline:
            result["baseline"] = self.baseline
        return result

    def to_json_string(self) -> str:
        """Convert the table to a JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=2)
