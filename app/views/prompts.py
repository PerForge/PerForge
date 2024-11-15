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
        project_id = request.cookies.get('project')
        form_data  = request.form.to_dict()

        original_prompt_id = form_data.get("id")
        prompt_name        = form_data.get("name")
        prompt_type        = form_data.get("type")
        prompt_place       = form_data.get("place")
        prompt_text        = form_data.get("prompt")
        scope              = form_data.get("project_id")

        prompt_project_id = project_id if scope == "project" else None
        if original_prompt_id:
            DBPrompts.update(
                id          = original_prompt_id,
                name        = prompt_name,
                type        = prompt_type,
                place       = prompt_place,
                prompt_text = prompt_text,
                project_id  = prompt_project_id
            )
            flash("Custom prompt updated.", "info")
        else:
            prompt_obj = DBPrompts(
                name       = prompt_name,
                type       = prompt_type,
                place      = prompt_place,
                prompt     = prompt_text,
                project_id = prompt_project_id
            )
            prompt_obj.save()
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