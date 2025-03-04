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

from app                                       import app
from app.backend.errors                        import ErrorMessages
from flask                                     import render_template, request, url_for, redirect, flash


@app.route('/templates', methods=['GET'])
def get_templates():
    try:
        return render_template('home/templates.html')
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00007.value, "error")
        return redirect(url_for("index"))

@app.route('/template', methods=['GET'])
def template():
    try:
        template_config = request.args.get('template_config')
        return render_template('home/template.html', template_config=template_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00002.value, "error")
        return redirect(url_for("get_templates"))

@app.route('/template-group', methods=['GET'])
def template_group():
    try:
        template_group_config = request.args.get('template_group_config')
        return render_template('home/template-group.html', template_group_config=template_group_config)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00005.value, "error")
        return redirect(url_for("get_templates"))
