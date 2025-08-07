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

import requests
import logging
import base64
import traceback

from app.backend.integrations.integration import Integration
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.components.secrets.secrets_db import DBSecrets


class Grafana(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.server}'

    def set_config(self, id):
        id = id if id else DBGrafana.get_default_config(project_id=self.project)["id"]
        config = DBGrafana.get_config_by_id(project_id=self.project, id=id)
        if config['id']:
            self.id = config["id"]
            self.name = config["name"]
            self.server = config["server"]
            self.org_id = config["org_id"]
            self.token = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]
            self.test_title = config["test_title"]
            self.baseline_test_title = config["baseline_test_title"]
            self.dashboards = config["dashboards"]
        else:
            logging.warning("There's no Grafana integration configured, or you're attempting to send a request from an unsupported location.")

    def get_grafana_link(self, start, end, dash_id = None):
        dashboard_content = next((dashboard['content'] for dashboard in self.dashboards if dashboard['id'] == dash_id), self.dashboards[0]['content'])
        return self.server + dashboard_content + '?orgId=' + self.org_id + '&from='+str(start)+'&to='+str(end)

    def get_grafana_test_link(self, start, end, test_title, dash_id = None):
        url = self.get_grafana_link(start, end, dash_id)
        url = f'{url}&var-{self.test_title}={test_title}'
        return url

    def dash_id_to_render(self, url):
        return url.replace("/d/", "/render/d-solo/")

    def encode_image(self, image):
        return base64.b64encode(image)

    def add_custom_tags(self, url, graph_json):
        if "custom_vars" in graph_json:
            custom_vars = graph_json["custom_vars"]
            if custom_vars:
                # Ensure the URL ends with an ampersand if it doesn't already
                if not url.endswith('&'):
                    url += '&'
                # Ensure custom_vars does not start with an ampersand
                if custom_vars.startswith('&'):
                    custom_vars = custom_vars[1:]
                url += custom_vars
        return url

    def render_image(self, graph_data, start, stop, test_title, baseline_test_title = None):
        image = None
        url = (
            self.get_grafana_link(start, stop, graph_data["dash_id"])
            + "&panelId=" + str(graph_data["view_panel"])
            + "&width=" + str(graph_data["width"])
            + "&height=" + str(graph_data["height"])
            + "&scale=3"
        )
        url = self.dash_id_to_render(url)
        if baseline_test_title:
            url = url+f'&var-{self.test_title}='+test_title+f'&var-{self.baseline_test_title}='+baseline_test_title
        else:
            url = url+f'&var-{self.test_title}='+test_title
        url = self.add_custom_tags(url=url, graph_json=graph_data)
        try:
            response = requests.get(url=url, headers={ 'Authorization': 'Bearer ' + self.token}, timeout=180, verify=False)
            if response.status_code == 200:
                image = response.content
            else:
                logging.info('ERROR: ' + response.content)
        except Exception as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)
        return image
