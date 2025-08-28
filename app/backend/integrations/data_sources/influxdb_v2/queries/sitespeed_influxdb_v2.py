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

from typing import override
from app.backend.integrations.data_sources.base_queries import FrontEndQueriesBase

class SitespeedFluxQueries(FrontEndQueriesBase):
  def get_tests_titles(
      self,
      bucket: str,
      test_title_tag_name: str,
  ) -> str:
        """Return Flux query to get distinct test titles."""
        base_query = (
            f"from(bucket: \"{bucket}\")\n"
            f"  |> range(start: 0, stop: now())\n"
            f"  |> filter(fn: (r) => r._measurement == \"largestContentfulPaint\" and r._field == \"median\" and r.origin == \"browsertime\" )\n"
            f"  |> group(columns: [\"{test_title_tag_name}\"])\n"
            f"  |> min(column: \"_time\")\n"
            f"  |> group()"
            f"  |> sort(columns: [\"_time\"], desc: true)\n"
            f"  |> keep(columns: [\"{test_title_tag_name}\"])"
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

    base_query = f'''data = from(bucket: "{bucket}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "largestContentfulPaint")
      |> filter(fn: (r) => r["_field"] == "median")
      |> filter(fn: (r) => contains(value: r["{test_title_tag_name}"], set: [{formatted}]))
      |> keep(columns: ["_time", "{test_title_tag_name}"])

    end_time = data
      |> max(column: "_time")
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "end_time"}})

    start_time = data
      |> min(column: "_time")
      |> group(columns: ["_time", "{test_title_tag_name}"])
      |> rename(columns: {{_time: "start_time"}})

    join(tables: {{d1: start_time, d2: end_time}}, on: ["{test_title_tag_name}"])
      |> map(fn: (r) => ({{ r with duration: (int(v: r.end_time)/1000000000 - int(v: r.start_time)/1000000000)}}))
      |> keep(columns: ["start_time","end_time","{test_title_tag_name}", "duration"])
      |> group()
      |> sort(columns: ["start_time"], desc: true)
      |> rename(columns: {{{test_title_tag_name}: "test_title"}})
      |> set(key: "max_threads", value: "1")'''
    return base_query

  def get_start_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "largestContentfulPaint")
      |> filter(fn: (r) => r["_field"] == "median")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> min(column: "_time")'''

  def get_end_time(self, testTitle: str, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "largestContentfulPaint")
      |> filter(fn: (r) => r["_field"] == "median")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["_time"])
      |> max(column: "_time")'''

  def get_google_web_vitals(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["statistics"] == "googleWebVitals")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      |> rename(columns: {{cumulativeLayoutShift: "CLS"}})
      |> rename(columns: {{firstContentfulPaint: "FCP"}})
      |> rename(columns: {{firstInputDelay: "FID"}})
      |> rename(columns: {{largestContentfulPaint: "LCP"}})
      |> rename(columns: {{totalBlockingTime: "TBT"}})
      |> rename(columns: {{ttfb: "TTFB"}})
      '''

  def get_timings_fully_loaded(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["statistics"] == "timings")
      |> filter(fn: (r) => r["_measurement"] == "fullyLoaded")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_timings_page_timings(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => exists r["pageTimings"])
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_timings_main_document(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["mainDocumentTimings"] != "")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_cpu_long_tasks(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["statistics"] == "cpu")
      |> filter(fn: (r) => r["summaryType"] == "pageSummary")
      |> filter(fn: (r) => r["_measurement"] == "durations" or r["_measurement"] == "lastLongTask" or r["_measurement"] == "maxPotentialFid"  or r["_measurement"] == "tasks" or r["_measurement"] == "totalBlockingTime" or r["_measurement"] == "totalDuration")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_cdp_performance_js_heap_used_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "JSHeapUsedSize")
      |> filter(fn: (r) => r["performance"] == "JSHeapUsedSize")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_cdp_performance_js_heap_total_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "JSHeapTotalSize")
      |> filter(fn: (r) => r["performance"] == "JSHeapTotalSize")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["_field"] == "{aggregation}")
      |> group(columns: ["page", "_measurement"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["_measurement"], valueColumn: "_value")
      |> group()
      '''

  def get_count_per_content_type(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["_measurement"] == "requests")
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> filter(fn: (r) => r["summaryType"] == "pageSummary")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => exists r["contentType"])
      |> filter(fn: (r) => not exists r["party"])
      |> filter(fn: (r) => not exists r["thirdPartyType"])
      |> group(columns: ["page", "contentType"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["contentType"], valueColumn: "_value")
      |> group()
      '''

  def get_first_party_transfer_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["party"] == "firstParty")
      |> filter(fn: (r) => r["_measurement"] == "transferSize")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => exists r["contentType"])
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "contentType"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["contentType"], valueColumn: "_value")
      |> group()
      '''

  def get_third_party_transfer_size(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median') -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["party"] == "thirdParty")
      |> filter(fn: (r) => r["_measurement"] == "transferSize")
      |> filter(fn: (r) => exists r["page"])
      |> filter(fn: (r) => exists r["contentType"])
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> group(columns: ["page", "contentType"])
      |> median()
      |> pivot(rowKey: ["page"], columnKey: ["contentType"], valueColumn: "_value")
      |> group()
      '''

  def get_custom_var(self, testTitle: str, custom_var: str, start: int, stop: int, bucket: str, test_title_tag_name: str) -> str:
      return f'''from(bucket: "{bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
      |> keep(columns: ["{custom_var}"])
      |> group()
      |> distinct(column: "{custom_var}")
      |> first()'''

  def get_overview_data(self, testTitle: str, start: int, stop: int, bucket: str, test_title_tag_name: str, aggregation: str = 'median', regex: str = '') -> str:
       return f'''base_data = from(bucket: "{bucket}")
            |> range(start: {start}, stop: {stop})
            |> filter(fn: (r) => r["{test_title_tag_name}"] == "{testTitle}")
            |> toFloat()

        web_vitals = base_data
            |> filter(fn: (r) => r["_measurement"] == "largestContentfulPaint" or r["_measurement"] == "firstContentfulPaint" or r["_measurement"] == "fullyLoaded" or r["_measurement"] == "ttfb")
            |> filter(fn: (r) => r["_field"] == "{aggregation}")
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{
                Metric:
                    if r._measurement == "firstContentfulPaint" then "FCP"
                    else if r._measurement == "largestContentfulPaint" then "LCP"
                    else if r._measurement == "fullyLoaded" then "Fully Loaded"
                    else if r._measurement == "ttfb" then "TTFB"
                    else r._measurement,
                Value: r._value
            }}))

        total_transfer = base_data
            |> filter(fn: (r) => r["_measurement"] == "transferSize" and r["summaryType"] == "pageSummary")
            |> filter(fn: (r) => not exists r["party"] and not exists r["contentType"])
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Total Transfer Size (KB)", Value: r._value / 1024.0}}))

        total_requests = base_data
            |> filter(fn: (r) => r["_measurement"] == "requests" and r["_field"] == "value")
            |> filter(fn: (r) => not exists r["contentType"] and not exists r["party"])
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Total Requests", Value: r._value}}))

        third_party_requests = base_data
            |> filter(fn: (r) => r["_measurement"] == "requests" and r["_field"] == "value")
            |> filter(fn: (r) => not exists r["contentType"] and r["party"] == "thirdParty")
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Third-Party Requests", Value: r._value}}))

        transfer_by_content = base_data
            |> filter(fn: (r) => r["_measurement"] == "transferSize" and r["summaryType"] == "pageSummary")
            |> filter(fn: (r) => not exists r["party"])

        js_transfer = transfer_by_content
            |> filter(fn: (r) => r["contentType"] == "javascript" and r["type"] == "ondemand" and r["env"] == "CAN")
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Transfer Size for JavaScript (KB)", Value: r._value / 1024.0}}))

        css_transfer = transfer_by_content
            |> filter(fn: (r) => r["contentType"] == "css")
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Transfer Size for CSS (KB)", Value: r._value / 1024.0}}))

        image_transfer = transfer_by_content
            |> filter(fn: (r) => r["contentType"] == "image")
            |> group(columns: ["_measurement"])
            |> quantile(q: 0.50)
            |> map(fn: (r) => ({{Metric: "Transfer Size for Image (KB)", Value: r._value / 1024.0}}))

        union(
            tables: [
                web_vitals,
                total_transfer,
                total_requests,
                third_party_requests,
                js_transfer,
                css_transfer,
                image_transfer
            ]
        )
        |> group()
        |> sort(columns: ["Metric"])
        '''
