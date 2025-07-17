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

from app                                                                       import app
from app.backend.components.projects.projects_db                               import DBProjects
from app.backend.components.templates.templates_db                             import DBTemplates
from app.backend.components.templates.template_groups_db                       import DBTemplateGroups
from app.backend.errors                                                        import ErrorMessages
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db             import DBInfluxdb
from flask                                                                     import render_template, request, url_for, redirect, flash


@app.route('/tests', methods=['GET'])
def get_tests():
    """
    Render the tests page with necessary configurations.

    This endpoint is maintained for backward compatibility.
    New implementations should use the RESTful API endpoint /api/v1/tests.
    """
    try:
        project_id             = request.cookies.get('project')
        influxdb_configs       = DBInfluxdb.get_configs(project_id=project_id)
        db_configs = []
        for config in influxdb_configs:
            db_configs.append({ "id": config["id"], "name": config["name"], "source_type": "influxdb_v2", "listener": config["listener"]})
        template_configs       = DBTemplates.get_configs_brief(project_id=project_id)
        template_group_configs = DBTemplateGroups.get_configs(project_id=project_id)
        output_configs         = DBProjects.get_project_output_configs(project_id=project_id)
        return render_template('home/tests.html', db_configs=db_configs, templates = template_configs, template_groups = template_group_configs, output_configs=output_configs)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00009.value, "error")
        return redirect(url_for("index"))
