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
import json
import logging

from app                                               import app
from app.backend                                       import pkg
from app.backend.integrations.secondary.influxdb       import Influxdb
from app.backend.reporting.azure_wiki_report           import AzureWikiReport
from app.backend.reporting.atlassian_confluence_report import AtlassianConfluenceReport
from app.backend.reporting.atlassian_jira_report       import AtlassianJiraReport
from app.backend.reporting.smtp_mail_report            import SmtpMailReport
from app.backend.reporting.pdf_report                  import PdfReport
from app.backend.ai_support.prompts                    import Prompt
from app.backend.errors                                import ErrorMessages
from flask                                             import render_template, request, url_for, redirect, flash, jsonify, send_file


@app.route('/template', methods=['GET', 'POST'])
def template():
    try:
        project                 = request.cookies.get('project')
        graphs                  = pkg.get_config_names_and_ids(project, "graphs")
        nfrs                    = pkg.get_config_names_and_ids(project, "nfrs")
        prompt_obj              = Prompt(project)
        template_prompts        = prompt_obj.get_prompts_by_place("template")
        aggregated_data_prompts = prompt_obj.get_prompts_by_place("aggregated_data")
        template_config         = request.args.get('template_config')
        template_data           = []
        if template_config is not None:
            template_data = pkg.get_template_values(project, template_config)
        if request.method == "POST":
            try:
                original_template_config = request.get_json().get("id")
                template_config          = pkg.save_template(project, request.get_json())
                if original_template_config == template_config:
                    flash("Template updated.","info")
                else:
                    flash("Template added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_TEMPLATE.value, "error")
            return jsonify({'redirect_url': 'reporting'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_TEMPLATE.value, "error")
        return redirect(url_for("get_reporting"))
    return render_template('home/template.html', template_config=template_config, graphs=graphs, nfrs=nfrs, template_data=template_data, template_prompts=template_prompts, aggregated_data_prompts=aggregated_data_prompts)

@app.route('/delete-template', methods=['GET'])
def delete_template():
    try:
        template_config = request.args.get('template_config')
        project         = request.cookies.get('project')
        if template_config is not None:
            pkg.delete_template_config(project, template_config)
            flash("Template is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DEL_TEMPLATE.value, "error")
    return redirect(url_for("get_reporting"))

@app.route('/template-group', methods=['GET', 'POST'])
def template_group():
    try:
        project                = request.cookies.get('project')
        templates              = pkg.get_config_names_and_ids(project, "templates")
        template_group_config  = request.args.get('template_group_config')
        prompt_obj             = Prompt(project)
        template_group_prompts = prompt_obj.get_prompts_by_place("template_group")
        template_group_data    = []
        if template_group_config is not None:
            template_group_data = pkg.get_template_group_values(project, template_group_config)
        if request.method == "POST":
            try:
                original_template_group_config = request.get_json().get("id")
                template_group_config          = pkg.save_template_group(project, request.get_json())
                if original_template_group_config == template_group_config:
                    flash("Template group updated.","info")
                else:
                    flash("Template group added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_TEMPLATE_GROUP.value, "error")
            return jsonify({'redirect_url': 'reporting'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_TEMPLATE_GROUP.value, "error")
        return redirect(url_for("get_reporting"))
    return render_template('home/template-group.html', template_group_config=template_group_config,templates=templates, template_group_data=template_group_data, template_group_prompts=template_group_prompts)

@app.route('/delete-template-group', methods=['GET'])
def delete_template_group():
    try:
        template_group_config = request.args.get('template_group_config')
        project               = request.cookies.get('project')
        if template_group_config is not None:
            pkg.delete_template_group_config(project, template_group_config)
            flash("Template group is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DEL_TEMPLATE_GROUP.value, "error")
    return redirect(url_for("get_reporting"))

@app.route('/reporting', methods=['GET', 'POST'])
def get_reporting():
    try:
        project                 = request.cookies.get('project')
        templates               = pkg.get_templates(project)
        template_groups         = pkg.get_template_groups(project)
        nfrs                    = pkg.get_nfrs(project)
        prompt_obj              = Prompt(project)
        template_prompts        = prompt_obj.get_prompts_by_place("template")
        aggregated_data_prompts = prompt_obj.get_prompts_by_place("aggregated_data")
        template_group_prompts  = prompt_obj.get_prompts_by_place("template_group")
        return render_template('home/reporting.html', templates=templates, template_groups=template_groups, nfrs=nfrs, template_prompts=template_prompts, aggregated_data_prompts=aggregated_data_prompts, template_group_prompts=template_group_prompts)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.REPORTING.value, "error")
        return redirect(url_for("index"))

@app.route('/tests', methods=['GET'])
def get_tests():
    try:
        # Get current project
        project          = request.cookies.get('project')
        influxdb_configs = pkg.get_integration_config_names_and_ids(project, "influxdb")
        templates        = pkg.get_config_names_and_ids(project, "templates")
        template_groups  = pkg.get_config_names_and_ids(project, "template_groups")
        output_configs   = pkg.get_output_configs(project)
        return render_template('home/tests.html', influxdb_configs=influxdb_configs, templates = templates, template_groups = template_groups, output_configs=output_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_INTEGRATIONS.value, "error")
        return redirect(url_for("index"))

@app.route('/load_tests', methods=['GET'])
def load_tests():
    try:
        project      = request.cookies.get('project')
        influxdb     = request.args.get('influxdb')
        influxdb_obj = Influxdb(project=project, id=influxdb)
        influxdb_obj.connect_to_influxdb()
        tests = influxdb_obj.get_test_log()
        if(tests):
            tests = pkg.sort_tests(tests)
        return jsonify(status="success", tests=tests)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_TESTS.value, "error")
        return jsonify(status="error", message=ErrorMessages.GET_TESTS.value)

@app.route('/generate', methods=['GET','POST'])
def generate_report():
    try:
        project = request.cookies.get('project')
        if request.method == "POST":
            data = request.get_json()
            if "outputId" in data:
                influxdb       = data.get("influxdbId")
                template_group = data.get("templateGroup")
                action_id      = data.get("outputId")
                action_type    = pkg.get_output_type_by_id(project, action_id)
            else:
                action_type = None
            result = "Wrong action: " + action_type
            if action_type == "azure":
                az     = AzureWikiReport(project)
                result = az.generate_report(data["tests"], influxdb, action_id, template_group)
                del(az)
            elif action_type == "atlassian_confluence":
                awr    = AtlassianConfluenceReport(project)
                result = awr.generate_report(data["tests"], influxdb, action_id, template_group)
                del(awr)
            elif action_type == "atlassian_jira":
                ajr    = AtlassianJiraReport(project)
                result = ajr.generate_report(data["tests"], influxdb, action_id, template_group)
                del(ajr)
            elif action_type == "smtp_mail":
                smr    = SmtpMailReport(project)
                result = smr.generate_report(data["tests"], influxdb, action_id, template_group)
                del(smr)
            elif action_type == "pdf_report":
                pdf      = PdfReport(project)
                filename = pdf.generate_report(data["tests"], influxdb, template_group)
                pdf.pdf_io.seek(0)
                return send_file(pdf.pdf_io, mimetype="application/pdf", download_name=f'{filename}.pdf', as_attachment=True)
            elif action_type == "delete":
                try:
                    influxdb_obj = Influxdb(project=project, id=influxdb)
                    influxdb_obj.connect_to_influxdb()
                    for test in data["tests"]:
                        result = influxdb_obj.delete_run_id(test["runId"])
                except:
                    logging.warning(str(traceback.format_exc()))
                    flash(ErrorMessages.DELETE_TEST.value, "error")
                    return redirect(url_for("index"))
            return result
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GENERATE_REPORT.value, "error")
        return redirect(url_for("index"))