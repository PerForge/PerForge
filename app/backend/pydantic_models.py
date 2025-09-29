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

from pydantic import BaseModel, Field, model_validator, field_validator, EmailStr, ConfigDict
from typing import Optional, Literal
import logging


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
    project_id: Optional[int]
    name      : str
    url       : str
    org_id    : str
    token     : Optional[int]
    timeout   : int
    bucket    : str
    listener  : str
    tmz       : str = Field(default="UTC")
    test_title_tag_name: str = Field(default="testTitle")
    regex: Optional[str] = Field(default=None)
    bucket_regex_bool: bool = Field(default=False)
    custom_vars: list[str] = Field(default_factory=list)
    is_default: bool

    @model_validator(mode='before')
    def normalize_custom_vars(cls, values):
        if 'custom_vars' not in values:
            return values
        cv = values.get('custom_vars')
        if cv is None:
            values['custom_vars'] = []
            return values
        if isinstance(cv, str):
            parts = [p.strip() for p in cv.split(',') if p and p.strip()]
            values['custom_vars'] = parts
        elif isinstance(cv, list):
            values['custom_vars'] = [str(p).strip() for p in cv if str(p).strip()]
        else:
            values['custom_vars'] = []
        return values


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
    project_id         : Optional[int]
    name               : str
    server             : str
    org_id             : str
    token              : Optional[int]
    test_title         : str
    baseline_test_title: str
    is_default         : bool
    dashboards         : list[GrafanaObjectModel]


class AzureWikiModel(BaseModelWithStripping):
    id              : Optional[int]
    project_id      : Optional[int]
    name            : str
    token           : Optional[int]
    org_url         : str
    azure_project_id: str
    identifier      : str
    path_to_report  : str
    is_default      : bool


class AtlassianConfluenceModel(BaseModelWithStripping):
    id           : Optional[int]
    project_id   : Optional[int]
    name         : str
    email        : EmailStr
    token        : Optional[int]
    token_type   : str
    org_url      : str
    space_key    : str
    parent_id    : str
    is_default   : bool


class AtlassianJiraModel(BaseModelWithStripping):
    id              : Optional[int]
    project_id      : Optional[int]
    name            : str
    email           : EmailStr
    token           : Optional[int]
    token_type      : str
    org_url         : str
    jira_project_key: str
    epic_field      : Optional[str]
    epic_name       : Optional[str]
    is_default      : bool


class SmtpMailObjectModel(BaseModelWithStripping):
    id          : Optional[int]
    email       : str
    smtp_mail_id: Optional[int]


class SmtpMailModel(BaseModelWithStripping):
    id        : Optional[int]
    project_id: Optional[int]
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
    project_id    : Optional[int]
    name          : str
    ai_provider   : str
    azure_url     : Optional[str]
    api_version   : Optional[str]
    ai_text_model : str
    ai_image_model: str
    token         : Optional[int]
    temperature   : float
    conversation_memory: bool = Field(default=False)
    is_default    : bool


class GraphModel(BaseModelWithStripping):
    id         : Optional[int]
    project_id : Optional[int]
    name       : str
    type       : Literal['default', 'custom'] = Field(default='custom')
    grafana_id : Optional[int]
    dash_id    : Optional[int]
    view_panel : Optional[int]
    width      : int
    height     : int
    custom_vars: Optional[str]
    prompt_id  : Optional[int]

    @model_validator(mode='before')
    def migration(cls, values):
        if 'custom_vars' in values:
            values['custom_vars'] = values.pop('custom_vars')
        return values

    @model_validator(mode='after')
    def validate_by_type(self):
        if self.type == 'custom':
            missing = []
            if self.grafana_id is None:
                missing.append('grafana_id')
            if self.dash_id is None:
                missing.append('dash_id')
            if self.view_panel is None:
                missing.append('view_panel')
            if missing:
                raise ValueError(f"External graph requires fields: {', '.join(missing)}")
        return self


class TemplateObjectModel(BaseModelWithStripping):
    id         : Optional[int] = Field(default=None)
    type       : str
    content    : Optional[str]
    graph_id   : Optional[int]
    template_id: Optional[int] = Field(default=None)
    ai_graph_switch     : bool = Field(default=False)
    ai_to_graphs_switch : bool = Field(default=False)


class TemplateModel(BaseModelWithStripping):
    id                       : Optional[int]
    project_id               : Optional[int]
    name                     : str
    nfr                      : Optional[int]
    title                    : str
    ai_switch                : bool
    ai_aggregated_data_switch: bool = Field(default=False)
    nfrs_switch              : bool
    ml_switch                : bool = Field(default=False)
    template_prompt_id       : Optional[int]
    aggregated_prompt_id     : Optional[int]
    system_prompt_id         : Optional[int]
    data                     : list[TemplateObjectModel]

    @field_validator('ai_switch', 'ai_aggregated_data_switch', 'nfrs_switch', 'ml_switch', mode='before')
    def empty_str_to_false(cls, v):
        if v is None:
            return False
        return v


class TemplateGroupObjectModel(BaseModelWithStripping):
    id               : Optional[int] = Field(default=None)
    type             : str
    content          : Optional[str]
    template_id      : Optional[int]
    template_group_id: Optional[int] = Field(default=None)


class TemplateGroupModel(BaseModelWithStripping):
    id        : Optional[int]
    project_id: Optional[int]
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
    threshold: float
    nfr_id   : Optional[int] = Field(default=None)


class NFRsModel(BaseModelWithStripping):
    id  : Optional[int]
    project_id: Optional[int]
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
