# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>

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


# For backward compatibility, map TestData to BackendTestData
# This allows existing code to continue working without changes
TestData = BackendTestData
