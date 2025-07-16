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

import logging
import pandas as pd

from app.backend.errors                          import ErrorMessages
from abc                                         import ABC, abstractmethod
from typing                                      import List, Dict, Any, Callable
from functools                                   import wraps
from datetime                                    import datetime


def validate_output(expected_keys: set):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            for record in result:
                record_keys = set(record.keys())
                if not expected_keys.issubset(record_keys):
                    logging.warning(ErrorMessages.ER00055.value.format(expected_keys))
                    return []
            return result
        return wrapper
    return decorator


def validate_time_format(func):
    def wrapper(self, *args, **kwargs):
        time_format = kwargs.get('time_format', 'iso')
        valid_formats = {
            'human': lambda r: isinstance(r, str) and datetime.strptime(r, "%Y-%m-%d %I:%M:%S %p"),
            'iso': lambda r: isinstance(r, str) and datetime.strptime(r, "%Y-%m-%dT%H:%M:%SZ"),
            'timestamp': lambda r: isinstance(r, int)
        }

        if time_format not in valid_formats:
            raise ValueError(f"Invalid time format: {time_format}. Valid formats: {list(valid_formats.keys())}")

        result = func(self, *args, **kwargs)

        try:
            valid_formats[time_format](result)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid return format for {time_format} time: {result}")

        return result
    return wrapper

def validate_integer_output(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not isinstance(result, int):
            raise ValueError(f"The return value must be an integer, got {type(result).__name__} instead.")
        return result
    return wrapper

def validate_string_output(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not isinstance(result, str):
            raise ValueError(f"The return value must be a string, got {type(result).__name__} instead.")
        return result
    return wrapper

def validate_dataframe_output(expected_columns: List[str], expected_index: str = 'timestamp'):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if not isinstance(result, pd.DataFrame):
                raise ValueError(f"The return value must be a pandas DataFrame, got {type(result).__name__} instead.")
            if result.index.name != expected_index:
                raise ValueError(f"The DataFrame index must be '{expected_index}', got {result.index.name} instead.")
            if set(result.columns) != set(expected_columns):
                raise ValueError(f"The DataFrame must contain the columns: {expected_columns}. Got columns: {result.columns.tolist()}")
            return result
        return wrapper
    return decorator

def validate_dict_output(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not isinstance(result, list):
            raise ValueError(f"The return value must be a list, got {type(result).__name__} instead.")
        for entry in result:
            if not isinstance(entry, dict):
                raise ValueError(f"All entries in the list must be dictionaries, got {type(entry).__name__} instead.")
            if 'transaction' not in entry or 'data' not in entry:
                raise ValueError(f"Each dictionary must contain 'transaction' and 'data' keys.")
            if not isinstance(entry['data'], pd.DataFrame):
                raise ValueError(f"The 'data' key must contain a pandas DataFrame, got {type(entry['data']).__name__} instead.")
            if entry['data'].index.name != 'timestamp' or 'value' not in entry['data'].columns:
                raise ValueError(f"The DataFrame must have 'timestamp' as the index and a 'value' column.")
        return result
    return wrapper

def validate_float_output(func: Callable):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not isinstance(result, float):
            raise ValueError(f"The return value must be a float, got {type(result).__name__} instead.")
        return result
    return wrapper

class DataExtractionBase(ABC):
    """
    Abstract base class for all data extraction implementations.
    Provides common infrastructure for metrics extraction with clear separation
    between backend and frontend metrics.
    """

    # Backend required metrics
    required_backend_metrics = ['overal_throughput',
                              'overal_users',
                              'overal_avg_response_time',
                              'overal_median_response_time',
                              'overal_90_pct_response_time',
                              'overal_errors']

    # Frontend required metrics
    required_frontend_metrics = ['google_web_vitals',
                               'timings_fully_loaded',
                               'timings_page_timings',
                               'timings_main_document']

    def __init__(self, project):
        """
        Initialize the DataExtractionBase class with configuration for the data source.
        :param project: Project configuration for the data source.
        """
        self.project = project
        self.metric_map = {}

    @abstractmethod
    def set_config(self):
        """
        Initialize the client for the data source.
        This method should be implemented by child classes.
        """
        raise NotImplementedError("Child classes must implement this method.")

    @abstractmethod
    def _initialize_client(self):
        """
        Initialize the client for the data source.
        This method should be implemented by child classes.
        """
        raise NotImplementedError("Child classes must implement this method.")

    @abstractmethod
    def _close_client(self):
        """
        Close the client for the data source.
        This method should be implemented by child classes.
        """
        raise NotImplementedError("Child classes must implement this method.")

    # Common methods for all extraction types
    @abstractmethod
    def _fetch_test_log(self) -> List[Dict[str, Any]]:
        """
        Fetch the test log from the data source.
        :return: A list of dictionaries containing test log data.
        """
        pass

    @validate_output(expected_keys={'duration', 'end_time', 'max_threads', 'start_time', 'test_title'})
    def get_test_log(self) -> List[Dict[str, Any]]:
        """
        Retrieve the test log data, validated to ensure required fields are present.
        Results are sorted by test_title in descending order.

        :return: A list of dictionaries containing test log data, sorted by test_title in descending order.
        """
        test_log = self._fetch_test_log()

        # Sort by test_title in descending order
        if test_log:
            test_log.sort(key=lambda x: x.get('test_title', ''), reverse=True)

        return test_log

    @abstractmethod
    def _fetch_start_time(self, test_title: str, time_format: str) -> Any:
        """
        Fetch the start time for a test in the specified time format.
        :param test_title: The title of the test.
        :param time_format: The time format ("human", "iso", "timestamp").
        :return: The start time in the specified format.
        """
        pass

    @validate_time_format
    def get_start_time(self, test_title: str, **kwargs) -> Any:
        """
        Retrieve the start time for a test, validated for the correct time format.
        :param test_title: The title of the test.
        :param kwargs: Additional arguments, including 'time_format'.
        :return: The start time in the specified format.
        """
        return self._fetch_start_time(test_title, **kwargs)

    @abstractmethod
    def _fetch_end_time(self, test_title: str, time_format: str) -> Any:
        """
        Fetch the end time for a test in the specified time format.
        :param test_title: The title of the test.
        :param time_format: The time format ("human", "iso", "timestamp").
        :return: The end time in the specified format.
        """
        pass

    @validate_time_format
    def get_end_time(self, test_title: str, **kwargs) -> Any:
        """
        Retrieve the end time for a test, validated for the correct time format.
        :param test_title: The title of the test.
        :param kwargs: Additional arguments, including 'time_format'.
        :return: The end time in the specified format.
        """
        return self._fetch_end_time(test_title, **kwargs)

    # ===================================================================
    # Backend metrics extraction methods
    # ===================================================================

    @abstractmethod
    def _fetch_aggregated_data(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Fetch the aggregated table for a test between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries containing aggregated table data.
        """
        pass

    @validate_output(expected_keys={'avg', 'count', 'errors', 'pct50', 'pct75', 'pct90', 'rpm', 'stddev', 'transaction'})
    def get_aggregated_data(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> List[Dict[str, Any]]:
        """
        Retrieve the aggregated table data for the specified test, validated to ensure required fields are present.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :param aggregation: The aggregation type to use ('median', 'mean', 'p90', 'p99').
        :return: A list of dictionaries containing aggregated table data.
        """
        try:
            aggregated_table = self._fetch_aggregated_data(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting aggregated table: {str(e)}")
            aggregated_table = []
        return aggregated_table

    @abstractmethod
    def _fetch_rps(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the RPS (Requests per Second) data between specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The RPS data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_rps(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the RPS (Requests per Second) data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The RPS data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_rps(test_title, start, end)

    @abstractmethod
    def _fetch_active_threads(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the active threads data between specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The active threads data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_active_threads(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the active threads data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The active threads data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_active_threads(test_title, start, end)

    @abstractmethod
    def _fetch_average_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the average response time data between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The average response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_average_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the average response time data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The average response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_average_response_time(test_title, start, end)

    @abstractmethod
    def _fetch_median_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the median response time data between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_median_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the median response time data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_median_response_time(test_title, start, end)

    @abstractmethod
    def _fetch_pct90_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the 90th percentile (PCT90) response time data between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The 90th percentile response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_pct90_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the 90th percentile (PCT90) response time data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The 90th percentile response time data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_pct90_response_time(test_title, start, end)

    @abstractmethod
    def _fetch_error_count(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch the error count data between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The error count data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        pass

    @validate_dataframe_output(expected_columns=['value'], expected_index='timestamp')
    def get_error_count(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        """
        Retrieve the error count data for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The error count data as a pandas DataFrame with columns 'timestamp' and 'value'.
        """
        return self._fetch_error_count(test_title, start, end)

    @abstractmethod
    def _fetch_average_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Fetch the average response time per request between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        pass

    @validate_dict_output
    def get_average_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Retrieve the average response time per request for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        return self._fetch_average_response_time_per_req(test_title, start, end)

    @abstractmethod
    def _fetch_median_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Fetch the median response time per request between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        pass

    @validate_dict_output
    def get_median_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Retrieve the median response time per request for the specified test.
        The result is validated to ensure it is a list of dictionaries with the correct structure.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        return self._fetch_median_response_time_per_req(test_title, start, end)

    @abstractmethod
    def _fetch_pct90_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Fetch the 90th percentile response time per request between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        pass

    @validate_dict_output
    def get_pct90_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Retrieve the 90th percentile (PCT90) response time per request for the specified test.
        The result is validated to ensure it is a list of dictionaries with the correct structure.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        return self._fetch_pct90_response_time_per_req(test_title, start, end)

    @abstractmethod
    def _fetch_max_active_users_stats(self, test_title: str, start: str, end: str) -> int:
        """
        Fetch the maximum number of active users between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The maximum number of active users.
        """
        pass

    @validate_integer_output
    def get_max_active_users_stats(self, test_title: str, start: str, end: str) -> int:
        """
        Retrieve the maximum number of active users for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The maximum number of active users.
        """
        try:
            value = self._fetch_max_active_users_stats(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting max active users: {str(e)}")
            value = 0
        return value

    @abstractmethod
    def _fetch_median_throughput_stats(self, test_title: str, start: str, end: str) -> int:
        """
        Fetch the median throughput stats between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median throughput stats as an integer.
        """
        pass

    @validate_integer_output
    def get_median_throughput_stats(self, test_title: str, start: str, end: str) -> int:
        """
        Retrieve the median throughput stats for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median throughput stats as an integer.
        """
        try:
            value = self._fetch_median_throughput_stats(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting median throughput: {str(e)}")
            value = 0
        return value

    @abstractmethod
    def _fetch_median_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Fetch the median response time stats between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median response time stats as a float.
        """
        pass

    @validate_float_output
    def get_median_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Retrieve the median response time stats for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The median response time stats as a float.
        """
        try:
            value = self._fetch_median_response_time_stats(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting median response time stats: {str(e)}")
            value = 0.0
        return value

    @abstractmethod
    def _fetch_pct90_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Fetch the 90th percentile response time stats between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The 90th percentile response time stats as a float.
        """
        pass

    @validate_float_output
    def get_pct90_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Retrieve the 90th percentile response time stats for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The 90th percentile response time stats as a float.
        """
        try:
            value = self._fetch_pct90_response_time_stats(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting 90th percentile response time stats: {str(e)}")
            value = 0.0
        return value

    @abstractmethod
    def _fetch_errors_pct_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Fetch the percentage of errors between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The percentage of errors as a float.
        """
        pass

    @validate_float_output
    def get_errors_pct_stats(self, test_title: str, start: str, end: str) -> float:
        """
        Retrieve the percentage of errors for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The percentage of errors as a float.
        """
        try:
            value = self._fetch_errors_pct_stats(test_title, start, end)
        except Exception as e:
            logging.warning(f"Error getting errors percentage stats: {str(e)}")
            value = 0.0
        return value

    # ===================================================================
    # Frontend metrics extraction methods
    # ===================================================================

    @abstractmethod
    def _fetch_google_web_vitals(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch Google Web Vitals metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of Google Web Vitals metrics
        """
        pass

    def get_google_web_vitals(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve Google Web Vitals metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of Google Web Vitals metrics
        """
        try:
            result = self._fetch_google_web_vitals(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting Google Web Vitals: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_timings_fully_loaded(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch fully loaded timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of fully loaded timing metrics
        """
        pass

    def get_timings_fully_loaded(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve fully loaded timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of fully loaded timing metrics
        """
        try:
            result = self._fetch_timings_fully_loaded(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting fully loaded timings: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_timings_page_timings(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch page timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of page timing metrics
        """
        pass

    def get_timings_page_timings(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve page timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of page timing metrics
        """
        try:
            result = self._fetch_timings_page_timings(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting page timings: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_timings_main_document(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch main document timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of main document timing metrics
        """
        pass

    def get_timings_main_document(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve main document timing metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of main document timing metrics
        """
        try:
            result = self._fetch_timings_main_document(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting main document timings: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_cpu_long_tasks(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch CPU long tasks metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of CPU long tasks metrics
        """
        pass

    def get_cpu_long_tasks(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve CPU long tasks metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of CPU long tasks metrics
        """
        try:
            result = self._fetch_cpu_long_tasks(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting CPU long tasks: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_cdp_performance_js_heap_used_size(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch JavaScript heap used size metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap used size metrics
        """
        pass

    def get_cdp_performance_js_heap_used_size(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve JavaScript heap used size metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap used size metrics
        """
        try:
            result = self._fetch_cdp_performance_js_heap_used_size(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting JS heap used size: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_cdp_performance_js_heap_total_size(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch JavaScript heap total size metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap total size metrics
        """
        pass

    def get_cdp_performance_js_heap_total_size(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve JavaScript heap total size metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap total size metrics
        """
        try:
            result = self._fetch_cdp_performance_js_heap_total_size(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting JS heap total size: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of content type metrics
        """
        pass

    def get_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of content type metrics
        """
        try:
            result = self._fetch_content_types(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting content types: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_first_party_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch first party content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of first party content type metrics
        """
        pass

    def get_first_party_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve first party content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of first party content type metrics
        """
        try:
            result = self._fetch_first_party_content_types(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting first party content types: {str(e)}")
            result = {}
        return result

    @abstractmethod
    def _fetch_third_party_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch third party content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of third party content type metrics
        """
        pass

    def get_third_party_content_types(self, test_title: str, start: str, end: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Retrieve third party content type metrics from frontend test.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of third party content type metrics
        """
        try:
            result = self._fetch_third_party_content_types(test_title, start, end, aggregation)
        except Exception as e:
            logging.warning(f"Error getting third party content types: {str(e)}")
            result = {}
        return result
