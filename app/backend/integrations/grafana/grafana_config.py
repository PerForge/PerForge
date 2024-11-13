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

from app.backend                                import pkg


class GrafanaConfig:

    def get_grafana_config_values(project, grafana_config, is_internal = False):
        data       = pkg.get_integration_values(project, "grafana", grafana_config, is_internal)
        output     = {}
        dashboards = []
        for key, value in data.items():
            if key == 'dashboards':
                for dashboard in value:
                    dashboards.append(dashboard)
            else:
                output[key] = value
        output['dashboards'] = dashboards
        return output

    def get_default_grafana_config_id(project):
        id = pkg.get_default_integration(project, "grafana")
        return id