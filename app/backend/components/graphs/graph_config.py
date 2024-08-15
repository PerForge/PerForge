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

from app.backend.pydantic_models import GraphModel
from app.backend                 import pkg


class GraphConfig:

    def get_graph_value_by_id(project, graph_id):
        config_data = pkg.get_project_config(project)
        for graph in config_data["graphs"]:
            if graph["id"] == graph_id:
                return graph

    def check_graph_if_exist(project, graph_id):
        config_data = pkg.get_project_config(project)
        for graph in config_data["graphs"]:
            if graph["id"] == graph_id:
                return True
        return False

    def get_all_graphs(project):
        config_data = pkg.get_project_config(project)
        return config_data["graphs"]

    def save_graph_config(project, form):
        validated_form       = GraphModel.model_validate(form).model_dump()
        config_data          = pkg.get_project_config(project)
        graph_id             = validated_form.get("id")
        existing_graph_index = next((index for index, g in enumerate(config_data["graphs"]) if g["id"] == graph_id), None)
        if existing_graph_index is None:
            validated_form["id"] = pkg.generate_unique_id()
            config_data["graphs"].append(validated_form)
        else:
            config_data["graphs"][existing_graph_index] = validated_form
            for template in config_data["templates"]:
                for item in template["data"]:
                    if item["type"] == "graph" and item["id"] == graph_id:
                        item["content"] = validated_form["name"]
                        break
        pkg.save_new_data(project, config_data)
        return form.get("id")

    def delete_graph_config(project, graph_id):
        config_data   = pkg.get_project_config(project)
        graph_deleted = False
        for idx, obj in enumerate(config_data["graphs"]):
            if obj["id"] == graph_id:
                config_data["graphs"].pop(idx)
                graph_deleted = True
                break
        if graph_deleted:
            for template in config_data["templates"]:
                template_data = template["data"]
                for idx, data_item in enumerate(template_data):
                    if data_item["type"] == "graph" and data_item["id"] == graph_id:
                        template_data.pop(idx)
                        break
        pkg.save_new_data(project, config_data)