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
import json

from app                                                                       import app
from app.forms                                                                 import InfluxDBForm, GrafanaForm, AzureWikiForm, AtlassianConfluenceForm, AtlassianJiraForm, SMTPMailForm, AISupportForm
from app.backend                                                               import pkg
from app.backend.errors                                                        import ErrorMessages
from app.backend.integrations.influxdb.influxdb_config                         import InfluxdbConfig
from app.backend.integrations.grafana.grafana_config                           import GrafanaConfig
from app.backend.integrations.azure_wiki.azure_wiki_config                     import AzureWikiConfig
from app.backend.integrations.atlassian_confluence.atlassian_confluence_config import AtlassianConfluenceConfig
from app.backend.integrations.atlassian_jira.atlassian_jira_config             import AtlassianJiraConfig
from app.backend.integrations.smtp_mail.smtp_mail_config                       import SmtpMailConfig
from app.backend.integrations.ai_support.ai_config                             import AISupportConfig
from flask                                                                     import render_template, request, url_for, redirect, flash


@app.route('/integrations')
def integrations():
    try:
        project                      = request.cookies.get('project')
        influxdb_configs             = pkg.get_integration_config_names_and_ids(project, "influxdb")
        grafana_configs              = pkg.get_integration_config_names_and_ids(project, "grafana")
        azure_configs                = pkg.get_integration_config_names_and_ids(project, "azure")
        atlassian_confluence_configs = pkg.get_integration_config_names_and_ids(project, "atlassian_confluence")
        atlassian_jira_configs       = pkg.get_integration_config_names_and_ids(project, "atlassian_jira")
        smtp_mail_configs            = pkg.get_integration_config_names_and_ids(project, "smtp_mail")
        ai_support_configs           = pkg.get_integration_config_names_and_ids(project, "ai_support")
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
        flash(ErrorMessages.GET_INTEGRATIONS.value, "error")
        return render_template('home/integrations.html')

@app.route('/influxdb', methods=['GET', 'POST'])
def add_influxdb():
    try:
        form            = InfluxDBForm(request.form)
        project         = request.cookies.get('project')
        influxdb_config = request.args.get('influxdb_config')
        if influxdb_config is not None:
            output = InfluxdbConfig.get_influxdb_config_values(project, influxdb_config)
            form   = InfluxDBForm(output)
        if form.validate_on_submit():
            try:
                original_influxdb_config = request.form.to_dict().get("id")
                influxdb_config          = InfluxdbConfig.save_influxdb_config(project, request.form.to_dict())
                if original_influxdb_config == influxdb_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_INFLUXDB.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/influxdb.html', form=form, influxdb_config=influxdb_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_INFLUXDB.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/influxdb', methods=['GET'])
def delete_influxdb():
    try:
        influxdb_config = request.args.get('influxdb_config')
        project         = request.cookies.get('project')
        if influxdb_config is not None:
            InfluxdbConfig.delete_influxdb_config(project, influxdb_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_INFLUXDB.value, "error")
    return redirect(url_for('integrations'))

@app.route('/grafana', methods=['GET', 'POST'])
def add_grafana():
    try:
        form           = GrafanaForm(request.form)
        project        = request.cookies.get('project')
        grafana_config = request.args.get('grafana_config')
        if grafana_config is not None:
            output = GrafanaConfig.get_grafana_config_values(project, grafana_config)
            form   = GrafanaForm(data=output)
        if request.method == 'POST':
            try:
                data                    = json.loads(request.data)
                original_grafana_config = data.get("id")
                grafana_config          = GrafanaConfig.save_grafana_config(project, data)
                if original_grafana_config == grafana_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
                return "grafana_config=" + grafana_config
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_GRAFANA.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/grafana.html', form=form, grafana_config=grafana_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_GRAFANA.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/grafana', methods=['GET'])
def delete_grafana_config():
    try:
        grafana_config = request.args.get('grafana_config')
        project        = request.cookies.get('project')
        if grafana_config is not None:
            GrafanaConfig.delete_grafana_config(project, grafana_config)
            flash("Integration deleted.", "info")
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_GRAFANA.value, "error")
    return redirect(url_for('integrations'))

@app.route('/azure', methods=['GET', 'POST'])
def add_azure():
    try:
        form         = AzureWikiForm(request.form)
        project      = request.cookies.get('project')
        azure_config = request.args.get('azure_config')
        if azure_config is not None:
            output = AzureWikiConfig.get_azure_wiki_config_values(project, azure_config)
            form   = AzureWikiForm(output)
        if form.validate_on_submit():
            try:
                original_azure_config = request.form.to_dict().get("id")
                azure_config          = AzureWikiConfig.save_azure_wiki_config(project, request.form.to_dict())
                if original_azure_config == azure_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_AZURE_WIKI.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/azure.html', form=form, azure_config=azure_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_AZURE_WIKI.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/azure', methods=['GET'])
def delete_azure_config():
    try:
        azure_config = request.args.get('azure_config')
        project      = request.cookies.get('project')
        if azure_config is not None:
            AzureWikiConfig.delete_azure_wiki_config(project, azure_config)
            flash("Integration deleted.", "info")
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_AZURE_WIKI.value, "error")
    return redirect(url_for('integrations'))

@app.route('/atlassian-confluence', methods=['GET', 'POST'])
def add_atlassian_confluence():
    try:
        form                        = AtlassianConfluenceForm(request.form)
        project                     = request.cookies.get('project')
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        if atlassian_confluence_config is not None:
            output = AtlassianConfluenceConfig.get_atlassian_confluence_config_values(project, atlassian_confluence_config)
            form   = AtlassianConfluenceForm(output)
        if form.validate_on_submit():
            try:
                original_atlassian_confluence_config = request.form.to_dict().get("id")
                atlassian_confluence_config          = AtlassianConfluenceConfig.save_atlassian_confluence_config(project, request.form.to_dict())
                if original_atlassian_confluence_config == atlassian_confluence_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_ATLASSIAN_CONFLUENCE.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/atlassian-confluence.html', form=form, atlassian_confluence_config=atlassian_confluence_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_ATLASSIAN_CONFLUENCE.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/atlassian-confluence', methods=['GET'])
def delete_atlassian_confluence():
    try:
        atlassian_confluence_config = request.args.get('atlassian_confluence_config')
        project                     = request.cookies.get('project')
        if atlassian_confluence_config is not None:
            AtlassianConfluenceConfig.delete_atlassian_confluence_config(project, atlassian_confluence_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_ATLASSIAN_CONFLUENCE.value, "error")
    return redirect(url_for('integrations'))

@app.route('/atlassian-jira', methods=['GET', 'POST'])
def add_atlassian_jira():
    try:
        form                  = AtlassianJiraForm(request.form)
        project               = request.cookies.get('project')
        atlassian_jira_config = request.args.get('atlassian_jira_config')
        if atlassian_jira_config is not None:
            output = AtlassianJiraConfig.get_atlassian_jira_config_values(project, atlassian_jira_config)
            form   = AtlassianJiraForm(output)
        if form.validate_on_submit():
            try:
                original_atlassian_jira_config = request.form.to_dict().get("id")
                atlassian_jira_config          = AtlassianJiraConfig.save_atlassian_jira_config(project, request.form.to_dict())
                if original_atlassian_jira_config == atlassian_jira_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_ATLASSIAN_JIRA.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/atlassian-jira.html', form=form, atlassian_jira_config=atlassian_jira_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_ATLASSIAN_JIRA.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/atlassian-jira', methods=['GET'])
def delete_atlassian_jira():
    try:
        atlassian_jira_config = request.args.get('atlassian_jira_config')
        project               = request.cookies.get('project')
        if atlassian_jira_config is not None:
            AtlassianJiraConfig.delete_atlassian_jira_config(project, atlassian_jira_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_ATLASSIAN_JIRA.value, "error")
    return redirect(url_for('integrations'))

@app.route('/smtp-mail', methods=['GET', 'POST'])
def add_smtp_mail():
    try:
        form             = SMTPMailForm(request.form)
        project          = request.cookies.get('project')
        smtp_mail_config = request.args.get('smtp_mail_config')
        if smtp_mail_config is not None:
            output = SmtpMailConfig.get_smtp_mail_config_values(project, smtp_mail_config)
            form   = SMTPMailForm(output)
        if request.method == 'POST':
            try:
                data                      = json.loads(request.data)
                original_smtp_mail_config = data.get("id")
                smtp_mail_config          = SmtpMailConfig.save_smtp_mail_config(project, data)
                if original_smtp_mail_config == smtp_mail_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
                return "smtp_mail_config=" + smtp_mail_config
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_SMTP.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/smtp-mail.html', form=form, smtp_mail_config=smtp_mail_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_SMTP.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/smtp-mail', methods=['GET'])
def delete_smtp_mail_config():
    try:
        smtp_mail_config = request.args.get('smtp_mail_config')
        project          = request.cookies.get('project')
        if smtp_mail_config is not None:
            SmtpMailConfig.delete_smtp_mail_config(project, smtp_mail_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_SMTP.value, "error")
    return redirect(url_for('integrations'))

@app.route('/ai-support', methods=['GET', 'POST'])
def add_ai_support():
    try:
        form              = AISupportForm(request.form)
        project           = request.cookies.get('project')
        ai_support_config = request.args.get('ai_support_config')
        if ai_support_config is not None:
            output = AISupportConfig.get_ai_support_config_values(project, ai_support_config)
            form   = AISupportForm(output)
        if form.validate_on_submit():
            try:
                original_ai_support_config = request.form.to_dict().get("id")
                ai_support_config          = AISupportConfig.save_ai_support_config(project, request.form.to_dict())
                if original_ai_support_config == ai_support_config:
                    flash("Integration updated.", "info")
                else:
                    flash("Integration added.", "info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_AI.value, "error")
                return redirect(url_for('integrations'))
        return render_template('integrations/ai-support.html', form=form, ai_support_config=ai_support_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_AI.value, "error")
        return redirect(url_for('integrations'))

@app.route('/delete/ai-support', methods=['GET'])
def delete_ai_support():
    try:
        ai_support_config = request.args.get('ai_support_config')
        project           = request.cookies.get('project')
        if ai_support_config is not None:
            AISupportConfig.delete_ai_support_config(project, ai_support_config)
            flash("Integration deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_AI.value, "error")
    return redirect(url_for('integrations'))