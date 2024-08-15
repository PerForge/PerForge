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

import json
import uuid
import logging
import portalocker
import yaml
import requests
import re
import logging
import traceback

from app.config                  import config_path
from app.models                  import Secret
from app.backend.pydantic_models import ProjectModel
from os                          import path as pt
from datetime                    import datetime
from pydantic                    import ValidationError


def generate_unique_id():
    return str(uuid.uuid4())

def read_from_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def validate_config(config_data):
    validated_config = []
    for project_data in config_data:
        try:
            validated_project_config = ProjectModel.model_validate(project_data).model_dump()
            validated_config.append(validated_project_config)
        except ValidationError as er:
            logging.warning("An error occurred: " + str(er))
            err_info = traceback.format_exc()
            logging.warning("Detailed error info: " + err_info)
    return validated_config

def save_new_config(data):
    path_to_config = config_path
    try:
        json_data = json.dumps(data, indent=4, separators=(',', ': '))
    except (TypeError, ValueError) as e:
        logging.warning(f"Invalid JSON data: {e}")
        return
    with open(path_to_config, 'w') as json_file:
        portalocker.lock(json_file, portalocker.LOCK_EX)
        try:
            json_file.write(json_data)
        finally:
            portalocker.unlock(json_file)

def save_new_data(project, data):
    config = get_json_config()
    for obj in config:
        if obj["id"] == project:
            obj["data"] = data
            break
    save_new_config(config)

def get_json_config():
    path_to_config = config_path
    config         = []
    if pt.isfile(path_to_config) is False or pt.getsize(path_to_config) == 0:
        return []
    with open(path_to_config, 'r') as json_file:
        portalocker.lock(json_file, portalocker.LOCK_SH)
        try:
            config = json.load(json_file)
        finally:
            portalocker.unlock(json_file)
    validated_config = validate_config(config)
    return validated_config

def get_json_values(project, json_name, config_id):
    data   = get_project_config(project)
    output = {}
    for item in data[json_name]:
        if item["id"] == config_id:
            for key, value in item.items():
                output[key] = value
    return output

def get_project_config(project):
    config = get_json_config()
    for obj in config:
        if obj["id"] == project:
            return obj["data"]
    return {}

def delete_config(project, config, list_name, type = None):
    data = get_project_config(project)
    if list_name == "templates" or list_name == "template_groups":
        for idx, obj in enumerate(data[list_name]):
            if obj["id"] == config:
                data[list_name].pop(idx)
    else:
        for idx, obj in enumerate(data[list_name][type]):
            if obj["id"] == config:
                data[list_name][type].pop(idx)
    save_new_data(project, data)

def get_all_projects():
    config = get_json_config()
    result = []
    for obj in config:
        project_data = {"id": obj["id"], "name": obj["name"]}
        result.append(project_data)
    return result

def get_project_config_stats(project):
    result = {}
    result["integrations"] = 0
    result["graphs"]       = 0
    result["nfrs"]         = 0
    result["templates"]    = 0
    result["secrets"]      = 0
    data = get_project_config(project)
    for integration in data["integrations"]:
        result["integrations"] += len(data["integrations"][integration])
    result["graphs"]    = len(data["graphs"])
    result["templates"] = len(data["templates"])
    result["nfrs"]      = len(data["nfrs"])
    result["secrets"]   = Secret.count_secrets()
    return result

def save_new_project_config(project_name):
    config     = get_json_config()
    project_id = generate_unique_id()
    config.append({"id": project_id, "name": project_name, "data": {}})
    save_new_config(config)
    return project_id

def delete_project_config(project):
    data = get_json_config()
    for idx, obj in enumerate(data):
        if obj["id"] == project:
            data.pop(idx)
            break
    save_new_config(data)

def get_integration_config_names_and_ids(project, integration_name):
    return get_config_names_and_ids(project, "integrations", integration_name)

def get_config_names_and_ids(project, key1, key2=None):
    result = []
    data = get_project_config(project)
    if key2:
        keys_list = data[key1][key2]
    else:
        keys_list = data[key1]
    for key in keys_list:
        result.append({"name": key["name"], "id": key["id"]})
    return result

def check_if_token(value):
    if isinstance(value, str):
        if value.startswith("{{") and value.endswith("}}"):
            secret_key = value[2:-2]
            value = Secret.get_by_key(secret_key)
    return value

def get_integration_values(project, integration_name, config_id, is_internal = None):
    data   = get_project_config(project)
    output = {}
    for item in data["integrations"][integration_name]:
        if item["id"] == config_id:
            for key, value in item.items():
                if is_internal:
                    output[key] = check_if_token(value)
                else:
                    output[key] = value
    return output

def del_csrf_token(data):
    if 'csrf_token' in data:
       del data['csrf_token']
    return data

def save_integration(project, form, integration_type):
    data                       = get_project_config(project)
    integration_id             = form.get("id")
    existing_integration_index = next((index for index, i in enumerate(data["integrations"][integration_type]) if i["id"] == integration_id), None)
    form                       = del_csrf_token(form)
    if existing_integration_index is None:
        form["id"] = generate_unique_id()
        data["integrations"][integration_type].append(form)
    else:
        data["integrations"][integration_type][existing_integration_index] = form
    if form.get("is_default") == "true":
        for integration in data["integrations"][integration_type]:
            integration["is_default"] = "true" if integration["id"] == form["id"] else "false"
    else:
        if all(integration.get("is_default") == "false" for integration in data["integrations"][integration_type]):
            data["integrations"][integration_type][0]["is_default"] = "true"
    save_new_data(project, data)
    return form.get("id")

def get_default_integration(project, integration_type):
    data = get_project_config(project)
    for config in data["integrations"][integration_type]:
        if config["is_default"] == "true":
            return config["id"]

def get_output_integration_configs(project):
    result = []
    types  = ["azure", "atlassian_confluence", "atlassian_jira", "smtp_mail"]
    for type in types:
        configs = get_config_names_and_ids(project, "integrations", type)
        for config in configs:
            config["type"] = type
        result += configs
    return result

def get_output_integration_type_by_id(project, id):
    output_configs = get_output_integration_configs(project)
    for config in output_configs:
        if config.get("id") == id:
            return config["type"]
    return None

def sort_tests(tests):
    def start_time(e): return e['startTime']
    if len(tests) != 0:
        for test in tests:
            test["startTimestamp"] = str(int(test["startTime"].timestamp() * 1000))
            test["endTimestamp"]   = str(int(test["endTime"].timestamp() * 1000))
            test["startTime"]      = datetime.strftime(test["startTime"], "%Y-%m-%d %I:%M:%S %p")
            test["endTime"]        = datetime.strftime(test["endTime"], "%Y-%m-%d %I:%M:%S %p")
    tests.sort(key=start_time, reverse=True)
    return tests

def get_current_version_from_file():
    try:
        with open('version.txt', 'r') as file:
            version = file.read().strip()
        return version
    except Exception as e:
        logging.warning(f"Failed to read version from file: {e}")
        return None

def get_new_version_from_docker_hub():
    url = "https://hub.docker.com/v2/repositories/perforge/perforge-app/tags"
    tags = []
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tags.extend([tag['name'] for tag in data['results']])
    return tags[1]

def is_valid_new_version_from_docker_hub(current_version, new_version):
    # Define a regex pattern for a valid version number (e.g., "1.0.15")
    pattern = re.compile(r'^\d+\.\d+\.\d+$')
    if not pattern.match(new_version):
        return False
    # Split the version strings into their numeric components
    current_parts = list(map(int, current_version.split('.')))
    new_parts     = list(map(int, new_version.split('.')))
    # Compare the numeric components
    return new_parts > current_parts