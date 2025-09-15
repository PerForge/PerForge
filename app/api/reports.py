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

"""
Reports API endpoints.
"""
import json
import logging
import importlib
import traceback
from flask import Blueprint, request, send_file
from app.backend.data_provider.data_provider import DataProvider
from app.backend.integrations.report_registry import ReportRegistry
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.templates.templates_db import DBTemplates
from app.backend.components.templates.template_groups_db import DBTemplateGroups
from app.backend.errors import ErrorMessages
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_OK, HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_INTERNAL_SERVER_ERROR
)

# Create a Blueprint for reports API
reports_api = Blueprint('reports_api', __name__)

def _ensure_report_types_loaded():
    """
    Dynamically import all report types to ensure they are registered.
    This avoids circular imports by only importing when needed.
    """
    report_modules = [
        'app.backend.integrations.pdf.pdf_report',
        'app.backend.integrations.smtp_mail.smtp_mail_report',
        'app.backend.integrations.azure_wiki.azure_wiki_report',
        'app.backend.integrations.atlassian_jira.atlassian_jira_report',
        'app.backend.integrations.atlassian_confluence.atlassian_confluence_report'
    ]

    for module_name in report_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            logging.warning(f"Could not import report module {module_name}: {e}")

@reports_api.route('/api/v1/tests/data', methods=['GET'])
@api_error_handler
def get_test_data():
    """
    Get test data for a specific data source.

    Query Parameters:
        source_type: The type of data source
        id: The ID of the data source

    Returns:
        A JSON response with test data
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        source_type = request.args.get('source_type')
        source_id = request.args.get('id')

        # Pagination parameters
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
        except ValueError:
            return api_response(
                message="Invalid pagination parameters",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_param", "message": "'page' and 'page_size' must be integers and > 0"}]
            )
        if page < 1 or page_size < 1:
            return api_response(
                message="Pagination parameters must be positive",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_param", "message": "'page' and 'page_size' must be positive"}]
            )


        if not source_type:
            return api_response(
                message="Missing source_type parameter",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_param", "message": "Missing source_type parameter"}]
            )

        ds_obj = DataProvider(project=project_id, source_type=source_type, id=source_id)

        # Retrieve all titles once and slice in-memory for pagination
        titles = ds_obj.get_tests_titles()
        total = len(titles)

        # If no titles are found, return an empty response immediately
        if total == 0:
            return api_response(data={
                "tests": [],
                "total": 0,
                "baseline_titles": [],
                "page": page,
                "page_size": page_size
            })

        # Determine slice of titles for current page
        start = (page - 1) * page_size
        end = start + page_size
        page_titles = titles[start:end]

        # Fetch only logs for the page titles via DB-level filtering
        tests = ds_obj.get_test_log(test_titles=page_titles)

        # Format timestamps to sortable format for better table sorting
        for test in tests:
            if 'start_time' in test and test['start_time']:
                # Convert pandas Timestamp to sortable string format
                if hasattr(test['start_time'], 'strftime'):
                    test['start_time'] = test['start_time'].strftime('%Y-%m-%d %H:%M:%S')

            if 'end_time' in test and test['end_time']:
                # Convert pandas Timestamp to sortable string format
                if hasattr(test['end_time'], 'strftime'):
                    test['end_time'] = test['end_time'].strftime('%Y-%m-%d %H:%M:%S')

        return api_response(data={
            "tests": tests,
            "total": total,
            "baseline_titles": titles,
            "page": page,
            "page_size": page_size
        })
    except Exception as e:
        logging.error(f"Error loading tests: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00008.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "test_data_error", "message": str(e)}]
        )

@reports_api.route('/api/v1/reports', methods=['POST'])
@api_error_handler
def generate_report():
    """
    Generate a report.

    Request Body:
        tests: List of tests to include in the report
        db_config: Database ID
        template_group: Template group ID
        output_id: Output ID
        integration_type: Integration type

    Returns:
        A JSON response with the generated report or a file download
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        data = request.get_json()
        if not data:
            return api_response(
                message="No data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No data provided"}]
            )

        output_config = data.get('output_config', {})

        if "output_id" not in output_config:
            return api_response(
                message="Missing output_id parameter",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_param", "message": "Missing output_id parameter"}]
            )

        template_group = data.get("template_group")
        action_id = output_config.get("output_id")
        integration_type = output_config.get("integration_type")

        # Determine action type
        if action_id == "pdf_report" or action_id == "delete":
            action_type = action_id
        elif integration_type:
            action_type = integration_type
        else:
            return api_response(
                message="Could not determine report type",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_report_type", "message": "Could not determine report type"}]
            )

        # Handle PDF report (special case)
        if action_type == "pdf_report":
            # Ensure all report types are loaded before getting the PDF report instance
            _ensure_report_types_loaded()
            project_id = get_project_id()
            theme = output_config.get('theme', 'dark')
            # Get the PDF report instance from the registry
            pdf = ReportRegistry.get_report_instance(action_type, project_id)
            if not pdf:
                return api_response("error", "PDF report type not found in registry.", HTTP_NOT_FOUND)

            # Generate the report
            result = pdf.generate_report(data["tests"], template_group, theme=theme)

            pdf.pdf_io.seek(0)
            # Convert the result to a JSON string and include it in the headers
            result_json = json.dumps(result)

            response = send_file(
                pdf.pdf_io,
                mimetype="application/pdf",
                download_name=f'{result["filename"]}.pdf',
                as_attachment=True
            )
            response.headers['X-Result-Data'] = result_json
            return response

        elif action_type == "delete":
            try:
                for test in data['tests']:
                    db_config = test.get('db_config')
                    dp = DataProvider(project=project_id, source_type=db_config['source_type'], id=db_config['id'])
                    dp.ds_obj.delete_test_data(test['test_title'])
                return api_response(message="Tests deleted successfully", status=HTTP_OK)
            except Exception as e:
                logging.error(f"Error deleting tests: {str(e)}")
                return api_response(
                    message="Error deleting tests",
                    status=HTTP_BAD_REQUEST,
                    errors=[{"code": "delete_error", "message": str(e)}]
                )

        # Handle standard report generation using the registry
        elif action_type:
            # Ensure all report types are loaded before validation
            _ensure_report_types_loaded()

            if ReportRegistry.is_valid_report_type(action_type):
                report_instance = ReportRegistry.get_report_instance(action_type, project_id)
                result = report_instance.generate_report(data["tests"], action_id, template_group)
                return api_response(data=result)
            else:
                return api_response(
                    message=f"Invalid action type: {action_type}",
                    status=HTTP_BAD_REQUEST,
                    errors=[{"code": "invalid_action", "message": f"Invalid action type: {action_type}"}]
                )
        else:
            return api_response(
                message=f"Invalid action type: {action_type}",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_action", "message": f"Invalid action type: {action_type}"}]
            )
    except Exception as e:
        logging.error(f"Error generating report: {traceback.format_exc()}")
        return api_response(
            message=ErrorMessages.ER00011.value,
            status=HTTP_INTERNAL_SERVER_ERROR,
            errors=[{"code": "report_error", "message": str(traceback.format_exc())}]
        )

@reports_api.route('/api/v1/reports/data', methods=['POST'])
@api_error_handler
def get_report_data():
    """
    Get report data for a specific test.

    Request Body:
        test_title: The title of the test
        source_type: The type of data source (e.g., "influxdb_v2", "timescaledb")
        id: Optional ID for the data source

    Returns:
        A JSON response with the report data including metrics, analysis, statistics, etc.
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        project_data = DBProjects.get_config_by_id(id=project_id)
        if not project_data:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )

        data = request.json
        if not data:
            return api_response(
                message="No data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No data provided"}]
            )

        test_title = data.get('test_title')
        source_type = data.get('source_type')
        source_id = data.get('id')

        if not test_title:
            return api_response(
                message="Missing test_title parameter",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_param", "message": "Missing test_title parameter"}]
            )

        if not source_type:
            return api_response(
                message="Missing source_type parameter",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_param", "message": "Missing source_type parameter"}]
            )

        dp = DataProvider(project=project_id, source_type=source_type, id=source_id)
        metrics, analysis, statistics, test_details, aggregated_table, summary, performance_status = dp.collect_test_data_for_report_page(test_title=test_title)

        response_data = {
            'data': metrics,
            'analysis': analysis,
            'statistics': statistics,
            'test_details': test_details,
            'aggregated_table': aggregated_table,
            'summary': summary,
            'performance_status': performance_status,
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

        return api_response(data=response_data)
    except Exception as e:
        logging.error(f"Error getting report data: {str(e)}")
        return api_response(
            message="Error retrieving report data",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "report_error", "message": str(e)}]
        )
