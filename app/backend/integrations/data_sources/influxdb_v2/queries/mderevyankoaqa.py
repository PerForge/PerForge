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

def get_test_log(bucket):
  return '''data = from(bucket: "'''+bucket+'''")
  |> range(start: 0, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "virtualUsers")
  |> filter(fn: (r) => r["_field"] == "maxActiveThreads")
  |> keep(columns: ["_time", "_value", "runId", "testName"])
  |> group(columns: ["runId", "testName"])
  |> fill(column: "testType", value: "-")

maxThreads = data 
  |> max(column: "_value")
  |> keep(columns: ["_value", "runId", "testName"])
  |> group(columns: ["_value", "runId", "testName"])
  |> rename(columns: {_value: "maxThreads"})

endTime = data 
  |> max(column: "_time")
  |> keep(columns: ["_time", "runId", "testName"])
  |> group(columns: ["_time", "runId", "testName"])
  |> rename(columns: {_time: "endTime"})

startTime = data 
  |> min(column: "_time")
  |> keep(columns: ["_time", "runId", "testName"])
  |> group(columns: ["_time", "runId", "testName"])
  |> rename(columns: {_time: "startTime"})

join1 = join(tables: {d1: maxThreads, d2: startTime}, on: ["runId", "testName"])
  |> keep(columns: ["startTime","runId", "testName",  "maxThreads"])
  |> group(columns: ["runId", "testName"])

join(tables: {d1: join1, d2: endTime}, on: ["runId", "testName"])
  |> map(fn: (r) => ({ r with duration: ((int(v: r.endTime)/1000000000 - int(v: r.startTime)/1000000000))}))
  |> keep(columns: ["startTime","endTime", "runId", "testName",  "maxThreads", "duration", "dashboard"])
  |> group(columns: ["1"])
  |> rename(columns: {runId: "test_title"})
'''


def get_start_time(run_id, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: -2y)
  |> filter(fn: (r) => r["_measurement"] == "virtualUsers")
  |> filter(fn: (r) => r["_field"] == "maxActiveThreads")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> keep(columns: ["_time"])
  |> min(column: "_time")'''

def get_end_time(run_id, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: -2y)
  |> filter(fn: (r) => r["_measurement"] == "virtualUsers")
  |> filter(fn: (r) => r["_field"] == "maxActiveThreads")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> keep(columns: ["_time"])
  |> max(column: "_time")'''

def get_max_active_users_stats(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "virtualUsers")
  |> filter(fn: (r) => r["_field"] == "maxActiveThreads")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> keep(columns: ["_value"])
  |> max(column: "_value")'''

def get_average_rps_stats(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1s, fn: count, createEmpty: false)   
  |> mean()'''


def get_errors_perc_stats(run_id, start, stop, bucket):
  return '''countResponseTime=from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group()
  |> count()
  |> toFloat()
  |> set(key: "key", value: "value")

sumerrorCount=from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "errorCount")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group()
  |> sum()
  |> toFloat()
  |> set(key: "key", value: "value")

join(
      tables:{countResponseTime:countResponseTime, sumerrorCount:sumerrorCount},
      on:["key"]
    )    
    |> map(fn:(r) => ({
             key: r.key,
             _value: r._value_sumerrorCount / r._value_countResponseTime * 100.0        
    }))  '''

def get_avg_response_time_stats(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"]) 
  |> mean()'''

def get_90_response_time_stats(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"]) 
  |> toFloat() 
  |> quantile(q: 0.90)'''

def get_median_response_time_stats(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"]) 
  |> toFloat() 
  |> median()'''

def get_avg_bandwidth_stats(run_id, start, stop, bucket):
  return '''sentBytes = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "sentBytes")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> keep(columns: ["_time", "_value", "_field"])
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
  |> mean()
  |> set(key: "key", value: "value")
receivedBytes = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "receivedBytes")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> keep(columns: ["_time", "_value", "_field"])
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
  |> mean()
  |> set(key: "key", value: "value")
join(
      tables:{sentBytes:sentBytes, receivedBytes:receivedBytes},
      on:["key"]
    )    
    |> map(fn:(r) => ({
             key: r.key,
             _value: r._value_sentBytes + r._value_receivedBytes     
    }))'''

def get_avg_response_time_graph(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1s, fn: mean, createEmpty: false)
  '''

def get_rps_graph(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1s, fn: count, createEmpty: false)
  '''

################################################################# NFR requests

def get_app_name(run_id, start, stop, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> group(columns: ["testName"])
  |> max()
  |> keep(columns: ["testName"])
  |> rename(columns: {testName: "application"})'''
  
def flux_constructor(app_name, run_id, start, stop, bucket, request_name = ''):
  constr                                  = {}
  constr["source"]                        = 'from(bucket: "'+bucket+'")\n'
  constr["range"]                         = '|> range(start: '+str(start)+', stop: '+str(stop)+')\n'
  constr["_measurement"]                  = {}
  constr["_measurement"]["response-time"] = '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")\n'
  constr["_measurement"]["rps"]           = '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")\n'
  constr["_measurement"]["errors"]        = '|> filter(fn: (r) => r["_measurement"] == "requestsRaw")\n'
  constr["metric"]                        = {}
  constr["metric"]["response-time"]       = '|> filter(fn: (r) => r["_field"] == "responseTime")\n'
  constr["metric"]["rps"]                 = '|> filter(fn: (r) => r["_field"] == "responseTime")\n' 
  constr["metric"]["errors"]              = '|> filter(fn: (r) => r["_field"] == "errorCount")\n'
  constr["runId"]                         = '|> filter(fn: (r) => r["runId"] == "'+run_id+'")\n'
  constr["scope"]                         = {}
  constr["scope"]['all']                  = '|> group(columns: ["_field"])\n'
  constr["scope"]['each']                 = '|> group(columns: ["requestName"])\n' + \
                                            '|> rename(columns: {requestName: "transaction"})\n'
  constr["scope"]['request']              = '|> filter(fn: (r) => r["requestName"] == "'+request_name+'")\n' + \
                                            '|> group(columns: ["requestName"])\n' + \
                                            '|> rename(columns: {requestName: "transaction"})\n'
  constr["aggregation"]                   = {}
  constr["aggregation"]['avg']            = '|> mean()\n'
  constr["aggregation"]['median']         = '|> median()\n'
  constr["aggregation"]['75%-tile']       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.75)\n'
  constr["aggregation"]['90%-tile']       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.90)\n'
  constr["aggregation"]['95%-tile']       = '|> toFloat()\n' + \
                                            '|> quantile(q: 0.95)\n'
  constr["aggregation"]['count']          = '|> count()\n'
  constr["aggregation"]['sum']            = '|> sum()\n'
  constr["aggregation"]["rps"]            = '|> aggregateWindow(every: 1s, fn: count, createEmpty: false)\n' 
  return constr

def get_test_names(run_id, bucket):
  return '''from(bucket: "'''+bucket+'''")
  |> range(start: -1y)
  |> filter(fn: (r) => r["_measurement"] == "tests")
  |> filter(fn: (r) => r["runId"] == "'''+run_id+'''")
  |> group(columns: ["runId"])
  |> count()
  |> keep(columns: ["runId"])'''

########################## AGGREGATED TABLE

def get_aggregated_data(testTitle, start, stop, bucket):
  return '''errorsCount = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> filter(fn: (r) => r["_field"] == "count" or r["_field"] == "errorCount")
  |> group(columns: ["requestName", "_field"])
  |> sum()
  |> toFloat()
  |> pivot(rowKey: ["requestName"], columnKey: ["_field"], valueColumn: "_value")
  |> group()
  |> map(fn: (r) => ({ r with errors: if exists r.errorCount then (r.errorCount/r.count*100.0) else 0.0 }))
  |> rename(columns: {"requestName": "transaction"})
  |> keep(columns: ["errors","count", "transaction"])

pct50 = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> median()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "pct50"})
  |> keep(columns: ["pct50", "transaction"])

pct75 = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> quantile(q: 0.75)
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "pct75"})
  |> keep(columns: ["pct75", "transaction"])

pct90 = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> quantile(q: 0.90)
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "pct90"})
  |> keep(columns: ["pct90", "transaction"])

avg = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> mean()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "avg"})
  |> keep(columns: ["avg", "transaction"])

min = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> min()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "min"})
  |> keep(columns: ["min", "transaction"])

max = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> max()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "max"})
  |> keep(columns: ["max", "transaction"])

rpm = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> aggregateWindow(every: 60s, fn: count, createEmpty: true)
  |> mean()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "rpm"})
  |> keep(columns: ["rpm", "transaction"])

stddev = from(bucket: "'''+bucket+'''")
  |> range(start: '''+str(start)+''', stop: '''+str(stop)+''')
  |> filter(fn: (r) => r["_measurement"] == "requestsRaw")
  |> filter(fn: (r) => r["_field"] == "responseTime")
  |> filter(fn: (r) => r["samplerType"] == "request")
  |> filter(fn: (r) => r["runId"] == "'''+testTitle+'''")
  |> group(columns: ["requestName"])
  |> stddev()
  |> toInt()
  |> rename(columns: {"requestName": "transaction"})
  |> rename(columns: {"_value": "stddev"})
  |> keep(columns: ["stddev", "transaction"])

join1 = join(tables: {errorsCount: errorsCount, pct50: pct50}, on: ["transaction"])
join2 = join(tables: {join1: join1, pct75: pct75}, on: ["transaction"])
join3 = join(tables: {join2: join2, pct90: pct90}, on: ["transaction"])
join4 = join(tables: {join3: join3, avg: avg}, on: ["transaction"])
join5 = join(tables: {join4: join4, min: min}, on: ["transaction"])
join6 = join(tables: {join5: join5, max: max}, on: ["transaction"])
join7 = join(tables: {join6: join6, rpm: rpm}, on: ["transaction"])
join(tables: {join7: join7, stddev: stddev}, on: ["transaction"])
|> group()'''