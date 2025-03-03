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

from app                                     import app
from app.backend.data_provider.data_provider import DataProvider
from flask                                   import render_template, request, jsonify

@app.route('/api/data', methods=['POST'])
def get_data():
    project = request.cookies.get('project')
    data = request.json
    source_type = data.get('source_type')
    id = data.get('id')
    test_title = data.get('test_title')
    dp = DataProvider(project=project, source_type=source_type, id=id)
    metrics, analysis, statistics, test_details, aggregated_table, summary, performance_status = dp.collect_test_data_for_report_page(test_title=test_title)
    response = {
        'data': metrics,
        'analysis': analysis,
        'statistics': statistics,
        'test_details': test_details,
        'aggregated_table': aggregated_table,
        'summary': summary,
        'performance_status':performance_status,
        'styling': {
            'paper_bgcolor': 'rgba(0,0,0,0)',  # Transparent background
            'plot_bgcolor': 'rgba(0,0,0,0)',   # Transparent background
            'title_font_color': '#ced4da',
            'axis_font_color': '#ced4da',
            'hover_bgcolor': '#333',
            'hover_bordercolor': '#fff',
            'hover_font_color': '#fff',
            'line_shape': 'spline',
            'line_width': 2,
            'marker_size': 8,
            'marker_color_normal': 'rgba(75, 192, 192, 1)',
            'marker_color_anomaly': 'red',
            'yaxis_tickformat': ',.0f',
            'font_family': 'Nunito Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol;',
            'yaxis_tickfont_size': 10,
            'xaxis_tickfont_size': 10,
            'title_size': 13,
            'gridcolor': '#444'  # Grid color
        },
        'layout': {
            'margin': {
                'l': 50,
                'r': 50,
                'b': 50,
                't': 50,
                'pad': 1
            },
            'autosize': True,
            'responsive': True
        }
    }
    return jsonify(response)

@app.route('/report')
def report():
    test_title = request.args.get('test_title')
    source_type = request.args.get('source_type')
    id = request.args.get('id')
    return render_template('home/report.html',test_title=test_title, source_type=source_type, id=id)