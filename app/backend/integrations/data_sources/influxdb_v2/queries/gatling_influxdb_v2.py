# Copyright Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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


class GatlingFluxQueries(BackEndQueriesBase):
    """
    Flux query implementations for Gatling metrics stored in InfluxDB v2 via Telegraf.

    Telegraf template used to parse Graphite paths:
      "gatling.*.*.*.*.* measurement.testTitle.simulation.request.status.field"

    Tag mapping vs JMeter:
      - measurement : "gatling"  (JMeter: "jmeter")
      - request tag : "request"  (JMeter: "transaction")
      - status tag  : "status"   (JMeter: "statut")
      - all-reqs row: request == "allRequests"  (JMeter: transaction == "all")
      - active users: request == "users", status == "allUsers", _field == "active"
                      (JMeter: _field == "maxAT")
    Field name mapping vs JMeter:
      - avg response time : "mean"          (JMeter: "avg")
      - median            : "percentiles50" (JMeter: "pct50.0")
      - 75th pct          : "percentiles75" (JMeter: "pct75.0")
      - 90th pct          : "percentiles95" (JMeter: "pct90.0", Gatling has no 90th)
      - error count       : _field=="count" + status=="ko"  (JMeter: "countError")
    """

    def __init__(self, granularity_seconds: int = 30):
        self.granularity_seconds = granularity_seconds

    # ------------------------------------------------------------------
    # Test discovery
    # ------------------------------------------------------------------

    def get_tests_titles(
        self,
        bucket: str,
        test_title_tag_name: str,
        search: str = '',
        custom_filter_tags: list = None,
    ) -> str:
        base_query = (
            f'from(bucket: "{bucket}")\n'
            f'  |> range(start: 0, stop: now())\n'
            f'  |> filter(fn: (r) => r._measurement == "gatling")\n'
            f'  |> filter(fn: (r) => r._field == "count")\n'
            f'  |> filter(fn: (r) => r["request"] == "allRequests")\n'
            f'  |> filter(fn: (r) => r["status"] == "all")\n'
        )

        if search:
            base_query += f'  |> filter(fn: (r) => r["{test_title_tag_name}"] =~ /(?i){search}/)\n'

        for f in (custom_filter_tags or []):
            tag = f.get("tag", "")
            value = f.get("value", "")
            is_regex = f.get("regex", False)
            if tag and value:
                if is_regex:
                    base_query += f'  |> filter(fn: (r) => r["{tag}"] =~ /{value}/)\n'
                else:
                    base_query += f'  |> filter(fn: (r) => r["{tag}"] == "{value}")\n'

        base_query += (
            f'  |> group(columns: ["{test_title_tag_name}"])\n'
            f'  |> min(column: "_time")\n'
            f'  |> group()\n'
            f'  |> sort(columns: ["_time"], desc: true)\n'
            f'  |> keep(columns: ["{test_title_tag_name}"])\n'
            f'  |> rename(columns: {{{test_title_tag_name}: "test_title"}})'
        )
        return base_query

    # ------------------------------------------------------------------
    # Time boundaries
    # ------------------------------------------------------------------

    def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["request"] == "allRequests")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> min(column: "_time")'''

    def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["request"] == "allRequests")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> max(column: "_time")'''

    # ------------------------------------------------------------------
    # Test log (list view)
    # ------------------------------------------------------------------

    def get_test_log(
        self,
        bucket: str,
        test_title_tag_name: str,
        *,
        test_titles: list,
        start_time: str,
        end_time: str,
        multi_node_tag: str = None,
    ) -> str:
        formatted = ", ".join([f'"{t}"' for t in test_titles])

        if multi_node_tag:
            return f'''
    data = from(bucket: "{bucket}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => contains(value: r["{test_title_tag_name}"], set: [{formatted}]))
      |> filter(fn: (r) => exists r["{multi_node_tag}"])

    max_threads = data
      |> keep(columns: ["_value", "{test_title_tag_name}", "{multi_node_tag}"])
      |> group(columns: ["{test_title_tag_name}", "{multi_node_tag}"])
      |> max()
      |> group(columns: ["{test_title_tag_name}"])
      |> sum()
      |> rename(columns: {{_value: "max_threads"}})

    end_time = data
      |> max(column: "_time")
      |> keep(columns: ["_time", "{test_title_tag_name}"])
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "end_time"}})

    start_time = data
      |> min(column: "_time")
      |> keep(columns: ["_time", "{test_title_tag_name}"])
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "start_time"}})

    join1 = join(tables: {{d1: max_threads, d2: start_time}}, on: ["{test_title_tag_name}"])
      |> keep(columns: ["start_time", "{test_title_tag_name}", "max_threads"])
      |> group(columns: ["{test_title_tag_name}"])

    join(tables: {{d1: join1, d2: end_time}}, on: ["{test_title_tag_name}"])
      |> map(fn: (r) => ({{ r with duration: (int(v: r.end_time) - int(v: r.start_time))/1000000000}}))
      |> keep(columns: ["start_time", "end_time", "{test_title_tag_name}", "max_threads", "duration"])
      |> group()
      |> sort(columns: ["start_time"], desc: true)
      |> rename(columns: {{{test_title_tag_name}: "test_title"}})'''
        else:
            return f'''
    data = from(bucket: "{bucket}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => contains(value: r["{test_title_tag_name}"], set: [{formatted}]))

    max_threads = data
      |> keep(columns: ["_value", "{test_title_tag_name}"])
      |> max()
      |> group(columns: ["_value", "{test_title_tag_name}"])
      |> rename(columns: {{_value: "max_threads"}})

    end_time = data
      |> max(column: "_time")
      |> keep(columns: ["_time", "{test_title_tag_name}"])
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "end_time"}})

    start_time = data
      |> min(column: "_time")
      |> keep(columns: ["_time", "{test_title_tag_name}"])
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "start_time"}})

    join1 = join(tables: {{d1: max_threads, d2: start_time}}, on: ["{test_title_tag_name}"])
      |> keep(columns: ["start_time", "{test_title_tag_name}", "max_threads"])
      |> group(columns: ["{test_title_tag_name}"])

    join(tables: {{d1: join1, d2: end_time}}, on: ["{test_title_tag_name}"])
      |> map(fn: (r) => ({{ r with duration: (int(v: r.end_time) - int(v: r.start_time))/1000000000}}))
      |> keep(columns: ["start_time", "end_time", "{test_title_tag_name}", "max_threads", "duration"])
      |> group()
      |> sort(columns: ["start_time"], desc: true)
      |> rename(columns: {{{test_title_tag_name}: "test_title"}})'''

    # ------------------------------------------------------------------
    # Time-series charts
    # ------------------------------------------------------------------

    def get_rps(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: sum, createEmpty: false)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: {self.granularity_seconds}))}}))
      |> set(key: "_field", value: "Requests per second")'''

    def get_active_threads(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, multi_node_tag: str = None) -> str:
        if multi_node_tag:
            return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => exists r["{multi_node_tag}"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: max, createEmpty: false)
      |> group(columns: ["_time", "_field"])
      |> sum()
      |> set(key: "_field", value: "Active threads")'''
        else:
            return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: max, createEmpty: false)
      |> set(key: "_field", value: "Active threads")'''

    def get_average_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "mean")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> group(columns: ["_field"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: mean, createEmpty: false)
      |> set(key: "_field", value: "Average response time")'''

    def get_median_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles50")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> group(columns: ["_field"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: median, createEmpty: false)
      |> set(key: "_field", value: "Median response time")'''

    def get_pct90_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles95")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> group(columns: ["_field"])
      |> aggregateWindow(
      every: {self.granularity_seconds}s,
      fn: (tables=<-, column) =>
      tables
          |> quantile(q: 0.90, method: "exact_selector"),
      createEmpty: false)
      |> set(key: "_field", value: "Pct response time")'''

    def get_error_count(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["status"] == "ko")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      |> group(columns: ["_field"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: sum, createEmpty: true)
      |> set(key: "_field", value: "Errors Per Second")'''

    # ------------------------------------------------------------------
    # Per-request time-series charts
    # ------------------------------------------------------------------

    def get_average_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "mean")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> rename(columns: {{request: "transaction"}})
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: mean, createEmpty: false)'''

    def get_median_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles50")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> rename(columns: {{request: "transaction"}})
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: median, createEmpty: false)'''

    def get_pct90_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles95")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> rename(columns: {{request: "transaction"}})
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(
          every: {self.granularity_seconds}s,
          fn: (tables=<-, column) =>
              tables
              |> quantile(q: 0.90, method: "exact_selector"),
          createEmpty: false)'''

    def get_throughput_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> rename(columns: {{request: "transaction"}})
      |> keep(columns: ["transaction", "_value", "_time"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: sum, createEmpty: false)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: {self.granularity_seconds}))}}))
      |> set(key: "_field", value: "Requests per second")'''

    # ------------------------------------------------------------------
    # Summary statistics (single scalar per test)
    # ------------------------------------------------------------------

    def get_max_active_users_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, multi_node_tag: str = None) -> str:
        if multi_node_tag:
            return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => exists r["{multi_node_tag}"])
      |> group(columns: ["{multi_node_tag}"])
      |> max()
      |> group()
      |> sum()'''
        else:
            return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "active")
      |> filter(fn: (r) => r["request"] == "users")
      |> filter(fn: (r) => r["status"] == "allUsers")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_value"])
      |> max(column: "_value")'''

    def get_median_throughput_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: sum, createEmpty: true)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: {self.granularity_seconds}))}}))
      |> keep(columns: ["_value"])
      |> median(column: "_value")'''

    def get_median_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles50")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> group(columns: ["_field"])
      |> keep(columns: ["_value"])
      |> median()'''

    def get_pct90_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "percentiles95")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["status"] == "all")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> group(columns: ["_field"])
      |> keep(columns: ["_value"])
      |> median()'''

    def get_errors_pct_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      |> group(columns: ["status"])
      |> sum()
      |> filter(fn: (r) => exists r.status)
      |> pivot(rowKey: [], columnKey: ["status"], valueColumn: "_value")
      |> map(fn: (r) => ({{ r with errors: if exists r.ko then (r.ko/r.all*100.0) else 0.0 }}))
      |> keep(columns: ["errors"])'''

    # ------------------------------------------------------------------
    # Aggregated table (per-request summary)
    # ------------------------------------------------------------------

    def get_aggregated_data(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, regex: str, multi_node_tag: str = None) -> str:
        return f'''import "join"
            rpm_set = from(bucket: "{bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "gatling")
            |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
            |> filter(fn: (r) => r._field == "count")
            |> filter(fn: (r) => r["status"] == "all")
            |> filter(fn: (r) => r["request"] != "users")
            |> filter(fn: (r) => r["request"] != "allRequests")
            {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
            {f'|> group(columns: ["request"])' if multi_node_tag else ''}
            |> rename(columns: {{request: "transaction"}})
            |> keep(columns: ["_value", "_time", "transaction"])
            |> aggregateWindow(every: 60s, fn: sum, createEmpty: true)
            |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: 60))}}))
            |> median()
            |> group()
            |> rename(columns: {{"_value": "rpm"}})
            |> keep(columns: ["rpm", "transaction"])

            errors_set = from(bucket: "{bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "gatling")
            |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
            |> filter(fn: (r) => r._field == "count")
            |> filter(fn: (r) => r["status"] == "ko" or r["status"] == "all")
            |> filter(fn: (r) => r["request"] != "users")
            |> filter(fn: (r) => r["request"] != "allRequests")
            {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
            |> rename(columns: {{request: "transaction"}})
            |> group(columns: ["transaction", "status"])
            |> sum()
            |> pivot(rowKey: ["transaction"], columnKey: ["status"], valueColumn: "_value")
            |> group()
            |> map(fn: (r) => ({{ r with errors: if exists r.ko then (r.ko/r.all*100.0) else 0.0 }}))
            |> toInt()
            |> rename(columns: {{"all": "count"}})
            |> keep(columns: ["errors", "count", "transaction"])

            stats1 = join.full(
                left: rpm_set,
                right: errors_set,
                on: (l, r) => l.transaction == r.transaction,
                as: (l, r) => {{
                    return {{transaction: l.transaction, rpm: l.rpm, errors: r.errors, count: r.count}}
                }},
            )

            base_stats2 = from(bucket: "{bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "gatling")
            |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
            |> filter(fn: (r) => r._field == "mean" or r._field == "percentiles50" or r._field == "percentiles75" or r._field == "percentiles95")
            |> filter(fn: (r) => r["status"] == "all")
            |> filter(fn: (r) => r["request"] != "users")
            |> filter(fn: (r) => r["request"] != "allRequests")
            {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
            {f'|> group(columns: ["request", "_field"])' if multi_node_tag else ''}
            |> rename(columns: {{request: "transaction"}})
            |> keep(columns: ["_value", "transaction", "_field"])

            avg_stat = base_stats2
              |> filter(fn: (r) => r._field == "mean")
              |> group(columns: ["transaction"])
              |> mean()
              |> toInt()
              |> set(key: "_field", value: "avg")

            p50_stat = base_stats2
              |> filter(fn: (r) => r._field == "percentiles50")
              |> group(columns: ["transaction"])
              |> quantile(q: 0.50)
              |> toInt()
              |> set(key: "_field", value: "pct50.0")

            p75_stat = base_stats2
              |> filter(fn: (r) => r._field == "percentiles75")
              |> group(columns: ["transaction"])
              |> quantile(q: 0.75)
              |> toInt()
              |> set(key: "_field", value: "pct75.0")

            p90_stat = base_stats2
              |> filter(fn: (r) => r._field == "percentiles95")
              |> group(columns: ["transaction"])
              |> quantile(q: 0.90)
              |> toInt()
              |> set(key: "_field", value: "pct90.0")

            stats2 = union(tables: [avg_stat, p50_stat, p75_stat, p90_stat])
            |> group()
            |> pivot(rowKey: ["transaction"], columnKey: ["_field"], valueColumn: "_value")
            |> map(fn: (r) => ({{
                r with
                pct50: if exists r["pct50.0"] then r["pct50.0"] else 0,
                pct75: if exists r["pct75.0"] then r["pct75.0"] else 0,
                pct90: if exists r["pct90.0"] then r["pct90.0"] else 0,
            }}))
            |> drop(columns: ["pct50.0", "pct75.0", "pct90.0"])

            stats3 = join.full(
                left: stats1,
                right: stats2,
                on: (l, r) => l.transaction == r.transaction,
                as: (l, r) => {{
                    return {{transaction: l.transaction, rpm: l.rpm, errors: l.errors, count: l.count, avg: r.avg, pct50: r.pct50, pct75: r.pct75, pct90: r.pct90}}
                }},
            )

            stddev = from(bucket: "{bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r._measurement == "gatling")
            |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
            |> filter(fn: (r) => r._field == "mean")
            |> filter(fn: (r) => r["status"] == "all")
            |> filter(fn: (r) => r["request"] != "users")
            |> filter(fn: (r) => r["request"] != "allRequests")
            {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
            {f'|> group(columns: ["request"])' if multi_node_tag else ''}
            |> rename(columns: {{request: "transaction"}})
            |> keep(columns: ["_value", "transaction"])
            |> group(columns: ["transaction"])
            |> stddev()
            |> toInt()
            |> group()
            |> rename(columns: {{"_value": "stddev"}})

            join.full(
                left: stats3,
                right: stddev,
                on: (l, r) => l.transaction == r.transaction,
                as: (l, r) => {{
                    return {{transaction: l.transaction, rpm: l.rpm, errors: l.errors, count: l.count, avg: l.avg, pct50: l.pct50, pct75: l.pct75, pct90: l.pct90, stddev: r.stddev }}
                }},
            )'''

    # ------------------------------------------------------------------
    # Custom variable extraction
    # ------------------------------------------------------------------

    def get_custom_var(self, testTitle: str, custom_var: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
        return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["{custom_var}"])
      |> group()
      |> distinct(column: "{custom_var}")
      |> first()'''

    # ------------------------------------------------------------------
    # Overview table (optional, mirrors the JMeter overview query)
    # ------------------------------------------------------------------

    def get_overview_data(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str, regex: str) -> str:
        return f'''gatling_data = from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "gatling" and r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["request"] != "users")
      |> filter(fn: (r) => r["request"] != "allRequests")
      {f'|> filter(fn: (r) => r.request =~ /{regex}/)' if regex else ''}
      |> keep(columns: ["_field", "_value", "_time", "status"])

      avg_stat = gatling_data
      |> filter(fn: (r) => r._field == "mean" and r["status"] == "all")
      |> mean()
      |> map(fn: (r) => ({{Metric: "Average", Value: r._value}}))

      median_stat = gatling_data
      |> filter(fn: (r) => r._field == "percentiles50" and r["status"] == "all")
      |> median()
      |> map(fn: (r) => ({{Metric: "Median", Value: r._value}}))

      p75_stat = gatling_data
      |> filter(fn: (r) => r._field == "percentiles75" and r["status"] == "all")
      |> quantile(q: 0.75)
      |> map(fn: (r) => ({{Metric: "75%-tile", Value: r._value}}))

      p90_stat = gatling_data
      |> filter(fn: (r) => r._field == "percentiles95" and r["status"] == "all")
      |> quantile(q: 0.90)
      |> map(fn: (r) => ({{Metric: "90%-tile", Value: r._value}}))

      count_data = gatling_data
      |> filter(fn: (r) => r._field == "count")

      total_stat = count_data
      |> filter(fn: (r) => r["status"] == "all")
      |> sum()
      |> map(fn: (r) => ({{Metric: "Total requests", Value: r._value}}))

      rps_stat = count_data
      |> filter(fn: (r) => r["status"] == "all")
      |> aggregateWindow(every: {self.granularity_seconds}s, fn: sum, createEmpty: true)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value) / float(v: {self.granularity_seconds}) }}))
      |> quantile(q: 0.75)
      |> map(fn: (r) => ({{Metric: "RPS", Value: r._value}}))

      error_stat = count_data
      |> group(columns: ["_field", "status"])
      |> sum()
      |> filter(fn: (r) => exists r.status)
      |> pivot(rowKey: ["_field"], columnKey: ["status"], valueColumn: "_value")
      |> map(fn: (r) => ({{
          Metric: "Error %",
          Value: if exists r.ko and exists r.all and r.all > 0.0 then float(v: r.ko) * 100.0 / float(v: r.all) else 0.0
        }}))

      union(tables: [avg_stat, median_stat, p75_stat, p90_stat, total_stat, rps_stat, error_stat])
      |> group()
      '''
