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

from abc import ABC, abstractmethod

class QueriesBase(ABC):
    @abstractmethod
    def get_test_log(self, bucket: str) -> str:
        pass

    @abstractmethod
    def get_start_time(self, testTitle: str, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_end_time(self, testTitle: str, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_app_name(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_aggregated_data(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_rps(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_active_threads(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_average_response_time(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_median_response_time(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_pct90_response_time(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_error_count(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_average_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_median_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass

    @abstractmethod
    def get_pct90_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_max_active_users_stats(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_median_throughput_stats(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_median_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_pct90_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass
    
    @abstractmethod
    def get_errors_pct_stats(self, testTitle: str, start: int, stop: int, bucket: str) -> str:
        pass