# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

import logging
from typing import Optional, Dict, List, Any, Union, Type
from abc import ABC


from app.backend.data_provider.test_data.metrics_table import MetricsTable

class BaseTestData(ABC):
    """
    Abstract base class for all test data types.

    This class defines the common interface and attributes that all test types should have,
    regardless of their specific metrics and characteristics. It provides flexible methods
    for checking and accessing metrics that may not be available in all test types.
    """

    # Common attributes that should be considered metadata, not metrics
    _metadata_attrs = {
        'test_title',
        'start_time_human',
        'end_time_human',
        'start_time_iso',
        'end_time_iso',
        'start_time_timestamp',
        'end_time_timestamp',
        'application',
        'test_type',
        'duration',
        'performance_status'
    }

    # Common aggregation types used for performance metrics across test types
    _aggregation_types = ['mean', 'median', 'p90', 'p99','']

    def __init__(self) -> None:
        # Common attributes for all test types
        self.test_title: Optional[str] = None
        self.start_time_human: Optional[str] = None
        self.end_time_human: Optional[str] = None
        self.start_time_iso: Optional[str] = None
        self.end_time_iso: Optional[str] = None
        self.start_time_timestamp: Optional[float] = None
        self.end_time_timestamp: Optional[float] = None
        self.application: Optional[str] = None
        self.test_type: Optional[str] = None
        self.duration: Optional[str] = None
        self.aggregated_table: Optional[List[Dict[str, Any]]] = None
        self.performance_status: Optional[bool] = None

        # Default aggregation type
        self.aggregation = "median"

        # Dictionary to cache loaded tables with their aggregations
        # Format: {(table_name, aggregation): table_obj}
        self._loaded_tables = {}

        # Data provider reference - will be set by DataProvider.collect_test_obj
        self.data_provider = None

    def calculate_duration(self) -> None:
        """Calculate test duration from start and end timestamps."""
        if self.start_time_timestamp and self.end_time_timestamp:
            self.duration = str(int((self.end_time_timestamp - self.start_time_timestamp) / 1000))

    def has_metric(self, metric_name: str) -> bool:
        """
        Check if a specific metric is available and has a non-None value.

        Args:
            metric_name: Name of the metric to check

        Returns:
            True if the metric exists and has a value, False otherwise
        """
        return hasattr(self, metric_name) and getattr(self, metric_name) is not None

    def get_metric(self, metric_name: str, default_value: Any = None) -> Any:
        """
        Get the value of a metric, with a fallback default value if not available.

        Args:
            metric_name: Name of the metric to retrieve
            default_value: Value to return if the metric is not available

        Returns:
            The metric value or the default value if not available
        """
        if self.has_metric(metric_name):
            return getattr(self, metric_name)
        return default_value

    def set_metric(self, metric_name: str, value: Any) -> None:
        """
        Set the value of a metric.

        Args:
            metric_name: Name of the metric to set
            value: Value to set for the metric
        """
        setattr(self, metric_name, value)

    def get_available_metrics(self) -> List[str]:
        """
        Get a list of all available metrics (non-None values) in this test data object.

        Returns:
            List of metric names that have values
        """
        # Get all metrics and filter out None values
        return [name for name, value in self.get_all_metrics().items() if value is not None]

    def get_metric_names(self) -> List[str]:
        """
        Get a list of all metric names defined for this test data class,
        regardless of whether they have values or not.

        Returns:
            List of all metric names defined for this class
        """
        # Get all instance attributes excluding metadata and methods
        excluded = self._metadata_attrs.union(self._get_method_names())

        return [attr for attr in dir(self)
                if not attr.startswith('_') and
                attr not in excluded and
                not callable(getattr(self, attr, None))]

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get a dictionary of all metrics and their values.

        Returns:
            Dictionary mapping metric names to their values
        """
        metric_names = self.get_metric_names()
        return {name: getattr(self, name) for name in metric_names}

    def _get_method_names(self) -> set:
        """
        Helper method to get names of all methods in this class.

        Returns:
            Set of method names
        """
        return {attr for attr in dir(self)
                if not attr.startswith('__') and
                callable(getattr(self, attr))}

    def get_metric_aggregation(self, metric_name: str, aggregation: str, default_value: Any = None) -> Any:
        """
        Get a specific aggregation value of a metric.

        Args:
            metric_name: Name of the metric to retrieve
            aggregation: Aggregation type (mean, median, p90, etc.)
            default_value: Value to return if the metric or aggregation is not available

        Returns:
            The metric aggregation value or the default value if not available
        """
        metric = self.get_metric(metric_name, {})
        if isinstance(metric, dict):
            return metric.get(aggregation, default_value)
        # For backward compatibility with non-dict metrics
        return metric if metric is not None else default_value

    def set_metric_aggregation(self, metric_name: str, aggregation: str, value: Any) -> None:
        """
        Set a specific aggregation value for a metric and update the default aggregation if needed.

        Args:
            metric_name: Name of the metric to set
            aggregation: Aggregation type (mean, median, p90, etc.)
            value: Value to set for the metric aggregation
        """
        metric = self.get_metric(metric_name)
        # Initialize the dictionary if it doesn't exist
        if not isinstance(metric, dict):
            metric = {}
            self.set_metric(metric_name, metric)
        metric[aggregation] = value

        # Legacy support for updating aggregation via metric name
        if metric_name == 'default_aggregation':
            self.set_aggregation_type(aggregation)

    def get_table(self, table_name: str, aggregation: str = None) -> Any:
        """
        Get a table with specific aggregation, loading it if needed.

        Args:
            table_name: Base name of the table (e.g., 'timings_fully_loaded')
            aggregation: Specific aggregation to use ('median', 'mean', 'p90', 'p99')
                          If None, uses the default aggregation

        Returns:
            MetricsTable object or None if table couldn't be loaded
        """
        # Use default aggregation if none specified
        aggregation = aggregation or self.aggregation

        # Validate aggregation type
        if aggregation not in self._aggregation_types:
            logging.warning(f"'{aggregation}' is not a recognized aggregation type. Using '{self.aggregation}' instead.")
            aggregation = self.aggregation

        # Check if table name is valid - child classes should override to add their specific metrics
        table_metrics = getattr(self, '_table_metrics', [])
        if not table_metrics or table_name not in table_metrics:
            logging.warning(f"Table '{table_name}' is not a recognized metric table for {self.__class__.__name__}.")
            return None

        # Create a cache key for this table+aggregation combination
        cache_key = (table_name, aggregation)

        # Check if we already have this table loaded
        if cache_key in self._loaded_tables:
            return self._loaded_tables[cache_key]

        # Load the table if we have a data provider reference
        if self.data_provider:
            try:
                # Get the data from the data provider
                table_data = getattr(self.data_provider.ds_obj, f'get_{table_name}', None)

                if table_data and callable(table_data):
                    current_data = table_data(
                        test_title=self.test_title,
                        start=self.start_time_iso,
                        end=self.end_time_iso,
                        aggregation=aggregation
                    )

                    # Create a new MetricsTable object
                    table = MetricsTable(name=table_name, aggregation=aggregation)
                    table.set_metrics_from_data(current_data, None)

                    # Cache the table
                    self._loaded_tables[cache_key] = table
                    return table

            except Exception as e:
                logging.warning(f"Failed to load table '{table_name}' with aggregation '{aggregation}': {e}")
                return None

        logging.warning(f"Cannot load table '{table_name}' - no data provider available")
        return None

    def set_aggregation_type(self, aggregation: str) -> None:
        """
        Set the default aggregation type for this test data object.

        Note: This only updates the aggregation type variable. To fully apply this to tables,
        they would need to be reinitialized with the new aggregation type.

        Args:
            aggregation: The aggregation type to use ("mean", "median", "p90", "p99", etc.)
        """
        if aggregation in self._aggregation_types:
            self.aggregation = aggregation
        else:
            logging.warning(f"'{aggregation}' is not a recognized aggregation type. Aggregation type unchanged.")

    def get_all_tables(self) -> Dict[str, MetricsTable]:
        """
        Preload and return all available tables with their default aggregation.

        This method will load all tables defined in _table_metrics using the default aggregation.
        If a table is already loaded, it will use the cached version.

        Returns:
            Dictionary mapping table names to MetricsTable objects
        """
        result = {}
        table_metrics = getattr(self, '_table_metrics', [])

        # Load all tables with default aggregation
        for table_name in table_metrics:
            table = self.get_table(table_name, self.aggregation)
            if table:
                result[table_name] = table

        return result

    def get_all_tables_json(self) -> str:
        """
        Get all tables as a JSON string representation in an optimized format.

        This method collects all tables and converts them to a flat list of metrics,
        where each metric contains: metric name, transaction/scope, value, NFR status,
        baseline (if available), and difference calculations.

        Returns:
            JSON string containing all tables with their metrics in a flat format
        """
        import json
        tables = self.get_all_tables()

        # Convert tables to the flat metrics format
        result = {}
        for table_name, table in tables.items():
            # Initialize table entry with metadata
            table_dict = {
                'name': table.name,
                'aggregation': table.aggregation,
                'metrics': []
            }

            # Use metrics if available (preferred path)
            if hasattr(table, 'metrics') and table.metrics:
                # Create a flat list of metrics
                for metric in table.metrics:
                    metric_dict = {
                        'metric': metric.name,
                        'transaction': metric.scope or 'unknown',
                        'value': metric.value,
                        'nfr_status': metric.nfr_status.value if hasattr(metric.nfr_status, 'value') else str(metric.nfr_status)
                    }
                    # Add baseline and differences if available
                    if metric.baseline is not None:
                        metric_dict['baseline'] = metric.baseline
                    if metric.difference is not None:
                        metric_dict['difference'] = metric.difference
                    if metric.difference_pct is not None:
                        metric_dict['difference_pct'] = metric.difference_pct

                    table_dict['metrics'].append(metric_dict)

            result[table_name] = table_dict

        return json.dumps(result, indent=2)
