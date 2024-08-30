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

from pydantic import BaseModel, Field, root_validator
from typing   import List


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


class GrafanaObjectModel(BaseModel):
    id     : str
    content: str


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


class AzureWikiModel(BaseModel):
    id            : str
    name          : str
    token         : str
    org_url       : str
    project_id    : str
    identifier    : str
    path_to_report: str
    is_default    : str


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
    id        : str
    name      : str
    grafana_id: str
    dash_id   : str
    view_panel: str
    width     : str
    height    : str
    prompt_id : str


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