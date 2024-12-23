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
from app.backend.pydantic_models import AISupportModel
from werkzeug.datastructures     import MultiDict


class AISupportConfig:

    def get_ai_support_config_values(project, ai_support_config, is_internal = False):
        data = pkg.get_integration_values(project, "ai_support", ai_support_config, is_internal)
        return MultiDict(data)

    def save_ai_support_config(project, data):
        validated_data = AISupportModel.model_validate(data).model_dump()
        id             = pkg.save_integration(project, validated_data, "ai_support")
        return id

    def get_default_ai_support_config_id(project):
        id = pkg.get_default_integration(project, "ai_support")
        return id

    def delete_ai_support_config(project, config):
        pkg.delete_config(project, config, "integrations", "ai_support")