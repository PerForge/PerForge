# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

from typing import Optional, Dict, List, Any
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
        'median_response_time_stats',
        'pct90_response_time_stats',
        'errors_pct_stats',
        'ml_anomalies',
        'ml_html_summary'
    ]

    def __init__(self) -> None:
        super().__init__()
        # Load test specific metrics
        self.max_active_users: Optional[int] = None
        self.median_throughput: Optional[float] = None
        self.median_response_time_stats: Optional[float] = None
        self.pct90_response_time_stats: Optional[float] = None
        self.errors_pct_stats: Optional[float] = None
        self.ml_anomalies: Optional[Dict[str, Any]] = None
        self.ml_html_summary: Optional[str] = None

        # Set the test type for backend tests
        self.test_type = "back_end"


class FrontendTestData(BaseTestData):
    """
    Test data specific to frontend web performance tests.

    This class extends the base test data with metrics specific to web performance testing,
    such as page load times, web vitals, and other frontend performance indicators.
    """

    # Define the list of metrics specific to frontend tests
    _frontend_metrics = [
        # Core Web Vitals
        'largest_contentful_paint',
        'first_contentful_paint',
        'cumulative_layout_shift',
        'total_blocking_time',
        'first_input_delay',
        'interaction_to_next_paint',

        # Other important metrics
        'speed_index',
        'time_to_interactive',
        'total_page_size',
        'dom_size',
        'cpu_long_tasks',
        'js_execution_time',

        # Lighthouse scores
        'performance_score',
        'accessibility_score',
        'best_practices_score',
        'seo_score',
        'pwa_score',

        # Resource counts
        'resource_counts'
    ]

    # Common aggregation types used for performance metrics
    _aggregation_types = ['mean', 'median', 'p90', 'p99']

    def __init__(self) -> None:
        super().__init__()
        # Sitespeed.io specific metrics

        # Core Web Vitals - using dictionaries for different aggregations
        self.largest_contentful_paint: Optional[Dict[str, float]] = None  # LCP (ms)
        self.first_contentful_paint: Optional[Dict[str, float]] = None    # FCP (ms)
        self.cumulative_layout_shift: Optional[Dict[str, float]] = None   # CLS (score)
        self.total_blocking_time: Optional[Dict[str, float]] = None       # TBT (ms)
        self.first_input_delay: Optional[Dict[str, float]] = None         # FID (ms)
        self.interaction_to_next_paint: Optional[Dict[str, float]] = None # INP (ms)

        # Other important metrics - using dictionaries for different aggregations
        self.speed_index: Optional[Dict[str, float]] = None               # Speed Index (ms)
        self.time_to_interactive: Optional[Dict[str, float]] = None       # TTI (ms)
        self.total_page_size: Optional[Dict[str, float]] = None           # Total transfer size (bytes)
        self.dom_size: Optional[Dict[str, int]] = None                    # Number of DOM elements
        self.cpu_long_tasks: Optional[Dict[str, int]] = None              # Number of long tasks
        self.js_execution_time: Optional[Dict[str, float]] = None         # JavaScript execution time (ms)

        # Lighthouse scores (0-100) - these remain as single values
        self.performance_score: Optional[float] = None
        self.accessibility_score: Optional[float] = None
        self.best_practices_score: Optional[float] = None
        self.seo_score: Optional[float] = None
        self.pwa_score: Optional[float] = None

        # Resource counts
        self.resource_counts: Optional[Dict[str, int]] = None   # Count by resource type

        # Set the test type for frontend tests
        self.test_type = "front_end"

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
        Set a specific aggregation value for a metric.

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
