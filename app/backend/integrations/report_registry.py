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

class ReportRegistry:
    """Registry for report classes with decorator-based registration"""

    # Dictionary to store registered report classes
    _registry = {}

    @classmethod
    def register(cls, report_type):
        """
        Decorator to register a report class for a specific report type

        Args:
            report_type (str): The type of report this class handles

        Returns:
            function: Decorator function
        """
        def decorator(report_class):
            cls._registry[report_type] = report_class
            return report_class
        return decorator

    @classmethod
    def get_report_instance(cls, report_type, project):
        """
        Create and return an instance of the appropriate report class

        Args:
            report_type (str): The type of report to create
            project (str): The project identifier

        Returns:
            Report instance or None if report_type is not supported
        """
        report_class = cls._registry.get(report_type)
        if report_class:
            return report_class(project)
        return None

    @classmethod
    def is_valid_report_type(cls, report_type):
        """
        Check if the given report type is supported

        Args:
            report_type (str): The report type to check

        Returns:
            bool: True if supported, False otherwise
        """
        return report_type in cls._registry

    @classmethod
    def get_supported_report_types(cls):
        """
        Get a list of all supported report types

        Returns:
            list: List of supported report types
        """
        return list(cls._registry.keys())
