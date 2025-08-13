# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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

class InfluxDBBackendListenerClientImpl(BackEndQueriesBase):
  def get_tests_titles(
      self,
      bucket: str,
      test_title_tag_name: str,
  ) -> str:
        """Return Flux query to get distinct test titles."""
        base_query = (
            f"from(bucket: \"{bucket}\")\n"
            f"  |> range(start: 0, stop: now())\n"
            f"  |> filter(fn: (r) => r._measurement == \"events\")\n"
            f"  |> group(columns: [\"{test_title_tag_name}\"])\n"
            f"  |> min(column: \"_time\")\n"
            f"  |> group()"
            f"  |> sort(columns: [\"_time\"], desc: true)\n"
            f"  |> keep(columns: [\"{test_title_tag_name}\"])\n"
            f"  |> rename(columns: {{{test_title_tag_name}: \"test_title\"}})"
        )
        return base_query

  def get_test_log(
    self,
    bucket: str,
    test_title_tag_name: str,
    *,
    test_titles: list[str],
    start_time: str,
    end_time: str,
) -> str:
    formatted = ", ".join([f'"{t}"' for t in test_titles])

    base_query = f'''
    data = from(bucket: "{bucket}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "maxAT")
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
      |> keep(columns: ["start_time","{test_title_tag_name}",  "max_threads"])
      |> group(columns: ["{test_title_tag_name}"])

    join(tables: {{d1: join1, d2: end_time}}, on: ["{test_title_tag_name}"])
      |> map(fn: (r) => ({{ r with duration: (int(v: r.end_time) - int(v: r.start_time))/1000000000}}))
      |> keep(columns: ["start_time","end_time","{test_title_tag_name}", "max_threads", "duration"])
      |> group()
      |> sort(columns: ["start_time"], desc: true)
      |> rename(columns: {{{test_title_tag_name}: "test_title"}})'''
    return base_query

  def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "maxAT")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> min(column: "_time")'''

  def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "maxAT")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> max(column: "_time")'''

  def get_aggregated_data(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''import "join"
      rpm_set = from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["statut"] == "all")
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(every: 60s, fn: sum, createEmpty: true)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: 60))}}))
      |> median()
      |> group()
      |> rename(columns: {{"_value": "rpm"}})
      |> keep(columns: ["rpm", "transaction"])

      errors_set = from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r._field == "count")
      |> filter(fn: (r) => r["statut"] == "ko" or r["statut"] == "all")
      |> group(columns: ["transaction", "statut"])
      |> sum()
      |> pivot(rowKey: ["transaction"], columnKey: ["statut"], valueColumn: "_value")
      |> group()
      |> map(fn: (r) => ({{ r with errors: if exists r.ko then (r.ko/r.all*100.0) else 0.0 }}))
      |> toInt()
      |> rename(columns: {{"all": "count"}})
      |> keep(columns: ["errors","count", "transaction"])

      stats1 = join.full(
        left: rpm_set,
        right: errors_set,
        on: (l, r) => l.transaction == r.transaction,
        as: (l, r) => {{
            return {{transaction: l.transaction, rpm: l.rpm, errors: r.errors, count: r.count}}
        }},
      )

      stats2 = from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r._field == "avg" or r._field == "pct50.0" or r._field == "pct75.0" or r._field == "pct90.0")
      |> filter(fn: (r) => r["statut"] == "all")
      |> keep(columns: ["_value", "transaction", "_field"])
      |> group(columns: ["transaction","_field"])
      |> median()
      |> toInt()
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
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r._field == "avg")
      |> filter(fn: (r) => r["statut"] == "all")
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

  def get_rps(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> filter(fn: (r) => r["transaction"] !~ /TR/ and r["transaction"] != "all")
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: 30s, fn: sum, createEmpty: false)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: 30))}}))
      |> set(key: "_field", value: "Requests per second")'''

  def get_active_threads(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "maxAT")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: 30s, fn: max, createEmpty: false)
      |> set(key: "_field", value: "Active threads")'''

  def get_average_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "avg")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> group(columns: ["_field"])
      |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
      |> set(key: "_field", value: "Average response time")'''

  def get_median_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "pct50.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> group(columns: ["_field"])
      |> aggregateWindow(every: 30s, fn: median, createEmpty: false)
      |> set(key: "_field", value: "Median response time")'''

  def get_pct90_response_time(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "pct90.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> group(columns: ["_field"])
      |> aggregateWindow(
      every: 30s,
      fn: (tables=<-, column) =>
      tables
          |> quantile(q: 0.90, method: "exact_selector"),
      createEmpty: false)
      |> set(key: "_field", value: "Pct response time")'''

  def get_error_count(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "countError")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["_field"])
      |> aggregateWindow(every: 30s, fn: sum, createEmpty: true)
      |> set(key: "_field", value: "Errors Per Second")'''

  def get_average_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "avg")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)'''

  def get_median_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "pct50.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(every: 30s, fn: median, createEmpty: false)'''

  def get_pct90_response_time_per_req(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "jmeter")
      |> filter(fn: (r) => r._field == "pct90.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> keep(columns: ["_value", "_time", "transaction"])
      |> aggregateWindow(
          every: 30s,
          fn: (tables=<-, column) =>
              tables
              |> quantile(q: 0.90, method: "exact_selector"),
          createEmpty: false)'''

  def get_max_active_users_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "maxAT")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_value"])
      |> max(column: "_value")'''

  def get_median_throughput_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> filter(fn: (r) => r["transaction"] != "all")
      |> keep(columns: ["_field", "_value", "_time"])
      |> aggregateWindow(every: 30s, fn: sum, createEmpty: true)
      |> map(fn: (r) => ({{ r with _value: float(v: r._value / float(v: 30))}}))
      |> keep(columns: ["_value"])
      |> median(column: "_value")'''

  def get_median_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "pct50.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> filter(fn: (r) => r["transaction"] != "all")
      |> group(columns: ["_field"])
      |> keep(columns: ["_value"])
      |> median()'''

  def get_pct90_response_time_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "pct90.0")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["statut"] == "all")
      |> filter(fn: (r) => r["transaction"] != "all")
      |> group(columns: ["_field"])
      |> keep(columns: ["_value"])
      |> median()'''

  def get_errors_pct_stats(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "jmeter")
      |> filter(fn: (r) => r["_field"] == "count")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["transaction"] != "all")
      |> group(columns: ["statut"])
      |> sum()
      |> filter(fn: (r) => exists r.statut)
      |> pivot(rowKey: [], columnKey: ["statut"], valueColumn: "_value")
      |> map(fn: (r) => ({{ r with errors: if exists r.ko then (r.ko/r.all*100.0) else 0.0 }}))
      |> keep(columns: ["errors"])'''

  def get_custom_var(self, testTitle: str, custom_var: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["{custom_var}"])
      |> group()
      |> distinct(column: "{custom_var}")
      |> first()'''
