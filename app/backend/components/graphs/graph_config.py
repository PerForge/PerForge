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