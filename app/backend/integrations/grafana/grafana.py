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

import os
import requests
import logging
import base64
import traceback

from app.backend.integrations.integration            import Integration
from app.backend.integrations.grafana.grafana_config import GrafanaConfig
from app.backend.components.graphs.graph_config      import GraphConfig
from os                                              import path


class Grafana(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.server}'

    def set_config(self, id):
        if path.isfile(self.config_path) is False or os.path.getsize(self.config_path) == 0:
            logging.warning("There is no config file.")
        else:
            id = id if id else GrafanaConfig.get_default_grafana_config_id(self.project)
            config = GrafanaConfig.get_grafana_config_values(self.project, id, is_internal=True)
            if "id" in config:
                if config['id'] == id:
                    self.id                  = config["id"]
                    self.name                = config["name"]
                    self.server              = config["server"]
                    self.org_id              = config["org_id"]
                    self.token               = config["token"]
                    self.test_title          = config["test_title"]
                    self.app                 = config["app"]
                    self.baseline_test_title = config["baseline_test_title"]
                    self.dashboards          = config["dashboards"]
                else:
                    raise Exception(f'No such config id: {id}')

    def get_grafana_link(self, start, end, test_name, dash_id = None):
        dashboard_content = next((dashboard['content'] for dashboard in self.dashboards if dashboard['id'] == dash_id), self.dashboards[0]['content'])
        return self.server + dashboard_content + '?orgId=' + self.org_id + '&from='+str(start)+'&to='+str(end)+f'&var-{self.app}='+str(test_name)

    def get_grafana_test_link(self, start, end, test_name, run_id, dash_id = None):
        url = self.get_grafana_link(start, end, test_name, dash_id)
        url = f'{url}&var-{self.test_title}={run_id}'
        return url

    def dash_id_to_render(self, url):
        return url.replace("/d/", "/render/d-solo/")

    def encode_image(self, image):
        return base64.b64encode(image)

    def render_image(self, graph_id, start, stop, test_name, run_id, baseline_run_id = None):
        image = None
        if GraphConfig.check_graph_if_exist(self.project, graph_id):
            graph_json = GraphConfig.get_graph_value_by_id(self.project, graph_id)
            url        = self.get_grafana_link(start, stop, test_name, graph_json["dash_id"]) + "&panelId="+graph_json["view_panel"]+"&width="+graph_json["width"]+"&height="+graph_json["height"]+"&scale=3"
            url = self.dash_id_to_render(url)
            if baseline_run_id:
                url = url+f'&var-{self.test_title}='+run_id+f'&var-{self.baseline_test_title}='+baseline_run_id
            else:
                url = url+f'&var-{self.test_title}='+run_id
            try:
                response = requests.get(url=url, headers={ 'Authorization': 'Bearer ' + self.token}, timeout=180)
                if response.status_code == 200:
                    image = response.content
                else:
                    logging.info('ERROR: ' + response.content)
            except Exception as er:
                logging.warning("An error occurred: " + str(er))
                err_info = traceback.format_exc()
                logging.warning("Detailed error info: " + err_info)
        return image