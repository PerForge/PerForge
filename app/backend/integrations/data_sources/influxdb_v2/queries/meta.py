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

class InfluxDBMetaQueries:
    @staticmethod
    def get_buckets(name_regex: str | None = None) -> str:
        """Return Flux query to list buckets (excluding internal buckets) and keep only names.

        If name_regex is provided, additionally filter by bucket name using the regex.
        """
        base = (
            "buckets()\n"
            "  |> filter(fn: (r) => r.name !~ /^(_monitoring|_tasks)$/)\n"
        )
        if name_regex:
            base += f"  |> filter(fn: (r) => r.name =~ /^{name_regex}$/)\n"
        base += "  |> keep(columns: [\"name\"])\n"
        return base
