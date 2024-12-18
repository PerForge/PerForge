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

from app                                         import app
from app.backend.components.nfrs.nfrs_db         import DBNFRs
from app.backend.components.projects.projects_db import DBProjects
from app.backend.errors                          import ErrorMessages
from flask                                       import render_template, request, url_for, redirect, flash, jsonify


@app.route('/nfrs', methods=['GET'])
def get_nfrs():
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        nfrs_list    = DBNFRs.get_configs(schema_name=project_data['name'])
        return render_template('home/nfrs.html', nfrs_list=nfrs_list)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00019.value, "error")

    return redirect(url_for('get_nfrs'))

@app.route('/nfr', methods=['GET', 'POST'])
def get_nfr():
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        nfr_id       = request.args.get('nfr_config')
        nfr_data     = {}
        if nfr_id:
            nfr_data = DBNFRs.get_config_by_id(schema_name=project_data['name'], id=nfr_id)

        if request.method == "POST":
            nfr_data = request.get_json()

            for key, value in nfr_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if v == '':
                                    item[k] = None
                elif value == '':
                    nfr_data[key] = None

            if nfr_data['id']:
                DBNFRs.update(
                    schema_name = project_data['name'],
                    data        = nfr_data
                )
                flash("NFR updated.", "info")
            else:
                DBNFRs.save(
                    schema_name = project_data['name'],
                    data        = nfr_data
                )
                flash("NFR added.", "info")
            return jsonify({'redirect_url': 'nfrs'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00020.value, "error")
    return render_template('home/nfr.html', nfr_config=nfr_id,nfr_data=nfr_data)

@app.route('/delete/nfr', methods=['GET'])
def delete_nfrs():
    try:
        project_id   = request.cookies.get('project')
        nfr_id       = request.args.get('nfr_config')
        project_data = DBProjects.get_config_by_id(id=project_id)
        DBNFRs.delete(schema_name=project_data['name'], id=nfr_id)
        flash("NFR deleted.", "info")
        return redirect(url_for('get_nfrs'))
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00021.value, "error")
        return redirect(url_for('get_nfrs'))
