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

from datetime                                                           import datetime
from app.backend.integrations.reporting_base                            import ReportingBase
from app.backend.integrations.report_registry                           import ReportRegistry
from app.backend.integrations.atlassian_confluence.atlassian_confluence import AtlassianConfluence
from app.backend.integrations.grafana.grafana                           import Grafana
from app.backend.components.graphs.graphs_db                            import DBGraphs


@ReportRegistry.register("atlassian_confluence")
class AtlassianConfluenceReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.page_id     = None

    def set_template(self, template, influxdb, action_id):
        super().set_template(template, influxdb)
        self.output_obj = AtlassianConfluence(project=self.project, id=action_id)

    def add_group_text(self, text):
        text = self.replace_variables(text)
        text = f'<h1>{text}</h1><br/>'
        text = text.replace('\\"', '"')
        text = text.replace('&', '&amp;')
        text = text.replace('\n', '<br/>')
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text = f'<p>{text}</p>'
        text = text.replace('\\"', '"')
        text = text.replace('&', '&amp;')
        text = text.replace('\n', '<br/>')
        return text

    def add_graph(self, graph_data, current_run_id, baseline_run_id):
        image = self.grafana_obj.render_image(graph_data, self.current_start_timestamp, self.current_end_timestamp, self.test_name, current_run_id, baseline_run_id)
        fileName = self.output_obj.put_image_to_confl(image, graph_data["id"], self.page_id)
        if(fileName):
            graph = f'<br/><ac:image ac:align="center" ac:layout="center" ac:original-height="500" ac:original-width="1000"><ri:attachment ri:filename="{str(fileName)}" /></ac:image><br/>'
        else:
            graph = f'Image failed to load, id: {graph_data["id"]}'
        if self.ai_switch and self.ai_graph_switch:
            ai_support_response = self.ai_support_obj.analyze_graph(graph_data["name"], image, graph_data["prompt_id"])
            return graph, ai_support_response
        else:
            return graph, ""

    def generate_path(self, isgroup):
        if isgroup:
            title = self.group_title
        else:
            title = self.replace_variables(self.title)
        return title

    def create_page_id(self, page_title):
        response     = self.output_obj.put_page(title=page_title, content="")
        self.page_id = response["id"]

    def generate_report(self, tests, influxdb, action_id, template_group=None):
        templates_title = ""
        group_title     = None
        def process_test(test, isgroup):
            nonlocal templates_title
            nonlocal group_title
            template_id = test.get('template_id')
            if template_id:
                self.set_template(template_id, influxdb, action_id)
                run_id          = test.get('test_title')
                baseline_run_id = test.get('baseline_test_title')
                self.collect_data(run_id, baseline_run_id)
                if not self.page_id:
                    if isgroup:
                        group_title = self.generate_path(True)
                        self.create_page_id(group_title)
                    else:
                        temporary_title = self.generate_path(False)
                        self.create_page_id(temporary_title)
                title             = self.generate_path(False)
                self.report_body += self.add_group_text(title)
                self.report_body += self.generate(run_id, baseline_run_id)
                if not group_title:
                    templates_title += f'{title} | '
        if template_group:
            self.set_template_group(template_group)
            title             = self.generate_path(True)
            self.report_body += self.add_group_text(title)
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
        current_time = datetime.now()
        time_str     = current_time.strftime("%d.%m.%Y %H:%M")
        if not group_title:
            templates_title += time_str
            self.output_obj.update_page(page_id=self.page_id, title=templates_title, content=self.report_body)
        else:
            group_title += f' {time_str}'
            self.output_obj.update_page(page_id=self.page_id, title=group_title, content=self.report_body)
        response = self.generate_response()
        response["Page id"] = self.page_id
        return response

    def generate(self, current_run_id, baseline_run_id = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data       = DBGraphs.get_config_by_id(project_id=self.project, id=obj["graph_id"])
                self.grafana_obj = Grafana(project=self.project, id=graph_data["grafana_id"])
                graph, ai_support_response = self.add_graph(graph_data, current_run_id, baseline_run_id)
                report_body += graph
                if self.ai_to_graphs_switch:
                    report_body += self.add_text(ai_support_response)
        if self.nfrs_switch or self.ai_switch:
            result      = self.analyze_template()
            report_body = self.add_text(result) + report_body
        return report_body