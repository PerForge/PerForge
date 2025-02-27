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

from app         import app
from app.backend import pkg
from flask       import render_template, jsonify


@app.route('/view-logs', methods=['GET'])
def view_logs():
    try:
        with open("./app/logs/info.log", "r", errors='ignore') as file:
            log_lines = file.readlines()
    except FileNotFoundError:
        log_lines = ["Log file not found."]
    log_lines = log_lines[-150:]
    logs      = ''.join(log_lines)
    return render_template('home/logs.html', logs=logs)

@app.route('/check_new_version')
def check_version():
    try:
        current_version = pkg.get_current_version_from_file()
        new_version     = pkg.get_new_version_from_docker_hub(current_version)
        if current_version != new_version:
            if pkg.is_valid_new_version_from_docker_hub(current_version, new_version):
                return jsonify({
                    "new_version_released": True,
                    "new_version": new_version
                })
        return jsonify({
            "new_version_released": False
        })
    except Exception:
        return jsonify({
            "new_version_released": False
        })