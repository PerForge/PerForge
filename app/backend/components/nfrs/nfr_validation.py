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
from enum import Enum

from app.backend.components.nfrs.nfrs_db import DBNFRs

# NFR validation status enum - moved from metric.py
class NFRStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EVALUATED = "NOT_EVALUATED"


class Nfr:
    def __init__(self, nfr, description):
        self.regex = nfr["regex"]
        self.scope = nfr["scope"]
        self.metric = nfr["metric"]
        self.aggregation = nfr["scope"]
        self.operation = nfr["operation"]
        self.threshold = nfr["threshold"]
        self.description = description


class NFRValidation:
    def __init__(self, project):
        self.project = project
        self.nfr_result = []
        self.transaction_result = []
        # Counters for per-scope checks
        self.total_checks = 0
        self.passed_checks = 0

    # Method accepts test value, operation and threshold
    # Compares value with treshold using specified operation
    # Returns PASSED or FAILED status
    @staticmethod
    def compare_value(value, operation, threshold):
        try:
            if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
                if operation == '>':
                    return NFRStatus.PASSED if value > threshold else NFRStatus.FAILED
                elif operation == '<':
                    return NFRStatus.PASSED if value < threshold else NFRStatus.FAILED
                elif operation == '>=':
                    return NFRStatus.PASSED if value >= threshold else NFRStatus.FAILED
                elif operation == '<=':
                    return NFRStatus.PASSED if value <= threshold else NFRStatus.FAILED
            else:
                return "threshold is not a number"
        except TypeError:
            return "value is not a number"

    def is_match(self, regex, string):
        # Compile the regex pattern
        compiled_pattern = re.compile(regex)
        # Check if the string matches the regex pattern
        match = compiled_pattern.match(string)
        # Return True if there is a match, otherwise False
        return match is not None

    # Method generates name based on NFR definition, for example:
    # NFR: {"scope": "all","metric": "response-time","aggregation": "95%-tile","operation": ">","threshold": 4000}
    # Name: 95%-tile response-time for all requests is greater than 4000
    def generate_name(self, nfr_row):
        name = f"{nfr_row['metric'].capitalize()} "
        if nfr_row['scope'] == 'all':
            name += 'for all requests '
        elif nfr_row['scope'] == 'each':
            name += 'for each request '
        else:
            name += f"for {nfr_row['scope']} request "
        operations = {
            '>': 'is greater than',
            '<': 'is less than',
            '>=': 'is greater than or equal to',
            '<=': 'is less than or equal to'
        }
        name += f"{operations[nfr_row['operation']]} {nfr_row['threshold']}"
        return name

    def is_float(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    def operation_to_text(self, operation):
        operations = {
            '>': 'is less than',
            '<': 'is greater than',
            '>=': 'is less than or not equal to',
            '<=': 'is greater than or not equal to'
        }
        return operations[operation]

    def compare_with_nfrs(self, nfr_config, table):
        """
        Compare table data with NFR configuration and update metrics accordingly.

        Args:
            nfr_config: NFR configuration containing rules
            table: MetricsTable object containing both data and metrics to validate/update
        """
        # Create a dictionary to track NFR results by description
        # This will be used to find existing NFR results when we're processing multiple tables
        nfr_results_dict = {}
        for nfr in self.nfr_result:
            if "nfr" in nfr:
                nfr_results_dict[nfr["nfr"]] = nfr

        # Group metrics by scope (transaction/page)
        metrics_by_scope = {}
        if table and hasattr(table, 'metrics'):
            for metric in table.metrics:
                scope = metric.scope or 'unknown'
                if scope not in metrics_by_scope:
                    metrics_by_scope[scope] = {}
                metrics_by_scope[scope][metric.name] = metric

        # Get all unique scopes
        all_scopes = list(metrics_by_scope.keys())

        # Iterate through NFRs
        for nfr_row in nfr_config["rows"]:
            nfr = Nfr(nfr_row, self.generate_name(nfr_row))

            # Get or create NFR result for this NFR
            nfr_desc = nfr.description
            if nfr_desc in nfr_results_dict:
                # This NFR has already been processed in a previous table
                nfr_result = nfr_results_dict[nfr_desc]
                # Remove it from self.nfr_result since we'll re-add it later
                self.nfr_result = [r for r in self.nfr_result if r.get("nfr") != nfr_desc]
            else:
                # This is the first time we're seeing this NFR
                nfr_result = {}

            # Determine which scopes we need to evaluate
            applicable_scopes = []
            if nfr.scope == 'each':
                applicable_scopes = all_scopes
            elif nfr.regex:
                # Check regex against all scopes
                applicable_scopes = [scope for scope in all_scopes if self.is_match(regex=nfr.scope, string=scope)]
            elif nfr.scope in all_scopes:
                applicable_scopes = [nfr.scope]

            if not applicable_scopes:
                # This NFR was not mapped to any test data, so it fails
                result = NFRStatus.FAILED
                self.transaction_result.append(f"NFR '{nfr.description}' failed: No data found for scope '{nfr.scope}'.")
            else:
                # Get initial status - default to PASSED if not set
                result = nfr_result.get("status", NFRStatus.PASSED)

                # Process each applicable scope
                for scope in applicable_scopes:
                    if scope in metrics_by_scope and nfr.metric in metrics_by_scope[scope]:
                        # Get the metric object
                        metric = metrics_by_scope[scope][nfr.metric]
                        # Get metric value
                        metric_value = metric.value

                        # Call compare_value function here
                        compare_result = self.compare_value(metric_value, nfr.operation, nfr.threshold)

                        # Update the metric's NFR status
                        metric.set_nfr_status(compare_result, nfr.threshold, nfr.operation)

                        # Update per-scope check counters
                        self.total_checks += 1
                        if compare_result == NFRStatus.PASSED:
                            self.passed_checks += 1

                        if compare_result == NFRStatus.FAILED:
                            self.transaction_result.append(f"{scope}: {nfr.metric} {metric_value} {self.operation_to_text(nfr.operation)} {nfr.threshold}.")

                        # Update the overall result status
                        # Append NFR result only if it was not set to FAILED before
                        if compare_result == NFRStatus.FAILED or result == NFRStatus.FAILED:
                            result = NFRStatus.FAILED

            # Update NFR result
            nfr_result["status"] = result
            nfr_result["nfr"] = nfr.description
            self.nfr_result.append(nfr_result)

    def create_summary(self, id, all_tables):
        """
        Create a summary of NFR validation results using all available tables.

        Args:
            id: The NFR configuration ID to use for validation
            all_tables: Dictionary of all available MetricsTable objects for validation

        Returns:
            A summary string of the validation results
        """
        # logging is already imported at the top of the file

        # Reset result collections to avoid duplications when processing multiple tables
        self.nfr_result = []
        self.transaction_result = []
        # Reset counters
        self.total_checks = 0
        self.passed_checks = 0

        # Get NFRs for the specific application
        nfr_config = DBNFRs.get_config_by_id(project_id=self.project, id=id)
        if not nfr_config:
            return f"No NFRs for test provided."

        # Find appropriate tables to use for validation
        # First check if we have any tables at all
        if not all_tables:
            logging.warning("No tables available for NFR validation")
            return "NFR validation failed: No tables available for validation."

        # Process all tables - this is an enhancement from the previous implementation
        # that only processed the first table
        for table_name, table in all_tables.items():
            if hasattr(table, 'metrics') and table.metrics:
                # Compare with NFRs and update metric objects directly
                self.compare_with_nfrs(nfr_config, table)

        # Calculate and format the results
        intro = "NFR compliance overview:"
        # Prepare pass-rate line
        if self.total_checks > 0:
            pass_pct = round((self.passed_checks / self.total_checks) * 100)
        else:
            pass_pct = 0
        summary_lines = [intro, f"- {pass_pct}% checks passed ({self.passed_checks}/{self.total_checks})."]

        # If there are no failed entries collected, all NFRs passed
        if len(self.transaction_result) == 0:
            summary_lines.append("- All NFRs are satisfied.")
            return "\n".join(summary_lines)

        # Otherwise, list only the failed requests (deduplicated, preserving order)
        unique_failures = list(dict.fromkeys(self.transaction_result))
        summary_lines.extend([f"- {row}" for row in unique_failures])
        return "\n".join(summary_lines)
