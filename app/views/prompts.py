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

from app                                       import app
from app.backend.components.prompts.prompts_db import DBPrompts
from app.backend.errors                        import ErrorMessages
from app.forms                                 import PromptForm
from flask                                     import flash, redirect, request, url_for, render_template


@app.route('/prompts', methods=['GET'])
def prompts():
    try:
        project          = request.cookies.get('project')
        form_for_prompts = PromptForm(request.form)
        default_prompts, custom_prompts = DBPrompts.get_configs(project)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00016.value, "error")
        return redirect(url_for("index"))
    return render_template('home/prompts.html', default_prompts = default_prompts, custom_prompts = custom_prompts, form_for_prompts = form_for_prompts)

@app.route('/save-prompt', methods=['POST'])
def save_prompt():
    try:
        project_id                = request.cookies.get('project')
        prompt_data               = request.form.to_dict()
        prompt_data['project_id'] = project_id if prompt_data['project_id'] == "project" else None

        for key, value in prompt_data.items():
            if value == '':
                prompt_data[key] = None

        if prompt_data['id']:
            DBPrompts.update(data = prompt_data)
            flash("Custom prompt updated.", "info")
        else:
            DBPrompts.save(data = prompt_data)
            flash("Custom prompt added.", "info")

    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00017.value, "error")
        return redirect(url_for("index"))

    return redirect(url_for('prompts', type='custom'))

@app.route('/delete-prompt', methods=['GET'])
def delete_prompt():
    try:
        prompt_id  = request.args.get('prompt_id')
        if prompt_id is not None:
            DBPrompts.delete(prompt_id)
            flash("Custom prompt deleted", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00018.value, "error")
        return redirect(url_for("index"))
    return redirect(url_for('prompts', type='custom'))