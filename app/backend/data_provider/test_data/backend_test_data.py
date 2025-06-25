# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

from typing import Optional

from .base_test_data import BaseTestData


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
        'aggregated_data'  # Added aggregated data for NFR validation
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
