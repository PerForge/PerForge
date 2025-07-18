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

from app.backend.integrations.data_sources.base_queries import FrontEndQueriesBase

class SitespeedFluxQueries(FrontEndQueriesBase):
  def get_test_log(self, bucket: str, test_title_tag_name: str) -> str:
    return f'''data = from(bucket: "{bucket}")
      |> range(start: 0, stop: now())
      |> filter(fn: (r) => r["_measurement"] == "largestContentfulPaint")
      |> filter(fn: (r) => r["_field"] == "median")
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
      |> rename(columns: {{{test_title_tag_name}: "test_title"}})
      |> set(key: "max_threads", value: "1")
      '''

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
