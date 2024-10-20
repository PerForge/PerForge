from abc import ABC, abstractmethod
from app.config import config_path
from typing import List, Dict, Any, Callable
from functools import wraps
import logging
from app.backend.errors import ErrorMessages
import functools
from datetime import datetime
import pandas as pd


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
        if not isinstance(result, int):
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

class DataExtractionBase(ABC):

    required_metrics = ['overal_throughput', 
                        'overal_users', 
                        'overal_avg_response_time', 
                        'overal_median_response_time',
                        'overal_90_pct_response_time',
                        'overal_errors']

    def __init__(self, project):
        """
        Initialize the DataExtractionBase class with configuration for the data source.
        :param project: Project configuration for the data source.
        """
        self.metric_map  = {}
        self.project     = project
        self.config_path = config_path
        
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
    
    @abstractmethod
    def _fetch_test_log(self) -> List[Dict[str, Any]]:
        """
        Fetch the test log from the data source.
        :return: A list of dictionaries containing test log data.
        """
        pass

    @abstractmethod
    def _fetch_aggregated_table(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Fetch the aggregated table for a test between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries containing aggregated table data.
        """
        pass
    
    @abstractmethod
    def _fetch_start_time(self, test_title: str, time_format: str) -> Any:
        """
        Fetch the start time for a test in the specified time format.
        :param test_title: The title of the test.
        :param time_format: The time format ("human", "iso", "timestamp").
        :return: The start time in the specified format.
        """
        pass
    
    @abstractmethod
    def _fetch_end_time(self, test_title: str, time_format: str) -> Any:
        """
        Fetch the end time for a test in the specified time format.
        :param test_title: The title of the test.
        :param time_format: The time format ("human", "iso", "timestamp").
        :return: The end time in the specified format.
        """
        pass

    @validate_output(expected_keys={'testName', 'duration', 'endTime', 'maxThreads', 'startTime', 'test_title'})
    def get_test_log(self) -> List[Dict[str, Any]]:
        """
        Retrieve the test log data, validated to ensure required fields are present.
        :return: A list of dictionaries containing test log data.
        """
        return self._fetch_test_log()

    @validate_output(expected_keys={'avg', 'count', 'errors', 'pct50', 'pct75', 'pct90', 'rpm', 'stddev', 'transaction'})
    def get_aggregated_table(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Retrieve the aggregated table data for the specified test, validated to ensure required fields are present.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: A list of dictionaries containing aggregated table data.
        """
        return self._fetch_aggregated_table(test_title, start, end)

    @validate_time_format
    def get_start_time(self, test_title: str, **kwargs) -> Any:
        """
        Retrieve the start time for a test, validated for the correct time format.
        :param test_title: The title of the test.
        :param kwargs: Additional arguments, including 'time_format'.
        :return: The start time in the specified format.
        """
        return self._fetch_start_time(test_title, **kwargs)
    
    @validate_time_format
    def get_end_time(self, test_title: str, **kwargs) -> Any:
        """
        Retrieve the end time for a test, validated for the correct time format.
        :param test_title: The title of the test.
        :param kwargs: Additional arguments, including 'time_format'.
        :return: The end time in the specified format.
        """
        return self._fetch_end_time(test_title, **kwargs)
    
    @abstractmethod
    def _fetch_max_active_users(self, test_title: str, start: str, end: str) -> int:
        """
        Fetch the maximum number of active users between the specified time range.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The maximum number of active users.
        """
        pass

    @validate_integer_output
    def get_max_active_users(self, test_title: str, start: str, end: str) -> int:
        """
        Retrieve the maximum number of active users for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The maximum number of active users.
        """
        return self._fetch_max_active_users(test_title, start, end)
    
    @abstractmethod
    def _fetch_test_name(self, test_title: str, start: str, end: str) -> str:
        """
        Fetch the application name for a specific test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The application name.
        """
        pass

    @validate_string_output
    def get_test_name(self, test_title: str, start: str, end: str) -> str:
        """
        Retrieve the application name for the specified test.
        :param test_title: The title of the test.
        :param start: The start time.
        :param end: The end time.
        :return: The application name.
        """
        return self._fetch_test_name(test_title, start, end)
    
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