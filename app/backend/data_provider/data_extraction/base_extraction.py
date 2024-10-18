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

class DataExtractionBase:
    def __init__(self, config):
        """
        Initialize the DataExtractionBase class with configuration for the data source.
        
        :param config: Configuration dictionary for the data source
        """
        self.config = config
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """
        Initialize the client for the data source.
        This method should be implemented by child classes.
        """
        raise NotImplementedError("Child classes must implement this method.")

    def extract_standard_metrics(self, query):
        """
        Extract standard metrics from the data source.
        This method should be implemented by child classes.
        
        :param query: Query string for the data source
        :return: DataFrame containing the extracted data
        """
        raise NotImplementedError("Child classes must implement this method.")

    def extract_dynamic_metrics(self, query):
        """
        Extract dynamic metrics from the data source.
        This method should be implemented by child classes.
        
        :param query: Query string for the data source
        :return: DataFrame containing the extracted data
        """
        raise NotImplementedError("Child classes must implement this method.")

    def extract_aggregated_statistics(self, query):
        """
        Extract aggregated statistics from the data source.
        This method should be implemented by child classes.
        
        :param query: Query string for the data source
        :return: DataFrame containing the extracted data
        """
        raise NotImplementedError("Child classes must implement this method.")

    def transform_to_unified_format(self, data):
        """
        Transform the extracted data into a unified format.
        
        :param data: DataFrame containing the extracted data
        :return: DataFrame containing the transformed data
        """
        # Implement transformation logic here
        pass

    def validate_unified_format(self, data):
        """
        Validate that the transformed data is in the correct unified format.
        
        :param data: DataFrame containing the transformed data
        :return: bool indicating whether the data is valid
        """
        # Implement validation logic here
        pass

    def check_for_new_data(self, last_timestamp):
        """
        Check if there is new data available since the last timestamp.
        This method should be implemented by child classes.
        
        :param last_timestamp: The timestamp of the last processed data
        :return: bool indicating whether new data is available
        """
        raise NotImplementedError("Child classes must implement this method.")

