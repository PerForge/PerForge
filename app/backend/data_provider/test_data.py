# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

import logging
from typing import Optional, Dict, List, Any, Union, Type
from abc import ABC


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
        'aggregated_table',
        'performance_status'
    }

    # Common aggregation types used for performance metrics across test types
    _aggregation_types = ['mean', 'median', 'p90', 'p99']

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

        # Import the MetricsTable class
        from app.backend.data_provider.metrics_table import MetricsTable
        self.MetricsTable = MetricsTable

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

        # Check if we've already loaded this table with this aggregation
        if cache_key not in self._loaded_tables:
            # Create the table with specified aggregation
            table = self.MetricsTable(f"{table_name}_table_{aggregation}", aggregation=aggregation)

            # Load data if we have a data provider
            if hasattr(self, 'data_provider') and self.data_provider is not None:
                # Determine method to call based on table name
                method_name = f"get_{table_name}"
                if hasattr(self.data_provider.ds_obj, method_name):
                    try:
                        method = getattr(self.data_provider.ds_obj, method_name)
                        value = method(
                            test_title=self.test_title,
                            start=self.start_time_iso,
                            end=self.end_time_iso,
                            bucket=self.data_provider.ds_obj.bucket,
                            aggregation=aggregation
                        )

                        # Set metrics in the table
                        table.set_current_metrics(value)

                        # Store in cache
                        self._loaded_tables[cache_key] = table

                        logging.info(f"Lazy loaded table '{table_name}' with aggregation '{aggregation}'")
                    except Exception as e:
                        logging.warning(f"Error loading table {table_name} with {aggregation}: {e}")
                        return None
                else:
                    logging.warning(f"Method get_{table_name} not found in data source")
                    return None
            else:
                logging.warning("No data provider available to load table data")
                return None

        # Return the cached table
        return self._loaded_tables.get(cache_key)

    def set_current_metrics_for_table(self, table_name: str, metrics_data: Dict[str, Any]) -> None:
        """
        Set current metrics for a specified MetricsTable.

        Args:
            table_name: The snake_case name of the metrics table (e.g., 'google_web_vitals')
            metrics_data: Dictionary containing the metrics data
        """
        # Get or create the table with default aggregation
        table = self.get_table(table_name)
        if table is not None:
            table.set_current_metrics(metrics_data)

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
            # Log warning that an unsupported aggregation type was provided
            logging.warning(f"'{aggregation}' is not a recognized aggregation type. Using '{self.aggregation}' instead.")

    def set_baseline_metrics_for_table(self, table_name: str, metrics_data: Dict[str, Any]) -> None:
        """
        Set baseline metrics for a specified MetricsTable.

        Args:
            table_name: The snake_case name of the metrics table (e.g., 'google_web_vitals')
            metrics_data: Dictionary containing the baseline metrics data
        """
        # Get or create the table with default aggregation
        table = self.get_table(table_name)
        if table is not None:
            table.set_baseline_metrics(metrics_data)

    def set_baseline_metrics_for_all_tables(self, baseline_test_data: 'BaseTestData') -> None:
        """
        Set baseline metrics for all loaded MetricsTable instances from another test data object.
        Note: This only sets baseline metrics for tables that are already loaded in the current object.

        Args:
            baseline_test_data: Another test data object containing baseline metrics
        """
        # For each loaded table in baseline_test_data, set the baseline metrics in this object
        if not hasattr(baseline_test_data, '_loaded_tables'):
            # Handle backward compatibility with old test data instances
            logging.warning("Baseline test data does not support lazy loading")
            return

        # Get the list of metrics tables for this class
        table_metrics = getattr(self, '_table_metrics', [])
        if not table_metrics:
            return

        # Iterate through all table names defined in the class
        for table_name in table_metrics:
            # Get the baseline table if it's loaded in the baseline object
            for (name, agg), baseline_table in baseline_test_data._loaded_tables.items():
                if name == table_name:
                    # Get or create this table with the same aggregation
                    current_table = self.get_table(table_name, agg)
                    if current_table and baseline_table:
                        baseline_metrics = baseline_table.get_current_metrics()
                        if baseline_metrics:
                            current_table.set_baseline_metrics(baseline_metrics)


class BackendTestData(BaseTestData):
    """
    Test data specific to backend performance tests.

    This class extends the base test data with metrics specific to backend testing,
    such as user counts, throughput, response times, and error rates.
    """

    # Define the list of metrics specific to backend tests
    _backend_metrics = [
        'max_active_users',
        'median_throughput',
        'median_response_time',
        'error_rate',
        'test_duration',
        'rps'
    ]

    # Define backend table metrics for lazy loading
    _table_metrics = [
        # Future backend tables can be added here
        'response_times',
        'throughput',
        'errors',
        'active_users'
    ]

    def __init__(self) -> None:
        super().__init__()
        # Set the test type for backend tests
        self.test_type = "back_end"

        # Initialize backend test specific metrics
        self.max_active_users: Optional[int] = None
        self.median_throughput: Optional[float] = None
        self.median_response_time: Optional[float] = None
        self.error_rate: Optional[float] = None
        self.test_duration: Optional[str] = None
        self.rps: Optional[float] = None


class FrontendTestData(BaseTestData):
    """
    Test data specific to frontend web performance tests.

    This class extends the base test data with metrics specific to web performance testing,
    such as page load times, web vitals, and other frontend performance indicators.

    This class implements lazy loading for metric tables, which means tables are only
    loaded when they are actually accessed or requested by templates.
    """

    # Metric table names that are available for lazy loading - used by the base class's get_table method
    _table_metrics = [
        # SiteSpeed tables
        'google_web_vitals',
        'timings_fully_loaded',
        'timings_page_timings',
        'timings_main_document',
        'cpu_long_tasks',
        'cdp_performance_js_heap_used_size',
        'cdp_performance_js_heap_total_size',
        'content_types',
        'first_party_content_types',
        'third_party_content_types'
    ]

    def __init__(self) -> None:
        super().__init__()
        # Set the test type for frontend tests
        self.test_type = "front_end"

    # All table-related methods are now inherited from BaseTestData


class TestDataFactory:
    """
    Factory class to create the appropriate test data object based on test type
    """

    @staticmethod
    def create_test_data(test_type: str) -> BaseTestData:
        """
        Create and return the appropriate test data object based on test type

        Args:
            test_type: Type of test ("back_end", "front_end", etc.)

        Returns:
            Instance of the appropriate test data class
        """
        if test_type == "front_end":
            return FrontendTestData()
        # Default to backend test for backward compatibility
        return BackendTestData()


# For backward compatibility, map TestData to BackendTestData
# This allows existing code to continue working without changes
TestData = BackendTestData
