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

def get_test_log_query(bucket):
  return '''data = from(bucket: "'''+bucket+'''")
    |> range(start: 0, stop: now())
    |> filter(fn: (r) => r["_measurement"] == "jmeter")
    |> filter(fn: (r) => r["_field"] == "maxAT")
    |> aggregateWindow(every: 1m, fn: last, createEmpty: false)

  maxThreads = data
    |> keep(columns: ["_value", "testTitle", "application"])
    |> max()
    |> group(columns: ["_value", "testTitle", "application"])
    |> rename(columns: {_value: "maxThreads"})

  endTime = data 
    |> max(column: "_time")
    |> keep(columns: ["_time", "testTitle", "application"])
    |> group(columns: ["_time", "testTitle", "application"])
    |> rename(columns: {_time: "endTime"})

  startTime = data 
    |> min(column: "_time")
    |> keep(columns: ["_time", "testTitle", "application"])
    |> group(columns: ["_time", "testTitle", "application"])
    |> rename(columns: {_time: "startTime"})

  join1 = join(tables: {d1: maxThreads, d2: startTime}, on: ["testTitle", "application"])
    |> keep(columns: ["startTime","testTitle", "application",  "maxThreads"])
    |> group(columns: ["testTitle", "application"])

  join(tables: {d1: join1, d2: endTime}, on: ["testTitle", "application"])
    |> map(fn: (r) => ({ r with duration: (int(v: r.endTime)/1000000000 - int(v: r.startTime)/1000000000)}))
    |> keep(columns: ["startTime","endTime","testTitle", "application", "maxThreads", "duration"])
    |> group()
    |> rename(columns: {testTitle: "runId"})
    |> rename(columns: {application: "testName"})'''

def get_start_time(testTitle, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "jmeter")
  |> filter(fn: (r) => r["_field"] == "maxAT")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> keep(columns: ["_time"])
  |> min(column: "_time")'''

def get_end_time(testTitle, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "jmeter")
  |> filter(fn: (r) => r["_field"] == "maxAT")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> keep(columns: ["_time"])
  |> max(column: "_time")'''

def get_max_active_users_stats(testTitle, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "jmeter")
  |> filter(fn: (r) => r["_field"] == "maxAT")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> keep(columns: ["_value"])
  |> max(column: "_value")'''

def get_app_name(testTitle, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "events")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> distinct(column: "application")
  |> keep(columns: ["application"])'''

def get_test_duration(testTitle, start, stop, bucket):
  return '''data = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "jmeter")
  |> filter(fn: (r) => r["_field"] == "maxAT")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  
  endTime = data 
    |> max(column: "_time")
    |> keep(columns: ["_time", "testTitle"])
    |> group(columns: ["_time", "testTitle"])
    |> rename(columns: {_time: "endTime"})

  startTime = data 
    |> min(column: "_time")
    |> keep(columns: ["_time", "testTitle"])
    |> group(columns: ["_time", "testTitle"])
    |> rename(columns: {_time: "startTime"})

  join(tables: {d1: startTime, d2: endTime}, on: ["testTitle"])
    |> map(fn: (r) => ({ r with duration: (int(v: r.endTime)/1000000000 - int(v: r.startTime)/1000000000)}))
    |> keep(columns: ["duration"])
  '''

################################################################# NFR requests
  
def flux_constructor(app_name, testTitle, start, stop, bucket, request_name = ''):
  constr                                  = {}
  constr["source"]                        = 'from(bucket: "'+bucket+'")\n'
  constr["range"]                         = '|> range(start: '+str(start)+', stop: '+str(stop)+')\n'
  constr["_measurement"]                  = '|> filter(fn: (r) => r["_measurement"] == "jmeter")\n'
  constr["metric"]                        = {}
  constr["metric"]["avg"]                 = '|> filter(fn: (r) => r["_field"] == "avg")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["metric"]["median"]              = '|> filter(fn: (r) => r["_field"] == "pct50.0")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["metric"]["75%-tile"]            = '|> filter(fn: (r) => r["_field"] == "pct75.0")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["metric"]["90%-tile"]            = '|> filter(fn: (r) => r["_field"] == "pct90.0")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["metric"]["95%-tile"]            = '|> filter(fn: (r) => r["_field"] == "pct95.0")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["metric"]["errors"]              = '|> filter(fn: (r) => r["_field"] == "count")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "ko")\n'
  constr["metric"]["rps"]                 = '|> filter(fn: (r) => r["_field"] == "count")\n' + \
                                            '|> filter(fn: (r) => r["statut"] == "all")\n'
  constr["testTitle"]                     = '|> filter(fn: (r) => r["testTitle"] == "'+testTitle+'")\n'
  constr["scope"]                         = {}
  constr["scope"]['all']                  = '|> filter(fn: (r) => r["transaction"] == "all")\n' + \
                                            '|> group(columns: ["_field"])\n'
  constr["scope"]['each']                 = '|> filter(fn: (r) => r["transaction"] != "all")\n' + \
                                            '|> group(columns: ["transaction"])\n'
  constr["scope"]['request']              = '|> filter(fn: (r) => r["transaction"] == "'+request_name+'")\n' + \
                                            '|> group(columns: ["transaction"])\n'
  constr["aggregation"]                   = {}
  constr["aggregation"]['avg']            = '|> mean()\n'
  constr["aggregation"]['median']         = '|> median()\n'
  constr["aggregation"]["75%-tile"]       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.75)\n'
  constr["aggregation"]["90%-tile"]       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.90)\n'
  constr["aggregation"]["95%-tile"]       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.95)\n'
  constr["aggregation"]['count']          = '|> count()\n'
  constr["aggregation"]['sum']            = '|> sum()\n'
  constr["aggregation"]["rps"]            = '|> aggregateWindow(every: 1s, fn: sum, createEmpty: false)\n'
  return constr


########################## AGGREGATED TABLE

def get_aggregated_data(testTitle, start, stop, bucket):
  return '''import "join"
rpm_set = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r._measurement == "jmeter")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> filter(fn: (r) => r._field == "count")
  |> filter(fn: (r) => r["statut"] == "all")
  |> keep(columns: ["_value", "_time", "transaction"])
  |> aggregateWindow(every: 60s, fn: sum, createEmpty: true)
  |> map(fn: (r) => ({ r with _value: float(v: r._value / float(v: 60))}))
  |> median()
  |> group()
  |> rename(columns: {"_value": "rpm"})
  |> keep(columns: ["rpm", "transaction"])

errors_set = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r._measurement == "jmeter")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> filter(fn: (r) => r._field == "count")
  |> filter(fn: (r) => r["statut"] == "ko" or r["statut"] == "all")
  |> group(columns: ["transaction", "statut"])
  |> sum()
  |> pivot(rowKey: ["transaction"], columnKey: ["statut"], valueColumn: "_value")
  |> group()
  |> map(fn: (r) => ({ r with errors: if exists r.ko then (r.ko/r.all*100.0) else 0.0 }))
  |> toInt()
  |> rename(columns: {"all": "count"})
  |> keep(columns: ["errors","count", "transaction"])

stats1 = join.full(
    left: rpm_set,
    right: errors_set,
    on: (l, r) => l.transaction== r.transaction,
    as: (l, r) => {
        return {transaction: l.transaction, rpm:l.rpm, errors:r.errors, count:r.count}
    },
)

stats2 = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r._measurement == "jmeter")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> filter(fn: (r) => r._field == "avg" or r._field == "pct50.0" or r._field == "pct75.0" or r._field == "pct90.0")
  |> filter(fn: (r) => r["statut"] == "all")
  |> keep(columns: ["_value", "transaction", "_field"])
  |> group(columns: ["transaction","_field"])
  |> median()
  |> toInt()
  |> group()
  |> pivot(rowKey: ["transaction"], columnKey: ["_field"], valueColumn: "_value")
  |> map(fn: (r) => ({
      r with
      pct50: if exists r["pct50.0"] then r["pct50.0"] else 0,
      pct75: if exists r["pct75.0"] then r["pct75.0"] else 0,
      pct90: if exists r["pct90.0"] then r["pct90.0"] else 0,
  }))
  |> drop(columns: ["pct50.0", "pct75.0", "pct90.0"])

stats3 = join.full(
    left: stats1,
    right: stats2,
    on: (l, r) => l.transaction== r.transaction,
    as: (l, r) => {
        return {transaction: l.transaction, rpm:l.rpm, errors:l.errors, count:l.count, avg:r.avg, pct50:r.pct50, pct75:r.pct75, pct90:r.pct90}
    },
)

stddev = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r._measurement == "jmeter")
  |> filter(fn: (r) => r["testTitle"] == "'''+testTitle+'''")
  |> filter(fn: (r) => r._field == "avg")
  |> filter(fn: (r) => r["statut"] == "all")
  |> keep(columns: ["_value", "transaction"])
  |> group(columns: ["transaction"])
  |> stddev()
  |> toInt()
  |> group()
  |> rename(columns: {"_value": "stddev"})

join.full(
    left: stats3,
    right: stddev,
    on: (l, r) => l.transaction== r.transaction,
    as: (l, r) => {
        return {transaction: l.transaction, rpm:l.rpm, errors:l.errors, count:l.count, avg:l.avg, pct50:l.pct50, pct75:l.pct75, pct90:l.pct90, stddev:r.stddev }
    },
)'''