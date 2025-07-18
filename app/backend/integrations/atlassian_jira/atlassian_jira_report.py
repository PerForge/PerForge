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


from app.backend.integrations.reporting_base                import ReportingBase
from app.backend.integrations.report_registry               import ReportRegistry
from app.backend.integrations.atlassian_jira.atlassian_jira import AtlassianJira
from app.backend.integrations.grafana.grafana               import Grafana
from app.backend.components.graphs.graphs_db                import DBGraphs
from datetime                                               import datetime


@ReportRegistry.register("atlassian_jira")
class AtlassianJiraReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.issue_id    = None

    def set_template(self, template, db_id, action_id):
        super().set_template(template, db_id)
        self.output_obj = AtlassianJira(project=self.project, id=action_id)

    def add_group_text(self, text):
        text += f'\n\n'
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text += f'\n\n'
        return text

    def add_graph(self, graph_data, current_test_title, baseline_test_title):
        image    = self.grafana_obj.render_image(graph_data, self.current_start_timestamp, self.current_end_timestamp, current_test_title, baseline_test_title)
        filename = self.output_obj.put_image_to_jira(issue=self.issue_id, image_bytes=image)
        if(filename):
            graph = f'!{str(filename)}|width=900!\n\n'
        else:
            graph = f'Image failed to load, id: {graph_data["id"]}'
        if self.ai_switch and self.ai_graph_switch and graph_data["prompt_id"] is not None:
            ai_support_response = self.ai_support_obj.analyze_graph(graph_data["name"], image, graph_data["prompt_id"])
            return graph, ai_support_response
        else:
            return graph, ""

    def format_table(self, metrics):
        if not metrics:
            return "No data available\n\n"

        all_keys = set()
        for record in metrics:
            all_keys.update(record.keys())

        keys = sorted(list(all_keys))

        if 'page' in keys:
            keys.remove('page')
            keys.insert(0, 'page')
        elif 'transaction' in keys:
            keys.remove('transaction')
            keys.insert(0, 'transaction')

        # Header
        header = '||' + '||'.join(keys) + '||\n'

        # Body
        body = []
        for record in metrics:
            row = []
            for key in keys:
                value = record.get(key, '')
                value_str = ""

                if value is None or value == 'None' or (isinstance(value, float) and (value != value)):
                    value_str = " "
                elif isinstance(value, str) and " -> " in value:
                    try:
                        parts = value.split(" -> ")
                        if len(parts) == 2:
                            first_val = float(parts[0])
                            second_val = float(parts[1])
                            value_str = value
                            if first_val != 0:
                                diff_pct = ((second_val - first_val) / first_val) * 100
                                if diff_pct <= -10:
                                    value_str = f'{{color:green}}{value}{{color}}'
                                elif diff_pct >= 10:
                                    value_str = f'{{color:red}}{value}{{color}}'
                            elif second_val > first_val:
                                value_str = f'{{color:red}}{value}{{color}}'
                        else:
                            value_str = value
                    except (ValueError, ZeroDivisionError, IndexError):
                        value_str = value
                elif isinstance(value, float):
                    value_str = f"{value:.2f}"
                else:
                    value_str = str(value)
                row.append(value_str)
            body.append('|' + '|'.join(row) + '|\n')

        return header + "".join(body) + "\n"

    def generate_path(self, isgroup):
        if isgroup: title = self.group_title
        else: title = self.replace_variables(self.title)
        return title

    def create_issue(self, issue_title):
        self.issue_id = self.output_obj.put_page_to_jira(title=issue_title)
        return self.issue_id

    def generate_report(self, tests, action_id, template_group=None):
        templates_title = ""
        group_title = None
        def process_test(test, isgroup):
            nonlocal templates_title
            nonlocal group_title
            template_id = test.get('template_id')
            if template_id:
                db_id = test.get('db_id')
                self.set_template(template_id, db_id, action_id)
                test_title          = test.get('test_title')
                baseline_test_title = test.get('baseline_test_title')
                self.collect_data(test_title, baseline_test_title)
                if not self.issue_id:
                    if isgroup:
                        group_title = self.generate_path(True)
                        self.create_issue(group_title)
                    else:
                        temporary_title = self.generate_path(False)
                        self.create_issue(temporary_title)
                title = self.generate_path(False)
                self.report_body += self.add_text(title)
                self.report_body += self.generate(test_title, baseline_test_title)
                if not group_title: templates_title += f'{title} | '
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
        time_str = current_time.strftime("%d.%m.%Y %H:%M")
        if not group_title:
            templates_title += time_str
            self.output_obj.update_jira_page(self.issue_id, templates_title, self.report_body)
        else:
            group_title += f' {time_str}'
            self.output_obj.update_jira_page(self.issue_id, group_title, self.report_body)
        response = self.generate_response()
        response["Issue id"] = self.issue_id
        return response

    def generate(self, current_test_title, baseline_test_title = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data       = DBGraphs.get_config_by_id(project_id=self.project, id=obj["graph_id"])
                self.grafana_obj = Grafana(project=self.project, id=graph_data["grafana_id"])
                graph, ai_support_response = self.add_graph(graph_data, current_test_title, baseline_test_title)
                report_body += graph
                if self.ai_to_graphs_switch:
                    report_body += self.add_text(ai_support_response)

        # Analyze templates after all data is collected
        if self.nfrs_switch or self.ai_switch or self.ml_switch:
            self.analyze_template()

        # Replace variables in the entire report body at the end
        report_body = self.replace_variables(report_body)

        return report_body
