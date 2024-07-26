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

import logging
import traceback

from flask                          import flash, redirect, request, url_for, render_template
from app                            import app
from app.backend                    import pkg
from app.backend.ai_support.prompts import Prompt
from app.forms                      import PromptForm
from app.backend.errors             import ErrorMessages


@app.route('/set-project', methods=['GET'])
def set_project():
    try:
        project = request.args.get('project')
        if project is None:
            projects = pkg.get_projects()
            if projects:
                project = projects[0]['id']
            else:
                return redirect(url_for('choose_project'))
        res = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.SET_PROJECT.value, "error")
    return res

@app.route('/get-projects', methods=['GET'])
def get_projects():
    try:
        projects = []
        projects = pkg.get_projects()
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_PROJECT.value, "error")
    return {'projects': projects}

@app.route('/save-project', methods=['GET'])
def save_project():
    try:
        project_name = request.args.get('project_name')
        project      = pkg.save_new_project(project_name)
        res          = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
        flash("The project was successfully added.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.SAVE_PROJECT.value, "error")
    return res

@app.route('/delete-project', methods=['GET'])
def delete_project():
    try:
        project = request.args.get('project')
        pkg.delete_project(project)
        projects = pkg.get_projects()
        if projects:
            project = projects[0]['id']
        else:
            return redirect(url_for('choose_project'))
        res = redirect(url_for('index'))
        res.set_cookie(key='project', value=project, max_age=None)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_PROJECT.value, "error")
    return res

@app.route('/view-logs', methods=['GET'])
def view_logs():
    try:
        with open("./app/logs/info.log", "r", errors='ignore') as file:
            log_lines = file.readlines()
    except FileNotFoundError:
        log_lines = ["Log file not found."]
    log_lines = log_lines[-150:]
    logs      = ''.join(log_lines)
    return render_template('home/logs.html', logs=logs)

@app.route('/prompts', methods=['GET'])
def prompts():
    try:
        project          = request.cookies.get('project')
        form_for_prompts = PromptForm(request.form)
        default_prompts  = Prompt.get_default_prompts()
        custom_prompts   = Prompt.get_custom_prompts(project)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_PROMPTS.value, "error")
        return redirect(url_for("index"))
    return render_template('home/prompts.html', default_prompts = default_prompts, custom_prompts = custom_prompts, form_for_prompts = form_for_prompts)

@app.route('/save-prompt', methods=['POST'])
def save_prompt():
    try:
        project    = request.cookies.get('project')
        if request.method == "POST":
            original_prompt_id = request.form.to_dict().get("id")
            prompt_id          = Prompt.save_custom_prompt(project, request.form.to_dict())
        if original_prompt_id == prompt_id:
            flash("Custom prompt updated.", "info")
        else:
            flash("Custom prompt added.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.SAVE_PROMPT.value, "error")
        return redirect(url_for("index"))
    return redirect(url_for('prompts', type='custom'))

@app.route('/delete-prompt', methods=['GET'])
def delete_prompt():
    try:
        project    = request.cookies.get('project')
        prompt_id  = request.args.get('prompt_id')
        if prompt_id is not None:
            Prompt.delete_custom_prompt(project, prompt_id)
            flash("Custom prompt deleted", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_PROMPT.value, "error")
        return redirect(url_for("index"))
    return redirect(url_for('prompts', type='custom'))