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

from app.backend.integrations.reporting_base        import ReportingBase
from app.backend.integrations.report_registry       import ReportRegistry
from app.backend.integrations.azure_wiki.azure_wiki import AzureWiki
from app.backend.integrations.grafana.grafana       import Grafana
from app.backend.components.graphs.graphs_db        import DBGraphs
from datetime                                       import datetime


@ReportRegistry.register("azure_wiki")
class AzureWikiReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.page_id     = None

    def set_template(self, template, db_id, action_id):
        super().set_template(template, db_id)
        self.output_obj = AzureWiki(project=self.project, id=action_id)

    def format_table(self, metrics):
        """
        Format a metrics table for Azure Wiki report. Converts the list of dictionaries
        into a Markdown table format suitable for Azure Wiki.

        Args:
            metrics: A list of dictionaries containing the metrics data

        Returns:
            A string with Markdown table markup
        """
        if not metrics:
            return "| No data available |\n|---|"

        # Create list of all keys from the metrics
        all_keys = set()
        for record in metrics:
            all_keys.update(record.keys())

        # Sort keys for consistent display with 'page' or 'transaction' first if it exists
        keys = sorted(all_keys)
        if 'page' in keys:
            keys.remove('page')
            keys.insert(0, 'page')
        elif 'transaction' in keys:
            keys.remove('transaction')
            keys.insert(0, 'transaction')

        # Start building the Markdown table
        # Header
        header = "| " + " | ".join(keys) + " |"
        # Separator
        separator = "| " + " | ".join(["---"] * len(keys)) + " |"

        markdown_table = [header, separator]

        # Add rows for each record
        for record in metrics:
            row_cells = []
            for key in keys:
                value = record.get(key, '')
                value_str = ""

                # Handle null values
                if value is None or value == 'None' or (isinstance(value, float) and (value != value)):
                    value_str = ""
                # Check for baseline comparison pattern (e.g., "15.00 -> 12.00")
                elif isinstance(value, str) and " -> " in value:
                    try:
                        # Parse the baseline and current values
                        parts = value.split(" -> ")
                        if len(parts) == 2:
                            first_val = float(parts[0])  # baseline
                            second_val = float(parts[1]) # current
                            
                            # Default value string is the original value
                            value_str = value

                            # Calculate percentage difference and color the value if threshold is met
                            if first_val != 0:
                                diff_pct = ((second_val - first_val) / first_val) * 100
                                
                                # Color for improvement (10% or more faster)
                                if diff_pct <= -10:
                                    value_str = f'<span style="color:green;font-weight:bold">{value}</span>'
                                # Color for degradation (10% or more slower)
                                elif diff_pct >= 10:
                                    value_str = f'<span style="color:red;font-weight:bold">{value}</span>'
                            else:
                                # Handle baseline is zero case: color for degradation if current value is higher
                                if second_val > first_val:
                                    value_str = f'<span style="color:red;font-weight:bold">{value}</span>'
                        else:
                            value_str = value
                    except (ValueError, ZeroDivisionError, IndexError):
                        # If parsing fails, just display the value normally
                        value_str = value
                    except Exception:
                        # Catch any other unexpected errors
                        value_str = value
                # Format numeric values to two decimal places
                elif isinstance(value, float):
                    value_str = f"{value:.2f}"
                else:
                    value_str = str(value)
                
                # Azure DevOps Wiki markdown tables are sensitive to pipe characters in content.
                # Replace them to avoid breaking the table structure.
                value_str = value_str.replace('|', '\\|')
                # Newlines also break the table, replace with <br>
                value_str = value_str.replace('\n', '<br/>')

                row_cells.append(value_str)
            
            markdown_table.append("| " + " | ".join(row_cells) + " |")

        # Return the complete Markdown table
        return "\n".join(markdown_table)

    def add_group_text(self, text):
        text += f'\n\n'
        return text

    def add_text(self, text):
        text = self.replace_variables(text)
        text += f'\n\n'
        return text

    def add_graph(self, graph_data, current_test_title, baseline_test_title):
        image         = self.grafana_obj.render_image(graph_data, self.current_test_obj.start_time_timestamp, self.current_test_obj.end_time_timestamp, self.current_test_obj.application, current_test_title, baseline_test_title)
        encoded_image = self.grafana_obj.encode_image(image)
        fileName      = self.output_obj.put_image_to_azure(encoded_image, graph_data["name"])
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

    def generate_report(self, tests, db_id, action_id, template_group=None):
        path = None
        def process_test(test, isgroup):
            nonlocal path
            template_id = test.get('template_id')
            if template_id:
                self.set_template(template_id, db_id, action_id)
                test_title            = test.get('test_title')
                baseline_test_title   = test.get('baseline_test_title')
                self.collect_data(test_title, baseline_test_title)
                self.report_body += self.generate_content(test_title, baseline_test_title)
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
        response = self.generate_response()
        return response

    def generate_content(self, current_test_title, baseline_test_title = None):
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
        if self.nfrs_switch or self.ai_switch:
            result      = self.analyze_template()
            report_body = self.add_text(result) + report_body
        return report_body
