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

from app.backend.pydantic_models import NFRsModel
from app.backend import pkg


class NFRConfig:

    def get_nfr_values_by_id(project, id):
        result = []
        data = pkg.get_project_config(project)
        for nfr in data["nfrs"]:
            if nfr["id"] == id:
                result = nfr
        return result

    def get_all_nfrs(project):
        data = pkg.get_project_config(project)
        return data["nfrs"]

    def save_nfr_config(project, form):
        validated_form     = NFRsModel.model_validate(form).model_dump()
        config_data        = pkg.get_project_config(project)
        nfr_id             = validated_form.get("id")
        existing_nfr_index = next((index for index, n in enumerate(config_data["nfrs"]) if n["id"] == nfr_id), None)
        if existing_nfr_index is None:
            validated_form["id"] = pkg.generate_unique_id()
            config_data["nfrs"].append(validated_form)
        else:
            config_data["nfrs"][existing_nfr_index] = validated_form
        pkg.save_new_data(project, config_data)
        return validated_form.get("id")

    def delete_nfr_config(project, id):
        data        = pkg.get_project_config(project)
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
        pkg.save_new_data(project, data)