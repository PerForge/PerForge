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

from app.backend.integrations.data_sources.base_queries import BackEndQueriesBase


class InfluxDBBackendListenerClientInfluxQL(BackEndQueriesBase):
    """InfluxQL queries for classic InfluxDB 1.8 JMeter Backend Listener.

    This class only builds query strings. Execution and result shaping are
    handled in the corresponding extraction class.
    """

    measurement = "jmeter"

    def __init__(self, granularity_seconds: int = 30):
        """Initialize the InfluxDB v1.8 Backend Listener query client.

        Args:
            granularity_seconds: Time granularity in seconds for aggregation windows (default: 30)
        """
        self.granularity_seconds = granularity_seconds

    # ------------------------------------------------------------------
    # Test list / meta
    # ------------------------------------------------------------------
    def get_tests_titles(self, bucket: str, test_title_tag_name: str, search: str = '') -> str:  # type: ignore[override]
        # bucket is unused in classic 1.8; database is selected on the client.
        query = f'SHOW TAG VALUES FROM "{self.measurement}" WITH KEY = "{test_title_tag_name}"'

        # Add search filter if provided
        if search:
            # InfluxQL uses WHERE clause with =~ for regex (case-insensitive with (?i))
            query += f" WHERE \"{test_title_tag_name}\" =~ /(?i){search}/"

        return query

    def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:  # type: ignore[override]
        return (
            f'SELECT "maxAT" FROM "{self.measurement}" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f'ORDER BY time ASC LIMIT 1'
        )

    def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:  # type: ignore[override]
        return (
            f'SELECT "maxAT" FROM "{self.measurement}" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f'ORDER BY time DESC LIMIT 1'
        )

    def get_custom_var(
        self,
        testTitle: str,
        custom_var: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:  # type: ignore[override]
        return (
            f'SELECT * FROM "{self.measurement}" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\' '
            f'LIMIT 1'
        )

    # ------------------------------------------------------------------
    # Backend time series
    # ------------------------------------------------------------------
    def get_rps(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT SUM("count")/{self.granularity_seconds} AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    def get_active_threads(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        return (
            f'SELECT MAX("maxAT") AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    def get_average_response_time(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEAN("avg") AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    def get_median_response_time(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEAN("pct50.0") AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    def get_pct90_response_time(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEAN("pct90.0") AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    def get_error_count(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        return (
            f'SELECT SUM("countError")/{self.granularity_seconds} AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s) fill(0)'
        )

    # ------------------------------------------------------------------
    # Backend stats
    # ------------------------------------------------------------------
    def get_max_active_users_stats(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        return (
            f'SELECT MAX("maxAT") AS "value" FROM "{self.measurement}" '
            f'WHERE {where}'
        )

    def get_median_throughput_stats(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("count")/{self.granularity_seconds} AS "value" FROM "{self.measurement}" '
            f'WHERE {where}'
        )

    def get_median_response_time_stats(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("pct50.0") AS "value" FROM "{self.measurement}" '
            f'WHERE {where}'
        )

    def get_pct90_response_time_stats(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT PERCENTILE("pct90.0", 90) AS "value" FROM "{self.measurement}" '
            f'WHERE {where}'
        )

    def get_errors_pct_stats(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:  # type: ignore[override]
        where_all = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        where_ko = where_all + ' AND "statut" = \'ko\''

        # Note: these two queries are executed separately by the extraction class.
        # Here we expose them as a dict-like structure encoded in a string key.
        # To keep the BackEndQueriesBase contract simple, we only implement
        # the \'all\' variant here and let the extraction class build the \'ko\'
        # variant from the same where-clause.
        return f'SELECT SUM("count") AS "value" FROM "{self.measurement}" WHERE {where_all}'

    # ------------------------------------------------------------------
    # The following methods implement backend test log and per-request
    # statistics. They follow the same semantics as the Flux-based
    # implementation but use InfluxQL over the classic 1.8 schema.
    # ------------------------------------------------------------------
    def get_test_log(
        self,
        bucket: str,
        test_title_tag_name: str,
        *,
        test_title: str,
    ) -> str:  # type: ignore[override]
        """Return query to get max active threads for a single test.

        Start/end times are derived separately by the extraction class using
        get_start_time/get_end_time.
        """
        return (
            f'SELECT MAX("maxAT") AS "max_threads" FROM "{self.measurement}" '
            f'WHERE "{test_title_tag_name}" = \'{test_title}\''
        )

    def get_aggregated_data(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        """Return query for aggregated per-transaction statistics.

        The corresponding extraction method is responsible for shaping the
        results into the expected dict format.
        """
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "transaction" != \'all\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT '
            f'MEDIAN("count")/60 AS "rpm", '
            f'SUM("countError") AS "errors", '
            f'SUM("count") AS "count", '
            f'MEAN("avg") AS "avg", '
            f'PERCENTILE("avg", 50) AS "pct50", '
            f'PERCENTILE("avg", 75) AS "pct75", '
            f'PERCENTILE("avg", 90) AS "pct90", '
            f'STDDEV("avg") AS "stddev" '
            f'FROM "{self.measurement}" '
            f'WHERE {where} '
            f'GROUP BY "transaction"'
        )

    def get_average_response_time_per_req(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT MEAN("avg") AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s), "transaction" fill(0)'
        )

    def get_median_response_time_per_req(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT PERCENTILE("pct50.0", 50) AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s), "transaction" fill(0)'
        )

    def get_pct90_response_time_per_req(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT PERCENTILE("pct90.0", 90) AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s), "transaction" fill(0)'
        )

    def get_throughput_per_req(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        regex: str,
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "statut" = \'all\' '
            f'AND "transaction" != \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where += f' AND "transaction" =~ /{regex}/'
        return (
            f'SELECT SUM("count")/{self.granularity_seconds} AS "value" FROM "{self.measurement}" '
            f'WHERE {where} GROUP BY time({self.granularity_seconds}s), "transaction" fill(0)'
        )

    def get_overview_data(
        self,
        testTitle: str,
        start: str,
        stop: str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str,
        regex: str,
    ) -> dict:  # type: ignore[override]
        """Return a dictionary of queries for overview stats.

        Returns dict with keys: 'avg', 'median', 'p75', 'p90', 'total', 'rps_query'
        Each value is an InfluxQL query string.
        """
        where_txn = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f'AND "transaction" != \'all\' '
            f'AND "statut" = \'all\' '
            f'AND time >= \'{start}\' AND time <= \'{stop}\''
        )
        if regex:
            where_txn += f' AND "transaction" =~ /{regex}/'

        return {
            "avg": f'SELECT MEAN("avg") AS "value" FROM "{self.measurement}" WHERE {where_txn}',
            "median": f'SELECT PERCENTILE("pct50.0", 50) AS "value" FROM "{self.measurement}" WHERE {where_txn}',
            "p75": f'SELECT PERCENTILE("pct75.0", 75) AS "value" FROM "{self.measurement}" WHERE {where_txn}',
            "p90": f'SELECT PERCENTILE("pct90.0", 90) AS "value" FROM "{self.measurement}" WHERE {where_txn}',
            "total": f'SELECT SUM("count") AS "value" FROM "{self.measurement}" WHERE {where_txn}',
            "rps_query": f'SELECT SUM("count")/{self.granularity_seconds} AS "value" FROM "{self.measurement}" WHERE {where_txn} GROUP BY time({self.granularity_seconds}s) fill(0)',
        }
