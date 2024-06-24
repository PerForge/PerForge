# # Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

# import plotly
# import plotly.express
# import json

# from app.backend.integrations.secondary.influxdb                   import Influxdb
# from app.backend.integrations.secondary.influxdb_backend_listeners import custom
# from app.backend.validation                                        import Validation
# from datetime                                                      import datetime
# from dateutil                                                      import tz


# class HtmlReport:

#     def __init__(self, project, run_id, influxdb_name):
#         self.project          = project
#         self.runId            = run_id
#         self.influxdb_obj     = Influxdb(project, influxdb_name).connect_to_influxdb()
#         self.query_api        = self.influxdb_obj.influxdb_connection.query_api()
#         self.report           = {}
#         self.report['run_id'] = run_id
#         self.report['stats']  = {}
#         self.report['graph']  = {}
#         self.tmz = tz.tzlocal()
#         self.get_start_time()
#         self.get_end_time()
#         self.get_app_name()

#     def get_start_time(self):
#         flux_tables = self.query_api.query(custom.get_start_time(self.runId, self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report["start_timestamp"] = datetime.strftime(flux_record['_time'],"%Y-%m-%dT%H:%M:%SZ")
#                 self.report["start_time"] = datetime.strftime(flux_record['_time'].astimezone(self.tmz), "%Y-%m-%d %I:%M:%S %p")

#     def get_end_time(self):
#         flux_tables = self.query_api.query(custom.get_end_time(self.runId, self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report["end_timestamp"] = datetime.strftime(flux_record['_time'],"%Y-%m-%dT%H:%M:%SZ")
#                 self.report["end_time"] = datetime.strftime(flux_record['_time'].astimezone(self.tmz), "%Y-%m-%d %I:%M:%S %p")

#     def get_duration(self):
#         duration = datetime.strptime(self.report['end_timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(self.report['start_timestamp'], "%Y-%m-%dT%H:%M:%SZ")
#         self.report["duration"] = str(duration)
    
#     def get_max_active_users_stats(self):
#         flux_tables = self.query_api.query(custom.get_max_active_users_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['max_active_threads'] = flux_record['_value']

#     def get_average_RPS_stats(self):
#         flux_tables = self.query_api.query(custom.get_average_rps_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['rps'] = round(flux_record['_value'], 2)

#     def get_errors_perc_stats(self):
#         flux_tables = self.query_api.query(custom.get_errors_perc_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['errors'] = round(flux_record['_value'], 2)

#     def get_avg_response_time_stats(self):
#         flux_tables = self.query_api.query(custom.get_avg_response_time_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['avg_response_time'] = round(flux_record['_value'], 2)

#     def get_90_response_time_stats(self):
#         flux_tables = self.query_api.query(custom.get_90_response_time_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['percentile_response_time'] = round(flux_record['_value'], 2)

#     def get_avg_bandwidth_stats(self):
#         flux_tables = self.query_api.query(custom.get_avg_bandwidth_stats(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['stats']['avgBandwidth'] = round(flux_record['_value']/1048576, 2)

#     def getavg_response_time_graph(self):
#         flux_tables = self.query_api.query(custom.get_avg_response_time_graph(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         for flux_table in flux_tables:
#             x_vals = []
#             y_vals = []
#             # Influxdb returns a list of tables and rows, therefore it needs to be iterated in a loop
#             for flux_record in flux_table:
#                 y_vals.append(flux_record["_value"])
#                 x_vals.append(flux_record["_time"])
#         fig = plotly.express.line(x=x_vals, y=y_vals) 
#         fig.update_layout(showlegend=False, 
#                     paper_bgcolor    = 'rgb(47, 46, 46)', 
#                     plot_bgcolor     = 'rgb(47, 46, 46)',
#                     title_text       = 'Response time',
#                     title_font_color = "white",
#                     title_x          = 0.5
#                     )
#         fig.update_yaxes(gridcolor='#444444', color="white", title_text='Milliseconds', ticksuffix="ms")
#         fig.update_xaxes(gridcolor='#444444', color="white", title_text='Time')
#         self.report['graph']['avg_response_time'] = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

#     def get_rps_graph(self):
#         flux_tables = self.query_api.query(custom.get_rps_graph(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         for flux_table in flux_tables:
#             x_vals = []
#             y_vals = []
#             for flux_record in flux_table:
#                 y_vals.append(flux_record["_value"])
#                 x_vals.append(flux_record["_time"])
#         fig = plotly.express.line(x=x_vals, y=y_vals) 
#         fig.update_layout(showlegend=False, 
#                     paper_bgcolor    = 'rgb(47, 46, 46)', 
#                     plot_bgcolor     = 'rgb(47, 46, 46)',
#                     title_text       = 'RPS',
#                     title_font_color = "white",
#                     title_x          = 0.5
#                     )
#         fig.update_yaxes(gridcolor='#444444', color="white", title_text='r/s', ticksuffix="r/s")
#         fig.update_xaxes(gridcolor='#444444', color="white", title_text='Time')
#         self.report['graph']['rps'] = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

#     def get_app_name(self):
#         flux_tables = self.query_api.query(custom.get_app_name(self.runId, self.report['start_timestamp'], self.report['end_timestamp'], self.influxdb_obj.bucket))
#         for flux_table in flux_tables:
#             for flux_record in flux_table:
#                 self.report['app_name'] = flux_record['test_name']

#     def create_report(self):
#         self.get_duration()
#         self.get_max_active_users_stats()
#         self.get_average_RPS_stats()
#         self.get_errors_perc_stats()
#         self.get_avg_response_time_stats()
#         self.get_90_response_time_stats()
#         self.get_avg_bandwidth_stats()
#         self.getavg_response_time_graph()
#         self.get_rps_graph()
#         NFR_obj              = Validation(self.project)
#         comp_result          = NFR_obj.compare_with_NFRs(app_name = self.report['app_name'], runId = self.report['run_id'],start = self.report["start_timestamp"], end = self.report["end_timestamp"])
#         self.report['NFRs']  = comp_result
#         self.report['apdex'] = NFR_obj.calculate_apdex(comp_result)
#         self.influxdb_obj.close_influxdb_connection()