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

from app                                                                       import app
from app.backend                                                               import pkg
from app.backend.errors                                                        import ErrorMessages
from app.backend.integrations.influxdb.influxdb                                import Influxdb
from app.backend.integrations.azure_wiki.azure_wiki_report                     import AzureWikiReport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_report import AtlassianConfluenceReport
from app.backend.integrations.atlassian_jira.atlassian_jira_report             import AtlassianJiraReport
from app.backend.integrations.smtp_mail.smtp_mail_report                       import SmtpMailReport
from app.backend.integrations.pdf.pdf_report                                   import PdfReport
from flask                                                                     import render_template, request, url_for, redirect, flash, jsonify, send_file


@app.route('/tests', methods=['GET'])
def get_tests():
    try:
        # Get current project
        project          = request.cookies.get('project')
        influxdb_configs = pkg.get_integration_config_names_and_ids(project, "influxdb")
        templates        = pkg.get_config_names_and_ids(project, "templates")
        template_groups  = pkg.get_config_names_and_ids(project, "template_groups")
        output_configs   = pkg.get_output_integration_configs(project)
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
            if "output_id" in data:
                influxdb       = data.get("influxdb_id")
                template_group = data.get("template_group")
                action_id      = data.get("output_id")
                if action_id == "pdf_report":
                    action_type = action_id
                elif action_id == "delete":
                    action_type = action_id
                else:
                    action_type = pkg.get_output_integration_type_by_id(project, action_id)
            else:
                action_type = None
            if action_type == "azure":
                az     = AzureWikiReport(project)
                result = az.generate_report(data["tests"], influxdb, action_id, template_group)
                result = json.dumps(result)
            elif action_type == "atlassian_confluence":
                awr    = AtlassianConfluenceReport(project)
                result = awr.generate_report(data["tests"], influxdb, action_id, template_group)
                result = json.dumps(result)
            elif action_type == "atlassian_jira":
                ajr    = AtlassianJiraReport(project)
                result = ajr.generate_report(data["tests"], influxdb, action_id, template_group)
                result = json.dumps(result)
            elif action_type == "smtp_mail":
                smr    = SmtpMailReport(project)
                result = smr.generate_report(data["tests"], influxdb, action_id, template_group)
                result = json.dumps(result)
            elif action_type == "pdf_report":
                pdf      = PdfReport(project)
                result = pdf.generate_report(data["tests"], influxdb, template_group)
                pdf.pdf_io.seek(0)
                # Convert the result to a JSON string and include it in the headers
                result_json = json.dumps(result)
                # Create a custom response with the PDF file and headers
                response = send_file(
                    pdf.pdf_io,
                    mimetype="application/pdf",
                    download_name=f'{result["filename"]}.pdf',
                    as_attachment=True
                )
                response.headers['X-Result-Data'] = result_json
                return response
            elif action_type == "delete":
                try:
                    influxdb_obj = Influxdb(project=project, id=influxdb)
                    influxdb_obj.connect_to_influxdb()
                    for test in data["tests"]:
                        result = influxdb_obj.delete_run_id(test["test_title"])
                except:
                    logging.warning(str(traceback.format_exc()))
                    flash(ErrorMessages.DELETE_TEST.value, "error")
                    return redirect(url_for("index"))
            else:
                result = f"Wrong action: {str(action_type)}"
            return result
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GENERATE_REPORT.value, "error")
        return redirect(url_for("index"))