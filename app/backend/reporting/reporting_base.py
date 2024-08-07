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

import re
import logging

from app.backend                                 import pkg
from app.backend.ai_support.ai_support           import AISupport
from app.backend.integrations.secondary.grafana  import Grafana
from app.backend.integrations.secondary.influxdb import Influxdb
from app.backend.validation                      import Validation


class ReportingBase:

    def __init__(self, project):
        self.project        = project
        self.progress       = 0
        self.status         = "Not started"
        self.validation_obj = Validation(project)

    def __del__(self):
        self.influxdb_obj.close_influxdb_connection()

    def set_template(self, template, influxdb):
        template_obj                   = pkg.get_template_values(self.project, template)
        self.nfr                       = template_obj["nfr"]
        self.title                     = template_obj["title"]
        self.data                      = template_obj["data"]
        self.template_prompt_id        = template_obj["template_prompt_id"]
        self.aggregated_prompt_id      = template_obj["aggregated_prompt_id"]
        self.system_prompt_id          = template_obj["system_prompt_id"]
        self.influxdb_obj              = Influxdb(project=self.project, id=influxdb).connect_to_influxdb()
        self.ai_switch                 = template_obj["ai_switch"]
        self.ai_aggregated_data_switch = template_obj["ai_aggregated_data_switch"]
        self.nfrs_switch               = template_obj["nfrs_switch"]
        self.ai_graph_switch           = template_obj["ai_graph_switch"]
        self.ai_to_graphs_switch       = template_obj["ai_to_graphs_switch"]
        if self.ai_switch:
            self.ai_support_obj = AISupport(project=self.project, system_prompt=self.system_prompt_id)

    def set_template_group(self, template_group):
        template_group_obj            = pkg.get_template_group_values(self.project, template_group)
        self.group_title              = template_group_obj["title"]
        self.template_order           = template_group_obj["data"]
        self.template_group_prompt_id = template_group_obj["prompt_id"]
        self.ai_summary               = template_group_obj["ai_summary"]

    def get_template_data(self, template):
        template_obj = pkg.get_template_values(self.project, template)
        return template_obj["data"]

    def replace_variables(self, text):
        variables = re.findall(r"\$\{(.*?)\}", text)
        for var in variables:
            if var in self.parameters:
                text = text.replace("${"+var+"}", str(self.parameters[var]))
            else:
                logging.warning(f"Variable {var} not found in parameters")
        return text
    
    def analyze_template(self):
        overall_summary = ""
        nfr_summary     = ""
        data            = []
        if self.nfrs_switch or self.ai_aggregated_data_switch:
            data = self.influxdb_obj.get_aggregated_table(self.current_run_id, self.current_start_time, self.current_end_time)
        if self.nfrs_switch:
            nfr_summary = self.validation_obj.create_summary(self.nfr, data)
        if self.ai_switch:
            if self.ai_aggregated_data_switch:
                self.ai_support_obj.analyze_aggregated_data(data, self.aggregated_prompt_id)
            overall_summary = self.ai_support_obj.create_template_summary(self.template_prompt_id, nfr_summary)
        else: 
            overall_summary += f"\n\n {nfr_summary}"
        return overall_summary

    def analyze_template_group(self):
        overall_summary = ""
        if self.ai_summary:
            overall_summary = self.ai_support_obj.create_template_group_summary(self.template_group_prompt_id)
        return overall_summary
    
    def generate_response(self):
        response = {}
        if self.ai_switch:
            response["Input tokens"]  = self.ai_support_obj.ai_obj.input_tokens
            response["Output tokens"] = self.ai_support_obj.ai_obj.output_tokens
        else:
            response["Input tokens"]  = 0
            response["Output tokens"] = 0
        return response
        
    def collect_data(self, current_run_id, baseline_run_id = None):
        default_grafana              = pkg.get_default_grafana(self.project)
        default_grafana_obj          = Grafana(project=self.project, id=default_grafana)
        self.current_run_id          = current_run_id
        self.baseline_run_id         = baseline_run_id
        self.current_start_time      = self.influxdb_obj.get_start_time(current_run_id)
        self.current_end_time        = self.influxdb_obj.get_end_time(current_run_id)
        self.current_start_timestamp = self.influxdb_obj.get_start_tmp(current_run_id)
        self.current_end_timestamp   = self.influxdb_obj.get_end_tmp(current_run_id)
        self.test_name               = self.influxdb_obj.get_test_name(current_run_id, self.current_start_time, self.current_end_time)
        self.parameters              = {
            "test_name"           : self.test_name,
            "current_start_time"  : self.influxdb_obj.get_human_start_time(current_run_id),
            "current_end_time"    : self.influxdb_obj.get_human_end_time(current_run_id),
            "current_grafana_link": default_grafana_obj.get_grafana_test_link(self.current_start_timestamp, self.current_end_timestamp, self.test_name, current_run_id),
            "current_duration"    : str(int((self.current_end_timestamp - self.current_start_timestamp) / 1000)),
            "current_vusers"      : self.influxdb_obj.get_max_active_users(current_run_id, self.current_start_time, self.current_end_time)
        }
        if baseline_run_id is not None:
            self.baseline_start_time      = self.influxdb_obj.get_start_time(baseline_run_id)
            self.baseline_end_time        = self.influxdb_obj.get_end_time(baseline_run_id)
            self.baseline_start_timestamp = self.influxdb_obj.get_start_tmp(baseline_run_id)
            self.baseline_end_timestamp   = self.influxdb_obj.get_end_tmp(baseline_run_id)

            self.parameters.update({
                "baseline_start_time"  : self.influxdb_obj.get_human_start_time(baseline_run_id),
                "baseline_end_time"    : self.influxdb_obj.get_human_end_time(baseline_run_id),
                "baseline_grafana_link": default_grafana_obj.get_grafana_test_link(self.baseline_start_timestamp, self.baseline_end_timestamp, self.test_name, baseline_run_id),
                "baseline_duration"    : str(int((self.baseline_end_timestamp - self.baseline_start_timestamp) / 1000)),
                "baseline_vusers"      : self.influxdb_obj.get_max_active_users(baseline_run_id, self.baseline_start_time, self.baseline_end_time)
            })
        self.status = "Collected data from InfluxDB"
        self.progress = 25