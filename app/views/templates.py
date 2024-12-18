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

from app                                                 import app
from app.backend.components.projects.projects_db         import DBProjects
from app.backend.components.templates.templates_db       import DBTemplates
from app.backend.components.templates.template_groups_db import DBTemplateGroups
from app.backend.components.nfrs.nfrs_db                 import DBNFRs
from app.backend.components.prompts.prompts_db           import DBPrompts
from app.backend.components.graphs.graphs_db             import DBGraphs
from app.backend.errors                                  import ErrorMessages
from flask                                               import render_template, request, url_for, redirect, flash, jsonify


@app.route('/templates', methods=['GET', 'POST'])
def get_templates():
    try:
        project_id                     = request.cookies.get('project')
        project_data                   = DBProjects.get_config_by_id(id=project_id)
        template_configs               = DBTemplates.get_configs(schema_name=project_data['name'])
        template_group_configs         = DBTemplateGroups.get_configs(schema_name=project_data['name'])
        nfr_configs                    = DBNFRs.get_configs(schema_name=project_data['name'])
        template_prompt_configs        = DBPrompts.get_configs_by_place(project_id=project_id, place="template")
        aggregated_data_prompt_configs = DBPrompts.get_configs_by_place(project_id=project_id, place="aggregated_data")
        template_group_prompt_configs  = DBPrompts.get_configs_by_place(project_id=project_id, place="template_group")
        return render_template('home/templates.html', templates=template_configs, template_groups=template_group_configs, nfrs=nfr_configs, template_prompts=template_prompt_configs, aggregated_data_prompts=aggregated_data_prompt_configs, template_group_prompts=template_group_prompt_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00007.value, "error")
        return redirect(url_for("index"))

@app.route('/template', methods=['GET', 'POST'])
def template():
    try:
        project_id                     = request.cookies.get('project')
        project_data                   = DBProjects.get_config_by_id(id=project_id)
        template_config                = request.args.get('template_config')
        graph_configs                  = DBGraphs.get_configs(schema_name=project_data['name'])
        nfr_configs                    = DBNFRs.get_configs(schema_name=project_data['name'])
        template_prompt_configs        = DBPrompts.get_configs_by_place(project_id=project_id, place="template")
        aggregated_data_prompt_configs = DBPrompts.get_configs_by_place(project_id=project_id, place="aggregated_data")
        system_prompt_configs          = DBPrompts.get_configs_by_place(project_id=project_id, place="system")
        template_data                  = []
        if template_config is not None:
            template_data = DBTemplates.get_config_by_id(schema_name=project_data['name'], id=template_config)
        if request.method == "POST":
            try:
                template_data = request.get_json()

                for key, value in template_data.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    if v == '':
                                        item[k] = None
                    elif value == '':
                        template_data[key] = None

                if template_data["id"]:
                    DBTemplates.update(
                        schema_name = project_data['name'],
                        data        = template_data
                    )
                    flash("Template updated.","info")
                else:
                    DBTemplates.save(
                        schema_name = project_data['name'],
                        data        = template_data
                    )
                    flash("Template added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00001.value, "error")
            return jsonify({'redirect_url': 'templates'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00002.value, "error")
        return redirect(url_for("get_templates"))
    return render_template('home/template.html', template_config=template_config, graphs=graph_configs, nfrs=nfr_configs, template_data=template_data, template_prompts=template_prompt_configs, aggregated_data_prompts=aggregated_data_prompt_configs, system_prompts=system_prompt_configs)

@app.route('/delete-template', methods=['GET'])
def delete_template():
    try:
        template_config = request.args.get('template_config')
        project_id      = request.cookies.get('project')
        project_data    = DBProjects.get_config_by_id(id=project_id)
        if template_config is not None:
            DBTemplates.delete(schema_name=project_data['name'], id=template_config)
            flash("Template is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00003.value, "error")
    return redirect(url_for("get_templates"))

@app.route('/template-group', methods=['GET', 'POST'])
def template_group():
    try:
        project_id                    = request.cookies.get('project')
        project_data                  = DBProjects.get_config_by_id(id=project_id)
        template_group_config         = request.args.get('template_group_config')
        template_configs              = DBTemplates.get_configs(schema_name=project_data['name'])
        template_group_prompt_configs = DBPrompts.get_configs_by_place(project_id=project_id, place="template_group")
        template_group_data           = []
        if template_group_config is not None:
            template_group_data = DBTemplateGroups.get_config_by_id(schema_name=project_data['name'], id=template_group_config)
        if request.method == "POST":
            try:
                template_group_data = request.get_json()

                for key, value in template_group_data.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    if v == '':
                                        item[k] = None
                    elif value == '':
                        template_group_data[key] = None

                if template_group_data["id"]:
                    DBTemplateGroups.update(
                        schema_name = project_data['name'],
                        data        = template_group_data
                    )
                    flash("Template group updated.","info")
                else:
                    DBTemplateGroups.save(
                        schema_name = project_data['name'],
                        data        = template_group_data
                    )
                    flash("Template added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00004.value, "error")
            return jsonify({'redirect_url': 'templates'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00005.value, "error")
        return redirect(url_for("get_templates"))
    return render_template('home/template-group.html', template_group_config=template_group_config,templates=template_configs, template_group_data=template_group_data, template_group_prompts=template_group_prompt_configs)

@app.route('/delete-template-group', methods=['GET'])
def delete_template_group():
    try:
        template_group_config = request.args.get('template_group_config')
        project_id            = request.cookies.get('project')
        project_data          = DBProjects.get_config_by_id(id=project_id)
        if template_group_config is not None:
            DBTemplateGroups.delete(schema_name=project_data['name'], id=template_group_config)
            flash("Template group is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00006.value, "error")
    return redirect(url_for("get_templates"))
