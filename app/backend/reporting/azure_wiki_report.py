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

from app.backend.integrations.main.azure_wiki   import AzureWiki
from app.backend.reporting.reporting_base       import ReportingBase
from app.backend                                import pkg
from app.backend.integrations.secondary.grafana import Grafana


class AzureWikiReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""

    def set_template(self, template, influxdb, action_id):
        super().set_template(template, influxdb)
        self.output_obj = AzureWiki(project=self.project, id=action_id)

    def add_group_text(self, text):
        text += f'\n\n'
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text += f'\n\n'
        return text

    def add_graph(self, graph_data, current_run_id, baseline_run_id):
        image         = self.grafana_obj.render_image(graph_data["id"], self.current_start_timestamp, self.current_end_timestamp, self.test_name, current_run_id, baseline_run_id)
        encoded_image = self.grafana_obj.encode_image(image)
        fileName      = self.output_obj.put_image_to_azure(encoded_image, graph_data["id"])
        if(fileName):
            graph = f'![image.png](/.attachments/{str(fileName)})\n\n'
        else:
            graph = f'Image failed to load, id: {graph_data["id"]}'
        if self.ai_switch and self.ai_graph_switch:
            ai_support_response = self.ai_support_obj.analyze_graph(graph_data["name"], image, graph_data["prompt_id"])
            return graph, ai_support_response
        else:
            return graph, ""
        
    def generate_path(self, isgroup):
        title = self.output_obj.get_path() + (self.group_title if isgroup else self.replace_variables(self.title))
        return title

    def generate_report(self, tests, influxdb, action_id, template_group=None):
        path = None
        def process_test(test, isgroup):
            nonlocal path
            template_id = test.get('template_id')
            if template_id:
                self.set_template(template_id, influxdb, action_id)
                run_id            = test.get('runId')
                baseline_run_id   = test.get('baseline_run_id')
                self.collect_data(run_id, baseline_run_id)
                self.report_body += self.generate(run_id, baseline_run_id)
                if not path:
                    path = self.generate_path(isgroup)
        if template_group:
            self.set_template_group(template_group)
            for obj in self.template_order:
                if obj["type"] == "text":
                    self.report_body += self.add_group_text(obj["content"])
                elif obj["type"] == "template":
                    for test in tests:
                        if obj.get('id') == test.get('template_id'):
                            process_test(test, True)
            result = self.analyze_template_group()
            self.report_body = self.add_text(result) + self.report_body
        else:
            for test in tests:
                process_test(test, False)
        self.output_obj.create_or_update_page(path, self.report_body)
        return self.report_body

    def generate(self, current_run_id, baseline_run_id = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data       = pkg.get_graph(self.project, obj["id"])
                self.grafana_obj = Grafana(project=self.project, id=graph_data["grafana_id"])
                graph, ai_support_response = self.add_graph(graph_data, current_run_id, baseline_run_id)
                report_body += graph
                if self.ai_to_graphs_switch:
                    report_body += self.add_text(ai_support_response)
        if self.nfrs_switch or self.ai_switch:
            result      = self.analyze_template()
            report_body = self.add_text(result) + report_body
        return report_body