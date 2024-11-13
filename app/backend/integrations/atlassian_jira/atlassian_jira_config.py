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
from werkzeug.datastructures     import MultiDict

class AtlassianJiraConfig:

    def get_atlassian_jira_config_values(project, atlassian_jira_config, is_internal = False):
        data           = pkg.get_integration_values(project, "atlassian_jira", atlassian_jira_config, is_internal)
        return MultiDict(data)

    def get_default_atlassian_jira_config_id(project):
        id = pkg.get_default_integration(project, "atlassian_jira")
        return id