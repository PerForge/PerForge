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
import os

from app.backend.integrations.integration                         import Integration
from app.backend.integrations.influxdb.influxdb_config            import InfluxdbConfig
from app.backend.integrations.influxdb.influxdb_backend_listeners import custom
from app.backend.integrations.influxdb.influxdb_backend_listeners import standart
from influxdb_client                                              import InfluxDBClient
from influxdb_client.client.write_api                             import SYNCHRONOUS
from os                                                           import path
from datetime                                                     import datetime
from dateutil                                                     import tz


class Influxdb(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)
        self.tmz_utc   = tz.tzutc()
        self.tmz_human = tz.tzutc() if self.tmz == "UTC" else tz.gettz(self.tmz)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.url}'

    def __del__(self):
        self.close_influxdb_connection()

    def set_config(self, id):
        if path.isfile(self.config_path) is False or os.path.getsize(self.config_path) == 0:
            logging.warning("There is no config file.")
        else:
            id     = id if id else InfluxdbConfig.get_default_influxdb_config_id(self.project)
            config = InfluxdbConfig.get_influxdb_config_values(self.project, id, is_internal=True)
            if "id" in config:
                if config['id'] == id:
                    self.id       = config["id"]
                    self.name     = config["name"]
                    self.url      = config["url"]
                    self.org_id   = config["org_id"]
                    self.token    = config["token"]
                    self.timeout  = config["timeout"]
                    self.bucket   = config["bucket"]
                    self.listener = config["listener"]
                    self.tmz      = config["tmz"]

    def connect_to_influxdb(self):
        try:
            self.influxdb_connection = InfluxDBClient(url=self.url, org=self.org_id, token=self.token, timeout=300000)
        except Exception as er:
            logging.warning('ERROR: influxdb opening connection failed')
            logging.warning(er)
        return self

    def close_influxdb_connection(self):
        try:
            self.influxdb_connection.__del__()
        except Exception as er:
            logging.warning('ERROR: influxdb connection closing failed')
            logging.warning(er)
   
    def sort_tests(self, tests):
        def start_time(e): return e['startTime']
        if len(tests) != 0:
            for test in tests:
                test["startTimestamp"] = str(int(test["startTime"].timestamp() * 1000))
                test["endTimestamp"]   = str(int(test["endTime"].timestamp() * 1000))
                test["startTime"]      = datetime.strftime(test["startTime"].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
                test["endTime"]        = datetime.strftime(test["endTime"].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
        tests.sort(key=start_time, reverse=True)
        return tests

    def get_test_log(self):
        result = []
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                query = standart.get_test_log_query(self.bucket)
            else:
                query = custom.get_test_log_query(self.bucket)
            tables = self.influxdb_connection.query_api().query(query)
            for table in tables:
                for row in table.records:
                    del row.values["result"]
                    del row.values["table"]
                    result.append(row.values)
            if result:
                result = self.sort_tests(result)
            return result
        except Exception as er:
            logging.warning(er)
            return result

    def get_aggregated_table(self, run_id, start, end):
        result = []
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                query = standart.get_aggregated_data(run_id, start, end, self.bucket)
            else:
                query = custom.get_aggregated_data(run_id, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    del flux_record.values["result"]
                    del flux_record.values["table"]
                    result.append(flux_record.values)
            return result
        except Exception as er:
            logging.warning(er)
            return result

    def send_query(self, query):
        results = []
        flux_tables = self.influxdb_connection.query_api().query(query)
        for flux_table in flux_tables:
            for flux_record in flux_table:
                results.append(flux_record)
        return results

    def write_point(self, point):
        self.influxdb_connection.write_api(write_options=SYNCHRONOUS).write(bucket=self.bucket, org=self.org_id, record=point)

    def get_human_start_time(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_start_time(run_id, self.bucket)
        else:
            query = custom.get_start_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = datetime.strftime(flux_record['_time'].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
        return tmp

    def get_start_time(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_start_time(run_id, self.bucket)
        else:
            query = custom.get_start_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = datetime.strftime(flux_record['_time'],"%Y-%m-%dT%H:%M:%SZ")
        return tmp

    def get_start_tmp(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_start_time(run_id, self.bucket)
        else:
            query = custom.get_start_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = int(flux_record['_time'].astimezone(self.tmz_utc).timestamp() * 1000)
        return tmp

    def get_end_tmp(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_end_time(run_id, self.bucket)
        else:
            query = custom.get_end_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = int(flux_record['_time'].astimezone(self.tmz_utc).timestamp() * 1000)
        return tmp

    def get_human_end_time(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_end_time(run_id, self.bucket)
        else:
            query = custom.get_end_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = datetime.strftime(flux_record['_time'].astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p")
        return tmp

    def get_end_time(self, run_id):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_end_time(run_id, self.bucket)
        else:
            query = custom.get_end_time(run_id, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                tmp = datetime.strftime(flux_record['_time'],"%Y-%m-%dT%H:%M:%SZ")
        return tmp

    def get_max_active_users(self, run_id, start, end):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_max_active_users_stats(run_id, start, end, self.bucket)
        else:
            query = custom.get_max_active_users_stats(run_id, start, end, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        for flux_table in flux_tables:
            for flux_record in flux_table:
                users = round(flux_record['_value'])
        return users

    def get_test_name(self, run_id, start, end):
        appName = None
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_app_name(run_id, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    appName = flux_record['application']
        else:
            query = custom.get_app_name(run_id, start, end, self.bucket)
            flux_tables = self.influxdb_connection.query_api().query(query)
            for flux_table in flux_tables:
                for flux_record in flux_table:
                    appName = flux_record['testName']
        return appName

    def delete_test_data(self, measurement, run_id, start = None, end = None):
        if start == None: start = "2000-01-01T00:00:00Z"
        else:
            start = datetime.strftime(datetime.fromtimestamp(int(start)/1000).astimezone(self.tmz_utc),"%Y-%m-%dT%H:%M:%SZ")
        if end   == None: end = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            end = datetime.strftime(datetime.fromtimestamp(int(end)/1000).astimezone(self.tmz_utc),"%Y-%m-%dT%H:%M:%SZ")
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                self.influxdb_connection.delete_api().delete(start, end, '_measurement="'+measurement+'" AND testTitle="'+run_id+'"',bucket=self.bucket, org=self.org_id)
            else:
                self.influxdb_connection.delete_api().delete(start, end, '_measurement="'+measurement+'" AND runId="'+run_id+'"',bucket=self.bucket, org=self.org_id)
        except Exception as er:
            logging.warning('ERROR: deleteTestPoint method failed')
            logging.warning(er)
    
    def delete_custom(self, bucket, filetr):
        try:
            start = "2000-01-01T00:00:00Z"
            end = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.influxdb_connection.delete_api().delete(start, end, filetr, bucket=bucket, org=self.org_id)
        except Exception as er:
            logging.warning('ERROR: deleteTestPoint method failed')
            logging.warning(er)

    def delete_run_id(self, run_id, start = None, end = None):
        response = f'The attempt to delete the {run_id} was successful.'
        try:
            if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
                self.delete_test_data("jmeter", run_id, start, end)
                self.delete_test_data("events", run_id, start, end)
            else:
                self.delete_test_data("virtualUsers", run_id, start, end)
                self.delete_test_data("requestsRaw", run_id, start, end)
        except Exception as er:
             return f'The attempt to delete the {run_id} was unsuccessful. Error: {er}'
        return response

    def get_average_rps_stats(self, run_id, start, end):
        flux_tables = self.influxdb_connection.query_api().query(custom.get_average_rps_stats(run_id, start, end, self.bucket))
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        value=""
        for flux_table in flux_tables:
            for flux_record in flux_table:
                value = round(flux_record['_value'], 2)
        return value

    def get_avg_response_time_stats(self, run_id, start, end):
        flux_tables = self.influxdb_connection.query_api().query(custom.get_avg_response_time_stats(run_id, start, end, self.bucket))
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        value=""
        for flux_table in flux_tables:
            for flux_record in flux_table:
                value = round(flux_record['_value'], 2)
        return value

    def get_90_response_time_stats(self, run_id, start, end):
        flux_tables = self.influxdb_connection.query_api().query(custom.get_90_response_time_stats(run_id, start, end, self.bucket))
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        value=""
        for flux_table in flux_tables:
            for flux_record in flux_table:
                value = round(flux_record['_value'], 2)
        return value

    def get_median_response_time_stats(self, run_id, start, end):
        flux_tables = self.influxdb_connection.query_api().query(custom.get_median_response_time_stats(run_id, start, end, self.bucket))
        # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
        value=""
        for flux_table in flux_tables:
            for flux_record in flux_table:
                value = round(flux_record['_value'], 2)
        return

        # Method generates flux query to get test data based on NFR definition
    def generate_flux_query(self, test_name, run_id, start, end, bucket, nfr):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            constr = standart.flux_constructor(test_name, run_id, start, end, bucket, request_name=nfr["scope"])
             # Create query
            query = (
                constr['source']
                + constr["range"]
                + constr["_measurement"]
                + constr["testTitle"]
            )
            if nfr["metric"] == "response-time":
                query += constr["metric"][nfr['aggregation']]
            else:
                query += constr["metric"][nfr["metric"]]
            # If scope is a specific request name, use the key "request"
            if nfr['scope'] not in ['all', 'each']:
                query += constr["scope"]['request']
            else:
                query += constr["scope"][nfr['scope']]
            # If the metric is rps, then add the aggregation window
            if nfr['metric'] == 'rps':
                query += constr["aggregation"][nfr['metric']]

            query += constr["aggregation"][nfr['aggregation']]
        else:
            constr = custom.flux_constructor(test_name, run_id, start, end, bucket, request_name=nfr["scope"])
             # Create query
            query = (
                constr['source']
                + constr["range"]
                + constr["_measurement"][nfr["metric"]]
                + constr["metric"][nfr["metric"]]
                + constr["runId"]
            )
            # If scope is a specific request name, use the key "request"
            if nfr['scope'] not in ['all', 'each']:
                query += constr["scope"]['request']
            else:
                query += constr["scope"][nfr['scope']]
            # If the metric is rps, then add the aggregation window
            if nfr['metric'] == 'rps':
                query += constr["aggregation"][nfr['metric']]
            query += constr["aggregation"][nfr['aggregation']]
        return query
    
    def get_rps(self, run_id, start, end):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_rps(run_id, start, end, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        return flux_tables
    
    def get_active_threads(self, run_id, start, end):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_active_threads(run_id, start, end, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        return flux_tables
    
    def get_response_time(self, run_id, start, end):
        if self.listener == "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient":
            query = standart.get_response_time(run_id, start, end, self.bucket)
        flux_tables = self.influxdb_connection.query_api().query(query)
        return flux_tables