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
        azure_configs                = DBAzureWiki.get_configs(schema_name=project_data['name'])
        atlassian_confluence_configs = DBAtlassianConfluence.get_configs(schema_name=project_data['name'])
        atlassian_jira_configs       = DBAtlassianJira.get_configs(schema_name=project_data['name'])
        smtp_mail_configs            = DBSMTPMail.get_configs(schema_name=project_data['name'])
        ai_support_configs           = DBAISupport.get_configs(schema_name=project_data['name'])
        return render_template('home/integrations.html',
                               influxdb_configs             = influxdb_configs,
                               grafana_configs              = grafana_configs,
                               azure_configs                = azure_configs,
                               atlassian_confluence_configs = atlassian_confluence_configs,
                               atlassian_jira_configs       = atlassian_jira_configs,
                               smtp_mail_configs            = smtp_mail_configs,
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
        secret_configs  = DBSecrets.get_configs(project_id=project_id)
        if influxdb_config is not None:
            output = DBInfluxdb.get_config_by_id(schema_name=project_data['name'], id=influxdb_config)
            form   = InfluxDBForm(data=output)
        if form.validate_on_submit():
            try:
                influxdb_data = form.data
                if influxdb_data['id']:
                    DBInfluxdb.update(
                        schema_name = project_data['name'],
                        id          = influxdb_data['id'],
                        name        = influxdb_data['name'],
                        url         = influxdb_data['url'],
                        org_id      = influxdb_data['org_id'],
                        token       = influxdb_data['token'],
                        timeout     = influxdb_data['timeout'],
                        bucket      = influxdb_data['bucket'],
                        listener    = influxdb_data['listener'],
                        tmz         = influxdb_data['tmz'],
                        is_default  = influxdb_data['is_default']
                    )
                    flash("Integration updated.", "info")
                else:
                    influxdb_obj = DBInfluxdb(
                        name        = influxdb_data['name'],
                        url         = influxdb_data['url'],
                        org_id      = influxdb_data['org_id'],
                        token       = influxdb_data['token'],
                        timeout     = influxdb_data['timeout'],
                        bucket      = influxdb_data['bucket'],
                        listener    = influxdb_data['listener'],
                        tmz         = influxdb_data['tmz'],
                        is_default  = influxdb_data['is_default']
                    )
                    influxdb_config = influxdb_obj.save(schema_name=project_data['name'])
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
        secret_configs = DBSecrets.get_configs(project_id=project_id)
        if grafana_config is not None:
            output = DBGrafana.get_config_by_id(schema_name=project_data['name'], id=grafana_config)
            form   = GrafanaForm(data=output)
        if request.method == "POST":
            try:
                grafana_data = request.get_json()
                if grafana_data["id"]:
                    DBGrafana.update(
                        schema_name         = project_data['name'],
                        id                  = grafana_data['id'],
                        name                = grafana_data['name'],
                        server              = grafana_data['server'],
                        org_id              = grafana_data['org_id'],
                        token               = grafana_data['token'],
                        test_title          = grafana_data['test_title'],
                        app                 = grafana_data['app'],
                        baseline_test_title = grafana_data['baseline_test_title'],
                        is_default          = grafana_data['is_default'],
                        dashboards          = grafana_data['dashboards']
                    )
                    flash("Integration updated.", "info")
                else:
                    grafana_obj = DBGrafana(
                        name                = grafana_data['name'],
                        server              = grafana_data['server'],
                        org_id              = grafana_data['org_id'],
                        token               = grafana_data['token'],
                        test_title          = grafana_data['test_title'],
                        app                 = grafana_data['app'],
                        baseline_test_title = grafana_data['baseline_test_title'],
                        is_default          = grafana_data['is_default'],
                        dashboards          = []
                    )
                    for dashboards_data in grafana_data['dashboards']:
                        dashboard = DBGrafanaDashboards(
                            content    = dashboards_data['content'],
                            grafana_id = None
                        )
                        grafana_obj.dashboards.append(dashboard)
                    grafana_config = grafana_obj.save(schema_name = project_data['name'])
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

@app.route('/azure', methods=['GET', 'POST'])
def add_azure():
    try:
        form           = AzureWikiForm(request.form)
        project_id     = request.cookies.get('project')
        project_data   = DBProjects.get_config_by_id(id=project_id)
        azure_config   = request.args.get('azure_config')
        secret_configs = DBSecrets.get_configs(project_id=project_id)
        if azure_config is not None:
            output = DBAzureWiki.get_config_by_id(schema_name=project_data['name'], id=azure_config)
            form   = AzureWikiForm(data=output)
        if form.validate_on_submit():
            try:
                azure_data = form.data
                if azure_data['id']:
                    DBAzureWiki.update(
                        schema_name    = project_data['name'],
                        id             = azure_data['id'],
                        name           = azure_data['name'],
                        token          = azure_data['token'],
                        org_url        = azure_data['org_url'],
                        project_id     = azure_data['project_id'],
                        identifier     = azure_data['identifier'],
                        path_to_report = azure_data['path_to_report'],
                        is_default     = azure_data['is_default']
                    )
                    flash("Integration updated.", "info")
                else:
                    azure_obj = DBAzureWiki(
                        name           = azure_data['name'],
                        token          = azure_data['token'],
                        org_url        = azure_data['org_url'],
                        project_id     = azure_data['project_id'],
                        identifier     = azure_data['identifier'],
                        path_to_report = azure_data['path_to_report'],
                        is_default     = azure_data['is_default']
                    )
                    azure_config = azure_obj.save(schema_name=project_data['name'])
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

@app.route('/atlassian-confluence', methods=['GET', 'POST'])
def add_atlassian_confluence():
    try:
        form                        = AtlassianConfluenceForm(request.form)
        project_id                  = request.cookies.get('project')
        project_data                = DBProjects.get_config_by_id(id=project_id)
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        secret_configs              = DBSecrets.get_configs(project_id=project_id)
        if atlassian_confluence_config is not None:
            output = DBAtlassianConfluence.get_config_by_id(schema_name=project_data['name'], id=atlassian_confluence_config)
            form   = AtlassianConfluenceForm(data=output)
        if form.validate_on_submit():
            try:
                atlassian_confluence_data = form.data
                if atlassian_confluence_data['id']:
                    DBAtlassianConfluence.update(
                        schema_name = project_data['name'],
                        id          = atlassian_confluence_data['id'],
                        name        = atlassian_confluence_data['name'],
                        email       = atlassian_confluence_data['email'],
                        token       = atlassian_confluence_data['token'],
                        token_type  = atlassian_confluence_data['token_type'],
                        org_url     = atlassian_confluence_data['org_url'],
                        space_key   = atlassian_confluence_data['space_key'],
                        parent_id   = atlassian_confluence_data['parent_id'],
                        is_default  = atlassian_confluence_data['is_default']
                    )
                    flash("Integration updated.", "info")
                else:
                    atlassian_confluence_obj = DBAtlassianConfluence(
                        name       = atlassian_confluence_data['name'],
                        email      = atlassian_confluence_data['email'],
                        token      = atlassian_confluence_data['token'],
                        token_type = atlassian_confluence_data['token_type'],
                        org_url    = atlassian_confluence_data['org_url'],
                        space_key  = atlassian_confluence_data['space_key'],
                        parent_id  = atlassian_confluence_data['parent_id'],
                        is_default = atlassian_confluence_data['is_default']
                    )
                    atlassian_confluence_config = atlassian_confluence_obj.save(schema_name=project_data['name'])
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
        secret_configs        = DBSecrets.get_configs(project_id=project_id)
        if atlassian_jira_config is not None:
            output = DBAtlassianJira.get_config_by_id(schema_name=project_data['name'], id=atlassian_jira_config)
            form   = AtlassianJiraForm(data=output)
        if form.validate_on_submit():
            try:
                atlassian_jira_data = form.data
                if atlassian_jira_data['id']:
                    DBAtlassianJira.update(
                        schema_name = project_data['name'],
                        id          = atlassian_jira_data['id'],
                        name        = atlassian_jira_data['name'],
                        email       = atlassian_jira_data['email'],
                        token       = atlassian_jira_data['token'],
                        token_type  = atlassian_jira_data['token_type'],
                        org_url     = atlassian_jira_data['org_url'],
                        project_id  = atlassian_jira_data['project_id'],
                        epic_field  = atlassian_jira_data['epic_field'],
                        epic_name   = atlassian_jira_data['epic_name'],
                        is_default  = atlassian_jira_data['is_default']
                    )
                    flash("Integration updated.", "info")
                else:
                    atlassian_jira_obj = DBAtlassianJira(
                        name        = atlassian_jira_data['name'],
                        email       = atlassian_jira_data['email'],
                        token       = atlassian_jira_data['token'],
                        token_type  = atlassian_jira_data['token_type'],
                        org_url     = atlassian_jira_data['org_url'],
                        project_id  = atlassian_jira_data['project_id'],
                        epic_field  = atlassian_jira_data['epic_field'],
                        epic_name   = atlassian_jira_data['epic_name'],
                        is_default  = atlassian_jira_data['is_default']
                    )
                    atlassian_jira_config = atlassian_jira_obj.save(schema_name=project_data['name'])
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

@app.route('/smtp-mail', methods=['GET', 'POST'])
def add_smtp_mail():
    try:
        form             = SMTPMailForm(request.form)
        project_id       = request.cookies.get('project')
        project_data     = DBProjects.get_config_by_id(id=project_id)
        smtp_mail_config = request.args.get('smtp_mail_config')
        secret_configs   = DBSecrets.get_configs(project_id=project_id)
        if smtp_mail_config is not None:
            output = DBSMTPMail.get_config_by_id(schema_name=project_data['name'], id=smtp_mail_config)
            form   = SMTPMailForm(data=output)
        if request.method == 'POST':
            try:
                smtp_mail_data = request.get_json()
                if smtp_mail_data["id"]:
                    DBSMTPMail.update(
                        schema_name = project_data['name'],
                        id          = smtp_mail_data['id'],
                        name        = smtp_mail_data['name'],
                        server      = smtp_mail_data['server'],
                        port        = smtp_mail_data['port'],
                        use_ssl     = smtp_mail_data['use_ssl'],
                        use_tls     = smtp_mail_data['use_tls'],
                        username    = smtp_mail_data['username'],
                        token       = smtp_mail_data['token'],
                        is_default  = smtp_mail_data['is_default'],
                        recipients  = smtp_mail_data['recipients']
                    )
                    flash("Integration updated.", "info")
                else:
                    smtp_mail_obj = DBSMTPMail(
                        name        = smtp_mail_data['name'],
                        server      = smtp_mail_data['server'],
                        port        = smtp_mail_data['port'],
                        use_ssl     = smtp_mail_data['use_ssl'],
                        use_tls     = smtp_mail_data['use_tls'],
                        username    = smtp_mail_data['username'],
                        token       = smtp_mail_data['token'],
                        is_default  = smtp_mail_data['is_default'],
                        recipients  = []
                    )
                    for recipients_data in smtp_mail_data['recipients']:
                        recipient = DBSMTPMailRecipient(
                            email        = recipients_data,
                            smtp_mail_id = None
                        )
                        smtp_mail_obj.recipients.append(recipient)
                    smtp_mail_config = smtp_mail_obj.save(schema_name = project_data['name'])
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

@app.route('/ai-support', methods=['GET', 'POST'])
def add_ai_support():
    try:
        form              = AISupportForm(request.form)
        project_id        = request.cookies.get('project')
        project_data      = DBProjects.get_config_by_id(id=project_id)
        ai_support_config = request.args.get('ai_support_config')
        secret_configs    = DBSecrets.get_configs(project_id=project_id)
        if ai_support_config is not None:
            output = DBAISupport.get_config_by_id(schema_name=project_data['name'], id=ai_support_config)
            form   = AISupportForm(data=output)
        if form.validate_on_submit():
            try:
                ai_support_data = form.data
                if ai_support_data['id']:
                    DBAISupport.update(
                        schema_name    = project_data['name'],
                        id             = ai_support_data['id'],
                        name           = ai_support_data['name'],
                        ai_provider    = ai_support_data['ai_provider'],
                        azure_url      = ai_support_data['azure_url'],
                        api_version    = ai_support_data['api_version'],
                        ai_text_model  = ai_support_data['ai_text_model'],
                        ai_image_model = ai_support_data['ai_image_model'],
                        token          = ai_support_data['token'],
                        temperature    = ai_support_data['temperature'],
                        is_default     = ai_support_data['is_default']
                    )
                    flash("Integration updated.", "info")
                else:
                    ai_support_obj = DBAISupport(
                        name           = ai_support_data['name'],
                        ai_provider    = ai_support_data['ai_provider'],
                        azure_url      = ai_support_data['azure_url'],
                        api_version    = ai_support_data['api_version'],
                        ai_text_model  = ai_support_data['ai_text_model'],
                        ai_image_model = ai_support_data['ai_image_model'],
                        token          = ai_support_data['token'],
                        temperature    = ai_support_data['temperature'],
                        is_default     = ai_support_data['is_default']
                    )
                    ai_support_config = ai_support_obj.save(schema_name=project_data['name'])
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