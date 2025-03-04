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

from flask import render_template, request
from app   import app

@app.route('/report', methods=['GET'])
def report_page():
    """
    Render the report page template.

    Query Parameters:
        test_title: The title of the test
        source_type: The type of data source
        id: Optional ID for the data source

    Returns:
        Rendered report.html template
    """
    test_title = request.args.get('test_title', '')
    source_type = request.args.get('source_type', '')
    id = request.args.get('id', None)

    return render_template('home/report.html',
                          test_title=test_title,
                          source_type=source_type,
                          id=id)
