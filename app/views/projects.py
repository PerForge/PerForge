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

from app                import app
from app.backend        import pkg
from app.backend.errors import ErrorMessages
from flask              import render_template, request, url_for, redirect, flash


@app.route('/choose-project', methods=['GET'])
def choose_project():
    try:
        projects = pkg.get_all_projects()
        return render_template('home/choose-project.html', projects=projects)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00016.value, "error")
    return redirect(url_for('index'))

@app.route('/set-project', methods=['GET'])
def set_project():
    try:
        project = request.args.get('project')
        if project is None:
            projects = pkg.get_all_projects()
            if projects:
                project = projects[0]['id']
            else:
                return redirect(url_for('choose_project'))
        res = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00012.value, "error")
    return res

@app.route('/get-projects', methods=['GET'])
def get_projects():
    try:
        projects = []
        projects = pkg.get_all_projects()
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00013.value, "error")
    return {'projects': projects}

@app.route('/save-project', methods=['GET'])
def save_project():
    try:
        project_name = request.args.get('project_name')
        project      = pkg.save_new_project_config(project_name)
        res          = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
        flash("The project was successfully added.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00014.value, "error")
    return res

@app.route('/delete-project', methods=['GET'])
def delete_project():
    try:
        project = request.args.get('project')
        pkg.delete_project_config(project)
        projects = pkg.get_all_projects()
        if projects:
            project = projects[0]['id']
        else:
            return redirect(url_for('choose_project'))
        res = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00015.value, "error")
    return res