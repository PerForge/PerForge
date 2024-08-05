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

from app.config                                                           import config_path
from app.backend                                                   import pkg

import re


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


class DataRow:
    def __init__(self, data_row):
        self.avg         = data_row["avg"]
        self.count       = data_row["count"]
        self.errors      = data_row["errors"]
        self.rpm         = data_row["rpm"]
        self.pct50       = data_row["pct50"]
        self.pct75       = data_row["pct75"]
        self.pct90       = data_row["pct90"]
        self.transaction = data_row["transaction"]


class Validation:
    def __init__(self, project):
        self.project            = project
        self.path_to_nfrs       = config_path
        self.nfr_result         = []
        self.transaction_result = []

    def delete_nfrs(self, name):
        pkg.delete_nfr(self.project, name)

    # Method returns NFRs for specific application
    def get_nfr(self, name):
        return pkg.get_nfr(self.project, name)
    
    def get_human_nfr(self, name):
        result = []
        nfrs   = pkg.get_nfr(self.project, name)
        for nfr_row in nfrs["rows"]:
            result.append(self.generate_name(nfr_row))
        return result

    # Method reqturns all NFRs for all applications
    def get_nfrs(self):
        return pkg.get_nfrs(self.project)


    # Method accepts test value, operation and threshold
    # Compares value with treshold using specified operation
    # Returns PASSED or FAILED status
    @staticmethod
    def compare_value(value, operation, threshold):
        try:
            if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
                if operation == '>':
                    return "PASSED" if value > threshold else "FAILED"
                elif operation == '<':
                    return "PASSED" if value < threshold else "FAILED"
                elif operation == '>=':
                    return "PASSED" if value >= threshold else "FAILED"
                elif operation == '<=':
                    return "PASSED" if value <= threshold else "FAILED"
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
    def compare_with_nfrs(self, nfrs, data):
        # try:
        nfr_result = {}
        # Initialize flags and variables
        bad_weight = False

        # Calculate total weight and count NFRs without weights
        total_weight = 0
        nfrs_without_weight = 0

        for nfr in nfrs["rows"]:
            if nfr["weight"] != '':
                total_weight += int(nfr["weight"])
            else:
                nfrs_without_weight += 1

        # Determine distribute_weight based on total weight
        if total_weight < 100 and nfrs_without_weight > 0:
            distribute_weight = (100 - total_weight) / nfrs_without_weight
        else:
            distribute_weight = 100 / len(nfrs["rows"])
            bad_weight = True

        # Iterate through NFRs
        for nfr_row in nfrs["rows"]:
            nfr = Nfr(nfr_row, self.generate_name(nfr_row))
            if nfr.scope == 'each' or nfr.scope in [item['transaction'] for item in data] or nfr.regex:
                # Iterate through Data for validation
                for row in data:
                    data_row = DataRow(row)
                    # Applying NFRs weights 
                    if nfr.weight == '' or bad_weight:
                        nfr.weight = distribute_weight
                    # Check if the regex matches the transaction
                    is_regex_match = self.is_match(regex=nfr.scope, string=data_row.transaction) if nfr.regex else False

                    # Determine whether to process this row based on the NFR scope
                    should_process = nfr.scope == 'each' or nfr.scope == data_row.transaction or is_regex_match

                    if should_process:
                        result = nfr_result.get("status", 'PASSED')
                        # Call compare_value function here
                        compare_result = self.compare_value(getattr(data_row, nfr.metric), nfr.operation, nfr.threshold)
                        if "FAILED" == compare_result:
                            self.transaction_result.append(f"{data_row.transaction} transaction did not meet the NFR as its {nfr.metric} of {getattr(data_row, nfr.metric)} {self.operation_to_text(nfr.operation)} {nfr.threshold}.")
                        # Append NFR result only if it was not set to FAILED before
                        nfr_result["status"] = compare_result if result != 'FAILED' else result
                        nfr_result["nfr"] = nfr.description
                        nfr_result["weight"] = distribute_weight
            self.nfr_result.append(nfr_result)
            nfr_result = {}

    def calculate_apdex(self):
        total_weight = 0
        total_passed_weight = 0
        # Iterate over each NFR result
        if len(self.nfr_result) > 0:
            for nfr in self.nfr_result:
                if 'weight' in nfr:
                    total_weight += nfr['weight']
                    # If the NFR status is PASSED, add the weight to total_passed_weight
                    if nfr['status'] == 'PASSED':
                        total_passed_weight += nfr['weight']
            # Calculate Apdex as the percentage of total_passed_weight in total_weight
            if total_weight == 0 or total_passed_weight == 0:
                self.apdex = 0
            else:
                self.apdex = round((total_passed_weight / total_weight) * 100)

    def create_summary(self, id, data):
        # Get NFRs for the specific application
        nfrs = self.get_nfr(id)
        if nfrs:
            self.compare_with_nfrs(nfrs, data)
            self.calculate_apdex()
            summary = 'Overall performance based on NFRs:\n'
            if self.apdex >= 80 : result = "acceptable"
            elif self.apdex < 80 and self.apdex >= 70: result = "conditionally acceptable"
            else: result = "unacceptable"
            summary += f"- Test results are {result}.\n"
            summary += f"- {self.apdex}% of NFRs are satisfied.\n\n"
            if len(self.transaction_result) > 0:
                summary += "Requests that do not meet NFRs:\n"
                for row in self.transaction_result:
                    summary += f"- {row}\n"
        else:
            summary = f"No NFRs for test provided."
        return summary