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

from flask_wtf          import FlaskForm
from wtforms            import StringField, IntegerField, FloatField, PasswordField, FieldList, SelectField, TextAreaField, FormField
from wtforms.validators import Email, DataRequired, NumberRange, Email


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class InfluxDBForm(FlaskForm):
    id         = StringField('Id')
    name       = StringField('Name', validators=[DataRequired()])
    url        = StringField('Url', validators=[DataRequired()])
    org_id     = StringField('Org', validators=[DataRequired()])
    token      = StringField('Token', validators=[DataRequired()])
    timeout    = StringField('Timeout', validators=[DataRequired()])
    bucket     = StringField('Bucket', validators=[DataRequired()])
    listener   = SelectField('Backend listener', choices=[('org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient', 'org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient'), ('mderevyankoaqa', 'mderevyankoaqa')], default='InfluxdbBackendListenerClient')
    tmz        = StringField('Timezone', default="UTC")
    is_default = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class DashboardForm(FlaskForm):
    id      = StringField('ID')
    content = StringField('Content', validators=[DataRequired()], default='')


class GrafanaForm(FlaskForm):
    id                  = StringField('Id')
    name                = StringField('Name', validators=[DataRequired()])
    server              = StringField('Server', validators=[DataRequired()])
    token               = StringField('Token', validators=[DataRequired()])
    org_id              = StringField('OrgId', validators=[DataRequired()])
    test_title          = StringField('Test title', validators=[DataRequired()], default="testTitle")
    app                 = StringField('App name', validators=[DataRequired()], default="app")
    baseline_test_title = StringField('Baseline test title', validators=[DataRequired()], default="baseline_testTitle")
    dashboards          = FieldList(FormField(DashboardForm), min_entries=1)
    is_default          = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class AzureWikiForm(FlaskForm):
    id             = StringField('Id')
    name           = StringField('Name', validators=[DataRequired()])
    token          = StringField('Personal Access Token', validators=[DataRequired()])
    org_url        = StringField('Wiki Organization Url', validators=[DataRequired()])
    project_id     = StringField('Wiki Project', validators=[DataRequired()])
    identifier     = StringField('Wiki Identifier', validators=[DataRequired()])
    path_to_report = StringField('Wiki Path To Report', validators=[DataRequired()])
    is_default     = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class GraphForm(FlaskForm):
    id         = StringField('Id')
    name       = StringField('Name', validators=[DataRequired()])
    view_panel = StringField('View panel id', validators=[DataRequired()])
    grafana_id = StringField('Grafana id', validators=[DataRequired()])
    dash_id    = SelectField('Dashboard Id', validators=[DataRequired()])
    width      = StringField('Panel width', validators=[DataRequired()])
    height     = StringField('Panel height', validators=[DataRequired()])
    prompt_id  = StringField('Prompt id', validators=[DataRequired()])


class AtlassianConfluenceForm(FlaskForm):
    id         = StringField('Id')
    name       = StringField('Name', validators=[DataRequired()])
    email      = StringField('Email', validators=[DataRequired()])
    token      = StringField('Token', validators=[DataRequired()])
    token_type = SelectField('Token type', choices=[('api_token', 'API Token'), ('personal_access_token', 'Personal Access Token')], default='api_token')
    org_url    = StringField('Organization url', validators=[DataRequired()])
    space_key  = StringField('Space key', validators=[DataRequired()])
    parent_id  = StringField('Parent id', validators=[DataRequired()])
    is_default = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class AtlassianJiraForm(FlaskForm):
    id         = StringField('Id')
    name       = StringField('Name', validators=[DataRequired()])
    email      = StringField('Email', validators=[DataRequired()])
    token      = StringField('Token', validators=[DataRequired()])
    token_type = SelectField('Token type', choices=[('api_token', 'API Token'), ('personal_access_token', 'Personal Access Token')], default='api_token')
    org_url    = StringField('Organization url', validators=[DataRequired()])
    project_id = StringField('Project id', validators=[DataRequired()])
    epic_field = StringField('Epic field')
    epic_name  = StringField('Epic name')
    is_default = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class SMTPMailForm(FlaskForm):
    id         = StringField('Id')
    name       = StringField('Name', validators=[DataRequired()])
    server     = StringField('Server', validators=[DataRequired()])
    port       = IntegerField('Port', validators=[DataRequired()])
    use_ssl    = SelectField('Use SSL', choices=[('True', 'True'), ('False', 'False')], default='True')
    use_tls    = SelectField('Use TLS', choices=[('True', 'True'), ('False', 'False')], default='False')
    username   = StringField('Username', validators=[DataRequired(), Email()])
    token      = StringField('Password', validators=[DataRequired()])
    recipients = FieldList(StringField('Recipient'), min_entries=1, validators=[DataRequired(), Email()])
    is_default = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class AISupportForm(FlaskForm):
    id             = StringField('Id')
    name           = StringField('Name', validators=[DataRequired()])
    ai_provider    = SelectField('AI Provider', choices=[('openai', 'OpenAI'), ('azure_openai', 'Azure OpenAI'), ('gemini', 'Gemini')], default='openai')
    azure_url      = StringField('Azure url')
    api_version    = StringField('Api version')
    ai_text_model  = StringField('AI Text model', validators=[DataRequired()])
    ai_image_model = StringField('AI Image model', validators=[DataRequired()])
    token          = StringField('Token', validators=[DataRequired()])
    temperature    = FloatField('Temperature', validators=[DataRequired(), NumberRange(min=0.1, max=1.0)], default=0.2)
    is_default     = SelectField('Default', choices=[('true', 'True'), ('false', 'False')], default='false')


class PromptForm(FlaskForm):
    id     = StringField('Id')
    name   = StringField('Name', validators=[DataRequired()])
    type   = StringField('Type', validators=[DataRequired()])
    place  = SelectField('Place', choices=[('graph', 'Graph'), ('aggregated_data', 'Aggregated Data'), ('template', 'Template'), ('template_group', 'Template Group'), ('system', 'System')])
    prompt = TextAreaField('Prompt', validators=[DataRequired()])


class SecretForm(FlaskForm):
    id    = StringField('Id')
    type  = StringField('Type')
    key   = StringField('Key', validators=[DataRequired()])
    value = StringField('Value', validators=[DataRequired()])