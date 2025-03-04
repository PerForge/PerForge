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

from app                                         import app
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.prompts.prompts_db   import DBPrompts
from app.backend.components.graphs.graphs_db     import DBGraphs
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.errors                          import ErrorMessages
from app.forms                                   import GraphForm
from flask                                       import render_template, request, url_for, redirect, flash


@app.route('/graphs', methods=['GET'])
def get_graphs():
    try:
        project_id      = request.cookies.get('project')
        project_data    = DBProjects.get_config_by_id(id=project_id)
        graph_configs   = DBGraphs.get_configs(schema_name=project_data['name'])
        prompt_configs  = DBPrompts.get_configs_by_place(project_id=project_id, place="graph")
        form            = GraphForm(request.form)
        grafana_configs = DBGrafana.get_configs(schema_name=project_data['name'])
        return render_template('home/graphs.html', graphs_list=graph_configs, graph_prompts=prompt_configs, form_for_graphs=form, grafana_configs=grafana_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00025.value, "error")
    return redirect(url_for('index'))
