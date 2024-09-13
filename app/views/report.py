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

from app                                    import app
from app.backend.errors                     import ErrorMessages
from app.backend.components.nfrs.nfr_config import NFRConfig
from flask                                  import render_template, request, url_for, redirect, flash, jsonify
from app.backend.analysis.prepare_data      import DataPreparation


@app.route('/api/data')
def get_data():
    project = request.cookies.get('project')
    dp = DataPreparation(project=project)
    test_title = request.args.get('test_title')
    df = dp.get_test_data(test_title=test_title)
    df_reset = df.reset_index()
    response = {
        'data': df_reset.to_dict(orient='records'),
        'analysis': dp.analysis
    }
    return jsonify(response)

@app.route('/report')
def report():
    test_title = request.args.get('test_title')
    return render_template('home/report.html',test_title=test_title)