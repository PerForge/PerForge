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
from app.backend.pydantic_models                import GrafanaModel
from app.backend.components.graphs.graph_config import GraphConfig


class GrafanaConfig:

    def get_grafana_config_names_ids_and_dashboards(project):
        data            = pkg.get_project_config(project)
        grafana_configs = data["integrations"]["grafana"]
        output          = []
        for grafana in grafana_configs:
            output.append({"id": grafana["id"], "name": grafana["name"], "dashboards": grafana["dashboards"]})
        return output

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

    def save_grafana_config(project, data, is_internal = False):
        existing_grafana_config = pkg.get_integration_values(project, "grafana", data['id'], is_internal)
        existing_dashboards     = {dashboard['id'] for dashboard in existing_grafana_config.get('dashboards', [])}
        new_dashboards          = {dashboard['id'] for dashboard in data['dashboards']}
        removed_dashboards      = existing_dashboards - new_dashboards
        if removed_dashboards:
            all_graphs = GraphConfig.get_all_graphs(project)
            for graph in all_graphs:
                if graph["dash_id"] in removed_dashboards:
                    GraphConfig.delete_graph_config(project, graph["id"])
        for dashboard in data['dashboards']:
            if not dashboard['id']:
                dashboard['id'] = pkg.generate_unique_id()
        validated_data = GrafanaModel.model_validate(data).model_dump()
        id             = pkg.save_integration(project, validated_data, "grafana")
        return id

    def get_default_grafana_config_id(project):
        id = pkg.get_default_integration(project, "grafana")
        return id

    def delete_grafana_config(project, config):
        pkg.delete_config(project, config, "integrations", "grafana")
        all_graphs = GraphConfig.get_all_graphs(project)
        for graph in all_graphs:
            if graph["grafana_id"] == config:
                GraphConfig.delete_graph_config(project, graph["id"])