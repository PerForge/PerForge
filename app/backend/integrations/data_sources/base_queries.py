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

from abc import ABC, abstractmethod

class BackEndQueriesBase(ABC):
    @abstractmethod
    def get_test_log(
        self,
        bucket: str,
        test_title_tag_name: str,
        *,
        sort_by: str | None = None,
        sort_dir: str = "desc",
        limit: int | None = None,
        offset: int = 0,
    ) -> str:
        pass

    @abstractmethod
    def get_tests_titles(self, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_aggregated_data(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_rps(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_active_threads(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_average_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_median_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_pct90_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_error_count(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_average_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_median_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_pct90_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_max_active_users_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_median_throughput_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_median_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_pct90_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_errors_pct_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        pass


class FrontEndQueriesBase(ABC):
    @abstractmethod
    def get_tests_titles(self, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_test_log(
        self,
        bucket: str,
        test_title_tag_name: str,
        *,
        test_titles: list[str],
        start_time: str,
        end_time: str,
    ) -> str:
        pass

    @abstractmethod
    def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        pass

    @abstractmethod
    def get_google_web_vitals(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_timings_fully_loaded(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_timings_page_timings(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_timings_main_document(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_cpu_long_tasks(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_cdp_performance_js_heap_used_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_cdp_performance_js_heap_total_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_count_per_content_type(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_first_party_transfer_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass

    @abstractmethod
    def get_third_party_transfer_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
        pass
