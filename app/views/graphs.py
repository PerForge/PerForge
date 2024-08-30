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

from app                                             import app
from app.forms                                       import GraphForm
from app.backend.errors                              import ErrorMessages
from app.backend.integrations.grafana.grafana_config import GrafanaConfig
from app.backend.components.graphs.graph_config      import GraphConfig
from app.backend.components.prompts.prompt_config    import PromptConfig
from flask                                           import render_template, request, url_for, redirect, flash


@app.route('/graphs', methods=['GET'])
def get_graphs():
    try:
        project         = request.cookies.get('project')
        prompt_obj      = PromptConfig(project)
        graph_prompts   = prompt_obj.get_prompts_by_place("graph")
        form_for_graphs = GraphForm(request.form)
        graphs_list     = GraphConfig.get_all_graphs(project)
        grafana_configs = GrafanaConfig.get_grafana_config_names_ids_and_dashboards(project)
        return render_template('home/graphs.html', graphs_list=graphs_list, graph_prompts=graph_prompts, form_for_graphs=form_for_graphs, grafana_configs=grafana_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_GRAPHS.value, "error")
    return redirect(url_for('index'))

@app.route('/save-graph', methods=['POST'])
def save_graph():
    try:
        project = request.cookies.get('project')
        if request.method == "POST":
            original_graph_id = request.form.to_dict().get("id")
            graph_id          = GraphConfig.save_graph_config(project, request.form.to_dict())
            if original_graph_id == graph_id:
                flash("Graph updated.", "info")
            else:
                flash("Graph added.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.SAVE_GRAPH.value, "error")
    return redirect(url_for('get_graphs'))

@app.route('/delete-graph', methods=['GET'])
def delete_graph():
    try:
        project  = request.cookies.get('project')
        graph_id = request.args.get('graph_id')
        if graph_id is not None:
            GraphConfig.delete_graph_config(project, graph_id)
            flash("Graph deleted", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DELETE_GRAPH.value, "error")
    return redirect(url_for('get_graphs'))