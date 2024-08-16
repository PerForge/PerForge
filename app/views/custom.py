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
from app.backend                                                               import pkg
from app.backend.integrations.azure_wiki.azure_wiki_report                     import AzureWikiReport
from app.backend.integrations.atlassian_confluence.atlassian_confluence_report import AtlassianConfluenceReport
from app.backend.integrations.atlassian_jira.atlassian_jira_report             import AtlassianJiraReport
from app.backend.integrations.smtp_mail.smtp_mail_report                       import SmtpMailReport
from app.backend.integrations.influxdb.influxdb                                import Influxdb
from app.backend.integrations.grafana.grafana                                  import Grafana
from flask                                                                     import request, redirect, make_response


@app.route('/gen-report', methods=['GET'])
def gen_report():
    try:
        project            = request.args.get('project')
        influxdb           = request.args.get("influxdbId")
        action_id          = request.args.get("outputId")
        action_type        = pkg.get_output_integration_type_by_id(project, action_id)
        testTitle          = request.args.get('testTitle')
        baseline_testTitle = request.args.get('baseline_testTitle')
        template_id        = request.args.get('template_id')
        data = {
            "runId": testTitle,
            "template_id": template_id
        }
        result = []
        if baseline_testTitle:
            data["baseline_run_id"] = baseline_testTitle
        grafana_obj        = Grafana(project)
        if action_type == "azure":
            az     = AzureWikiReport(project)
            result = az.generate_report([data], influxdb, action_id)
            result = json.dumps(result)
        elif action_type == "atlassian_confluence":
            awr    = AtlassianConfluenceReport(project)
            result = awr.generate_report([data], influxdb, action_id)
            result = json.dumps(result)
        elif action_type == "atlassian_jira":
            ajr    = AtlassianJiraReport(project)
            result = ajr.generate_report([data], influxdb, action_id)
            result = json.dumps(result)
        elif action_type == "smtp_mail":
            smr    = SmtpMailReport(project)
            result = smr.generate_report([data], influxdb, action_id)
            result = json.dumps(result)
    except Exception:
        logging.warning(str(traceback.format_exc()))
    resp                                             = make_response(result)
    resp.headers['Access-Control-Allow-Origin']      = grafana_obj.server
    resp.headers['access-control-allow-methods']     = '*'
    resp.headers['access-control-allow-credentials'] = 'true'
    return resp

@app.route('/delete-influxdata', methods=['GET'])
def influx_data_delete():
    try:
        project      = request.args.get('project')
        influxdb_obj = Influxdb(project)
        grafana_obj  = Grafana(project)
        bucket       = request.args.get('bucket')
        testTitle    = request.args.get('testTitle')
        start        = request.args.get('start')
        end          = request.args.get('end')
        status       = request.args.get('status')
        redirect_url = request.args.get('redirect_url')
        influxdb_obj.connect_to_influxdb()
        if bucket: influxdb_obj.bucket = bucket
        if request.args.get('user') in ["admin"]:
            if status == "delete_test":
                influxdb_obj.delete_run_id(run_id=testTitle)
            elif status == "delete_timerange":
                influxdb_obj.delete_run_id(run_id=testTitle, start=start, end=end)
            elif status == "delete_custom":
                filter = request.args.get('filter')
                influxdb_obj.delete_custom(bucket=bucket, filetr=filter)
    except Exception:
        logging.warning(str(traceback.format_exc()))
    resp = make_response("Done")
    resp.headers['Access-Control-Allow-Origin']      = grafana_obj.server
    resp.headers['access-control-allow-methods']     = '*'
    resp.headers['access-control-allow-credentials'] = 'true'
    if redirect_url:
        return redirect(redirect_url, code=302)
    else:
        return resp