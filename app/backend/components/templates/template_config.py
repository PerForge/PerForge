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
from app.backend.pydantic_models import TemplateModel, TemplateGroupModel


class TemplateConfig:

    def get_all_templates(project):
        data = pkg.get_project_config(project)
        return data["templates"]

    def get_template_config_values(project, template):
        data = pkg.get_json_values(project, "templates", template)
        return data

    def save_template_config(project, data):
        validated_data          = TemplateModel.model_validate(data).model_dump()
        config_data             = pkg.get_project_config(project)
        template_id             = validated_data.get("id")
        existing_template_index = next((index for index, t in enumerate(config_data["templates"]) if t["id"] == template_id), None)
        if existing_template_index is None:
            validated_data["id"] = pkg.generate_unique_id()
            config_data["templates"].append(validated_data)
        else:
            config_data["templates"][existing_template_index] = validated_data
            for template_group in config_data["template_groups"]:
                for item in template_group["data"]:
                    if item["type"] == "template" and item["id"] == template_id:
                        item["content"] = validated_data["name"]
                        break
        pkg.save_new_data(project, config_data)
        return validated_data.get("id")

    def delete_template_config(project, config):
        data             = pkg.get_project_config(project)
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
        pkg.save_new_data(project, data)

    def get_all_template_groups(project):
        data = pkg.get_project_config(project)
        return data["template_groups"]

    def get_template_group_config_values(project, template_group):
        data = pkg.get_json_values(project, "template_groups", template_group)
        return data

    def save_template_group_config(project, data):
        validated_data                = TemplateGroupModel.model_validate(data).model_dump()
        config_data                   = pkg.get_project_config(project)
        template_group_id             = validated_data.get("id")
        existing_template_group_index = next((index for index, tg in enumerate(config_data["template_groups"]) if tg["id"] == template_group_id), None)
        if existing_template_group_index is None:
            validated_data["id"] = pkg.generate_unique_id()
            config_data["template_groups"].append(validated_data)
        else:
            config_data["template_groups"][existing_template_group_index] = validated_data
        pkg.save_new_data(project, config_data)
        return validated_data.get("id")

    def delete_template_group_config(project, config):
        pkg.delete_config(project, config, "template_groups")