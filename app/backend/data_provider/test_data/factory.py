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
from .backend_test_data import BackendTestData
from .frontend_test_data import FrontendTestData


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
