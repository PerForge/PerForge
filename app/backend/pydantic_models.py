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
from typing   import List

# Cleaning functions
def remove_trailing_slash(url: str) -> str:
    url = remove_all_spaces(url)
    return url[:-1] if url.endswith('/') else url

def ensure_leading_slash(url: str) -> str:
    url = remove_all_spaces(url)
    return '/' + url if not url.startswith('/') else url

def remove_all_spaces(url: str) -> str:
    return url.replace(' ', '')

class InfluxdbModel(BaseModel):
    id        : str
    name      : str
    url       : str
    org_id    : str
    token     : str
    timeout   : str
    bucket    : str
    listener  : str
    tmz       : str = Field(default="UTC")
    is_default: str

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'url' in values:
            values['url'] = remove_trailing_slash(values['url'])
        return values

class GrafanaObjectModel(BaseModel):
    id     : str
    content: str

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'content' in values:
            values['content'] = ensure_leading_slash(values['content'])
        return values

class GrafanaModel(BaseModel):
    id                 : str
    name               : str
    server             : str
    org_id             : str
    token              : str
    test_title         : str
    app                : str
    baseline_test_title: str
    is_default         : str
    dashboards         : list[GrafanaObjectModel]

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'server' in values:
            values['server'] = remove_trailing_slash(values['server'])
        return values

class AzureWikiModel(BaseModel):
    id            : str
    name          : str
    token         : str
    org_url       : str
    project_id    : str
    identifier    : str
    path_to_report: str
    is_default    : str

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'org_url' in values:
            values['org_url'] = remove_trailing_slash(values['org_url'])
        return values

class AtlassianConfluenceModel(BaseModel):
    id        : str
    name      : str
    email     : str
    token     : str
    token_type: str
    org_url   : str
    space_key : str
    parent_id : str
    is_default: str

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'org_url' in values:
            values['org_url'] = remove_trailing_slash(values['org_url'])
        return values

class AtlassianJiraModel(BaseModel):
    id        : str
    name      : str
    email     : str
    token     : str
    token_type: str
    org_url   : str
    project_id: str
    epic_field: str
    epic_name : str
    is_default: str

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'org_url' in values:
            values['org_url'] = remove_trailing_slash(values['org_url'])
        return values


class SmtpMailModel(BaseModel):
    id        : str
    name      : str
    server    : str
    port      : int
    use_ssl   : str
    use_tls   : str
    username  : str
    token     : str
    is_default: str
    recipients: list

    @model_validator(mode='before')
    def validate_url(cls, values):
        if 'server' in values:
            values['server'] = remove_trailing_slash(values['server'])
        return values

class AISupportModel(BaseModel):
    id            : str
    name          : str
    ai_provider   : str
    azure_url     : str
    api_version   : str
    ai_text_model : str
    ai_image_model: str
    token         : str
    temperature   : float
    is_default    : str


class GraphModel(BaseModel):
    id         : str
    name       : str
    grafana_id : str
    dash_id    : str
    view_panel : str
    width      : str
    height     : str
    custom_vars: str = Field(default="") ## This field should be added to all new fields
    prompt_id  : str = Field(default="") ## This field should be added to all new fields

    @model_validator(mode='before')
    def migration(cls, values):
        if 'custom_vars' in values:
            values['custom_vars'] = values.pop('custom_vars')
        return values


class TemplateObjectModel(BaseModel):
    id     : str
    type   : str
    content: str


class TemplateModel(BaseModel):
    id                       : str
    name                     : str
    nfr                      : str
    title                    : str
    ai_switch                : bool
    ai_aggregated_data_switch: bool = Field(default=False)
    ai_graph_switch          : bool
    ai_to_graphs_switch      : bool
    nfrs_switch              : bool
    template_prompt_id       : str
    aggregated_prompt_id     : str
    system_prompt_id         : str = Field(default="system_message") ## This field should be added to all new fields
    data                     : list[TemplateObjectModel]

    # @root_validator(pre=True)
    # def migration(cls, values):
    #     if 'aggregated_data_prompt_id' in values:
    #         values['aggregated_prompt_id'] = values.pop('aggregated_data_prompt_id')
    #     return values


class NFRObjectModel(BaseModel):
    regex    : bool
    scope    : str
    metric   : str
    operation: str
    threshold: int
    weight   : str


class NFRsModel(BaseModel):
    id  : str
    name: str
    rows: list[NFRObjectModel]


class PromptModel(BaseModel):
    id    : str
    type  : str
    name  : str
    place : str
    prompt: str


class TemplateGroupModel(BaseModel):
    id        : str
    name      : str
    title     : str
    ai_summary: bool
    prompt_id : str
    data      : list[TemplateObjectModel]


class IntegrationsModel(BaseModel):
    influxdb            : List[InfluxdbModel] = Field(default_factory=list)
    grafana             : List[GrafanaModel] = Field(default_factory=list)
    azure               : List[AzureWikiModel] = Field(default_factory=list)
    atlassian_confluence: List[AtlassianConfluenceModel] = Field(default_factory=list)
    atlassian_jira      : List[AtlassianJiraModel] = Field(default_factory=list)
    smtp_mail           : List[SmtpMailModel] = Field(default_factory=list)
    ai_support          : List[AISupportModel] = Field(default_factory=list)


class ProjectObjectModel(BaseModel):
    integrations   : IntegrationsModel = Field(default_factory=IntegrationsModel)
    graphs         : List[GraphModel] = Field(default_factory=list)
    templates      : List[TemplateModel] = Field(default_factory=list)
    nfrs           : List[NFRsModel] = Field(default_factory=list)
    prompts        : List[PromptModel] = Field(default_factory=list)
    template_groups: List[TemplateGroupModel] = Field(default_factory=list)

class ProjectModel(BaseModel):
    id  : str
    name: str
    data: ProjectObjectModel = Field(default_factory=ProjectObjectModel)