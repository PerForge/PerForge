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

import re
import logging
from enum import Enum

from app.backend.components.nfrs.nfrs_db         import DBNFRs

# NFR validation status enum - moved from metric.py
class NFRStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EVALUATED = "NOT_EVALUATED"


class Nfr:
    def __init__(self, nfr, description):
        self.regex       = nfr["regex"]
        self.scope       = nfr["scope"]
        self.metric      = nfr["metric"]
        self.aggregation = nfr["scope"]
        self.operation   = nfr["operation"]
        self.threshold   = nfr["threshold"]
        self.weight      = nfr["weight"]
        self.description = description


class NFRValidation:
    def __init__(self, project):
        self.project            = project
        self.nfr_result         = []
        self.transaction_result = []

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

    # Method takes a list of NFRs
    # Constructs a flux request to the InfluxDB based on the NFRs
    # Takes test data and compares it with the NFRs
    def calculate_nfr_weights(self, nfr_config):
        """
        Calculate weights for NFRs based on the configuration.

        Args:
            nfr_config: NFR configuration containing rules

        Returns:
            tuple: (distribute_weight, bad_weight)
        """
        # Initialize flags and variables
        bad_weight = False

        # Calculate total weight and count NFRs without weights
        total_weight = 0
        nfrs_without_weight = 0

        for nfr in nfr_config["rows"]:
            if nfr["weight"]:
                total_weight += int(nfr["weight"])
            else:
                nfrs_without_weight += 1

        # Determine distribute_weight based on total weight
        if total_weight < 100 and nfrs_without_weight > 0:
            distribute_weight = (100 - total_weight) / nfrs_without_weight
        else:
            distribute_weight = 100 / len(nfr_config["rows"])
            bad_weight = True
            logging.warning("The total weight of your NFRs exceeds 100, so all NFRs will be considered equal.")

        return distribute_weight, bad_weight

    def compare_with_nfrs(self, nfr_config, table, distribute_weight=None, bad_weight=False):
        """
        Compare table data with NFR configuration and update metrics accordingly.

        Args:
            nfr_config: NFR configuration containing rules
            table: MetricsTable object containing both data and metrics to validate/update
            distribute_weight: Weight to distribute for NFRs without specified weights
            bad_weight: Flag indicating if the total weight exceeds 100%
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

            # Applying NFRs weights
            if nfr.weight is None or bad_weight:
                nfr.weight = distribute_weight

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

                        if compare_result == NFRStatus.FAILED:
                            self.transaction_result.append(f"{scope}: {nfr.metric} {metric_value} {self.operation_to_text(nfr.operation)} {nfr.threshold}.")

                        # Update the overall result status
                        # Append NFR result only if it was not set to FAILED before
                        if compare_result == NFRStatus.FAILED or result == NFRStatus.FAILED:
                            result = NFRStatus.FAILED

            # Update NFR result
            nfr_result["status"] = result
            nfr_result["nfr"] = nfr.description
            nfr_result["weight"] = float(nfr.weight)
            self.nfr_result.append(nfr_result)

    def calculate_apdex(self):
        total_weight = 0
        total_passed_weight = 0
        self.apdex = "N/A"
        # Iterate over each NFR result
        if len(self.nfr_result) > 0:
            for nfr in self.nfr_result:
                if 'weight' in nfr:
                    total_weight += nfr['weight']
                    # If the NFR status is PASSED, add the weight to total_passed_weight
                    if nfr['status'] == NFRStatus.PASSED:
                        total_passed_weight += nfr['weight']
            # Calculate Apdex as the percentage of total_passed_weight in total_weight
            if total_weight == 0:
                self.apdex = "N/A"
            elif total_passed_weight == 0:
                self.apdex = 0
            else:
                self.apdex = round((total_passed_weight / total_weight) * 100)

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

        # Get NFRs for the specific application
        nfr_config = DBNFRs.get_config_by_id(project_id=self.project, id=id)
        if not nfr_config:
            return f"No NFRs for test provided."

        # Find appropriate tables to use for validation
        # First check if we have any tables at all
        if not all_tables:
            logging.warning("No tables available for NFR validation")
            return "NFR validation failed: No tables available for validation."

        # Calculate NFR weights once for all tables
        distribute_weight, bad_weight = self.calculate_nfr_weights(nfr_config)

        # Process all tables - this is an enhancement from the previous implementation
        # that only processed the first table
        for table_name, table in all_tables.items():
            if hasattr(table, 'metrics') and table.metrics:
                # Compare with NFRs and update metric objects directly
                # Pass the pre-calculated weights to ensure consistency across all tables
                self.compare_with_nfrs(nfr_config, table, distribute_weight, bad_weight)

        # Calculate and format the results
        self.calculate_apdex()
        summary = 'Overall performance based on NFRs:\n'
        if self.apdex == "N/A": result = "cannot be evaluated based on NFRs, as the provided scope does not align with any available data."
        elif self.apdex >= 80 : result = "are acceptable"
        elif self.apdex < 80 and self.apdex >= 70: result = "are conditionally acceptable"
        else: result = "are unacceptable"
        summary += f"- Test results {result}.\n"
        summary += f"- {self.apdex}% of NFRs are satisfied.\n\n"
        if len(self.transaction_result) > 0:
            summary += "Requests that do not meet NFRs:\n"
            for row in self.transaction_result:
                summary += f"- {row}\n"

        return summary
