# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion
# Viatoshkin <sema.cod@gmail.com>
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
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Type
from urllib.parse import urlparse

import pandas as pd
from dateutil import tz
from influxdb import InfluxDBClient

from app.backend.components.secrets.secrets_db import DBSecrets
from app.backend.errors import ErrorMessages
from app.backend.integrations.data_sources.base_extraction import DataExtractionBase
from app.backend.integrations.data_sources.base_queries import BackEndQueriesBase, FrontEndQueriesBase
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.integrations.data_sources.influxdb_v1_8.queries.influxdb_backend_listener_client_influxql import (
    InfluxDBBackendListenerClientInfluxQL,
)
from app.backend.integrations.data_sources.influxdb_v1_8.queries.sitespeed_influxdb_v1_8 import (
    SitespeedInfluxQLQueries,
)
from app.backend.components.settings.settings_service import SettingsService


class InfluxdbV18(DataExtractionBase):
    """Classic InfluxDB 1.8 data extraction (InfluxQL + influxdb client).

    Mirrors the InfluxdbV2 pattern by selecting a single query
    implementation based on the configured listener.
    """

    # Maps listener types to their respective query implementations
    queries_map: Dict[str, Type[BackEndQueriesBase | FrontEndQueriesBase]] = {
        # Backend query implementation (JMeter backend listener)
        "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient_v1.8": InfluxDBBackendListenerClientInfluxQL,
        # Frontend query implementation (Sitespeed-style)
        "sitespeed_influxdb_v1.8": SitespeedInfluxQLQueries,
    }

    def __init__(self, project, id: int | None = None) -> None:
        super().__init__(project)
        self.influxdb_connection: InfluxDBClient | None = None

        # Timezone helpers
        self.tmz_utc = tz.tzutc()
        self.tmz_human = self.tmz_utc
        self._target_tz = self.tmz_utc

        # Load configuration to determine listener type and other settings
        self.set_config(id)

        listener = getattr(self, "listener", None)

        if listener in self.queries_map:
            # Get granularity setting from project settings
            granularity = SettingsService.get_setting(
                project, 'data_query', 'backend_query_granularity_seconds', default=30
            )
            # Instantiate the correct query implementation (backend or frontend) with granularity
            self.queries = self.queries_map[listener](granularity_seconds=granularity)
        else:
            self.queries = None
            logging.warning(ErrorMessages.ER00054.value.format(listener))

        self._initialize_client()

    def __enter__(self):
        self._initialize_client()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close_client()

    # ------------------------------------------------------------------
    # Configuration & client lifecycle
    # ------------------------------------------------------------------
    def set_config(self, id: int | None = None) -> None:  # type: ignore[override]
        default_cfg = DBInfluxdb.get_default_config(project_id=self.project)
        if not id and default_cfg:
            id = default_cfg["id"]

        if id is None:
            logging.warning(
                "There's no InfluxDB integration configured for this project."
            )
            return

        config = DBInfluxdb.get_config_by_id(project_id=self.project, id=id)
        if not config or not config.get("id"):
            logging.warning(
                "There's no InfluxDB integration configured for id=%s.", id
            )
            return

        self.id = config["id"]
        self.name = config["name"]
        self.url = config["url"]

        # Map unified InfluxDB config fields to InfluxDB 1.8 connection params
        # bucket -> database, org_id -> username, token (secret id) -> password
        self.database = config.get("bucket")
        self.username = config.get("org_id")

        password_id = config.get("token")
        if password_id:
            self.password = DBSecrets.get_config_by_id(
                project_id=self.project, id=password_id
            )["value"]
        else:
            self.password = None

        self.timeout = config["timeout"]
        self.listener = config["listener"]
        self.tmz = config["tmz"]
        self.test_title_tag_name = config["test_title_tag_name"]
        self.regex = config.get("regex")
        self.custom_vars = config.get("custom_vars", [])
        # Treat empty strings as None to avoid triggering slow multi-node queries
        multi_node_tag = config.get("multi_node_tag")
        self.multi_node_tag = multi_node_tag if multi_node_tag and multi_node_tag.strip() else None

        self.tmz_utc = tz.tzutc()
        self.tmz_human = tz.tzutc() if self.tmz == "UTC" else tz.gettz(self.tmz)
        self._target_tz = self.tmz_human or self.tmz_utc

    def _initialize_client(self) -> None:  # type: ignore[override]
        if getattr(self, "url", None) is None:
            return
        try:
            parsed = urlparse(self.url)
            host = parsed.hostname or self.url
            port = getattr(self, "port", None) or parsed.port or 8086

            self.influxdb_connection = InfluxDBClient(
                host=host,
                port=port,
                username=getattr(self, "username", None),
                password=getattr(self, "password", None),
                database=getattr(self, "database", None),
                timeout=getattr(self, "timeout", None),
                ssl=parsed.scheme == "https",
                verify_ssl=False,
            )
        except Exception as er:
            logging.error(ErrorMessages.ER00052.value.format(getattr(self, "name", "InfluxDB 1.8")))
            logging.error(er)

    def _close_client(self) -> None:  # type: ignore[override]
        if self.influxdb_connection is not None:
            try:
                self.influxdb_connection.close()
            except Exception as er:
                logging.error(ErrorMessages.ER00053.value.format(getattr(self, "name", "InfluxDB 1.8")))
                logging.error(er)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _localize_timestamp(self, timestamp: datetime | None) -> datetime | None:
        if timestamp is None:
            return None
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=self.tmz_utc)
        try:
            return timestamp.astimezone(self._target_tz)
        except Exception:
            return timestamp

    def _empty_time_series(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["value"]).set_index(pd.Index([], name="timestamp"))

    def _query(self, query: str) -> List[Dict[str, Any]]:
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for query: %s", query)
            return []
        try:
            result = self.influxdb_connection.query(query)
            # When using GROUP BY, we need to iterate through result sets to get tag values
            # Each result set corresponds to a unique combination of grouped tags
            points = []
            for series_key, series_data in result.items():
                # series_key is a tuple like ('measurement_name', tags_dict)
                if len(series_key) > 1 and isinstance(series_key[1], dict):
                    tags = series_key[1]
                    # Get points and add tag values to each point
                    for point in series_data:
                        point_with_tags = dict(point)
                        point_with_tags.update(tags)
                        points.append(point_with_tags)
                else:
                    # No GROUP BY, just add points as-is
                    points.extend(list(series_data))
            return points
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

    def _query_df(self, query: str, value_field: str, agg_func: str = "mean") -> pd.DataFrame:
        """Query InfluxDB and return a DataFrame with timestamp index.

        Args:
            query: InfluxQL query string
            value_field: Field name to extract as 'value' column
            agg_func: Aggregation function for duplicate timestamps ('mean', 'sum', 'max')
                      Default is 'mean' for response times; use 'sum' for counts/throughput
        """
        points = self._query(query)
        if not points:
            return self._empty_time_series()

        data: List[Dict[str, Any]] = []
        for p in points:
            t_str = p.get("time")
            if not t_str:
                continue
            ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()
            ts = self._localize_timestamp(ts_utc)
            data.append({"timestamp": ts, "value": p.get(value_field)})

        if not data:
            return self._empty_time_series()

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)

        # Aggregate duplicate timestamps (multi-node support)
        if df.index.has_duplicates:
            if agg_func == "sum":
                df = df.groupby(level=0).sum()
            elif agg_func == "max":
                df = df.groupby(level=0).max()
            else:
                df = df.groupby(level=0).mean()

        return df

    def list_buckets(self, name_regex: str | None = None) -> List[str]:
        """Return a list of database names (buckets) available in the connected InfluxDB 1.8 instance.

        If name_regex is provided, filter database names using an anchored regex pattern,
        following the same semantics as the ping_influxdb helper.
        """
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for list_buckets")
            return []

        try:
            databases = self.influxdb_connection.get_list_database() or []
            names: List[str] = [db.get("name") for db in databases if isinstance(db, dict)]

            if name_regex:
                pattern = name_regex
                anchored = pattern
                if not pattern.startswith("^"):
                    anchored = "^" + anchored
                if not pattern.endswith("$"):
                    anchored = anchored + "$"
                try:
                    rgx = re.compile(anchored)
                except re.error as e:
                    logging.error(f"InfluxdbV18: invalid bucket regex '{pattern}': {e}")
                    return []

                names = [name for name in names if name and rgx.search(name)]

            return sorted(set(n for n in names if n))
        except Exception as er:
            logging.error(f"InfluxdbV18: error listing buckets for {getattr(self, 'name', 'InfluxDB 1.8')}: {er}")
            return []

    # ------------------------------------------------------------------
    # Backend interface implemented with InfluxQL
    # ------------------------------------------------------------------
    def _fetch_tests_titles(self, search: str = '') -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_tests_titles(bucket="", test_title_tag_name=tag_key, search=search)
        points = self._query(query)

        results: List[Dict[str, Any]] = []
        for p in points:
            value = p.get("value")
            if value:
                results.append({"test_title": value})
        return results

    def _fetch_start_time(self, test_title: str, time_format: str) -> Any:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_start_time(
            testTitle=test_title,
            bucket="",
            test_title_tag_name=tag_key,
        )
        points = self._query(query)
        if not points:
            logging.warning(
                "InfluxdbV18: no start time found for test '%s'", test_title
            )
            return None

        t_str = points[0].get("time")
        if not t_str:
            return None

        ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()

        if time_format == "human":
            return datetime.strftime(
                ts_utc.astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p"
            )
        if time_format == "iso":
            start_dt = ts_utc - timedelta(seconds=30)
            return datetime.strftime(start_dt, "%Y-%m-%dT%H:%M:%SZ")
        if time_format == "timestamp":
            return int(ts_utc.astimezone(self.tmz_utc).timestamp() * 1000)

        return None

    def _fetch_end_time(self, test_title: str, time_format: str) -> Any:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_end_time(
            testTitle=test_title,
            bucket="",
            test_title_tag_name=tag_key,
        )
        points = self._query(query)
        if not points:
            logging.warning(
                "InfluxdbV18: no end time found for test '%s'", test_title
            )
            return None

        t_str = points[0].get("time")
        if not t_str:
            return None

        ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()

        if time_format == "human":
            return datetime.strftime(
                ts_utc.astimezone(self.tmz_human), "%Y-%m-%d %I:%M:%S %p"
            )
        if time_format == "iso":
            end_dt = ts_utc + timedelta(seconds=30)
            return datetime.strftime(end_dt, "%Y-%m-%dT%H:%M:%SZ")
        if time_format == "timestamp":
            return int(ts_utc.astimezone(self.tmz_utc).timestamp() * 1000)

        return None

    def _fetch_test_log(self, test_titles: List[str]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        tag_key = getattr(self, "test_title_tag_name", "testTitle")

        for title in test_titles:
            start_iso = self._fetch_start_time(title, "iso")
            end_iso = self._fetch_end_time(title, "iso")
            if not start_iso or not end_iso:
                continue

            start_dt = pd.to_datetime(start_iso, utc=True).to_pydatetime()
            end_dt = pd.to_datetime(end_iso, utc=True).to_pydatetime()
            duration = int((end_dt - start_dt).total_seconds())

            # Use queries helper to get max_threads for this test
            # Only pass multi_node_tag for BackEndQueriesBase (JMeter listener)
            if isinstance(self.queries, BackEndQueriesBase):
                query = self.queries.get_test_log(
                    bucket="",
                    test_title_tag_name=tag_key,
                    test_title=title,
                    multi_node_tag=self.multi_node_tag,
                )
            else:
                query = self.queries.get_test_log(
                    bucket="",
                    test_title_tag_name=tag_key,
                    test_title=title,
                )
            if query:
                points = self._query(query)
            else:
                points = []
                max_threads = 1
            if points:
                try:
                    max_threads = int(round(points[0].get("max_threads") or 0))
                except Exception:
                    max_threads = 1

            start_local = self._localize_timestamp(start_dt)
            end_local = self._localize_timestamp(end_dt)

            records.append(
                {
                    "test_title": title,
                    "start_time": start_local,
                    "end_time": end_local,
                    "duration": duration,
                    "max_threads": max_threads,
                }
            )

        records.sort(key=lambda r: r.get("start_time"), reverse=True)
        return records

    def _fetch_custom_var(self, test_title: str, custom_var: str, start: str, end: str) -> Any:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_custom_var(
            testTitle=test_title,
            custom_var=custom_var,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
        )
        points = self._query(query)
        if points:
            return points[0].get(custom_var)
        return None

    def _fetch_aggregated_data(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_aggregated_data(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for aggregated data query: %s", query)
            return []

        try:
            result = self.influxdb_connection.query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

        results: List[Dict[str, Any]] = []
        for (_measurement, tags), points in result.items():
            txn = (tags or {}).get("transaction")
            if not txn:
                continue

            p = next(iter(points), None)
            if not p:
                continue

            results.append(
                {
                    "transaction": txn,
                    "rpm": p.get("rpm", 0),
                    "errors": p.get("errors", 0),
                    "count": p.get("count", 0),
                    "avg": p.get("avg", 0),
                    "pct50": p.get("pct50", 0),
                    "pct75": p.get("pct75", 0),
                    "pct90": p.get("pct90", 0),
                    "stddev": p.get("stddev", 0),
                }
            )

        return results

    def _fetch_rps(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_rps(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        return self._query_df(query, "value")

    def _fetch_active_threads(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        # Only pass multi_node_tag for BackEndQueriesBase (JMeter listener)
        if isinstance(self.queries, BackEndQueriesBase):
            query = self.queries.get_active_threads(
                testTitle=test_title,
                start=start,
                stop=end,
                bucket="",
                test_title_tag_name=tag_key,
                multi_node_tag=self.multi_node_tag,
            )
            return self._query_df(query, "value", agg_func="sum")
        return pd.DataFrame()

    def _fetch_average_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_average_response_time(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        return self._query_df(query, "value")

    def _fetch_median_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_median_response_time(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        return self._query_df(query, "value")

    def _fetch_pct90_response_time(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_pct90_response_time(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        return self._query_df(query, "value")

    def _fetch_error_count(self, test_title: str, start: str, end: str) -> pd.DataFrame:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_error_count(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
        )
        return self._query_df(query, "value", agg_func="sum")

    def _fetch_average_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_average_response_time_per_req(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for average response time per req query: %s", query)
            return []

        try:
            result = self.influxdb_connection.query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

        txn_data: Dict[str, List[pd.DataFrame]] = {}
        for (_measurement, tags), points in result.items():
            txn = (tags or {}).get("transaction")
            if not txn:
                continue

            rows: List[Dict[str, Any]] = []
            for p in points:
                t_str = p.get("time")
                if not t_str:
                    continue
                ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()
                ts = self._localize_timestamp(ts_utc)
                rows.append({"timestamp": ts, "value": p.get("value")})

            if not rows:
                continue

            df = pd.DataFrame(rows)
            df.set_index("timestamp", inplace=True)
            df.index.name = "timestamp"
            txn_data.setdefault(txn, []).append(df)

        # Merge DataFrames for same transaction (multi-node support)
        results: List[Dict[str, Any]] = []
        for txn, dfs in txn_data.items():
            if len(dfs) == 1:
                merged = dfs[0]
            else:
                merged = pd.concat(dfs).groupby(level=0).mean()
            results.append({"transaction": txn, "data": merged})

        return results

    def _fetch_median_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_median_response_time_per_req(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for median response time per req query: %s", query)
            return []

        try:
            result = self.influxdb_connection.query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

        txn_data: Dict[str, List[pd.DataFrame]] = {}
        for (_measurement, tags), points in result.items():
            txn = (tags or {}).get("transaction")
            if not txn:
                continue

            rows: List[Dict[str, Any]] = []
            for p in points:
                t_str = p.get("time")
                if not t_str:
                    continue
                ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()
                ts = self._localize_timestamp(ts_utc)
                rows.append({"timestamp": ts, "value": p.get("value")})

            if not rows:
                continue

            df = pd.DataFrame(rows)
            df.set_index("timestamp", inplace=True)
            df.index.name = "timestamp"
            txn_data.setdefault(txn, []).append(df)

        # Merge DataFrames for same transaction (multi-node support)
        results: List[Dict[str, Any]] = []
        for txn, dfs in txn_data.items():
            if len(dfs) == 1:
                merged = dfs[0]
            else:
                merged = pd.concat(dfs).groupby(level=0).mean()
            results.append({"transaction": txn, "data": merged})

        return results

    def _fetch_pct90_response_time_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_pct90_response_time_per_req(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for pct90 response time per req query: %s", query)
            return []

        try:
            result = self.influxdb_connection.query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

        txn_data: Dict[str, List[pd.DataFrame]] = {}
        for (_measurement, tags), points in result.items():
            txn = (tags or {}).get("transaction")
            if not txn:
                continue

            rows: List[Dict[str, Any]] = []
            for p in points:
                t_str = p.get("time")
                if not t_str:
                    continue
                ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()
                ts = self._localize_timestamp(ts_utc)
                rows.append({"timestamp": ts, "value": p.get("value")})

            if not rows:
                continue

            df = pd.DataFrame(rows)
            df.set_index("timestamp", inplace=True)
            df.index.name = "timestamp"
            txn_data.setdefault(txn, []).append(df)

        # Merge DataFrames for same transaction (multi-node support)
        results: List[Dict[str, Any]] = []
        for txn, dfs in txn_data.items():
            if len(dfs) == 1:
                merged = dfs[0]
            else:
                merged = pd.concat(dfs).groupby(level=0).mean()
            results.append({"transaction": txn, "data": merged})

        return results

    def _fetch_throughput_per_req(self, test_title: str, start: str, end: str) -> List[Dict[str, Any]]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_throughput_per_req(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for throughput per req query: %s", query)
            return []

        try:
            result = self.influxdb_connection.query(query)
        except Exception as er:
            logging.error(ErrorMessages.ER00056.value.format(query))
            logging.error(er)
            return []

        txn_data: Dict[str, List[pd.DataFrame]] = {}
        for (_measurement, tags), points in result.items():
            txn = (tags or {}).get("transaction")
            if not txn:
                continue

            rows: List[Dict[str, Any]] = []
            for p in points:
                t_str = p.get("time")
                if not t_str:
                    continue
                ts_utc = pd.to_datetime(t_str, utc=True).to_pydatetime()
                ts = self._localize_timestamp(ts_utc)
                rows.append({"timestamp": ts, "value": p.get("value")})

            if not rows:
                continue

            df = pd.DataFrame(rows)
            df.set_index("timestamp", inplace=True)
            df.index.name = "timestamp"
            txn_data.setdefault(txn, []).append(df)

        # Merge DataFrames for same transaction (multi-node support, sum for throughput)
        results: List[Dict[str, Any]] = []
        for txn, dfs in txn_data.items():
            if len(dfs) == 1:
                merged = dfs[0]
            else:
                merged = pd.concat(dfs).groupby(level=0).sum()
            results.append({"transaction": txn, "data": merged})

        return results

    def _fetch_max_active_users_stats(self, test_title: str, start: str, end: str) -> int:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_max_active_users_stats(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
        )
        points = self._query(query)
        if points:
            try:
                return int(round(points[0].get("value") or 0))
            except Exception:
                return 0
        return 0

    def _fetch_median_throughput_stats(self, test_title: str, start: str, end: str) -> int:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_median_throughput_stats(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        if points:
            try:
                return int(round(points[0].get("value") or 0))
            except Exception:
                return 0
        return 0

    def _fetch_median_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_median_response_time_stats(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        if points:
            try:
                return round(float(points[0].get("value") or 0.0), 2)
            except Exception:
                return 0.0
        return 0.0

    def _fetch_pct90_response_time_stats(self, test_title: str, start: str, end: str) -> float:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_pct90_response_time_stats(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        if points:
            try:
                return round(float(points[0].get("value") or 0.0), 2)
            except Exception:
                return 0.0
        return 0.0

    def _fetch_errors_pct_stats(self, test_title: str, start: str, end: str) -> float:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        where_all = (
            f'"{tag_key}" = \'{test_title}\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{end}\''
        )
        regex = getattr(self, "regex", "")
        if regex:
            where_all += f' AND "transaction" =~ /{regex}/'
        where_ko = where_all + ' AND "statut" = \'ko\''
        if regex:
            query_all = (
                f'SELECT SUM("count") AS "value" FROM "jmeter" '
                f'WHERE {where_all}'
            )
        else:
            query_all = self.queries.get_errors_pct_stats(
                testTitle=test_title,
                start=start,
                stop=end,
                bucket="",
                test_title_tag_name=tag_key,
            )
        query_ko = (
            f'SELECT SUM("count") AS "value" FROM "jmeter" WHERE {where_ko}'
        )

        total_points = self._query(query_all)
        error_points = self._query(query_ko)

        try:
            total = float(total_points[0].get("value") or 0.0) if total_points else 0.0
            errors = float(error_points[0].get("value") or 0.0) if error_points else 0.0
            if total <= 0.0:
                return 0.0
            return round(errors * 100.0 / total, 2)
        except Exception:
            return 0.0

    def _fetch_overview_data(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        """Fetch overview data using query class methods.

        This method works for both backend (JMeter) and frontend (Sitespeed) tests
        by delegating to the appropriate query class.
        """
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        regex = getattr(self, "regex", "")

        # Get queries dict from the query class
        queries_dict = self.queries.get_overview_data(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=regex,
        )

        # Check if this is a backend test (has 'rps_query' key) or frontend test
        is_backend = "rps_query" in queries_dict

        if is_backend:
            # Backend (JMeter) overview
            avg_points = self._query(queries_dict["avg"])
            avg_val = float(avg_points[0].get("value") or 0.0) if avg_points else 0.0

            median_points = self._query(queries_dict["median"])
            median_val = float(median_points[0].get("value") or 0.0) if median_points else 0.0

            p75_points = self._query(queries_dict["p75"])
            p75_val = float(p75_points[0].get("value") or 0.0) if p75_points else 0.0

            p90_points = self._query(queries_dict["p90"])
            p90_val = float(p90_points[0].get("value") or 0.0) if p90_points else 0.0

            total_points = self._query(queries_dict["total"])
            total_val = float(total_points[0].get("value") or 0.0) if total_points else 0.0

            rps_df = self._query_df(queries_dict["rps_query"], "value")
            if not rps_df.empty:
                try:
                    rps_val = float(rps_df["value"].quantile(0.75))
                except Exception:
                    rps_val = float(rps_df["value"].median())
            else:
                rps_val = 0.0

            error_pct = self.get_errors_pct_stats(test_title=test_title, start=start, end=end)

            return [
                {"Metric": "Average", "Value": round(avg_val, 2)},
                {"Metric": "Median", "Value": round(median_val, 2)},
                {"Metric": "75%-tile", "Value": round(p75_val, 2)},
                {"Metric": "90%-tile", "Value": round(p90_val, 2)},
                {"Metric": "Total requests", "Value": int(total_val)},
                {"Metric": "RPS", "Value": round(rps_val, 2)},
                {"Metric": "Error %", "Value": round(error_pct, 2)},
            ]
        else:
            # Frontend (Sitespeed) overview
            records = []
            for metric_name, query in queries_dict.items():
                points = self._query(query)
                value = float(points[0].get("value") or 0.0) if points else 0.0
                records.append({"Metric": metric_name, "Value": round(value, 2)})

            return records

    def _fetch_google_web_vitals(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        """Fetch Google Web Vitals metrics for frontend tests from InfluxDB 1.8.

        Returns a list of dicts, each representing a page-level row, similar to
        the InfluxdbV2 frontend implementation. The MetricsTable layer will
        normalize numeric fields and handle baselines.
        """
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        queries = self.queries.get_google_web_vitals(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )

        # Execute multiple queries and merge results by page
        # queries is a list of (query, column_name) tuples
        page_data = {}
        for query, column_name in queries:
            points = self._query(query)
            for p in points:
                page = p.get("page")
                if not page:
                    continue
                if page not in page_data:
                    page_data[page] = {"page": page}
                # Map the 'value' field to the proper column name
                value = p.get("value")
                if value is not None:
                    page_data[page][column_name] = value

        return list(page_data.values())

    def _fetch_timings_fully_loaded(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_timings_fully_loaded(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        for p in points:
            p.pop("time", None)
        return points

    def _fetch_timings_page_timings(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        queries = self.queries.get_timings_page_timings(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )

        # Execute multiple queries and merge results by page
        # queries is a list of (query, column_name) tuples
        page_data = {}
        for query, column_name in queries:
            points = self._query(query)
            for p in points:
                page = p.get("page")
                if not page:
                    continue
                if page not in page_data:
                    page_data[page] = {"page": page}
                # Map the 'value' field to the proper column name
                value = p.get("value")
                if value is not None:
                    page_data[page][column_name] = value

        return list(page_data.values())

    def _fetch_timings_main_document(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        queries = self.queries.get_timings_main_document(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )

        # Execute multiple queries and merge results by page
        # queries is a list of (query, column_name) tuples
        page_data = {}
        for query, column_name in queries:
            points = self._query(query)
            for p in points:
                page = p.get("page")
                if not page:
                    continue
                if page not in page_data:
                    page_data[page] = {"page": page}
                # Map the 'value' field to the proper column name
                value = p.get("value")
                if value is not None:
                    page_data[page][column_name] = value

        return list(page_data.values())

    def _fetch_cpu_long_tasks(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        queries = self.queries.get_cpu_long_tasks(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )

        # Execute multiple queries and merge results by page
        # queries is a list of (query, column_name) tuples
        page_data = {}
        for query, column_name in queries:
            points = self._query(query)
            for p in points:
                page = p.get("page")
                if not page:
                    continue
                if page not in page_data:
                    page_data[page] = {"page": page}
                # Map the 'value' field to the proper column name
                value = p.get("value")
                if value is not None:
                    page_data[page][column_name] = value

        return list(page_data.values())

    def _fetch_cdp_performance_js_heap_used_size(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_cdp_performance_js_heap_used_size(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        for p in points:
            p.pop("time", None)
        return points

    def _fetch_cdp_performance_js_heap_total_size(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_cdp_performance_js_heap_total_size(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)
        for p in points:
            p.pop("time", None)
        return points

    def _fetch_count_per_content_type(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_count_per_content_type(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)

        # Pivot data: transform rows with (page, contentType, value) into
        # rows with page and content types as columns, matching v2 format
        page_data = {}
        for p in points:
            page = p.get("page")
            content_type = p.get("contentType")
            value = p.get("value")

            if page and content_type:
                if page not in page_data:
                    page_data[page] = {"page": page}
                page_data[page][content_type] = value

        return list(page_data.values())

    def _fetch_first_party_transfer_size(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_first_party_transfer_size(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)

        # Pivot data: transform rows with (page, contentType, value) into
        # rows with page and content types as columns, matching v2 format
        page_data = {}
        for p in points:
            page = p.get("page")
            content_type = p.get("contentType")
            value = p.get("value")

            if page and content_type:
                if page not in page_data:
                    page_data[page] = {"page": page}
                page_data[page][content_type] = value

        return list(page_data.values())

    def _fetch_third_party_transfer_size(self, test_title: str, start: str, end: str, aggregation: str = "median") -> Dict[str, Any]:
        tag_key = getattr(self, "test_title_tag_name", "testTitle")
        query = self.queries.get_third_party_transfer_size(
            testTitle=test_title,
            start=start,
            stop=end,
            bucket="",
            test_title_tag_name=tag_key,
            aggregation=aggregation,
            regex=getattr(self, "regex", ""),
        )
        points = self._query(query)

        # Pivot data: transform rows with (page, contentType, value) into
        # rows with page and content types as columns, matching v2 format
        page_data = {}
        for p in points:
            page = p.get("page")
            content_type = p.get("contentType")
            value = p.get("value")

            if page and content_type:
                if page not in page_data:
                    page_data[page] = {"page": page}
                page_data[page][content_type] = value

        return list(page_data.values())

    def delete_test_data(self, test_title: str, start=None, end=None) -> None:
        """
        Delete test data from InfluxDB 1.8 using DROP SERIES.

        InfluxDB 1.8 doesn't have a DELETE API like v2, so we use DROP SERIES
        to remove all data points for a specific test title.

        Args:
            test_title: The test title to delete data for
            start: Optional start time (not used in InfluxDB 1.8, kept for API compatibility)
            end: Optional end time (not used in InfluxDB 1.8, kept for API compatibility)
        """
        if self.influxdb_connection is None:
            logging.warning("InfluxdbV18: no active connection for delete_test_data")
            return

        try:
            tag_key = getattr(self, "test_title_tag_name", "testTitle")

            # For InfluxDB 1.8, we use DROP SERIES to delete data
            # We need to drop series from both the measurement tables and events table
            measurements = ["jmeter", "events"]

            # For Sitespeed (frontend) tests, we also need to delete from various measurements
            if hasattr(self, 'listener') and 'sitespeed' in self.listener.lower():
                measurements.extend([
                    "largestContentfulPaint", "firstContentfulPaint",
                    "cumulativeLayoutShift", "firstInputDelay",
                    "totalBlockingTime", "ttfb", "fullyLoaded",
                    "domInteractive", "domContentLoadedTime", "loadTime",
                    "dns", "connect", "serverResponseTime", "pageDownloadTime",
                    "tasks", "lastLongTask", "maxPotentialFid", "totalDuration",
                    "JSHeapUsedSize", "JSHeapTotalSize", "requests", "transferSize"
                ])

            for measurement in measurements:
                try:
                    # DROP SERIES FROM <measurement> WHERE <tag_key>='<test_title>'
                    query = f'DROP SERIES FROM "{measurement}" WHERE "{tag_key}"=\'{test_title}\''
                    self.influxdb_connection.query(query)
                    logging.info(f"Deleted data from measurement '{measurement}' for test '{test_title}'")
                except Exception as e:
                    # It's okay if a measurement doesn't exist
                    logging.debug(f"Could not delete from measurement '{measurement}': {e}")

            logging.info(f"Successfully deleted test data for '{test_title}'")
        except Exception as er:
            logging.error(f'ERROR: delete_test_data method failed for test "{test_title}"')
            logging.error(er)
