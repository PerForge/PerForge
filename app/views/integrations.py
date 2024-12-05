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
from app.backend.integrations.grafana.grafana_db                           import DBGrafana, DBGrafanaDashboards
from app.backend.integrations.azure_wiki.azure_wiki_db                     import DBAzureWiki
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db             import DBAtlassianJira
from app.backend.integrations.smtp_mail.smtp_mail_db                       import DBSMTPMail, DBSMTPMailRecipient
from app.backend.integrations.ai_support.ai_support_db                     import DBAISupport
from app.backend.components.secrets.secrets_db                             import DBSecrets
from app.backend.errors                                                    import ErrorMessages
from app.forms                                                             import InfluxDBForm, GrafanaForm, AzureWikiForm, AtlassianConfluenceForm, AtlassianJiraForm, SMTPMailForm, AISupportForm
from flask                                                                 import render_template, request, url_for, redirect, flash


@app.route('/integrations')
def integrations():
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)

        influxdb_configs             = DBInfluxdb.get_configs(schema_name=project_data['name'])
        grafana_configs              = DBGrafana.get_configs(schema_name=project_data['name'])
        smtp_mail_configs            = DBSMTPMail.get_configs(schema_name=project_data['name'])
        atlassian_confluence_configs = DBAtlassianConfluence.get_configs(schema_name=project_data['name'])
        atlassian_jira_configs       = DBAtlassianJira.get_configs(schema_name=project_data['name'])
        azure_configs                = DBAzureWiki.get_configs(schema_name=project_data['name'])
        ai_support_configs           = DBAISupport.get_configs(schema_name=project_data['name'])
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

@app.route('/influxdb', methods=['GET', 'POST'])
def add_influxdb():
    try:
        form            = InfluxDBForm(request.form)
        project_id      = request.cookies.get('project')
        project_data    = DBProjects.get_config_by_id(id=project_id)
        influxdb_config = request.args.get('influxdb_config')
        secret_configs  = DBSecrets.get_configs(id=project_id)
        if influxdb_config is not None:
            output = DBInfluxdb.get_config_by_id(schema_name=project_data['name'], id=influxdb_config)
            form   = InfluxDBForm(data=output)
        if form.validate_on_submit():
            try:
                influxdb_data = form.data
                if influxdb_data['id']:
                    DBInfluxdb.update(
                        schema_name = project_data['name'],
                        data        = influxdb_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBInfluxdb.save(
                        schema_name = project_data['name'],
                        data        = influxdb_data
                    )
                    flash("Integration added.", "info")
                return redirect(url_for('integrations',tab='influxdb'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00028.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/influxdb.html', form=form, influxdb_config=influxdb_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00030.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/influxdb', methods=['GET'])
def delete_influxdb():
    try:
        influxdb_config = request.args.get('influxdb_config')
        project_id      = request.cookies.get('project')
        project_data    = DBProjects.get_config_by_id(id=project_id)
        if influxdb_config is not None:
            DBInfluxdb.delete(schema_name=project_data['name'], id=influxdb_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00029.value, "error")
    return redirect(url_for('integrations',tab='influxdb'))

@app.route('/grafana', methods=['GET', 'POST'])
def add_grafana():
    try:
        form           = GrafanaForm(request.form)
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        grafana_config = request.args.get('grafana_config')
        secret_configs = DBSecrets.get_configs(id=project_id)
        if grafana_config is not None:
            output = DBGrafana.get_config_by_id(schema_name=project_data['name'], id=grafana_config)
            form   = GrafanaForm(data=output)
        if request.method == "POST":
            try:
                grafana_data = request.get_json()
                if grafana_data["id"]:
                    DBGrafana.update(
                        schema_name = project_data['name'],
                        data        = grafana_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBGrafana.save(
                        schema_name = project_data['name'],
                        data        = grafana_data
                    )
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00031.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/grafana.html', form=form, grafana_config=grafana_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00033.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/grafana', methods=['GET'])
def delete_grafana_config():
    try:
        grafana_config = request.args.get('grafana_config')
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        if grafana_config is not None:
            DBGrafana.delete(schema_name=project_data['name'], id=grafana_config)
            flash("Integration deleted.", "info")
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00032.value, "error")
    return redirect(url_for('integrations',tab='grafana'))

@app.route('/smtp-mail', methods=['GET', 'POST'])
def add_smtp_mail():
    try:
        form             = SMTPMailForm(request.form)
        project_id       = request.cookies.get('project')
        project_data     = DBProjects.get_config_by_id(id=project_id)
        smtp_mail_config = request.args.get('smtp_mail_config')
        secret_configs   = DBSecrets.get_configs(id=project_id)
        if smtp_mail_config is not None:
            output = DBSMTPMail.get_config_by_id(schema_name=project_data['name'], id=smtp_mail_config)
            form   = SMTPMailForm(data=output)
        if request.method == 'POST':
            try:
                smtp_mail_data = request.get_json()
                if smtp_mail_data["id"]:
                    DBSMTPMail.update(
                        schema_name = project_data['name'],
                        data        = smtp_mail_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBSMTPMail.save(
                        schema_name = project_data['name'],
                        data        = smtp_mail_data
                    )
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00043.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/smtp-mail.html', form=form, smtp_mail_config=smtp_mail_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00045.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/smtp-mail', methods=['GET'])
def delete_smtp_mail_config():
    try:
        smtp_mail_config = request.args.get('smtp_mail_config')
        project_id       = request.cookies.get('project')
        project_data     = DBProjects.get_config_by_id(id=project_id)
        if smtp_mail_config is not None:
            DBSMTPMail.delete(schema_name=project_data['name'], id=smtp_mail_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00044.value, "error")
    return redirect(url_for('integrations',tab='smtp-mail'))

@app.route('/atlassian-confluence', methods=['GET', 'POST'])
def add_atlassian_confluence():
    try:
        form                        = AtlassianConfluenceForm(request.form)
        project_id                  = request.cookies.get('project')
        project_data                = DBProjects.get_config_by_id(id=project_id)
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        secret_configs              = DBSecrets.get_configs(id=project_id)
        if atlassian_confluence_config is not None:
            output = DBAtlassianConfluence.get_config_by_id(schema_name=project_data['name'], id=atlassian_confluence_config)
            form   = AtlassianConfluenceForm(data=output)
        if form.validate_on_submit():
            try:
                atlassian_confluence_data = form.data

                for key, value in atlassian_confluence_data.items():
                    if value == '':
                        atlassian_confluence_data[key] = None

                if atlassian_confluence_data['id']:
                    DBAtlassianConfluence.update(
                        schema_name = project_data['name'],
                        data        = atlassian_confluence_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBAtlassianConfluence.save(
                        schema_name = project_data['name'],
                        data        = atlassian_confluence_data
                    )
                    flash("Integration added.", "info")
                return redirect(url_for('integrations',tab='confluence'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00037.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/atlassian-confluence.html', form=form, atlassian_confluence_config=atlassian_confluence_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00039.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/atlassian-confluence', methods=['GET'])
def delete_atlassian_confluence():
    try:
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        project_id                  = request.cookies.get('project')
        project_data                = DBProjects.get_config_by_id(id=project_id)
        if atlassian_confluence_config is not None:
            DBAtlassianConfluence.delete(schema_name=project_data['name'], id=atlassian_confluence_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00038.value, "error")
    return redirect(url_for('integrations',tab='confluence'))

@app.route('/atlassian-jira', methods=['GET', 'POST'])
def add_atlassian_jira():
    try:
        form                  = AtlassianJiraForm(request.form)
        project_id            = request.cookies.get('project')
        project_data          = DBProjects.get_config_by_id(id=project_id)
        atlassian_jira_config = request.args.get('atlassian_jira_config')
        secret_configs        = DBSecrets.get_configs(id=project_id)
        if atlassian_jira_config is not None:
            output = DBAtlassianJira.get_config_by_id(schema_name=project_data['name'], id=atlassian_jira_config)
            form   = AtlassianJiraForm(data=output)
        if form.validate_on_submit():
            try:
                atlassian_jira_data = form.data

                for key, value in atlassian_jira_data.items():
                    if value == '':
                        atlassian_jira_data[key] = None

                if atlassian_jira_data['id']:
                    DBAtlassianJira.update(
                        schema_name = project_data['name'],
                        data        = atlassian_jira_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBAtlassianJira.save(
                        schema_name = project_data['name'],
                        data        = atlassian_jira_data
                    )
                    flash("Integration added.", "info")
                return redirect(url_for('integrations',tab='jira'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00040.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/atlassian-jira.html', form=form, atlassian_jira_config=atlassian_jira_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00042.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/atlassian-jira', methods=['GET'])
def delete_atlassian_jira():
    try:
        atlassian_jira_config = request.args.get('atlassian_jira_config')
        project_id            = request.cookies.get('project')
        project_data          = DBProjects.get_config_by_id(id=project_id)
        if atlassian_jira_config is not None:
            DBAtlassianJira.delete(schema_name=project_data['name'], id=atlassian_jira_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00041.value, "error")
    return redirect(url_for('integrations',tab='jira'))

@app.route('/azure', methods=['GET', 'POST'])
def add_azure():
    try:
        form           = AzureWikiForm(request.form)
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        azure_config   = request.args.get('azure_config')
        secret_configs = DBSecrets.get_configs(id=project_id)
        if azure_config is not None:
            output = DBAzureWiki.get_config_by_id(schema_name=project_data['name'], id=azure_config)
            form   = AzureWikiForm(data=output)
        if form.validate_on_submit():
            try:
                azure_data = form.data

                for key, value in azure_data.items():
                    if value == '':
                        azure_data[key] = None

                if azure_data['id']:
                    DBAzureWiki.update(
                        schema_name = project_data['name'],
                        data        = azure_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBAzureWiki.save(
                        schema_name = project_data['name'],
                        data        = azure_data
                    )
                    flash("Integration added.", "info")
                return redirect(url_for('integrations',tab='azure'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00034.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/azure.html', form=form, azure_config=azure_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00036.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/azure', methods=['GET'])
def delete_azure_config():
    try:
        azure_config = request.args.get('azure_config')
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        if azure_config is not None:
            DBAzureWiki.delete(schema_name=project_data['name'], id=azure_config)
            flash("Integration deleted.", "info")
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00035.value, "error")
    return redirect(url_for('integrations',tab='azure'))

@app.route('/ai-support', methods=['GET', 'POST'])
def add_ai_support():
    try:
        form              = AISupportForm(request.form)
        project_id        = request.cookies.get('project')
        project_data      = DBProjects.get_config_by_id(id=project_id)
        ai_support_config = request.args.get('ai_support_config')
        secret_configs    = DBSecrets.get_configs(id=project_id)
        if ai_support_config is not None:
            output = DBAISupport.get_config_by_id(schema_name=project_data['name'], id=ai_support_config)
            form   = AISupportForm(data=output)
        if form.validate_on_submit():
            try:
                ai_support_data = form.data

                for key, value in ai_support_data.items():
                    if value == '':
                        ai_support_data[key] = None

                print(ai_support_data)
                if ai_support_data['id']:
                    DBAISupport.update(
                        schema_name = project_data['name'],
                        data        = ai_support_data
                    )
                    flash("Integration updated.", "info")
                else:
                    DBAISupport.save(
                        schema_name = project_data['name'],
                        data        = ai_support_data
                    )
                    flash("Integration added.", "info")
                return redirect(url_for('integrations',tab='ai-support'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00046.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/ai-support.html', form=form, ai_support_config=ai_support_config, secret_configs=secret_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00048.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/ai-support', methods=['GET'])
def delete_ai_support():
    try:
        ai_support_config = request.args.get('ai_support_config')
        project_id        = request.cookies.get('project')
        project_data      = DBProjects.get_config_by_id(id=project_id)
        if ai_support_config is not None:
            DBAISupport.delete(schema_name=project_data['name'], id=ai_support_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00047.value, "error")
    return redirect(url_for('integrations',tab='ai-support'))
