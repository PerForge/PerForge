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

from flask                                       import request, make_response
from app                                         import app
from app.backend.reporting.azure_wiki_report     import AzureWikiReport
from app.backend.integrations.secondary.influxdb import Influxdb
from app.backend.integrations.secondary.grafana  import Grafana


@app.route('/gen-az-report', methods=['GET'])
def gen_az_report():
    try:
        grafana_obj     = Grafana("default")
        project         = "default"
        run_id          = request.args.get('run_id')
        baseline_run_id = request.args.get('baseline_run_id')
        report_name     = request.args.get('reportName')
        azreport        = AzureWikiReport(project, report_name)
        azreport.generate_report(run_id, baseline_run_id)
    except Exception:
        logging.warning(str(traceback.format_exc()))
    resp                                             = make_response("Done")
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
        influxdb_obj.connect_to_influxdb()
        bucket = request.args.get('bucket')
        run_id = request.args.get('run_id')
        start  = request.args.get('start')
        end    = request.args.get('end')
        status = request.args.get('status')
        if bucket: influxdb_obj.bucket = bucket
        if request.args.get('user') in ["admin"]:
            if status == "delete_test":
                influxdb_obj.delete_run_id(run_id=run_id)
            elif status == "delete_timerange":
                influxdb_obj.delete_run_id(run_id=run_id, start=start, end=end)
    except Exception:
        logging.warning(str(traceback.format_exc()))
    resp = make_response("Done")
    resp.headers['Access-Control-Allow-Origin']      = grafana_obj.server
    resp.headers['access-control-allow-methods']     = '*'
    resp.headers['access-control-allow-credentials'] = 'true'
    return resp