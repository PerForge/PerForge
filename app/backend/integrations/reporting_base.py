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

import re
import logging

from app.backend.integrations.ai_support.ai_support import AISupport
from app.backend.integrations.grafana.grafana import Grafana
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.components.nfrs.nfr_validation import NFRValidation
from app.backend.components.templates.templates_db import DBTemplates
from app.backend.components.templates.template_groups_db import DBTemplateGroups
from app.backend.data_provider.data_provider import DataProvider
from app.backend.data_provider.test_data import BaseTestData, MetricsTable
from app.backend.data_provider.image_creator.plotly_image_renderer import PlotlyImageRenderer

from typing import Dict, Any



class ReportingBase:

    def __init__(self, project):
        self.project = project
        self.validation_obj = NFRValidation(project=self.project)
        self.current_test_obj: BaseTestData = None
        self.baseline_test_obj: BaseTestData = None

    def set_template(self, template, db_config: Dict[str, str]):
        template_obj = DBTemplates.get_config_by_id(project_id=self.project, id=template)
        self.nfr = template_obj["nfr"]
        self.title = template_obj["title"]
        self.data = template_obj["data"]
        self.template_prompt_id = template_obj["template_prompt_id"]
        self.aggregated_prompt_id = template_obj["aggregated_prompt_id"]
        self.system_prompt_id = template_obj["system_prompt_id"]
        self.dp_obj = DataProvider(project=self.project, source_type=db_config.get("source_type"), id=db_config.get("id"))
        self.nfrs_switch = template_obj["nfrs_switch"]
        self.ai_switch = template_obj["ai_switch"]
        if self.ai_switch:
            self.ai_support_obj = AISupport(project=self.project, system_prompt=self.system_prompt_id)
        self.ai_aggregated_data_switch = template_obj["ai_aggregated_data_switch"]
        self.ml_switch = template_obj["ml_switch"]

        if self.dp_obj.test_type == "front_end":
            self.ml_switch = False # Temporary fix for ML switch

    def set_template_group(self, template_group):
        template_group_obj = DBTemplateGroups.get_config_by_id(project_id=self.project, id=template_group)
        self.group_title = template_group_obj["title"]
        self.template_order = template_group_obj["data"]
        self.template_group_prompt_id = template_group_obj["prompt_id"]
        self.ai_summary = template_group_obj["ai_summary"]

    def replace_variables(self, text):
        """Replace template variables with their corresponding values

        Args:
            text: Template text with variables to replace

        Returns:
            Text with all replaceable variables substituted
        """
        variables = re.findall(r"\$\{(.*?)\}", text)
        for var in variables:
            # First check if it's a regular parameter
            if var in self.parameters and self.parameters[var]:
                text = text.replace("${" + var + "}", str(self.parameters[var]))
                continue

            # Check if it's a table variable with aggregation suffix
            # Format: table_name_table_aggregation (e.g., timings_fully_loaded_table_median)
            match = re.match(r"(.+?)_table_(median|mean|p75|p90|p95|p99|)$", var)
            if match and hasattr(self.current_test_obj, "get_table"):
                table_name = match.group(1)
                aggregation = match.group(2)

                # Lazy load the table with specified aggregation
                try:
                    # Get the table from current test object
                    table: MetricsTable = self.current_test_obj.get_table(table_name, aggregation)

                    # If baseline test object exists, set baseline metrics
                    if self.baseline_test_obj is not None and hasattr(self.baseline_test_obj, "get_table"):
                        try:
                            # Get the corresponding table from baseline
                            baseline_table: MetricsTable = self.baseline_test_obj.get_table(table_name, aggregation)
                            if baseline_table is not None and baseline_table.metrics:
                                # Set baseline metrics in current table to enable difference calculation
                                # Apply baseline values to current metrics directly
                                table.set_baseline_metrics(baseline_table.metrics)
                        except Exception as e:
                            logging.warning(f"Error loading baseline table '{table_name}' with aggregation '{aggregation}': {e}")

                    if table is not None:
                        # Format the table based on the report type
                        # When baseline is available, use comparison metrics (baseline -> current format)
                        if self.baseline_test_obj is not None and table.has_baseline():
                            metrics = table.format_comparison_metrics()
                        else:
                            # No baseline, just format current metrics
                            metrics = table.format_metrics()
                        value = self.format_table(metrics)
                        if value:
                            text = text.replace("${" + var + "}", value)
                        continue
                except Exception as e:
                    logging.warning(f"Error loading table '{table_name}' with aggregation '{aggregation}': {e}")

        return text

    def format_table(self, metrics):
        """
        Format a metrics table for report consumption. This base implementation returns a JSON string
        representation of the metrics list. Derived classes can override this to provide
        format-specific implementations.

        Args:
            metrics: A list of dictionaries containing the metrics data

        Returns:
            A string representation of the metrics suitable for the report format
        """
        return metrics

    def analyze_template(self):
        # Initialize parameters to ensure they exist
        self.parameters['nfr_summary'] = ""
        self.parameters['ml_summary'] = ""
        self.parameters['ai_summary'] = ""

        all_tables = self.current_test_obj.get_all_tables()

        # 1. NFR validation
        if self.nfrs_switch:
            self.parameters['nfr_summary'] = self.validation_obj.create_summary(self.nfr, all_tables)

        # 2. ML analysis
        if self.ml_switch:
            self.dp_obj.get_ml_analysis_to_test_obj(self.current_test_obj)
            if self.current_test_obj.ml_summary:
                self.parameters['ml_summary'] = self.current_test_obj.ml_summary

        # 3. AI-generated summary
        if self.ai_switch:
            # Use JSON string of all tables for AI analysis
            if self.ai_aggregated_data_switch:
                # Apply baseline to all tables only when aggregated data analysis is requested
                if getattr(self, "baseline_test_obj", None) is not None:
                    self._apply_baseline_to_all_tables()
                all_tables_json = self.current_test_obj.get_all_tables_json()
                self.ai_support_obj.analyze_aggregated_data(all_tables_json, self.aggregated_prompt_id)

            # Generate template summary, including NFR and ML summaries
            self.parameters['ai_summary'] = self.ai_support_obj.create_template_summary(
                self.template_prompt_id,
                self.parameters['nfr_summary'],
                self.current_test_obj.ml_anomalies,
                self.parameters.get('additional_context', '')
            )

    def analyze_template_group(self):
        overall_summary = ""
        if self.ai_summary:
            overall_summary = self.ai_support_obj.create_template_group_summary(self.template_group_prompt_id)
        return overall_summary

    def generate_response(self):
        response = {}
        if self.ai_switch:
            response["Input tokens"] = self.ai_support_obj.ai_obj.input_tokens
            response["Output tokens"] = self.ai_support_obj.ai_obj.output_tokens
        else:
            response["Input tokens"] = 0
            response["Output tokens"] = 0
        return response

    # ----------------------------------------------------------------------------------
    # Centralized Graph Rendering
    # ----------------------------------------------------------------------------------

    def _ensure_ml_metrics(self) -> dict:
        """
        Make sure ML metrics are available on current_test_obj and return metrics dict.
        If already computed, reconstruct a minimal metrics dict from existing tables if possible.
        """
        metrics = self.dp_obj.get_ml_analysis_to_test_obj(self.current_test_obj)
        if not isinstance(metrics, dict) or not metrics:
            logging.error("_ensure_ml_metrics: Failed to obtain ML metrics dict. ml_anomalies=%s",
                          bool(getattr(self.current_test_obj, "ml_anomalies", None)))
            raise RuntimeError("Internal graph rendering failed: ML metrics could not be constructed.")
        return metrics

    def _render_internal_graph(self, graph_data: dict) -> bytes:
        """Render an internal Plotly graph fully in-memory and return PNG bytes."""
        # Ensure metric series exist
        metrics = self._ensure_ml_metrics()

        # Render via Plotly
        renderer = PlotlyImageRenderer()
        width = int(graph_data.get("width") or 1024)
        height = int(graph_data.get("height") or 400)
        image = renderer.render_bytes_by_name(
            name=graph_data.get("name", ""),
            chart_data=metrics,
            width=width,
            height=height,
            image_format="png",
        )
        return image

    def add_graph(self, graph_data: dict, current_test_title: str, baseline_test_title: str | None):
        """
        Unified graph renderer for both internal and external graphs.

        Returns: (image_bytes, ai_support_response or None)
        """
        ai_support_response = None

        if graph_data.get("type") == "default":
            # Render internal Plotly graph
            image = self._render_internal_graph(graph_data)

            # Optional AI analysis
            ai_graph_enabled = bool(graph_data.get("ai_graph_switch"))
            if self.ai_switch and ai_graph_enabled and graph_data.get("prompt_id"):
                ai_support_response = self.ai_support_obj.analyze_graph(graph_data.get("name"), image, graph_data.get("prompt_id"))
            return image, ai_support_response

        # External (Grafana) graph fallback
        # Instantiate Grafana using graph-specific grafana_id to respect overrides
        grafana_id = graph_data.get("grafana_id")
        if grafana_id:
            grafana = Grafana(project=self.project, id=grafana_id)
        else:
            # Fallback to default Grafana
            default_grafana_config = DBGrafana.get_default_config(project_id=self.project)
            grafana = Grafana(project=self.project, id=default_grafana_config["id"]) if default_grafana_config else None

        if grafana is None:
            raise RuntimeError("Grafana configuration is missing for external graph rendering.")

        # Use the timestamps from current_test_obj instead of direct attributes
        start_timestamp = self.current_test_obj.start_time_timestamp
        end_timestamp = self.current_test_obj.end_time_timestamp

        url = grafana.generate_url_to_render_graph(graph_data, start_timestamp, end_timestamp, current_test_title, baseline_test_title)
        url = self.replace_variables(url)
        image = grafana.render_image(url)

        ai_graph_enabled = bool(graph_data.get("ai_graph_switch"))
        if self.ai_switch and ai_graph_enabled and graph_data.get("prompt_id"):
            ai_support_response = self.ai_support_obj.analyze_graph(graph_data.get("name"), image, graph_data.get("prompt_id"))

        return image, ai_support_response

    def _apply_baseline_to_all_tables(self) -> None:
        """
        If a baseline test is available, preload all current tables and apply baseline metrics
        so subsequent consumers (e.g., get_all_tables_json()) include comparison fields.

        This mirrors the lazy baseline wiring done in replace_variables() but applies it
        globally during data collection.

        Safe to call multiple times.
        """
        try:
            # Ensure both current and baseline objects are present and support table access
            if (
                getattr(self, "current_test_obj", None) is None
                or getattr(self, "baseline_test_obj", None) is None
                or not hasattr(self.current_test_obj, "get_all_tables")
                or not hasattr(self.baseline_test_obj, "get_table")
            ):
                return

            # Preload all current tables with default aggregation
            current_tables = self.current_test_obj.get_all_tables() or {}

            # Use the same aggregation for baseline tables
            aggregation = getattr(self.current_test_obj, "aggregation", None)

            for table_name, table in current_tables.items():
                if table is None:
                    continue
                try:
                    baseline_table = self.baseline_test_obj.get_table(table_name, aggregation)
                    if baseline_table is not None and getattr(baseline_table, "metrics", None):
                        table.set_baseline_metrics(baseline_table.metrics)
                except Exception as e:
                    logging.warning(
                        f"_apply_baseline_to_all_tables: failed to apply baseline for table '{table_name}': {e}"
                    )
        except Exception as e:
            logging.warning(f"_apply_baseline_to_all_tables: unexpected error: {e}")

    def _collect_parameters(self, test_obj: BaseTestData, prefix: str = "") -> Dict[str, Any]:
        """
        Extract all metrics from a test data object and format them as parameters with optional prefix.

        Args:
            test_obj: The test data object to extract parameters from
            prefix: Prefix to add to parameter names (e.g., "baseline_" for baseline metrics)

        Returns:
            Dictionary of parameters with original metric names (prefixed if specified)
        """
        if not test_obj:
            return {}

        parameters = {}

        # First, collect all available metrics that are not considered metadata
        for metric_name in test_obj.get_available_metrics():
            param_name = f"{prefix}{metric_name}"
            parameters[param_name] = str(test_obj.get_metric(metric_name))

        # Then, explicitly collect common parameters that might be filtered out as metadata
        # This ensures that essential variables for reporting are always present.
        common_params_to_collect = {
            'duration': 'duration',
            'start_time': 'start_time_human',
            'end_time': 'end_time_human',
            'test_type': 'test_type',
            'custom_vars': 'custom_vars'
        }

        for report_name, attr_name in common_params_to_collect.items():
            if test_obj.has_metric(attr_name):
                if attr_name == 'custom_vars':
                    custom_vars = test_obj.get_metric(attr_name)
                    for custom_var in custom_vars:
                        param_name = f"{prefix}{custom_var['name']}"
                        parameters[param_name] = str(custom_var['value'])
                else:
                    param_name = f"{prefix}{report_name}"
                    parameters[param_name] = str(test_obj.get_metric(attr_name))

        # Add a single, global report generation timestamp (no prefix)
        # Use the DataProvider helper to honour data source timezones.
        if hasattr(self, "dp_obj") and "report_timestamp" not in parameters:
            try:
                parameters["report_timestamp"] = self.dp_obj.get_current_timestamp()
            except Exception:
                # Fallback to a simple UTC timestamp if anything goes wrong
                from datetime import datetime, timezone
                parameters["report_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return parameters

    def _create_grafana_link(self, test_obj: BaseTestData, test_title: str, prefix: str = "") -> Dict[str, str]:
        """
        Generate a Grafana dashboard link parameter for the test.

        Args:
            test_obj: The test data object
            test_title: The test title to use in the link
            prefix: Prefix for the parameter name

        Returns:
            Dictionary with the Grafana link parameter
        """
        # Get default Grafana configuration
        default_grafana_config = DBGrafana.get_default_config(project_id=self.project)
        default_grafana_obj = None
        if default_grafana_config:
            default_grafana_id = default_grafana_config["id"]
            default_grafana_obj = Grafana(project=self.project, id=default_grafana_id)

        # Create parameter name with prefix
        link_param_name = f"{prefix}grafana_link"

        # Generate the link if Grafana object exists and has the required method
        if default_grafana_obj is not None and hasattr(default_grafana_obj, 'get_grafana_test_link'):
            return {
                link_param_name: default_grafana_obj.get_grafana_test_link(
                    test_obj.get_metric('start_time_timestamp'),
                    test_obj.get_metric('end_time_timestamp'),
                    test_title
                )
            }
        else:
            # Return empty link if Grafana object or method doesn't exist
            return {link_param_name: ""}

    def collect_data(self, current_test_title, baseline_test_title=None, additional_context=None):
        """
        Collect test data and prepare parameters for report generation.

        Args:
            current_test_title: Title of the current test to analyze
            baseline_test_title: Optional title of a baseline test for comparison
            additional_context: Optional additional context for the report
        """

        # Initialize parameters dictionary
        self.parameters = {}

        # Process baseline test data if provided
        if baseline_test_title is not None and baseline_test_title != "no data":
            # First collect the baseline test object
            self.baseline_test_obj = self.dp_obj.collect_test_obj(test_title=baseline_test_title)

            # Set compatibility attributes
            self.baseline_start_timestamp = self.baseline_test_obj.get_metric('start_time_timestamp')
            self.baseline_end_timestamp = self.baseline_test_obj.get_metric('end_time_timestamp')

            # Add baseline parameters with consistent 'baseline_' prefix
            self.parameters.update(self._collect_parameters(self.baseline_test_obj, "baseline_"))
            self.parameters.update(self._create_grafana_link(self.baseline_test_obj, baseline_test_title, "baseline_"))
            self.parameters['baseline_test_title'] = baseline_test_title

        # Now collect the current test object
        self.current_test_obj = self.dp_obj.collect_test_obj(test_title=current_test_title)

        # Set compatibility attributes for report types that expect them directly on the object
        self.current_start_timestamp = self.current_test_obj.get_metric('start_time_timestamp')
        self.current_end_timestamp = self.current_test_obj.get_metric('end_time_timestamp')

        # Process current test data with 'current_' prefix
        self.parameters.update(self._collect_parameters(self.current_test_obj, "current_"))
        self.parameters.update(self._create_grafana_link(self.current_test_obj, current_test_title, "current_"))
        self.parameters['current_test_title'] = current_test_title

        if additional_context:
            self.parameters['additional_context'] = additional_context

        # Baseline application for tables is deferred to analyze_template() and only
        # executed when aggregated data analysis is enabled, to avoid unnecessary loading.
