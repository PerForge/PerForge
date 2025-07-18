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
from app.backend.components.projects.projects_db import DBProjects
from app.backend.errors                          import ErrorMessages
from flask                                       import render_template, url_for, redirect, flash


@app.route('/choose-project', methods=['GET'])
def choose_project():
    try:
        projects = DBProjects.get_configs()
        return render_template('home/choose-project.html', projects=projects)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00016.value, "error")
    return redirect(url_for('index'))
