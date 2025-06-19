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

from app.backend.integrations.data_sources.base_extraction                                      import DataExtractionBase
from app.backend.integrations.data_sources.base_queries                                         import BackEndQueriesBase, FrontEndQueriesBase
from app.backend.integrations.data_sources.influxdb_v2.queries.influxdb_backend_listener_client import InfluxDBBackendListenerClientImpl
from app.backend.integrations.data_sources.influxdb_v2.queries                                  import mderevyankoaqa
from app.backend.integrations.data_sources.influxdb_v2.queries.sitespeed_influxdb_v2            import SitespeedFluxQueries
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db                              import DBInfluxdb
from app.backend.components.secrets.secrets_db                                                  import DBSecrets
from app.backend.errors                                                                         import ErrorMessages
from influxdb_client                                                                            import InfluxDBClient
from datetime                                                                                   import datetime
from dateutil                                                                                   import tz
from typing                                                                                     import List, Dict, Any, Type
from collections                                                                                import defaultdict


class InfluxdbV2(DataExtractionBase):
    """
    InfluxDB V2 data extraction implementation that handles both frontend and backend metrics.
    Uses a query mapping system to select the appropriate query implementation based on source type.
    """

    # Maps source types to their respective query implementations
    queries_map: Dict[str, Type[BackEndQueriesBase | FrontEndQueriesBase]] = {
        # Backend query implementations
        "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient": InfluxDBBackendListenerClientImpl,
        "mderevyankoaqa": mderevyankoaqa,

        # Frontend query implementations
        "sitespeed_influxdb_v2": SitespeedFluxQueries
    }

    def __init__(self, project, id=None):
        super().__init__(project)
        self.set_config(id)
        self.tmz_utc = tz.tzutc()
        self.tmz_human = tz.tzutc() if self.tmz == "UTC" else tz.gettz(self.tmz)
        if self.listener in self.queries_map:
            # Instantiate the correct client class
            self.queries = self.queries_map[self.listener]()
        else:
            self.queries = None
            logging.warning(ErrorMessages.ER00054.value.format(self.listener))

        self._initialize_client()

    def __str__(self):
        return str(self.to_dict())

    def __enter__(self):
        self._initialize_client()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close_client()

    def set_config(self, id):
        id     = id if id else DBInfluxdb.get_default_config(project_id=self.project)["id"]
        config = DBInfluxdb.get_config_by_id(project_id=self.project, id=id)
        if config["id"]:
            self.id       = config["id"]
            self.name     = config["name"]
            self.url      = config["url"].replace("influxdb", "localhost")
            self.org_id   = config["org_id"]
            self.token    = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]
            self.timeout  = config["timeout"]
            self.bucket   = config["bucket"]
            self.listener = config["listener"]
            self.tmz      = config["tmz"]
        else:
            logging.warning("There's no InfluxDB integration configured, or you're attempting to send a request from an unsupported location.")

    def _initialize_client(self):
        try:
            self.influxdb_connection = InfluxDBClient(
                url=self.url, org=self.org_id, token=self.token, timeout=int(self.timeout)
            )
        except Exception as er:
            logging.error(ErrorMessages.ER00052.value.format(self.name))
            logging.error(er)

    def _close_client(self):
        if self.influxdb_connection:
            try:
                self.influxdb_connection.close()
            except Exception as er:
                logging.error(ErrorMessages.ER00053.value.format(self.name))
                logging.error(er)

    def _fetch_test_log(self) -> List[Dict[str, Any]]:
        try:
            query = self.queries.get_test_log(self.bucket)
            records = self._execute_query(query)

            df = pd.DataFrame(records)
            sorted_df = df.sort_values(by='start_time')
            return sorted_df.to_dict(orient='records')
        except Exception as er:
            logging.error(ErrorMessages.ER00057.value.format(self.name))
            logging.error(er)
            return []

    def _fetch_aggregated_table(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        try:
            query = self.queries.get_aggregated_data(test_title, start, end, self.bucket)
            return self._execute_query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00058.value.format(self.name))
            logging.error(er)
            return []

    def _fetch_start_time(self, test_title: str, time_format: str) -> Any:
        try:
            query       = self.queries.get_start_time(test_title, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table.records:
                    if time_format == "human":
                        return datetime.strftime(flux_record["_time"].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
                    elif time_format == "iso":
                        return datetime.strftime(flux_record["_time"], "%Y-%m-%dT%H:%M:%SZ")
                    elif time_format == "timestamp":
                        return int(flux_record["_time"].astimezone(self.tmz_utc).timestamp() * 1000)
        except Exception as er:
            logging.error(ErrorMessages.ER00059.value.format(self.name))
            logging.error(er)
            return None

    def _fetch_end_time(self, test_title: str, time_format: str) -> Any:
        try:
            query       = self.queries.get_end_time(test_title, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table.records:
                    if time_format == "human":
                        return datetime.strftime(flux_record["_time"].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
                    elif time_format == "iso":
                        return datetime.strftime(flux_record["_time"], "%Y-%m-%dT%H:%M:%SZ")
                    elif time_format == "timestamp":
                        return int(flux_record["_time"].astimezone(self.tmz_utc).timestamp() * 1000)
        except Exception as er:
            logging.error(ErrorMessages.ER00060.value.format(self.name))
            logging.error(er)
            return None

    def _fetch_application(self, test_title: str, start: str, end: str) -> str:
        try:
            query       = self.queries.get_app_name(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    appName = flux_record['application']
            return appName
        except Exception as er:
            logging.error(ErrorMessages.ER00062.value.format(self.name))
            logging.error(er)
            return ""

    def _fetch_rps(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_rps(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00063.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_active_threads(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_active_threads(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00064.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_average_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_average_response_time(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00065.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_median_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_median_response_time(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00066.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_pct90_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_pct90_response_time(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00067.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_error_count(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        try:
            query       = self.queries.get_error_count(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            df          = self.process_data(flux_tables)
            return df
        except Exception as er:
            logging.error(ErrorMessages.ER00068.value.format(self.name))
            logging.error(er)
            return pd.DataFrame()

    def _fetch_average_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        try:
            query       = self.queries.get_average_response_time_per_req(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            result      = self.transform_flux_tables_to_dict(flux_tables)
            return result
        except Exception as er:
            logging.error(ErrorMessages.ER00069.value.format(self.name))
            logging.error(er)
            return []

    def _fetch_median_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        try:
            query       = self.queries.get_median_response_time_per_req(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            result      = self.transform_flux_tables_to_dict(flux_tables)
            return result
        except Exception as er:
            logging.error(ErrorMessages.ER00070.value.format(self.name))
            logging.error(er)
            return []

    def _fetch_pct90_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        try:
            query       = self.queries.get_pct90_response_time_per_req(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            result      = self.transform_flux_tables_to_dict(flux_tables)
            return result
        except Exception as er:
            logging.error(ErrorMessages.ER00071.value.format(self.name))
            logging.error(er)
            return []

    def _fetch_max_active_users_stats(self, test_title: str, start: str, end: str) -> int:
        try:
            query       = self.queries.get_max_active_users_stats(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    users = round(flux_record['_value'])
            return users
        except Exception as er:
            logging.error(ErrorMessages.ER00061.value.format(self.name))
            logging.error(er)
            return 0

    def _fetch_median_throughput_stats(self, test_title: str, start: str, end: str) -> int:
        try:
            query       = self.queries.get_median_throughput_stats(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    value = round(flux_record['_value'])
            return value
        except Exception as er:
            logging.error(ErrorMessages.ER00074.value.format(self.name))
            logging.error(er)
            return 0

    def _fetch_median_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        try:
            query       = self.queries.get_median_response_time_stats(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table.records:
                    value = round(flux_record['_value'], 2)
            return value
        except Exception as er:
            logging.error(ErrorMessages.ER00075.value.format(self.name))
            logging.error(er)
            return 0.0

    def _fetch_pct90_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        try:
            query       = self.queries.get_pct90_response_time_stats(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table.records:
                    value = round(flux_record['_value'], 2)
            return value
        except Exception as er:
            logging.error(ErrorMessages.ER00075.value.format(self.name))
            logging.error(er)
            return 0.0

    def _fetch_errors_pct_stats(self, test_title: str, start: str, end: str) -> float:
        try:
            query       = self.queries.get_errors_pct_stats(test_title, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table.records:
                    value = round(flux_record['errors'], 2)
            return value
        except Exception as er:
            logging.error(ErrorMessages.ER00075.value.format(self.name))
            logging.error(er)
            return 0.0

    def delete_test_data(self, measurement, test_title, start = None, end = None):
        if start == None: start = "2000-01-01T00:00:00Z"
        else:
            start = datetime.strftime(datetime.fromtimestamp(int(start)/1000).astimezone(self.tmz_utc),"%Y-%m-%dT%H:%M:%SZ")
        if end   == None: end = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            end = datetime.strftime(datetime.fromtimestamp(int(end)/1000).astimezone(self.tmz_utc),"%Y-%m-%dT%H:%M:%SZ")
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                self.influxdb_connection.delete_api().delete(start, end, '_measurement="'+measurement+'" AND testTitle="'+test_title+'"',bucket=self.bucket, org=self.org_id)
            else:
                self.influxdb_connection.delete_api().delete(start, end, '_measurement="'+measurement+'" AND runId="'+test_title+'"',bucket=self.bucket, org=self.org_id)
        except Exception as er:
            logging.warning('ERROR: deleteTestPoint method failed')
            logging.warning(er)

    def delete_custom(self, bucket, filetr):
        try:
            start = "2000-01-01T00:00:00Z"
            end   = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.influxdb_connection.delete_api().delete(start, end, filetr, bucket=bucket, org=self.org_id)
        except Exception as er:
            logging.warning('ERROR: deleteTestPoint method failed')
            logging.warning(er)

    def delete_test_title(self, test_title, start = None, end = None):
        response = f'The attempt to delete the {test_title} was successful.'
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                self.delete_test_data("jmeter", test_title, start, end)
                self.delete_test_data("events", test_title, start, end)
            else:
                self.delete_test_data("virtualUsers", test_title, start, end)
                self.delete_test_data("requestsRaw", test_title, start, end)
        except Exception as er:
             return f'The attempt to delete the {test_title} was unsuccessful. Error: {er}'
        return response

    ###HELPER FUNCTIONS

    def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        try:
            flux_tables = self.influxdb_connection.query_api().query(query)
            records     = []
            for table in flux_tables:
                for row in table.records:
                    row_data = row.values
                    row_data.pop("result", None)
                    row_data.pop("table", None)
                    records.append(row_data)
            return records
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

    def process_data(self, flux_tables):
        data = []
        for flux_table in flux_tables:
            for flux_record in flux_table:
                timestamp = flux_record['_time']
                value = flux_record['_value']
                data.append({'timestamp': timestamp, 'value': value})

        df = pd.DataFrame(data, columns=['timestamp', 'value'])
        df.set_index('timestamp', inplace=True)
        return df

    def process_data_req(self, result):
        grouped_records = defaultdict(list)

        for table in result:
            for record in table.records:
                timestamp = record.get_time()
                value = record.get_value()
                transaction = record.values.get('transaction')

                grouped_records[transaction].append({
                    'timestamp': timestamp.isoformat(),
                    'value': value,
                    "anomaly": "Normal"
                })

        json_result = []
        for transaction, data in grouped_records.items():
            json_result.append({
                'name': transaction,
                'data': data
            })

        return json_result


    def transform_flux_tables_to_dict(self, flux_tables) -> List[Dict[str, Any]]:
        """
        Transform flux_tables to a list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        :param flux_tables: The flux tables to transform.
        :return: A list of dictionaries with 'transaction' and 'data' (DataFrame with 'timestamp' and 'value').
        """
        data_dict = {}

        for flux_table in flux_tables:
            for flux_record in flux_table:
                timestamp   = flux_record['_time']
                value       = flux_record['_value']
                transaction = flux_record['transaction']

                if transaction not in data_dict:
                    data_dict[transaction] = []

                data_dict[transaction].append({'timestamp': timestamp, 'value': value})

        result = []
        for transaction, records in data_dict.items():
            df = pd.DataFrame(records)
            df.set_index('timestamp', inplace=True)
            result.append({'transaction': transaction, 'data': df})

        return result

    # ===================================================================
    # Frontend metrics extraction methods
    # ===================================================================

    def _fetch_google_web_vitals(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> List[Dict[str, Any]]:
        """
        Fetch Google Web Vitals metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: List of dictionaries with Google Web Vitals metrics
        """
        try:
            query = self.queries.get_google_web_vitals(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting Google Web Vitals: {str(e)}")
            return []

    def _fetch_timings_fully_loaded(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> List[Dict[str, Any]]:
        """
        Fetch fully loaded timing metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: List of dictionaries with fully loaded timing metrics
        """
        try:
            query = self.queries.get_timings_fully_loaded(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting fully loaded timings: {str(e)}")
            return []

    def _fetch_timings_page_timings(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> List[Dict[str, Any]]:
        """
        Fetch page timing metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: List of dictionaries with page timing metrics
        """
        try:
            query = self.queries.get_timings_page_timings(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting page timings: {str(e)}")
            return []

    def _fetch_timings_main_document(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch main document timing metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of main document timing metrics
        """
        try:
            query = self.queries.get_timings_main_document(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting main document timings: {str(e)}")
            return {}

    def _fetch_cpu_long_tasks(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch CPU long tasks metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of CPU long tasks metrics
        """
        try:
            query = self.queries.get_cpu_long_tasks(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting CPU long tasks: {str(e)}")
            return {}

    def _fetch_cdp_performance_js_heap_used_size(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch JavaScript heap used size metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap used size metrics
        """
        try:
            query = self.queries.get_cdp_performance_js_heap_used_size(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting JS heap used size: {str(e)}")
            return {}

    def _fetch_cdp_performance_js_heap_total_size(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch JavaScript heap total size metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of JS heap total size metrics
        """
        try:
            query = self.queries.get_cdp_performance_js_heap_total_size(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting JS heap total size: {str(e)}")
            return {}

    def _fetch_content_types(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch content type metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of content type metrics
        """
        try:
            query = self.queries.get_content_types(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting content types: {str(e)}")
            return {}

    def _fetch_first_party_content_types(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch first party content type metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of first party content type metrics
        """
        try:
            query = self.queries.get_first_party_content_types(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting first party content types: {str(e)}")
            return {}

    def _fetch_third_party_content_types(self, test_title: str, start: str, end: str, bucket: str, aggregation: str = 'median') -> Dict[str, Any]:
        """
        Fetch third party content type metrics from frontend test using SitespeedFluxQueries.
        :param test_title: The title of the test
        :param start: Start time
        :param end: End time
        :param bucket: The InfluxDB bucket to query
        :param aggregation: The aggregation type (mean, median, p90, p99, etc.)
        :return: Dictionary of third party content type metrics
        """
        try:
            query = self.queries.get_third_party_content_types(test_title, start, end, bucket, aggregation)
            records = self._execute_query(query)

            if not records:
                return []

            # Remove _start and _stop fields from each record
            for record in records:
                if '_start' in record:
                    del record['_start']
                if '_stop' in record:
                    del record['_stop']

            return records
        except Exception as e:
            logging.error(f"Error getting third party content types: {str(e)}")
            return {}
