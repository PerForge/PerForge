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

from app.backend.integrations.data_sources.base_queries import FrontEndQueriesBase


class SitespeedInfluxQLQueries(FrontEndQueriesBase):
    """InfluxQL queries for Sitespeed-style frontend metrics in InfluxDB 1.8.

    These methods mirror the Flux-based SitespeedFluxQueries interface but
    generate InfluxQL strings instead. The exact measurements/fields may need
    to be adjusted to match the concrete Sitespeed 1.8 schema in your setup.
    """

    # In classic InfluxDB 1.8 the database (bucket) is selected on the client,
    # so the `bucket` argument is currently unused but kept for API parity.

    def get_tests_titles(self, bucket: str, test_title_tag_name: str) -> str:  # type: ignore[override]
        # Use SHOW TAG VALUES to list distinct test titles from a representative
        # Sitespeed measurement. Adjust the measurement name if needed.
        return (
            f'SHOW TAG VALUES FROM "largestContentfulPaint" '
            f'WITH KEY = "{test_title_tag_name}"'
        )

    def get_test_log(
        self,
        bucket: str,
        test_title_tag_name: str,
        *,
        test_title: str,
    ) -> str:  # type: ignore[override]
        # In 1.8 we do not have the same join-based duration calculation as in
        # Flux. The extraction layer will derive duration from start/end times,
        # so here we only return distinct titles within the window.
        #
        # For frontend (Sitespeed) data we do not track active threads, so we
        # always report max_threads = 1. Use the existing "jmeter" measurement
        # to avoid issues when Sitespeed measurements are not present.
        return None

    def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:  # type: ignore[override]
        # Use the earliest point of the main LCP series as a proxy for start.
        return (
            f'SELECT FIRST("median") FROM "largestContentfulPaint" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f'ORDER BY time ASC LIMIT 1'
        )

    def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:  # type: ignore[override]
        # Use the latest point of the main LCP series as a proxy for end.
        return (
            f'SELECT LAST("median") FROM "largestContentfulPaint" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f'ORDER BY time DESC LIMIT 1'
        )

    def get_custom_var(
        self,
        testTitle: str,
        custom_var: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:
        # Query a specific known measurement (largestContentfulPaint) to extract custom var tags
        # Sitespeed stores custom vars as tags that are present across all measurements
        return (
            'SELECT * '
            'FROM "largestContentfulPaint" '
            f'WHERE "{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
            'LIMIT 1'
        )

    # ------------------------------------------------------------------
    # Google Web Vitals and timings
    # ------------------------------------------------------------------

    def get_google_web_vitals(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> list[tuple[str, str]]:  # type: ignore[override]
        # Query Web Vitals measurements directly (LCP, FCP, CLS, FID, TBT, TTFB)
        # Returns a list of (query, column_name) tuples
        # Each measurement has fields like "median", "mean", "p90", etc.
        # We select the field based on aggregation parameter
        where_base = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where_base += f' AND "page" =~ /{regex}/'

        return [
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "largestContentfulPaint" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "LCP"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "firstContentfulPaint" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "FCP"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "cumulativeLayoutShift" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "CLS"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "firstInputDelay" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "FID"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "totalBlockingTime" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "TBT"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "ttfb" '
                f'WHERE {where_base}'
                f'GROUP BY "page"',
                "TTFB"
            ),
        ]

    def get_timings_fully_loaded(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("{aggregation}") AS "value" '
            f'FROM "fullyLoaded" '
            f'WHERE {where} '
            f'GROUP BY "page"'
        )

    def get_timings_page_timings(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> list[tuple[str, str]]:  # type: ignore[override]
        # Query page timing measurements that exist: domInteractive, domContentLoadedTime, etc.
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return [
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "domInteractive" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "domInteractive"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "domContentLoadedTime" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "domContentLoadedTime"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "loadTime" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "loadTime"
            ),
        ]

    def get_timings_main_document(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> list[tuple[str, str]]:  # type: ignore[override]
        # Query main document timing measurements: dns, connect, serverResponseTime, etc.
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return [
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "dns" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "dns"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "connect" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "connect"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "serverResponseTime" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "serverResponseTime"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "pageDownloadTime" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "pageDownloadTime"
            ),
        ]

    def get_cpu_long_tasks(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> list[tuple[str, str]]:  # type: ignore[override]
        # Query CPU-related measurements that exist: tasks, lastLongTask, maxPotentialFid, etc.
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return [
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "tasks" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "tasks"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "lastLongTask" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "lastLongTask"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "maxPotentialFid" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "maxPotentialFid"
            ),
            (
                f'SELECT MEDIAN("{aggregation}") AS "value" '
                f'FROM "totalDuration" '
                f'WHERE {where} '
                f'GROUP BY "page"',
                "totalDuration"
            ),
        ]

    def get_cdp_performance_js_heap_used_size(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("{aggregation}") AS "value" '
            f'FROM "JSHeapUsedSize" '
            f'WHERE {where} '
            f'GROUP BY "page"'
        )

    def get_cdp_performance_js_heap_total_size(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("{aggregation}") AS "value" '
            f'FROM "JSHeapTotalSize" '
            f'WHERE {where} '
            f'GROUP BY "page"'
        )

    def get_count_per_content_type(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        # Query requests measurement with pageSummary filter
        # pageSummary rows store data in the "value" field, not in "median"/"mean" fields
        # Filter out rows where page or contentType is empty, similar to v2
        where = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
            f'AND "summaryType" = \'pageSummary\' '
            f'AND "page" != \'\'  '
            f'AND "contentType" != \'\'  '
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("value") AS "value" '
            f'FROM "requests" '
            f'WHERE {where} '
            f'GROUP BY "page", "contentType"'
        )

    def get_first_party_transfer_size(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        # transferSize data with party tags stores values in the "value" field
        # Filter out rows where page or contentType is empty, similar to v2
        where = (
            f'"party" = \'firstParty\' '
            f'AND "{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
            f'AND "page" != \'\'  '
            f'AND "contentType" != \'\'  '
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("value") AS "value" '
            f'FROM "transferSize" '
            f'WHERE {where} '
            f'GROUP BY "page", "contentType"'
        )

    def get_third_party_transfer_size(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> str:  # type: ignore[override]
        # transferSize data with party tags stores values in the "value" field
        # Filter out rows where page or contentType is empty, similar to v2
        where = (
            f'"party" = \'thirdParty\' '
            f'AND "{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
            f'AND "page" != \'\'  '
            f'AND "contentType" != \'\'  '
        )
        if regex:
            where += f' AND "page" =~ /{regex}/'
        return (
            f'SELECT MEDIAN("value") AS "value" '
            f'FROM "transferSize" '
            f'WHERE {where} '
            f'GROUP BY "page", "contentType"'
        )

    def get_overview_data(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
        aggregation: str = "median",
        regex: str = "",
    ) -> dict:  # type: ignore[override]
        """Return a dictionary of queries for frontend overview stats.

        Returns dict with keys for each metric: 'LCP', 'FCP', 'Fully Loaded', 'TTFB', etc.
        Each value is an InfluxQL query string.
        """
        where_common = (
            f'"{test_title_tag_name}" = \'{testTitle}\' '
            f"AND time >= '{start}' AND time <= '{stop}' "
        )
        if regex:
            where_common += f' AND "page" =~ /{regex}/'

        return {
            "LCP": f'SELECT MEDIAN("{aggregation}") AS "value" FROM "largestContentfulPaint" WHERE {where_common}',
            "FCP": f'SELECT MEDIAN("{aggregation}") AS "value" FROM "firstContentfulPaint" WHERE {where_common}',
            "Fully Loaded": f'SELECT MEDIAN("{aggregation}") AS "value" FROM "fullyLoaded" WHERE {where_common}',
            "TTFB": f'SELECT MEDIAN("{aggregation}") AS "value" FROM "ttfb" WHERE {where_common}',
        }

    def get_errors_pct_stats(
        self,
        testTitle: str,
        start: int | str,
        stop: int | str,
        bucket: str,
        test_title_tag_name: str,
    ) -> str:
        """Return None for frontend tests as error percentage is not applicable.

        This method exists for compatibility with the base extraction layer
        but is not meaningful for Sitespeed/frontend tests.
        """
        # Frontend tests don't track errors in the same way as backend tests
        # Return a query that will return no results
        return f'SELECT COUNT("page") FROM "largestContentfulPaint" WHERE 1=0'
