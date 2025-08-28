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

import time


from app.backend.integrations.reporting_base import ReportingBase
from app.backend.integrations.report_registry import ReportRegistry
from app.backend.integrations.smtp_mail.smtp_mail import SmtpMail
from app.backend.components.graphs.graphs_db import DBGraphs
from datetime import datetime


@ReportRegistry.register("smtp_mail")
class SmtpMailReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.images = []

    def set_template(self, template, db_config, action_id):
        super().set_template(template, db_config)
        self.output_obj = SmtpMail(project=self.project, id=action_id)

    def add_group_text(self, text):
        text = text.replace("\r\n", "")
        text = text.replace("\r", "")
        text = text.replace("\n", "")
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text = text.replace("\r\n", "")
        text = text.replace("\r", "")
        text = text.replace("\n", "")
        return text

    def add_graph(self, graph_data, current_test_title, baseline_test_title):
        # Use centralized renderer (supports internal Plotly and external Grafana)
        image, ai_support_response = super().add_graph(graph_data, current_test_title, baseline_test_title)
        if image:
            timestamp = str(round(time.time() * 1000))
            content_id = f'{graph_data["id"]}_{timestamp}'.replace(" ", "_")
            file_name = f'{content_id}.png'
            self.images.append({'file_name': file_name, 'data': image, 'content_id': content_id})
            graph = f'<img src="cid:{content_id}" width="900" alt="{content_id}" /><br>'
        else:
            graph = f'Image failed to load, id: {graph_data["id"]}'
        return graph, (ai_support_response or "")

    def format_table(self, metrics):
        if not metrics:
            return "<p>No data available</p>"

        all_keys = set()
        for record in metrics:
            all_keys.update(record.keys())

        keys = sorted(list(all_keys))

        # Prioritize 'page' or 'transaction' column
        if 'page' in keys:
            keys.remove('page')
            keys.insert(0, 'page')
        elif 'transaction' in keys:
            keys.remove('transaction')
            keys.insert(0, 'transaction')
        elif 'Metric' in keys:
            keys.remove('Metric')
            keys.insert(0, 'Metric')

        # Start building the HTML table
        html = ['<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">']

        # Header
        html.append('<thead><tr style="background-color: #f2f2f2;">')
        for key in keys:
            html.append(f'<th>{key}</th>')
        html.append('</tr></thead>')

        # Body
        html.append('<tbody>')
        for record in metrics:
            html.append('<tr>')
            for key in keys:
                value = record.get(key, '')
                value_str = ""
                style = ""

                # Handle null values
                if value is None or value == 'None' or (isinstance(value, float) and (value != value)):
                    value_str = ""
                # Check for baseline comparison pattern
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
                                    style = 'style="color:green;font-weight:bold;"'
                                elif diff_pct >= 10:
                                    style = 'style="color:red;font-weight:bold;"'
                            elif second_val > first_val:
                                style = 'style="color:red;font-weight:bold;"'
                        else:
                            value_str = value
                    except (ValueError, ZeroDivisionError, IndexError):
                        value_str = value
                # Format float to two decimal places
                elif isinstance(value, float):
                    value_str = f"{value:.2f}"
                else:
                    value_str = str(value)

                html.append(f'<td {style}>{value_str}</td>')
            html.append('</tr>')

        html.append('</tbody></table>')
        return "".join(html)

    def generate_path(self, isgroup):
        if isgroup:
            return self.replace_variables(self.group_title)
        else:
            return self.replace_variables(self.title)

    def generate_report(self, tests, action_id, template_group=None):
        page_title = None

        def process_test(test, isgroup):
            nonlocal page_title

            template_id = test.get('template_id')
            if template_id:
                db_config = test.get('db_config')
                self.set_template(template_id, db_config, action_id)

                test_title = test.get('test_title')
                baseline_test_title = test.get('baseline_test_title')
                self.collect_data(test_title, baseline_test_title)
                additional_context = test.get('additional_context')
                self.collect_data(test_title, baseline_test_title, additional_context)

                # Determine the final wiki page title once
                if page_title is None:
                    if isgroup:
                        page_title = self.generate_path(True)
                    else:
                        page_title = self.generate_path(False)
                self.report_body += self.generate(test_title, baseline_test_title)
        if template_group:
            self.set_template_group(template_group)

            for obj in self.template_order:
                if obj["type"] == "text":
                    self.report_body += self.add_group_text(obj["content"])
                elif obj["type"] == "template":
                    for test in tests:
                        if int(obj.get('template_id')) == int(test.get('template_id')):
                            process_test(test, True)
            result = self.analyze_template_group()
            self.report_body = self.add_text(result) + self.report_body
        else:
            for test in tests:
                process_test(test, False)

        self.output_obj.put_page_to_mail(page_title, self.report_body, self.images)
        response = self.generate_response()
        response['title'] = page_title
        return response

    def generate(self, current_test_title, baseline_test_title = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data = DBGraphs.get_config_by_id(project_id=self.project, id=obj["graph_id"])
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
