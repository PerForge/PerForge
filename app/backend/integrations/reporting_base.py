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

from sqlalchemy.sql.expression import False_

from app.backend.integrations.ai_support.ai_support                        import AISupport
from app.backend.integrations.grafana.grafana                              import Grafana
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.integrations.grafana.grafana_db                           import DBGrafana
from app.backend.components.nfrs.nfr_validation                            import NFRValidation
from app.backend.components.projects.projects_db                           import DBProjects
from app.backend.components.templates.templates_db                         import DBTemplates
from app.backend.components.templates.template_groups_db                   import DBTemplateGroups
from app.backend.data_provider.data_provider                               import DataProvider
from app.backend.data_provider.test_data                                        import TestData

from typing import Dict, Any



class ReportingBase:

    def __init__(self, project):
        self.project                   = project
        self.schema_name               = DBProjects.get_config_by_id(id=self.project)['name']
        self.validation_obj            = NFRValidation(project=self.project)
        self.current_test_obj: TestData        = None
        self.baseline_test_obj: TestData       = None

    def set_template(self, template, db_id: Dict[str, str]):
        template_obj                   = DBTemplates.get_config_by_id(schema_name=self.schema_name, id=template)
        self.nfr                       = template_obj["nfr"]
        self.title                     = template_obj["title"]
        self.data                      = template_obj["data"]
        self.template_prompt_id        = template_obj["template_prompt_id"]
        self.aggregated_prompt_id      = template_obj["aggregated_prompt_id"]
        self.system_prompt_id          = template_obj["system_prompt_id"]
        self.dp_obj                    = DataProvider(project=self.project, source_type=db_id.get("source_type"), id=db_id.get("id"))
        self.ai_switch                 = template_obj["ai_switch"]
        if db_id.get("source_type") == "influxdb_v2":
            self.ml_switch                 = True # Temporary fix for ML switch
        else:
            self.ml_switch                 = False
        self.ai_aggregated_data_switch = template_obj["ai_aggregated_data_switch"]
        self.nfrs_switch               = template_obj["nfrs_switch"]
        self.ai_graph_switch           = template_obj["ai_graph_switch"]
        self.ai_to_graphs_switch       = template_obj["ai_to_graphs_switch"]
        if self.ai_switch:
            self.ai_support_obj        = AISupport(project=self.project, system_prompt=self.system_prompt_id)

    def set_template_group(self, template_group):
        template_group_obj             = DBTemplateGroups.get_config_by_id(schema_name=self.schema_name, id=template_group)
        self.group_title               = template_group_obj["title"]
        self.template_order            = template_group_obj["data"]
        self.template_group_prompt_id  = template_group_obj["prompt_id"]
        self.ai_summary                = template_group_obj["ai_summary"]

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
        data            = self.current_test_obj.aggregated_table
        if self.nfrs_switch:
            nfr_summary = self.validation_obj.create_summary(self.nfr, data)
        if self.ml_switch:
            self.dp_obj.get_ml_analysis_to_test_obj(self.current_test_obj) # Update ML analysis in TestData object
        if self.ai_switch:
            if self.ai_aggregated_data_switch:
                self.ai_support_obj.analyze_aggregated_data(data, self.aggregated_prompt_id)
            if self.ml_switch:
                overall_summary = self.ai_support_obj.create_template_summary(self.template_prompt_id, nfr_summary, self.current_test_obj.ml_anomalies)
            else:
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

    def collect_data(self, current_test_title, baseline_test_title = None):
        default_grafana_id           = DBGrafana.get_default_config(schema_name=self.schema_name)["id"]
        default_grafana_obj          = Grafana(project=self.project, id=default_grafana_id)
        self.current_test_obj: TestData      = self.dp_obj.collect_test_obj(test_title=current_test_title)

        self.parameters              = {
            "test_name"           : self.current_test_obj.application,
            "current_start_time"  : self.current_test_obj.start_time_human,
            "current_end_time"    : self.current_test_obj.end_time_human,
            "current_grafana_link": default_grafana_obj.get_grafana_test_link(self.current_test_obj.start_time_timestamp, self.current_test_obj.end_time_timestamp, self.current_test_obj.application, current_test_title),
            "current_duration"    : self.current_test_obj.duration,
            "current_vusers"      : self.current_test_obj.max_active_users
        }
        if baseline_test_title is not None:
            self.baseline_test_obj: TestData      = self.dp_obj.collect_test_obj(test_title=baseline_test_title)

            self.parameters.update({
                "baseline_start_time"  : self.baseline_test_obj.start_time_human,
                "baseline_end_time"    : self.baseline_test_obj.end_time_human,
                "baseline_grafana_link": default_grafana_obj.get_grafana_test_link(self.baseline_test_obj.start_time_timestamp, self.baseline_test_obj.end_time_timestamp, self.baseline_test_obj.application, baseline_test_title),
                "baseline_duration"    : self.baseline_test_obj.duration,
                "baseline_vusers"      : self.baseline_test_obj.max_active_users
            })
