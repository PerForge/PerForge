# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

from typing import Dict, Any, List
import logging

from .base_test_data import BaseTestData


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
