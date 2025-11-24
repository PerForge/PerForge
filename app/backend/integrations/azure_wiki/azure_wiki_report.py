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

import base64

from app.backend.integrations.reporting_base import ReportingBase
from app.backend.integrations.report_registry import ReportRegistry
from app.backend.integrations.azure_wiki.azure_wiki import AzureWiki
from app.backend.components.graphs.graphs_db import DBGraphs


@ReportRegistry.register("azure_wiki")
class AzureWikiReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.report_body = ""
        self.page_id = None

    def set_template(self, template, db_config, action_id):
        super().set_template(template, db_config)
        self.output_obj = AzureWiki(project=self.project, id=action_id)

    def colorize_status(self, value):
        """
        Apply color formatting to status values for Azure Wiki HTML rendering.

        Args:
            value: The cell value to potentially colorize

        Returns:
            The value wrapped in HTML span tags if it's a recognized status, otherwise unchanged
        """
        # Convert to string for comparison
        value_str = str(value).strip().upper()

        # Define status colors
        status_colors = {
            'PASSED': 'green',
            'FAILED': 'red',
            'WARNING': 'orange',
        }

        # Check if this is a status value
        if value_str in status_colors:
            color = status_colors[value_str]
            # Return with HTML span and inline CSS
            return f"<span style='color: {color};'>{value}</span>"

        return value

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

        # Preserve OrderedDict order if present, otherwise sort and reorder
        from collections import OrderedDict
        if metrics and isinstance(metrics[0], OrderedDict):
            # Use the order from the first OrderedDict
            keys = list(metrics[0].keys())
        else:
            # Create list of all keys from the metrics
            all_keys = set()
            for record in metrics:
                all_keys.update(record.keys())

            # Sort keys for consistent display
            keys = sorted(all_keys)

            # Prioritize common first columns (Transaction/transaction/page/Metric)
            if 'Transaction' in keys:
                keys.remove('Transaction')
                keys.insert(0, 'Transaction')
            elif 'transaction' in keys:
                keys.remove('transaction')
                keys.insert(0, 'transaction')
            elif 'page' in keys:
                keys.remove('page')
                keys.insert(0, 'page')
            elif 'Metric' in keys:
                keys.remove('Metric')
                keys.insert(0, 'Metric')

            # Put Status column second if it exists and Transaction is first
            if len(keys) > 1 and keys[0] in ('Transaction', 'transaction') and 'Status' in keys:
                keys.remove('Status')
                keys.insert(1, 'Status')

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
                            value_str = self.colorize_status(value)
                    except (ValueError, ZeroDivisionError, IndexError):
                        # If parsing fails, just display the value normally
                        value_str = self.colorize_status(value)
                    except Exception:
                        # Catch any other unexpected errors
                        value_str = self.colorize_status(value)
                # Format numeric values to two decimal places
                elif isinstance(value, float):
                    value_str = f"{value:.2f}"
                    # Colorize status values
                    value_str = self.colorize_status(value_str)
                else:
                    value_str = str(value)
                    # Colorize status values
                    value_str = self.colorize_status(value_str)

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
        # Use centralized renderer (supports internal Plotly and external Grafana)
        image, ai_support_response = super().add_graph(graph_data, current_test_title, baseline_test_title)
        # Azure expects base64 per existing flow
        encoded_image = base64.b64encode(image)
        fileName = self.output_obj.put_image_to_azure(encoded_image, graph_data["name"])
        if(fileName):
            graph = f'![image.png](/.attachments/{str(fileName)})\n\n'
        else:
            graph = f'Image failed to load, id: {graph_data["id"]}'
        return graph, (ai_support_response or "")

    def generate_path(self, isgroup):
        if isgroup:
            return self.replace_variables(self.output_obj.get_path() + self.group_title)
        else:
            return self.replace_variables(self.output_obj.get_path() + self.title)

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

        # Create or update the Azure Wiki page using the determined title
        self.output_obj.create_or_update_page(page_title, self.report_body)

        response = self.generate_response()
        return response

    def generate(self, current_test_title, baseline_test_title = None):
        report_body = ""
        for obj in self.data:
            if obj["type"] == "text":
                report_body += self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data = DBGraphs.get_config_by_id(project_id=self.project, id=obj["graph_id"])
                # Inject per-graph AI switch only (no fallback to legacy template-level flags)
                graph_data = {
                    **graph_data,
                    "ai_graph_switch": bool(obj.get("ai_graph_switch")),
                }
                graph, ai_support_response = self.add_graph(graph_data, current_test_title, baseline_test_title)
                report_body += graph
                per_graph_ai_to_graphs = bool(obj.get("ai_to_graphs_switch"))
                if per_graph_ai_to_graphs and ai_support_response:
                    report_body += self.add_text(ai_support_response)

        # Analyze templates after all data is collected
        if self.nfrs_switch or self.ai_switch or self.ml_switch:
            self.analyze_template()

        # Replace variables in the entire report body at the end
        report_body = self.replace_variables(report_body)

        return report_body
