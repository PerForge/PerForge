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
        'count_per_content_type',
        'first_party_transfer_size',
        'third_party_transfer_size'
    ]

    def __init__(self) -> None:
        super().__init__()
        # Set the test type for frontend tests
        self.test_type = "front_end"
