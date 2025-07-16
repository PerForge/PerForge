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

import traceback
import logging

from app                                                                   import app
from app.backend.components.projects.projects_db                           import DBProjects
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db         import DBInfluxdb
from app.backend.integrations.grafana.grafana_db                           import DBGrafana
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail
from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.errors                                                    import ErrorMessages
from app.forms                                                             import InfluxDBForm, GrafanaForm, AzureWikiForm, AtlassianConfluenceForm, AtlassianJiraForm, SMTPMailForm, AISupportForm
from flask                                                                 import render_template, request, url_for, redirect, flash



@app.route('/integrations')
def integrations():
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)

        influxdb_configs             = DBInfluxdb.get_configs(project_id=project_id)
        grafana_configs              = DBGrafana.get_configs(project_id=project_id)
        smtp_mail_configs            = DBSMTPMail.get_configs(project_id=project_id)
        atlassian_confluence_configs = DBAtlassianConfluence.get_configs(project_id=project_id)
        atlassian_jira_configs       = DBAtlassianJira.get_configs(project_id=project_id)
        azure_configs                = DBAzureWiki.get_configs(project_id=project_id)
        ai_support_configs           = DBAISupport.get_configs(project_id=project_id)
        return render_template('home/integrations.html',
                               influxdb_configs             = influxdb_configs,
                               grafana_configs              = grafana_configs,
                               smtp_mail_configs            = smtp_mail_configs,
                               atlassian_confluence_configs = atlassian_confluence_configs,
                               atlassian_jira_configs       = atlassian_jira_configs,
                               azure_configs                = azure_configs,
                               ai_support_configs           = ai_support_configs
                               )
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00009.value, "error")
        return render_template('home/integrations.html')

@app.route('/influxdb', methods=['GET'])
def add_influxdb():
    try:
        form            = InfluxDBForm(request.form)
        project_id      = request.cookies.get('project')
        project_data    = DBProjects.get_config_by_id(id=project_id)
        influxdb_config = request.args.get('influxdb_config')
        clone           = request.args.get('clone')
        secret_configs  = DBSecrets.get_configs(project_id=project_id)
        if influxdb_config is not None:
            output = DBInfluxdb.get_config_by_id(project_id=project_id, id=influxdb_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                influxdb_config = None
            form   = InfluxDBForm(data=output)
        return render_template('integrations/influxdb.html', form=form, influxdb_config=influxdb_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00028.value, "error")
        return redirect(url_for('integrations'))

@app.route('/grafana', methods=['GET'])
def add_grafana():
    try:
        form           = GrafanaForm(request.form)
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        grafana_config = request.args.get('grafana_config')
        clone          = request.args.get('clone')
        secret_configs = DBSecrets.get_configs(project_id=project_id)
        if grafana_config is not None:
            output = DBGrafana.get_config_by_id(project_id=project_id, id=grafana_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                grafana_config = None
            form   = GrafanaForm(data=output)
        return render_template('integrations/grafana.html', form=form, grafana_config=grafana_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00033.value, "error")
        return redirect(url_for('integrations'))

@app.route('/smtp-mail', methods=['GET'])
def add_smtp_mail():
    try:
        form             = SMTPMailForm(request.form)
        project_id       = request.cookies.get('project')
        project_data     = DBProjects.get_config_by_id(id=project_id)
        smtp_mail_config = request.args.get('smtp_mail_config')
        clone            = request.args.get('clone')
        secret_configs   = DBSecrets.get_configs(project_id=project_id)
        if smtp_mail_config is not None:
            output = DBSMTPMail.get_config_by_id(project_id=project_id, id=smtp_mail_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                smtp_mail_config = None
            form   = SMTPMailForm(data=output)
        return render_template('integrations/smtp-mail.html', form=form, smtp_mail_config=smtp_mail_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00045.value, "error")
        return redirect(url_for('integrations'))

@app.route('/atlassian-confluence', methods=['GET'])
def add_atlassian_confluence():
    try:
        form                        = AtlassianConfluenceForm(request.form)
        project_id                  = request.cookies.get('project')
        project_data                = DBProjects.get_config_by_id(id=project_id)
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        clone                       = request.args.get('clone')
        secret_configs              = DBSecrets.get_configs(project_id=project_id)
        if atlassian_confluence_config is not None:
            output = DBAtlassianConfluence.get_config_by_id(project_id=project_id, id=atlassian_confluence_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                atlassian_confluence_config = None
            form   = AtlassianConfluenceForm(data=output)
        return render_template('integrations/atlassian-confluence.html', form=form, atlassian_confluence_config=atlassian_confluence_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00039.value, "error")
        return redirect(url_for('integrations'))

@app.route('/atlassian-jira', methods=['GET'])
def add_atlassian_jira():
    try:
        form                  = AtlassianJiraForm(request.form)
        project_id            = request.cookies.get('project')
        project_data          = DBProjects.get_config_by_id(id=project_id)
        atlassian_jira_config = request.args.get('atlassian_jira_config')
        clone                 = request.args.get('clone')
        secret_configs        = DBSecrets.get_configs(project_id=project_id)
        if atlassian_jira_config is not None:
            output = DBAtlassianJira.get_config_by_id(project_id=project_id, id=atlassian_jira_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                atlassian_jira_config = None
            form   = AtlassianJiraForm(data=output)
        return render_template('integrations/atlassian-jira.html', form=form, atlassian_jira_config=atlassian_jira_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00042.value, "error")
        return redirect(url_for('integrations'))

@app.route('/azure', methods=['GET'])
def add_azure():
    try:
        form           = AzureWikiForm(request.form)
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        azure_config   = request.args.get('azure_config')
        clone          = request.args.get('clone')
        secret_configs = DBSecrets.get_configs(project_id=project_id)
        if azure_config is not None:
            output = DBAzureWiki.get_config_by_id(project_id=project_id, id=azure_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                azure_config = None
            form   = AzureWikiForm(data=output)
        return render_template('integrations/azure.html', form=form, azure_config=azure_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00036.value, "error")
        return redirect(url_for('integrations'))

@app.route('/ai-support', methods=['GET'])
def add_ai_support():
    try:
        form              = AISupportForm(request.form)
        project_id        = request.cookies.get('project')
        project_data      = DBProjects.get_config_by_id(id=project_id)
        ai_support_config = request.args.get('ai_support_config')
        clone             = request.args.get('clone')
        secret_configs    = DBSecrets.get_configs(project_id=project_id)
        if ai_support_config is not None:
            output = DBAISupport.get_config_by_id(project_id=project_id, id=ai_support_config)
            if clone:
                output['name'] = f"{output.get('name', '')} COPY"
                ai_support_config = None
            form   = AISupportForm(data=output)
        return render_template('integrations/ai-support.html', form=form, ai_support_config=ai_support_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00048.value, "error")
        return redirect(url_for('integrations'))
