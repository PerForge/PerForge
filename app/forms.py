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

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, PasswordField, FieldList, SelectField, TextAreaField, FormField, BooleanField
from wtforms.validators import Email, DataRequired, NumberRange


class LoginForm(FlaskForm):
    user = StringField('User', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    user = StringField('User', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class InfluxDBForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    url = StringField('Url', validators=[DataRequired()])
    org_id = StringField('Org', validators=[DataRequired()])
    token = StringField('Token', validators=[DataRequired()])
    timeout = StringField('Timeout', validators=[DataRequired()], default="60000")
    bucket = StringField('Bucket', validators=[DataRequired()])
    listener = SelectField(
        'Backend listener',
        choices=[
            ('org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient', 'org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient'),
            ('sitespeed_influxdb_v2', 'sitespeed_influxdb_v2'),
            ('org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient_v1.8', 'org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient_v1.8'),
            ('sitespeed_influxdb_v1.8', 'sitespeed_influxdb_v1.8'),
        ],
        default='InfluxdbBackendListenerClient'
    )
    tmz = StringField('Timezone', default="UTC")
    test_title_tag_name = StringField('Test Title Tag Name', default="testTitle")
    regex = StringField('Transaction regex')
    bucket_regex_bool = BooleanField('Bucket regex')
    custom_vars= FieldList(StringField('Custom vars'), min_entries=0)
    is_default = BooleanField("Is default")


class DashboardForm(FlaskForm):
    id = StringField('ID')
    content = StringField('Content', validators=[DataRequired()], default='')


class GrafanaForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    server = StringField('Server', validators=[DataRequired()])
    token = StringField('Token', validators=[DataRequired()])
    org_id = StringField('OrgId', validators=[DataRequired()])
    test_title = StringField('Test title', validators=[DataRequired()], default="testTitle")
    baseline_test_title = StringField('Baseline test title', validators=[DataRequired()], default="baseline_testTitle")
    dashboards = FieldList(FormField(DashboardForm), min_entries=1)
    is_default = BooleanField("Is default")


class AzureWikiForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    token = StringField('Personal Access Token', validators=[DataRequired()])
    org_url = StringField('Wiki Organization Url', validators=[DataRequired()])
    azure_project_id = StringField('Azure DevOps Project Name or ID', validators=[DataRequired()])
    identifier = StringField('Wiki Identifier', validators=[DataRequired()])
    path_to_report = StringField('Wiki Path To Report', validators=[DataRequired()])
    is_default = BooleanField("Is default")


class GraphForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    view_panel = StringField('View panel id', validators=[DataRequired()])
    grafana_id = StringField('Grafana id', validators=[DataRequired()])
    dash_id = StringField('Dashboard Id', validators=[DataRequired()])
    width = StringField('Panel width', validators=[DataRequired()])
    height = StringField('Panel height', validators=[DataRequired()])
    custom_vars= StringField('Custom vars', default="")
    prompt_id = StringField('Prompt id')


class AtlassianConfluenceForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    token = StringField('Token', validators=[DataRequired()])
    token_type = SelectField('Token type', choices=[('api_token', 'API Token'), ('personal_access_token', 'Personal Access Token')], default='api_token')
    org_url = StringField('Organization url', validators=[DataRequired()])
    space_key = StringField('Space key', validators=[DataRequired()])
    parent_id = StringField('Parent id', validators=[DataRequired()])
    is_default = BooleanField("Is default")


class AtlassianJiraForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    token = StringField('Token', validators=[DataRequired()])
    token_type = SelectField('Token type', choices=[('api_token', 'API Token'), ('personal_access_token', 'Personal Access Token')], default='api_token')
    org_url = StringField('Organization url', validators=[DataRequired()])
    jira_project_key = StringField('Jira Project Key', validators=[DataRequired()])
    epic_field = StringField('Epic field')
    epic_name = StringField('Epic name')
    is_default = BooleanField("Is default")


class SMTPMailForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    server = StringField('Server', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired()])
    use_ssl = BooleanField('Use SSL')
    use_tls = BooleanField('Use TLS')
    username = StringField('Username', validators=[DataRequired(), Email()])
    token = StringField('Password', validators=[DataRequired()])
    recipients = FieldList(StringField('Recipient'), min_entries=1, validators=[DataRequired(), Email()])
    is_default = BooleanField("Is default")


class AISupportForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    ai_provider = SelectField(
        'AI Provider',
        choices=[
            ('openai', 'OpenAI'),
            ('azure_openai', 'Azure OpenAI'),
            ('gemini', 'Gemini'),
            ('anthropic', 'Anthropic'),
        ],
        default='openai'
    )
    azure_url = StringField('Azure url')
    api_version = StringField('Api version')
    ai_text_model = StringField('AI Text model', validators=[DataRequired()])
    ai_image_model = StringField('AI Image model', validators=[DataRequired()])
    token = StringField('Token', validators=[DataRequired()])
    temperature = FloatField('Temperature', validators=[DataRequired(), NumberRange(min=0.1, max=1.0)], default=0.2)
    conversation_memory = BooleanField("Conversation Memory")
    is_default = BooleanField("Is default")


class PromptForm(FlaskForm):
    id = StringField('Id')
    name = StringField('Name', validators=[DataRequired()])
    type = StringField('Type', validators=[DataRequired()])
    place = SelectField('Place', choices=[('graph', 'Graph'), ('aggregated_data', 'Aggregated Data'), ('template', 'Template'), ('template_group', 'Template Group'), ('system', 'System')])
    prompt = TextAreaField('Prompt', validators=[DataRequired()])
    project_id = SelectField('Scope', choices=[('all', 'All Projects'), ('project', 'Current Project Only')])


class SecretForm(FlaskForm):
    id = StringField('Id')
    type = StringField('Type')
    key = StringField('Key', validators=[DataRequired()])
    value = StringField('Value', validators=[DataRequired()])
    project_id = SelectField('Scope', choices=[('all', 'All Projects'), ('project', 'Current Project Only')])
