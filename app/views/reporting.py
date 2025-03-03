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
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction     import InfluxdbV2
from app.backend.integrations.azure_wiki.azure_wiki_report                     import AzureWikiReport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_report import AtlassianConfluenceReport
from app.backend.integrations.atlassian_jira.atlassian_jira_report             import AtlassianJiraReport
from app.backend.integrations.smtp_mail.smtp_mail_report                       import SmtpMailReport
from app.backend.integrations.pdf.pdf_report                                   import PdfReport
from app.backend.integrations.report_registry                                  import ReportRegistry
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db             import DBInfluxdb
from app.backend.components.projects.projects_db                               import DBProjects
from app.backend.components.templates.templates_db                             import DBTemplates
from app.backend.components.templates.template_groups_db                       import DBTemplateGroups
from app.backend.data_provider.data_provider                                   import DataProvider
from app.backend.errors                                                        import ErrorMessages
from flask                                                                     import render_template, request, url_for, redirect, flash, jsonify, send_file


@app.route('/tests', methods=['GET'])
def get_tests():
    try:
        project_id             = request.cookies.get('project')
        project_data           = DBProjects.get_config_by_id(id=project_id)
        influxdb_configs       = DBInfluxdb.get_configs(schema_name=project_data['name'])
        db_configs = []
        for config in influxdb_configs:
            db_configs.append({ "id": config["id"], "name": config["name"], "source_type": "influxdb_v2"})
        db_configs.append({ "id": None, "name": "TimescaleDB", "source_type": "timescaledb"})
        template_configs       = DBTemplates.get_configs_brief(schema_name=project_data['name'])
        template_group_configs = DBTemplateGroups.get_configs(schema_name=project_data['name'])
        output_configs         = DBProjects.get_project_output_configs(id=project_id)
        return render_template('home/tests.html', db_configs=db_configs, templates = template_configs, template_groups = template_group_configs, output_configs=output_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00009.value, "error")
        return redirect(url_for("index"))

@app.route('/load_tests', methods=['GET'])
def load_tests():
    try:
        project     = request.cookies.get('project')
        source_type = request.args.get('source_type')
        id          = request.args.get('id')
        ds_obj      = DataProvider(project=project, source_type=source_type, id=id)
        tests       = ds_obj.get_test_log()
        return jsonify(status="success", tests=tests)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00008.value, "error")
        return jsonify(status="error", message=ErrorMessages.ER00008.value.format(source_type))

@app.route('/generate', methods=['GET','POST'])
def generate_report():
    try:
        project = request.cookies.get('project')
        if request.method == "POST":
            data = request.get_json()
            if "output_id" in data:
                db_id            = data.get("db_id")
                template_group   = data.get("template_group")
                action_id        = data.get("output_id")
                integration_type = data.get("integration_type")  # Get the integration type from the request

                # Special cases that need different handling
                if action_id == "pdf_report" or action_id == "delete":
                    action_type = action_id
                elif integration_type:
                    # If integration_type is provided, use it directly as the action_type
                    action_type = integration_type

            # Handle PDF report (special case)
            if action_type == "pdf_report":
                pdf = ReportRegistry.get_report_instance(action_type, project)
                result = pdf.generate_report(data["tests"], db_id, template_group)
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
            # Handle delete action (special case) TBD DATA PROVIDER
            # elif action_type == "delete":
            #     try:
            #         influxdb_obj = InfluxdbV2(project=project, id=db_id)
            #         influxdb_obj._initialize_client()
            #         for test in data["tests"]:
            #             result = influxdb_obj.delete_test_title(test["test_title"])
            #     except:
            #         logging.warning(str(traceback.format_exc()))
            #         flash(ErrorMessages.ER00010.value, "error")
            #         return redirect(url_for("index"))
            # Handle standard report generation using the registry
            elif action_type and ReportRegistry.is_valid_report_type(action_type):
                report_instance = ReportRegistry.get_report_instance(action_type, project)
                result = report_instance.generate_report(data["tests"], db_id, action_id, template_group)
                result = json.dumps(result)
            else:
                result = f"Wrong action: {str(action_type)}"
            return result
    except Exception:
        logging.warning(str(traceback.format_exc()))
        return jsonify({"status": "error", "message": ErrorMessages.ER00011.value}), 500
