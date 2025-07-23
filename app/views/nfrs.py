# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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
from flask                                       import render_template, request, url_for, redirect, flash


@app.route('/nfrs', methods=['GET'])
def get_nfrs():
    """
    Render the NFRs list page.

    Returns:
        Rendered template for the NFRs list page
    """
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        nfrs_list    = DBNFRs.get_configs(project_id=project_id)
        return render_template('home/nfrs.html', nfrs_list=nfrs_list)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00019.value, "error")
        return redirect(url_for('get_nfrs'))

@app.route('/nfr', methods=['GET'])
def get_nfr():
    """
    Render the NFR edit/create page.

    Returns:
        Rendered template for the NFR edit/create page
    """
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        nfr_id       = request.args.get('nfr_config')
        clone        = request.args.get('clone')
        nfr_data     = {}
        if nfr_id:
            nfr_data = DBNFRs.get_config_by_id(project_id=project_id, id=nfr_id)
            if clone:
                nfr_data['name'] = f"{nfr_data.get('name', '')} COPY"
                nfr_id = None
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00020.value, "error")
    return render_template('home/nfr.html', nfr_config=nfr_id, nfr_data=nfr_data)
