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

from flask              import render_template, request, url_for, redirect, flash, jsonify
from app                import app
from app.backend        import pkg
from app.backend.errors import ErrorMessages


@app.route('/nfrs', methods=['GET'])
def get_nfrs():
    try:
        project   = request.cookies.get('project')
        nfrs_list = pkg.get_nfrs(project)
        return render_template('home/nfrs.html', nfrs_list=nfrs_list)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_NFRS.value, "error")
    return redirect(url_for('get_nfrs'))

@app.route('/nfr', methods=['GET', 'POST'])
def get_nfr():
    try:
        nfr_data   = {}
        project    = request.cookies.get('project')
        nfr_config = request.args.get('nfr_config')
        if nfr_config is not None:
            nfr_data = pkg.get_nfr(project, nfr_config)
        if request.method == "POST":
            original_nfr_config = request.get_json().get("id")
            nfr_config          = pkg.save_nfrs(project, request.get_json())
            if original_nfr_config == nfr_config:
                flash("NFR updated.", "info")
            else:
                flash("NFR added.", "info")
            return jsonify({'redirect_url': 'nfrs'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.SAVE_NFR.value, "error")
    return render_template('home/nfr.html', nfr_config=nfr_config,nfr_data=nfr_data)

@app.route('/delete/nfr', methods=['GET'])
def delete_nfrs():
    try:
        project = request.cookies.get('project')
        pkg.delete_nfr(project, request.args.get('nfr_config'))
        flash("NFR deleted.", "info")
        return redirect(url_for('get_nfrs'))
    except Exception as er:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_NFR.value, "error")
        return redirect(url_for('get_nfrs'))