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

import logging
import traceback

from app import app
from app.backend.errors import ErrorMessages
from flask import flash, redirect, url_for, render_template, request


@app.route('/advanced-settings', methods=['GET'])
def advanced_settings():
    """
    Render the Advanced Settings page for configuring project-specific parameters.

    Settings include:
    - ML Analysis parameters (contamination, thresholds, windows, etc.)
    - Transaction Status parameters (NFR, baseline, ML checks)
    - Data Aggregation parameters (default aggregation type)
    """
    try:
        # Get current project info from cookies for display
        project_name = request.cookies.get('project_name', 'No Project Selected')

        return render_template(
            'home/settings.html',
            project_name=project_name
        )
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00016.value, "error")
        return redirect(url_for("index"))
