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

from app import app
from app.backend.errors import ErrorMessages
from flask import render_template, request, url_for, redirect, flash


@app.route('/tests', methods=['GET'])
def get_tests():
    """
    Render the tests page with necessary configurations.

    This endpoint is maintained for backward compatibility.
    New implementations should use the RESTful API endpoint /api/v1/tests.
    """
    try:
        return render_template('home/tests.html')
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00009.value, "error")
        return redirect(url_for("index"))
