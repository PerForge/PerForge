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

from app.backend.components.settings.settings_service import SettingsService
from app.backend.integrations.ai_support.ai_support import AISupport
from app.backend.integrations.grafana.grafana import Grafana
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.components.nfrs.nfr_validation import NFRValidation
from app.backend.components.templates.templates_db import DBTemplates
from app.backend.components.templates.template_groups_db import DBTemplateGroups
from app.backend.components.prompts.prompts_db import DBPrompts
from app.backend.data_provider.data_provider import DataProvider
from app.backend.data_provider.test_data import BaseTestData, BackendTestData, FrontendTestData, MetricsTable
from app.backend.data_provider.image_creator.plotly_image_renderer import PlotlyImageRenderer

from typing import Dict, Any



class ReportingBase:

    def __init__(self, project):
        self.project = project
        self.validation_obj = NFRValidation(project=self.project)
        self.current_test_obj: BaseTestData = None
        self.baseline_test_obj: BaseTestData = None
        self._needs_transaction_status_table = False  # Flag to track if status table is needed

    def set_template(self, template, db_config: Dict[str, str]):
        template_obj = DBTemplates.get_config_by_id(project_id=self.project, id=template)
        self.nfr = template_obj["nfr"]
        self.title = template_obj["title"]
        self.data = template_obj["data"]
        self.template_prompt_id = template_obj["template_prompt_id"]
        self.aggregated_prompt_id = template_obj["aggregated_prompt_id"]
        self.system_prompt_id = template_obj["system_prompt_id"]
        self.dp_obj = DataProvider(
            project=self.project,
            source_type=db_config.get("source_type"),
            id=db_config.get("id"),
            bucket=(db_config or {}).get("bucket")
        )
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
                        # Format the table based on the report type.
                        # For the aggregated_data table, apply per-project reporting settings
                        # (column selection, labels, split-baseline mode).
                        if table_name == 'aggregated_data':
                            rt = SettingsService.get_project_settings(self.project, 'reporting_table')
                            columns_config = self._parse_columns_config(
                                rt.get('aggregated_table_columns', [])
                            )
                            split_baseline = rt.get('aggregated_table_split_baseline', False)
                            current_label = rt.get('aggregated_table_current_label', 'Current')
                            baseline_label = rt.get('aggregated_table_baseline_label', 'Baseline')
                            show_diff = rt.get('aggregated_table_show_diff', False)
                            diff_label = rt.get('aggregated_table_diff_label', 'Diff')
                            show_diff_pct = rt.get('aggregated_table_show_diff_pct', False)
                            diff_pct_label = rt.get('aggregated_table_diff_pct_label', 'Diff %')

                            has_baseline = self.baseline_test_obj is not None and table.has_baseline()

                            if split_baseline and has_baseline:
                                metrics = table.format_split_columns_metrics(
                                    columns_config, current_label, baseline_label,
                                    show_diff, diff_label, show_diff_pct, diff_pct_label
                                )
                            elif has_baseline and (show_diff or show_diff_pct):
                                metrics = table.format_comparison_metrics_with_diff(
                                    columns_config, show_diff, diff_label, show_diff_pct, diff_pct_label
                                )
                            elif has_baseline:
                                metrics = table.format_comparison_metrics()
                                metrics = self._apply_columns_config(
                                    metrics, columns_config, table.scope_column_name
                                )
                            else:
                                metrics = table.format_metrics()
                                metrics = self._apply_columns_config(
                                    metrics, columns_config, table.scope_column_name
                                )
                        else:
                            # All other tables: original behaviour, no settings applied
                            if self.baseline_test_obj is not None and table.has_baseline():
                                metrics = table.format_comparison_metrics()
                            else:
                                metrics = table.format_metrics()
                        value = self.format_table(metrics)
                        if value:
                            text = text.replace("${" + var + "}", value)
                        continue
                except Exception as e:
                    logging.warning(f"Error loading table '{table_name}' with aggregation '{aggregation}': {e}")

            # Check for transaction status table variables
            if var == "transaction_status_table":
                # Set flag indicating status table is needed
                self._needs_transaction_status_table = True

            if var == "transaction_status_table_detailed":
                # Set flag indicating status table is needed
                self._needs_transaction_status_table = True

        return text

    def _ensure_transaction_status_table(self):
        """
        Helper function to ensure tables are loaded with baseline data
        and build the transaction status table.

        For backend tests: loads aggregated_data with baseline
        For frontend tests: loads tables with baseline applied

        Returns:
            Transaction status table or None if build fails
        """
        try:
            is_frontend = isinstance(self.current_test_obj, FrontendTestData)

            # Try to load aggregated_data table (backend tests)
            # This maintains backward compatibility - if test_type is not set or is backend, try aggregated_data
            if not is_frontend and hasattr(self.current_test_obj, 'get_table'):
                agg_table = self.current_test_obj.get_table('aggregated_data')

                # If baseline test exists, apply baseline metrics to aggregated_data
                if agg_table is not None and self.baseline_test_obj is not None and hasattr(self.baseline_test_obj, 'get_table'):
                    try:
                        baseline_agg_table = self.baseline_test_obj.get_table('aggregated_data')
                        if baseline_agg_table is not None and baseline_agg_table.metrics:
                            agg_table.set_baseline_metrics(baseline_agg_table.metrics)
                    except Exception as e:
                        logging.warning(f"Error loading baseline aggregated_data for transaction status: {e}")

            # Frontend-specific handling: apply baseline to loaded tables
            if is_frontend and self.baseline_test_obj is not None:
                # Frontend: Apply baseline to any loaded tables
                # If tables are already loaded from template variables, apply baseline to them
                # If no tables loaded yet, load one lightweight table to get transaction names
                if hasattr(self.current_test_obj, '_loaded_tables') and self.current_test_obj._loaded_tables:
                    # Tables already loaded, apply baseline to them
                    aggregation = getattr(self.current_test_obj, 'aggregation', 'median')
                    for (table_name, _), current_table in self.current_test_obj._loaded_tables.items():
                        if table_name == 'overview_data':  # Skip overview table
                            continue
                        try:
                            baseline_table = self.baseline_test_obj.get_table(table_name, aggregation)
                            if baseline_table is not None and baseline_table.metrics:
                                current_table.set_baseline_metrics(baseline_table.metrics)
                        except Exception as e:
                            logging.debug(f"Could not apply baseline to frontend table '{table_name}': {e}")
                else:
                    # No tables loaded yet, load one lightweight table with baseline
                    # This ensures transaction names are available with baseline data
                    try:
                        aggregation = getattr(self.current_test_obj, 'aggregation', 'median')
                        # Load google_web_vitals as it's lightweight and present in most frontend tests
                        current_table = self.current_test_obj.get_table('google_web_vitals', aggregation)
                        if current_table:
                            baseline_table = self.baseline_test_obj.get_table('google_web_vitals', aggregation)
                            if baseline_table is not None and baseline_table.metrics:
                                current_table.set_baseline_metrics(baseline_table.metrics)
                    except Exception as e:
                        logging.debug(f"Could not load google_web_vitals with baseline for status table: {e}")

            # Now build the transaction status table with all data available
            if hasattr(self, 'dp_obj'):
                table = self.dp_obj.build_transaction_status_table(self.current_test_obj)
                self.current_test_obj.transaction_status_table = table
                return table
        except Exception as e:
            logging.warning(f"Failed to build transaction status table: {e}")

        return None

    @staticmethod
    def _parse_columns_config(raw_columns: list) -> list:
        """Parse a list of 'metric_key:Display Label' strings into (key, label) tuples.

        Items without a colon are used as both key and label.
        Empty items are ignored.
        """
        result = []
        for item in raw_columns:
            item = item.strip()
            if not item:
                continue
            if ':' in item:
                key, _, label = item.partition(':')
                result.append((key.strip(), label.strip()))
            else:
                result.append((item, item))
        return result

    @staticmethod
    def _apply_columns_config(metrics: list, columns_config: list, scope_column_name: str) -> list:
        """Filter and rename columns in a list of formatted metric row dicts.

        When columns_config is empty the original rows are returned unchanged.
        The scope column is always preserved.
        """
        if not columns_config:
            return metrics
        result = []
        for row in metrics:
            new_row = {}
            if scope_column_name and scope_column_name in row:
                new_row[scope_column_name] = row[scope_column_name]
            for metric_key, display_label in columns_config:
                if metric_key in row:
                    new_row[display_label] = row[metric_key]
            result.append(new_row)
        return result

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
        self.parameters['transaction_status_table'] = ""
        self.parameters['transaction_status_table_detailed'] = ""

        all_tables = self.current_test_obj.get_all_tables()

        # 1. NFR validation
        if self.nfrs_switch:
            self.parameters['nfr_summary'] = self.validation_obj.create_summary(self.nfr, all_tables)

        # 2. ML analysis
        if self.ml_switch:
            self.dp_obj.get_ml_analysis_to_test_obj(self.current_test_obj)
            if self.current_test_obj.ml_summary:
                self.parameters['ml_summary'] = self.current_test_obj.ml_summary

        # 2.5. Build transaction status table (after ML and NFR, before AI)
        # Only build if the flag indicates it's needed in the report
        if self._needs_transaction_status_table:
            if not hasattr(self.current_test_obj, 'transaction_status_table') or self.current_test_obj.transaction_status_table is None:
                table = self._ensure_transaction_status_table()
            else:
                table = self.current_test_obj.transaction_status_table

            # Format and store both versions in parameters
            if table:
                try:
                    # Simple format
                    simple_metrics = table.format_for_report()
                    self.parameters['transaction_status_table'] = self.format_table(simple_metrics)

                    # Detailed format
                    detailed_metrics = table.format_detailed()
                    self.parameters['transaction_status_table_detailed'] = self.format_table(detailed_metrics)
                except Exception as e:
                    logging.warning(f"Error formatting transaction status table for parameters: {e}")

        # 3. AI-generated summary
        if self.ai_switch:
            # Use JSON string of all tables for AI analysis
            if self.ai_aggregated_data_switch:
                # Apply baseline to all tables only when aggregated data analysis is requested
                if getattr(self, "baseline_test_obj", None) is not None:
                    self._apply_baseline_to_all_tables()
                all_tables_json = self.current_test_obj.get_all_tables_json()
                self.ai_support_obj.analyze_aggregated_data(all_tables_json, self.aggregated_prompt_id)

            # Prepare AI-specific variables for prompt replacement
            # Store them temporarily in parameters so replace_variables can access them
            self.parameters['aggregated_data_analysis'] = self.ai_support_obj.prepare_list_of_analysis(
                self.ai_support_obj.aggregated_data_analysis) or "N/A"
            self.parameters['graphs_analysis'] = self.ai_support_obj.prepare_list_of_analysis(
                self.ai_support_obj.graph_analysis) or "N/A"
            # NFR and ML summaries are already in parameters
            if 'nfr_summary' not in self.parameters or not self.parameters['nfr_summary']:
                self.parameters['nfr_summary'] = "N/A"
            if 'ml_anomalies' not in self.parameters or not self.parameters['ml_anomalies']:
                self.parameters['ml_anomalies'] = self.current_test_obj.ml_anomalies or "N/A"
            if 'additional_context' not in self.parameters:
                self.parameters['additional_context'] = "N/A"

            # Fetch the prompt template and apply centralized variable replacement
            prompt_template = DBPrompts.get_config_by_id(
                project_id=self.project,
                id=self.template_prompt_id
            )["prompt"]

            # Use replace_variables for ALL replacements (parameters, tables, AI-specific values)
            processed_prompt = self.replace_variables(prompt_template)

            # Generate AI summary with the fully processed prompt
            self.parameters['ai_summary'] = self.ai_support_obj.run_summary_chain(processed_prompt)

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

        # Attach overall anomaly windows (per overall metric) for backend graph shading.
        try:
            windows_by_metric = {}
            engine = getattr(self.dp_obj, "anomaly_detection_engine", None)
            if engine is not None:
                overall_list = getattr(engine, "overall_anomalies", []) or []
                for oa in overall_list:
                    metric = oa.get("metric")
                    start_time = oa.get("start_time")
                    end_time = oa.get("end_time")
                    if not metric or start_time is None or end_time is None:
                        continue
                    windows_by_metric.setdefault(metric, []).append(
                        {"start": str(start_time), "end": str(end_time)}
                    )
            if windows_by_metric:
                metrics["overall_anomaly_windows"] = windows_by_metric
        except Exception as e:
            logging.warning(f"_ensure_ml_metrics: failed to attach overall anomaly windows: {e}")

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

        # Include data source bucket if available from DataProvider.ds_obj
        try:
            ds_obj = getattr(self, "dp_obj", None)
            if ds_obj is not None and getattr(ds_obj, "ds_obj", None) is not None:
                bucket = getattr(ds_obj.ds_obj, "bucket", None)
                if bucket:
                    parameters["bucket"] = str(bucket)
        except Exception as e:
            logging.warning(f"_collect_parameters: could not read data source bucket: {e}")

        # Add a single, global report generation timestamp (no prefix)
        # Use the DataProvider helper to honour data source timezones.
        if hasattr(self, "dp_obj"):
            try:
                # Report timestamp
                if "report_timestamp" not in parameters:
                    parameters["report_timestamp"] = self.dp_obj.get_current_timestamp()
                # Current month (e.g., September)
                if "current_month" not in parameters:
                    parameters["current_month"] = self.dp_obj.get_current_timestamp("%B")
                # Current day (e.g., 12)
                if "current_day" not in parameters:
                    day_str = self.dp_obj.get_current_timestamp("%d")
                    parameters["current_day"] = str(int(day_str)) if day_str.isdigit() else day_str
            except Exception:
                # Fallback to UTC if anything goes wrong
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if "report_timestamp" not in parameters:
                    parameters["report_timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S UTC")
                if "current_month" not in parameters:
                    parameters["current_month"] = now.strftime("%B")
                if "current_day" not in parameters:
                    parameters["current_day"] = str(now.day)
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
