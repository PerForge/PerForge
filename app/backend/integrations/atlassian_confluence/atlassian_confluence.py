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

import logging
import uuid
import traceback
import time

from app.backend.integrations.integration                                  import Integration
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.components.secrets.secrets_db                             import DBSecrets
from atlassian                                                             import Confluence


class AtlassianConfluence(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.org_url}'

    def set_config(self, id):
        id     = id if id else DBAtlassianConfluence.get_default_config(project_id=self.project)["id"]
        config = DBAtlassianConfluence.get_config_by_id(project_id=self.project, id=id)
        if config['id']:
            self.id        = config["id"]
            self.name      = config["name"]
            self.email     = config["email"]
            self.token     = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]
            self.org_url   = config["org_url"]
            self.space_key = config["space_key"]
            self.parent_id = config["parent_id"]
            if config["token_type"] == "api_token":
                self.confluence_auth = Confluence(
                    url      = self.org_url,
                    username = self.email,
                    password = self.token
                )
            else:
                self.confluence_auth = Confluence(
                    url   = self.org_url,
                    token = self.token
                )
        else:
            logging.warning("There's no Confluence integration configured, or you're attempting to send a request from an unsupported location.")

    def put_page(self, title, content):
        try:
            response = self.confluence_auth.create_page(space=self.space_key, title=title, body=content, parent_id=self.parent_id)
            return response
        except Exception as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)

    def put_image_to_confl(self, image, name, page_id):
        name = f'{uuid.uuid4()}.png'
        for _ in range(3):
            try:
                self.confluence_auth.attach_content(content=image, name=name, content_type="image/png", page_id=page_id, space=self.space_key)
                return name
            except Exception as er:
                logging.warning('ERROR: uploading image to confluence failed')
                logging.warning(er)
            time.sleep(10)

    def update_page(self, page_id, title, content):
        try:
            response = self.confluence_auth.update_page(page_id=page_id, title=title, body=content)
            return response
        except Exception as er:
            logging.warning(er)
            return {"status":"error", "message":er}