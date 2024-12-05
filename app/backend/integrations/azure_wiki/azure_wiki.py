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

import requests
import base64
import logging
import random
import traceback
import time

from app.backend.integrations.integration              import Integration
from app.backend.integrations.azure_wiki.azure_wiki_db import DBAzureWiki
from app.backend.components.secrets.secrets_db         import DBSecrets

class AzureWiki(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.org_url}'

    def set_config(self, id):
        id = id if id else DBAzureWiki.get_default_config(schema_name=self.schema_name)["id"]
        config = DBAzureWiki.get_config_by_id(schema_name=self.schema_name, id=id)
        if config['id']:
            self.id                        = config["id"]
            self.name                      = config["name"]
            self.token                     = DBSecrets.get_config_by_id(id=config["token"])["value"]
            self.org_url                   = config["org_url"]
            self.project_id                = config["project_id"]
            self.identifier                = config["identifier"]
            self.path_to_report            = config["path_to_report"]
            self.azure_headers_attachments = {
                    'Accept'       : 'application/json',
                    'Authorization': 'Basic ' + str(base64.b64encode(bytes(':'+ self.token, 'ascii')), 'ascii'),
                    'Content-Type' : 'application/octet-stream'
                }
            self.azure_authorization_headers = {
                    'Accept'       : 'application/json',
                    'Authorization': 'Basic ' + str(base64.b64encode(bytes(':'+ self.token, 'ascii')), 'ascii')
                }
        else:
            logging.warning("There's no Azure integration configured, or you're attempting to send a request from an unsupported location.")

    def get_path(self):
        return self.path_to_report

    def put_image_to_azure(self, image, name):
        name = f'{name.replace(" ", "-")}.png'
        for _ in range(3):
            try:
                response = requests.put(
                url = f'{self.org_url}/{self.project_id}/_apis/wiki/wikis/{self.identifier}/attachments?name={name}&api-version=6.0', headers=self.azure_headers_attachments, data=image)
                if response.status_code != 201:
                    name = str(random.randint(1,100)) + name
                elif response.status_code == 201:
                    return name
            except Exception as er:
                logging.warning('ERROR: uploading image to azure failed')
                logging.warning("An error occurred: " + str(er))
                err_info = traceback.format_exc()
                logging.warning("Detailed error info: " + err_info)
            time.sleep(10)
        return None

    def put_page(self, path, page_content):
        wiki_api_url = f'{self.org_url}/{self.project_id}/_apis/wiki/wikis/{self.identifier}/pages?path={path}&api-version=6.0'
        try:
            response = requests.put(
                url=wiki_api_url, headers=self.azure_authorization_headers, json={ "content": page_content })
            return response
        except Exception as er:
            logging.warning('ERROR: failed to upload the page to wiki')
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)

    def get_page(self, path):
        wiki_api_url = f'{self.org_url}/{self.project_id}/_apis/wiki/wikis/{self.identifier}/pages?path={path}&api-version=6.0'
        try:
            response = requests.get(url=wiki_api_url, headers=self.azure_authorization_headers)
            return response
        except Exception as er:
            logging.warning('ERROR: getting ETag failed')
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)

    def create_or_update_page(self, path, page_content):
        response = self.put_page(path, page_content)
        if response.status_code != 201:
            for x in range(1,5):
                if "WikiAncestorPageNotFoundException" in str(response.content):
                    newPage  = '/'.join(path.split('/')[:-x])
                    response = self.put_page(newPage, '')
                else:
                    response = self.put_page(path, page_content)
                    break
            if "specified in the add operation already exists in the wiki" in str(response.content):
                try:
                    response = self.get_page(path)
                except Exception as er:
                    logging.warning('ERROR: getting ETag failed')
                    logging.warning("An error occurred: " + str(er))
                    err_info = traceback.format_exc()
                    logging.warning("Detailed error info: " + err_info)
                self.azure_authorization_headers["If-Match"]=str(response.headers["ETag"])
                try:
                    response = self.put_page(path, page_content)
                except Exception as er:
                    logging.warning('ERROR: failed to update the page in wiki')
                    logging.warning("An error occurred: " + str(er))
                    err_info = traceback.format_exc()
                    logging.warning("Detailed error info: " + err_info)