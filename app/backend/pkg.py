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

import app.backend.pydantic_models as md
import os
import json
import uuid
import logging
import portalocker
import yaml

from app.config              import config_path
from app.models              import Secret
from os                      import path as pt
from werkzeug.datastructures import MultiDict
from datetime                import datetime


def get_files_in_dir(path):
    listOfValues = os.listdir(path)
    output       = []
    for elem in listOfValues:
        if ".md" not in elem:
            output.append(elem)
    return output

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
    return config

def get_project_config(project):
    config = get_json_config()
    for obj in config:
        if obj["id"] == project:
            return obj["data"]
    return {}

def validate_config(project, key1, key2 = None):
    data = get_project_config(project)
    if key2 == None:
        if key1 not in data:
            data[key1] = []
    else:
        if key1 not in data:
            data[key1]       = {}
            data[key1][key2] = []
        else:
            if key2 not in data[key1]:
                data[key1][key2] = []
    save_new_data(project, data)

def get_projects():
    config = get_json_config()
    result = []
    for obj in config:
        project_data = {"id": obj["id"], "name": obj["name"]}
        result.append(project_data)
    return result

def get_project_stats(project):
    result = {}
    result["integrations"] = 0
    result["graphs"]       = 0
    result["nfrs"]         = 0
    result["templates"]    = 0
    result["secrets"]      = 0
    validate_config(project, "integrations", "influxdb")
    data = get_project_config(project)
    for integration in data["integrations"]:
        result["integrations"] += len(data["integrations"][integration])
    validate_config(project, "graphs")
    data             = get_project_config(project)
    result["graphs"] = len(data["graphs"])
    validate_config(project, "templates")
    data                = get_project_config(project)
    result["templates"] = len(data["templates"])
    validate_config(project, "nfrs")
    data              = get_project_config(project)
    result["nfrs"]    = len(data["nfrs"])
    result["secrets"] = Secret.count_secrets()
    return result


def delete_config(project, config, list_name, type = None):
    if(type):
        validate_config(project, list_name, type)
    else:
        validate_config(project, list_name)
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

def get_integration_config_names_and_ids(project, integration_name):
    return get_config_names_and_ids(project, "integrations", integration_name)

def get_config_names_and_ids(project, key1, key2=None):
    result = []
    validate_config(project, key1, key2)
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
    validate_config(project, "integrations", integration_name)
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

def get_json_values(project, json_name, config_id):
    validate_config(project, json_name)
    data   = get_project_config(project)
    output = {}
    for item in data[json_name]:
        if item["id"] == config_id:
            for key, value in item.items():
                output[key] = value
    return output

def del_csrf_token(data):
    if 'csrf_token' in data:
       del data['csrf_token']
    return data

def save_integration(project, form, integration_type):
    validate_config(project, "integrations", integration_type)
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
    validate_config(project, "integrations", integration_type)
    data = get_project_config(project)
    for config in data["integrations"][integration_type]:
        if config["is_default"] == "true":
            return config["id"]

####################### INFLUXDB:

def get_influxdb_config_values(project, influxdb_config, is_internal = False):
    output = md.InfluxdbModel.model_validate(get_integration_values(project, "influxdb", influxdb_config, is_internal))
    return MultiDict(output.model_dump())

def save_influxdb(project, data):
    data = md.InfluxdbModel.model_validate(data)
    return save_integration(project, data.model_dump(), "influxdb")

def get_default_influxdb(project):
    return get_default_integration(project, "influxdb")

def delete_influxdb_config(project, config):
    delete_config(project, config, "integrations", "influxdb")

####################### GRAFANA:

def get_grafana_configs_names_ids_and_dashboards(project):
    validate_config(project, "integrations", "grafana")
    data            = get_project_config(project)
    grafana_configs = data["integrations"]["grafana"]
    result          = []
    for grafana in grafana_configs:
        result.append({"id": grafana["id"], "name": grafana["name"], "dashboards": grafana["dashboards"]})
    return result

def get_grafana_config_values(project, grafana_config, is_internal = False):
    output     = md.GrafanaModel.model_validate(get_integration_values(project, "grafana", grafana_config, is_internal))
    result     = {}
    dashboards = []
    for key, value in output.model_dump().items():
        if key == 'dashboards':
            for dashboard in value:
                dashboards.append(dashboard)
        else:
            result[key] = value
    result['dashboards'] = dashboards
    return result

def save_grafana(project, data, is_internal = False):
    existing_grafana_config = get_integration_values(project, "grafana", data['id'], is_internal)
    existing_dashboards     = {dashboard['id'] for dashboard in existing_grafana_config.get('dashboards', [])}
    new_dashboards          = {dashboard['id'] for dashboard in data['dashboards']}
    removed_dashboards      = existing_dashboards - new_dashboards
    if removed_dashboards:
        all_graphs = get_graphs(project)
        for graph in all_graphs:
            if graph["dash_id"] in removed_dashboards:
                delete_graph(project, graph["id"])
    for dashboard in data['dashboards']:
        if not dashboard['id']:
            dashboard['id'] = generate_unique_id()
    data = md.GrafanaModel.model_validate(data)
    return save_integration(project, data.model_dump(), "grafana")

def get_default_grafana(project):
    return get_default_integration(project, "grafana")

def get_dashboards(project):
    validate_config(project, "integrations", "grafana")
    data   = get_project_config(project)
    output = []
    for item in data["integrations"]["grafana"]:
        if (item["dashboards"]):
            for id in item["dashboards"]:
                output.append(id)
    return output

def delete_grafana_config(project, config):
    delete_config(project, config, "integrations", "grafana")
    all_graphs = get_graphs(project)
    for graph in all_graphs:
        if graph["grafana_id"] == config:
            delete_graph(project, graph["id"])

####################### AZURE:

def get_azure_config_values(project, azure_config, is_internal = False):
    output = md.AzureModel.model_validate(get_integration_values(project, "azure", azure_config, is_internal))
    return MultiDict(output.model_dump())

def save_azure(project, data):
    data = md.AzureModel.model_validate(data)
    return save_integration(project, data.model_dump(), "azure")

def get_default_azure(project):
    return get_default_integration(project, "azure")

def delete_azure_config(project, config):
    delete_config(project, config, "integrations", "azure")

####################### ATLASSIAN CONFLUENCE:

def get_atlassian_confluence_config_values(project, atlassian_confluence_config, is_internal = False):
    output = md.AtlassianConfluenceModel.model_validate(get_integration_values(project, "atlassian_confluence", atlassian_confluence_config, is_internal))
    return MultiDict(output.model_dump())

def save_atlassian_confluence(project, data):
    data = md.AtlassianConfluenceModel.model_validate(data)
    return save_integration(project, data.model_dump(), "atlassian_confluence")

def get_default_atlassian_confluence(project):
    return get_default_integration(project, "atlassian_confluence")

def delete_atlassian_confluence_config(project, config):
    delete_config(project, config, "integrations", "atlassian_confluence")

####################### ATLASSIAN JIRA:

def get_atlassian_jira_config_values(project, atlassian_jira_config, is_internal = False):
    output = md.AtlassianJiraModel.model_validate(get_integration_values(project, "atlassian_jira", atlassian_jira_config, is_internal))
    return MultiDict(output.model_dump())

def save_atlassian_jira(project, data):
    data = md.AtlassianJiraModel.model_validate(data)
    return save_integration(project, data.model_dump(), "atlassian_jira")

def get_default_atlassian_jira(project):
    return get_default_integration(project, "atlassian_jira")

def delete_atlassian_jira_config(project, config):
    delete_config(project, config, "integrations", "atlassian_jira")

####################### SMTP MAIL:

def get_smtp_mail_config_values(project, smtp_mail_config, is_internal = False):
    output = md.SmtpMailModel.model_validate(get_integration_values(project, "smtp_mail", smtp_mail_config, is_internal))
    result = []
    for key, value in output.model_dump().items():
        if key == 'recipients':
            for index, recipient in enumerate(value):
                result.append((f'{key}-{index}', recipient))
        else:
            result.append((key, value))
    return MultiDict(result)

def save_smtp_mail(project, data):
    data = md.SmtpMailModel.model_validate(data)
    return save_integration(project, data.model_dump(), "smtp_mail")

def get_default_smtp_mail(project):
    return get_default_integration(project, "smtp_mail")

def delete_smtp_mail_config(project, config):
    delete_config(project, config, "integrations", "smtp_mail")

####################### AI SUPPORT:

def get_ai_support_config_values(project, ai_support_config, is_internal = False):
    output = md.AISupportModel.model_validate(get_integration_values(project, "ai_support", ai_support_config, is_internal))
    return MultiDict(output.model_dump())

def save_ai_support(project, data):
    data = md.AISupportModel.model_validate(data)
    return save_integration(project, data.model_dump(), "ai_support")

def get_default_ai_support(project):
    return get_default_integration(project, "ai_support")

def delete_ai_support_config(project, config):
    delete_config(project, config, "integrations", "ai_support")

####################### OUTPUT:

def get_output_configs(project):
    result = []
    types  = ["azure", "atlassian_confluence", "atlassian_jira", "smtp_mail"]
    for type in types:
        configs = get_config_names_and_ids(project, "integrations", type)
        for config in configs:
            config["type"] = type
        result += configs
    return result

def get_output_type_by_id(project, id):
    output_configs = get_output_configs(project)
    for config in output_configs:
        if config.get("id") == id:
            return config["type"]
    return None

####################### NFRS CONFIG:

def get_nfr(project, id):
    result = []
    validate_config(project, "nfrs")
    data = get_project_config(project)
    for nfr in data["nfrs"]:
        if nfr["id"] == id:
            result = nfr
    return result

def get_nfrs(project):
    validate_config(project, "nfrs")
    data = get_project_config(project)
    return data["nfrs"]

def save_nfrs(project, nfr):
    validate_config(project, "nfrs")
    data               = get_project_config(project)
    nfr_id             = nfr.get("id")
    existing_nfr_index = next((index for index, n in enumerate(data["nfrs"]) if n["id"] == nfr_id), None)
    if existing_nfr_index is None:
        nfr["id"] = generate_unique_id()
        data["nfrs"].append(nfr)
    else:
        data["nfrs"][existing_nfr_index] = nfr
    save_new_data(project, data)
    return nfr.get("id")

def delete_nfr(project, id):
    validate_config(project, "nfrs")
    data        = get_project_config(project)
    nfr_deleted = False
    for idx, obj in enumerate(data["nfrs"]):
        if obj["id"] == id:
            data["nfrs"].pop(idx)
            nfr_deleted = True
            break
    if nfr_deleted:
        for template in data["templates"]:
            if template["nfr"] == id:
                template["nfr"] == ""
    save_new_data(project, data)

####################### TEMPLATE CONFIG:

def get_templates(project):
    validate_config(project, "templates")
    data = get_project_config(project)
    return data["templates"]

def get_template_values(project, template):
    template_obj = get_json_values(project, "templates", template)
    output       = md.TemplateModel.model_validate(template_obj)
    return output.model_dump()

def save_template(project, template):
    template = md.TemplateModel.model_validate(template).model_dump()
    validate_config(project, "templates")
    data                    = get_project_config(project)
    template_id             = template.get("id")
    existing_template_index = next((index for index, t in enumerate(data["templates"]) if t["id"] == template_id), None)
    if existing_template_index is None:
        template["id"] = generate_unique_id()
        data["templates"].append(template)
    else:
        data["templates"][existing_template_index] = template
        for template_group in data["template_groups"]:
            for item in template_group["data"]:
                if item["type"] == "template" and item["id"] == template_id:
                    item["content"] = template["name"]
                    break
    save_new_data(project, data)
    return template.get("id")

def get_template_groups(project):
    validate_config(project, "template_groups")
    data = get_project_config(project)
    return data["template_groups"]

def get_template_group_values(project, template_group):
    output = md.TemplateGroupModel.model_validate(get_json_values(project, "template_groups", template_group))
    return output.model_dump()

def save_template_group(project, template_group):
    template_group = md.TemplateGroupModel.model_validate(template_group).model_dump()
    validate_config(project, "template_groups")
    data                          = get_project_config(project)
    template_group_id             = template_group.get("id")
    existing_template_group_index = next((index for index, tg in enumerate(data["template_groups"]) if tg["id"] == template_group_id), None)
    if existing_template_group_index is None:
        template_group["id"] = generate_unique_id()
        data["template_groups"].append(template_group)
    else:
        data["template_groups"][existing_template_group_index] = template_group
    save_new_data(project, data)
    return template_group.get("id")

def delete_template_config(project, config):
    validate_config(project, "templates")
    data             = get_project_config(project)
    template_deleted = False
    for idx, obj in enumerate(data["templates"]):
        if obj["id"] == config:
            data["templates"].pop(idx)
            template_deleted = True
            break
    if template_deleted:
        for template_group in data["template_groups"]:
            template_group_data = template_group["data"]
            for idx, data_item in enumerate(template_group_data):
                if data_item["type"] == "template" and data_item["id"] == config:
                    template_group_data.pop(idx)
                    break
    save_new_data(project, data)

def delete_template_group_config(project, config):
    delete_config(project, config, "template_groups")

####################### GRAPHS:

def get_graph(project, graph_id):
    validate_config(project, "graphs")
    data = get_project_config(project)
    for graph in data["graphs"]:
        if graph["id"] == graph_id:
            return graph

def check_graph(project, graph_id):
    validate_config(project, "graphs")
    data = get_project_config(project)
    for graph in data["graphs"]:
        if graph["id"] == graph_id:
            return True
    return False

def get_graphs(project):
    validate_config(project, "graphs")
    data = get_project_config(project)
    return data["graphs"]

def save_graph(project, form):
    validate_config(project, "graphs")
    data                 = get_project_config(project)
    graph_id             = form.get("id")
    existing_graph_index = next((index for index, g in enumerate(data["graphs"]) if g["id"] == graph_id), None)
    if existing_graph_index is None:
        form["id"] = generate_unique_id()
        data["graphs"].append(form)
    else:
        data["graphs"][existing_graph_index] = form
        for template in data["templates"]:
            for item in template["data"]:
                if item["type"] == "graph" and item["id"] == graph_id:
                    item["content"] = form["name"]
                    break
    save_new_data(project, data)
    return form.get("id")

def delete_graph(project, graph_id):
    validate_config(project, "graphs")
    data          = get_project_config(project)
    graph_deleted = False
    for idx, obj in enumerate(data["graphs"]):
        if obj["id"] == graph_id:
            data["graphs"].pop(idx)
            graph_deleted = True
            break
    if graph_deleted:
        for template in data["templates"]:
            template_data = template["data"]
            for idx, data_item in enumerate(template_data):
                if data_item["type"] == "graph" and data_item["id"] == graph_id:
                    template_data.pop(idx)
                    break
    save_new_data(project, data)

####################### OTHER:
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

def save_new_project(project_name):
    config     = get_json_config()
    project_id = generate_unique_id()
    config.append({"id": project_id, "name": project_name, "data": {}})
    save_new_config(config)
    return project_id

def delete_project(project):
    data = get_json_config()
    for idx, obj in enumerate(data):
        if obj["id"] == project:
            data.pop(idx)
            break
    save_new_config(data)

def generate_unique_id():
    return str(uuid.uuid4())

def read_from_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)