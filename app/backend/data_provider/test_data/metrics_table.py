# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

from typing import Dict, Any, Optional, List
import logging
import re

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

    def add_metric(self, metric: Metric) -> None:
        """Add a metric object to the table"""
        self.metrics.append(metric)

    def set_metrics_from_data(self, current_data: List[Dict], baseline_data: Optional[List[Dict]] = None):
        """Convert raw data to Metric objects"""
        self.metrics = []

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

            # Create metrics for each numeric field
            for field_name, value in current_row.items():
                if isinstance(value, (int, float)) and field_name not in ['page', 'transaction']:
                    baseline_value = baseline_row.get(field_name) if baseline_row else None

                    metric = Metric(
                        name=field_name,
                        value=value,
                        scope=current_row.get('page') or current_row.get('transaction'),
                        baseline=baseline_value
                    )
                    self.add_metric(metric)

    def _get_row_key(self, row: Dict[str, Any]) -> str:
        """Generate a unique key for a row to match baseline with current"""
        # Try common identifier fields first
        for key in ['page', 'transaction', 'name', 'id', 'url']:
            if key in row:
                return str(row[key])

        # If no identifier found, use a hash of the serialized dict
        # Exclude highly variable fields that shouldn't affect matching
        matching_dict = {k: v for k, v in row.items() if k not in ['timestamp']}
        return str(hash(frozenset(matching_dict.items())))

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

    def to_display_format(self) -> List[Dict[str, Any]]:
        """Convert metrics to display format with colors"""
        display_data = []

        # Group by scope
        scope_groups = {}
        for metric in self.metrics:
            scope = metric.scope or 'unknown'
            if scope not in scope_groups:
                scope_groups[scope] = {}
            scope_groups[scope][metric.name] = metric

        # Create display rows
        for scope, metrics_dict in scope_groups.items():
            row = {'transaction': scope}
            for metric_name, metric in metrics_dict.items():
                row[metric_name] = metric.value
                row[f"{metric_name}_color"] = metric.get_display_color()  # Color info
                if metric.baseline is not None:
                    row[f"{metric_name}_baseline"] = metric.baseline
                    row[f"{metric_name}_diff"] = metric.difference
                    row[f"{metric_name}_diff_pct"] = metric.difference_pct
            display_data.append(row)

        return display_data

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
            row = {'transaction': scope}
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

        # Check if any metric in a scope has baseline data
        has_baseline_by_scope = {}
        for scope, metrics_dict in scope_groups.items():
            has_baseline_by_scope[scope] = any(m.baseline is not None for m in metrics_dict.values())

        # Create comparison rows
        for scope, metrics_dict in scope_groups.items():
            row = {'transaction': scope}
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
                metric.baseline = baseline_lookup[key].value
                # Recalculate differences
                if metric.baseline is not None and metric.value is not None:
                    metric.difference = metric.value - metric.baseline
                    if metric.baseline != 0:
                        metric.difference_pct = (metric.difference / metric.baseline) * 100
    
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
