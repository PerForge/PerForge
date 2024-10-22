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

from app                                    import app
from app.backend.errors                     import ErrorMessages
from app.backend.components.nfrs.nfr_config import NFRConfig
from flask                                  import render_template, request, url_for, redirect, flash, jsonify


@app.route('/nfrs', methods=['GET'])
def get_nfrs():
    try:
        project   = request.cookies.get('project')
        nfrs_list = NFRConfig.get_all_nfrs(project)
        return render_template('home/nfrs.html', nfrs_list=nfrs_list)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00019.value, "error")
    return redirect(url_for('get_nfrs'))

@app.route('/nfr', methods=['GET', 'POST'])
def get_nfr():
    try:
        nfr_data   = {}
        project    = request.cookies.get('project')
        nfr_config = request.args.get('nfr_config')
        if nfr_config is not None:
            nfr_data = NFRConfig.get_nfr_values_by_id(project, nfr_config)
        if request.method == "POST":
            original_nfr_config = request.get_json().get("id")
            nfr_config          = NFRConfig.save_nfr_config(project, request.get_json())
            if original_nfr_config == nfr_config:
                flash("NFR updated.", "info")
            else:
                flash("NFR added.", "info")
            return jsonify({'redirect_url': 'nfrs'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00020.value, "error")
    return render_template('home/nfr.html', nfr_config=nfr_config,nfr_data=nfr_data)

@app.route('/delete/nfr', methods=['GET'])
def delete_nfrs():
    try:
        project = request.cookies.get('project')
        NFRConfig.delete_nfr_config(project, request.args.get('nfr_config'))
        flash("NFR deleted.", "info")
        return redirect(url_for('get_nfrs'))
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00021.value, "error")
        return redirect(url_for('get_nfrs'))