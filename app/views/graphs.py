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

from app                           import app
from app.forms                     import GraphForm
from app.backend.errors            import ErrorMessages
from app.backend.database.projects import DBProjects
from app.backend.database.prompts  import DBPrompts
from app.backend.database.graphs   import DBGraphs
from app.backend.database.grafana  import DBGrafana
from flask                         import render_template, request, url_for, redirect, flash


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

@app.route('/save-graph', methods=['POST'])
def save_graph():
    try:
        form = GraphForm(request.form)
        if form.validate_on_submit():
            project_id   = request.cookies.get('project')
            project_data = DBProjects.get_config_by_id(id=project_id)
            graph_data   = form.data
            if graph_data['id']:
                DBGraphs.update(
                    schema_name = project_data['name'],
                    id          = graph_data['id'],
                    name        = graph_data['name'],
                    grafana_id  = graph_data['grafana_id'],
                    dash_id     = graph_data['dash_id'],
                    view_panel  = graph_data['view_panel'],
                    width       = graph_data['width'],
                    height      = graph_data['height'],
                    custom_vars = graph_data['custom_vars'] if graph_data['custom_vars'] else None,
                    prompt_id   = graph_data['prompt_id'] if graph_data['prompt_id'] else None
                )
                flash("Graph updated.", "info")
            else:
                graph_obj = DBGraphs(
                    name        = graph_data['name'],
                    grafana_id  = graph_data['grafana_id'],
                    dash_id     = graph_data['dash_id'],
                    view_panel  = graph_data['view_panel'],
                    width       = graph_data['width'],
                    height      = graph_data['height'],
                    custom_vars = graph_data['custom_vars'] if graph_data['custom_vars'] else None,
                    prompt_id   = graph_data['prompt_id'] if graph_data['prompt_id'] else None
                )
                graph_obj.save(schema_name=project_data['name'])
                flash("Graph added.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00026.value, "error")
    return redirect(url_for('get_graphs'))

@app.route('/delete-graph', methods=['GET'])
def delete_graph():
    try:
        project_id   = request.cookies.get('project')
        project_data = DBProjects.get_config_by_id(id=project_id)
        graph_id     = request.args.get('graph_id')
        if graph_id is not None:
            DBGraphs.delete(schema_name=project_data['name'], id=graph_id)
            flash("Graph deleted", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00027.value, "error")
    return redirect(url_for('get_graphs'))