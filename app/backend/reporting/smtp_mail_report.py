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

import time

from datetime                                   import datetime
from app.backend.reporting.reporting_base       import ReportingBase
from app.backend.integrations.main.smtp_mail    import SmtpMail
from app.backend                                import pkg
from app.backend.integrations.secondary.grafana import Grafana


class SmtpMailReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.images      = []

    def set_template(self, template, influxdb, action_id):
        super().set_template(template, influxdb)
        self.output_obj = SmtpMail(project=self.project, id=action_id)

    def add_group_text(self, text):
        text = f'<p>{text}</p><br>'
        text = text.replace('\n', '<br>')
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text = f'<p>{text}</p>'
        text = text.replace('\n', '<br>')
        return text
    
    def add_graph(self, graph_id, current_run_id, baseline_run_id): 
        image = self.grafana_obj.render_image(graph_id, self.current_start_timestamp, self.current_end_timestamp, self.test_name, current_run_id, baseline_run_id)
        if image: 
            timestamp  = str(round(time.time() * 1000))
            content_id = f"{self.test_name}_{graph_id}_{timestamp}".replace(' ', '_')
            file_name  = f"{content_id}.png"
            self.images.append({'file_name':file_name, 'data': image, 'content_id': content_id})
            graph = f'<img src="cid:{content_id}" width="900" alt="{content_id}" /><br>'
        else: 
            graph = f'Image failed to load, id: {graph_id}'
        if self.ai_switch and self.ai_graph_switch:
            graph_json          = pkg.get_graph(self.project, graph_id)
            ai_support_response = self.ai_support_obj.analyze_graph(graph_json["name"], image, graph_json["prompt"])
            return graph, ai_support_response
        else:
            return graph, ""

    def generate_path(self, isgroup):
        return self.group_title if isgroup else self.replace_variables(self.title)

    def generate_report(self, tests, influxdb, action_id, template_group=None):
        templates_title = ""
        group_title     = None
        def process_test(test):
            nonlocal templates_title
            template_id = test.get('template_id')
            if template_id:
                self.set_template(template_id, influxdb, action_id)
                run_id            = test.get('runId')
                baseline_run_id   = test.get('baseline_run_id')
                self.collect_data(run_id, baseline_run_id)
                title             = self.generate_path(False)
                self.report_body += f'<h3>{title}</h3>'
                self.report_body += self.generate(run_id, baseline_run_id)
                if not group_title:
                    templates_title += f'{title} | '
        if template_group:
            self.set_template_group(template_group)
            group_title       = self.generate_path(True)
            self.report_body += f'<h2>{group_title}</h2>'
            for obj in self.template_order:
                if obj["type"] == "text":
                    self.report_body += self.add_group_text(obj["content"])
                elif obj["type"] == "template":
                    for test in tests:
                        if obj.get('id') == test.get('template_id'):
                            process_test(test)
            result = self.analyze_template_group()
            self.report_body = self.add_text(result) + self.report_body
        else:
            for test in tests:
                process_test(test)
        current_time = datetime.now()
        time_str     = current_time.strftime("%d.%m.%Y %H:%M")
        if not group_title:
            templates_title += time_str
            self.output_obj.put_page_to_mail(templates_title, self.report_body, self.images)
        else:
            group_title += f' {time_str}'
            self.output_obj.put_page_to_mail(group_title, self.report_body, self.images)
        return self.report_body

    def generate(self, current_run_id, baseline_run_id = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data       = pkg.get_graph(self.project, obj["id"])
                self.grafana_obj = Grafana(project=self.project, id=graph_data["grafana_id"])
                graph, ai_support_response = self.add_graph(obj["id"], current_run_id, baseline_run_id)
                report_body += graph
                if self.ai_to_graphs_switch:
                    report_body += self.add_text(ai_support_response)
        result = self.analyze_template()
        report_body = self.add_text(result) + report_body
        return report_body