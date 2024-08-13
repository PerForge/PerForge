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
from app.backend.ai_support.prompts import Prompt
from app.forms                      import PromptForm
from app.backend.errors             import ErrorMessages


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