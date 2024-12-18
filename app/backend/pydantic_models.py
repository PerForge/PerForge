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

from pydantic import BaseModel, Field, model_validator
from typing   import Optional


# Cleaning functions
def ensure_leading_slash(url: str) -> str:
    return '/' + url if not url.startswith('/') else url

class BaseModelWithStripping(BaseModel):
    @model_validator(mode='before')
    def strip_whitespace_and_trailing_slash(cls, values):
        for field_name, value in values.items():
            if isinstance(value, str):
                value = value.strip()
                if field_name in {'url', 'org_url', 'server', 'azure_url'}:
                    value = value.rstrip('/')
                values[field_name] = value
        return values

class InfluxdbModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    url       : str
    org_id    : str
    token     : Optional[int]
    timeout   : int
    bucket    : str
    listener  : str
    tmz       : str = Field(default="UTC")
    is_default: bool


class GrafanaObjectModel(BaseModelWithStripping):
    id        : Optional[int]
    content   : str
    grafana_id: Optional[int]

    @model_validator(mode='before')
    def validate_content(cls, values):
        if 'content' in values:
            values['content'] = ensure_leading_slash(values['content'])
        return values

class GrafanaModel(BaseModelWithStripping):
    id                 : Optional[int]
    name               : str
    server             : str
    org_id             : str
    token              : Optional[int]
    test_title         : str
    app                : str
    baseline_test_title: str
    is_default         : bool
    dashboards         : list[GrafanaObjectModel]


class AzureWikiModel(BaseModelWithStripping):
    id            : Optional[int]
    name          : str
    token         : Optional[int]
    org_url       : str
    project_id    : str
    identifier    : str
    path_to_report: str
    is_default    : bool


class AtlassianConfluenceModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    email     : str
    token     : Optional[int]
    token_type: str
    org_url   : str
    space_key : str
    parent_id : str
    is_default: bool


class AtlassianJiraModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    email     : str
    token     : Optional[int]
    token_type: str
    org_url   : str
    project_id: str
    epic_field: Optional[str]
    epic_name : Optional[str]
    is_default: bool


class SmtpMailObjectModel(BaseModelWithStripping):
    id          : Optional[int]
    email       : str
    smtp_mail_id: Optional[int]


class SmtpMailModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    server    : str
    port      : int
    use_ssl   : bool
    use_tls   : bool
    username  : str
    token     : Optional[int]
    is_default: bool
    recipients: list[SmtpMailObjectModel]


class AISupportModel(BaseModelWithStripping):
    id            : Optional[int]
    name          : str
    ai_provider   : str
    azure_url     : Optional[str]
    api_version   : Optional[str]
    ai_text_model : str
    ai_image_model: str
    token         : Optional[int]
    temperature   : float
    is_default    : bool


class GraphModel(BaseModelWithStripping):
    id         : Optional[int]
    name       : str
    grafana_id : int
    dash_id    : int
    view_panel : int
    width      : int
    height     : int
    custom_vars: Optional[str]
    prompt_id  : Optional[int]

    @model_validator(mode='before')
    def migration(cls, values):
        if 'custom_vars' in values:
            values['custom_vars'] = values.pop('custom_vars')
        return values


class TemplateObjectModel(BaseModelWithStripping):
    id         : Optional[int] = Field(default=None)
    type       : str
    content    : Optional[str]
    graph_id   : Optional[int]
    template_id: Optional[int] = Field(default=None)


class TemplateModel(BaseModelWithStripping):
    id                       : Optional[int]
    name                     : str
    nfr                      : Optional[int]
    title                    : str
    ai_switch                : bool
    ai_aggregated_data_switch: bool = Field(default=False)
    ai_graph_switch          : bool
    ai_to_graphs_switch      : bool
    nfrs_switch              : bool
    template_prompt_id       : Optional[int]
    aggregated_prompt_id     : Optional[int]
    system_prompt_id         : Optional[int]
    data                     : list[TemplateObjectModel]


class TemplateGroupObjectModel(BaseModelWithStripping):
    id               : Optional[int] = Field(default=None)
    type             : str
    content          : Optional[str]
    template_id      : Optional[int]
    template_group_id: Optional[int] = Field(default=None)


class TemplateGroupModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    title     : str
    ai_summary: bool
    prompt_id : Optional[int]
    data      : list[TemplateGroupObjectModel]


class NFRObjectModel(BaseModelWithStripping):
    id       : Optional[int] = Field(default=None)
    regex    : bool
    scope    : str
    metric   : str
    operation: str
    threshold: int
    weight   : Optional[int]
    nfr_id   : Optional[int] = Field(default=None)


class NFRsModel(BaseModelWithStripping):
    id  : Optional[int]
    name: str
    rows: list[NFRObjectModel]


class PromptModel(BaseModelWithStripping):
    id        : Optional[int]
    name      : str
    type      : str
    place     : str
    prompt    : str
    project_id: Optional[int]


class SecretsModel(BaseModelWithStripping):
    id        : Optional[int]
    key       : str
    type      : str
    value     : str
    project_id: Optional[int]


class UsersModel(BaseModelWithStripping):
    id      : Optional[int]
    user    : str
    password: str
    is_admin: bool


class ProjectModel(BaseModelWithStripping):
    id  : Optional[int]
    name: str
