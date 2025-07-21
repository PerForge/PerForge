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
Projects API endpoints.
"""
import logging
from flask import Blueprint, request, make_response

from app.api.base import (
    api_response, api_error_handler,
    HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.secrets.secrets_db import DBSecrets
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.components.nfrs.nfrs_db import DBNFRs
from app.backend.components.graphs.graphs_db import DBGraphs
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.components.templates.templates_db import DBTemplates
from app.backend.errors import ErrorMessages
from app import db

# Create a Blueprint for projects API
projects_api = Blueprint('projects_api', __name__)

@projects_api.route('/api/v1/projects', methods=['GET'])
@api_error_handler
def get_projects():
    """
    Get all projects.

    Returns:
        A JSON response with all projects
    """
    project_configs = DBProjects.get_configs()
    return api_response(data={"projects": project_configs})

@projects_api.route('/api/v1/projects/<project_id>', methods=['GET'])
@api_error_handler
def get_project(project_id):
    """
    Get a specific project by ID.

    Args:
        project_id: The ID of the project to get

    Returns:
        A JSON response with the project data
    """
    try:
        project_data = DBProjects.get_config_by_id(id=project_id)
        if not project_data:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )
        return api_response(data={"project": project_data})
    except Exception as e:
        logging.error(f"Error getting project: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00013.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

@projects_api.route('/api/v1/projects', methods=['POST'])
@api_error_handler
def create_project():
    """
    Create a new project.

    Returns:
        A JSON response with the new project ID
    """
    try:
        project_data = request.get_json()
        if not project_data:
            return api_response(
                message="No project data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No project data provided"}]
            )

        # Close any existing sessions before creating a new project
        db.session.close()
        db.engine.dispose()

        # Extract flag whether to create example secrets
        create_examples_flag = project_data.pop("create_examples", False)

        new_project_id = DBProjects.save(data=project_data)

        # If requested, generate example data for the new project
        if create_examples_flag:
            _create_example_data(new_project_id)



        return api_response(
            data={"project_id": new_project_id},
            message="Project created successfully",
            status=HTTP_CREATED
        )
    except ValueError as e:
        logging.error(f"Error creating project: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00014.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "validation_error", "message": str(e)}]
        )
    except AttributeError as e:
        logging.error(f"Error creating project: {str(e)}")
        return api_response(
            message="Database configuration error",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "db_config_error", "message": f"Database configuration error: {str(e)}"}]
        )
    except Exception as e:
        logging.error(f"Error creating project: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00014.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

@projects_api.route('/api/v1/projects/<project_id>', methods=['PUT'])
@api_error_handler
def update_project(project_id):
    """
    Update an existing project.

    Args:
        project_id: The ID of the project to update

    Returns:
        A JSON response with the updated project
    """
    try:
        project_data = request.get_json()
        if not project_data:
            return api_response(
                message="No project data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No project data provided"}]
            )

        # Check if project exists
        existing_project = DBProjects.get_config_by_id(id=project_id)
        if not existing_project:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )

        # Update project ID to match URL
        project_data['id'] = project_id
        DBProjects.update(data=project_data)

        return api_response(
            data={"project_id": project_id},
            message="Project updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating project: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00014.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

@projects_api.route('/api/v1/projects/<project_id>', methods=['DELETE'])
@api_error_handler
def delete_project(project_id):
    """
    Delete a project.

    Args:
        project_id: The ID of the project to delete

    Returns:
        A JSON response confirming deletion
    """
    try:
        # Check if project exists
        existing_project = DBProjects.get_config_by_id(id=project_id)
        if not existing_project:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )

        DBProjects.delete(id=project_id)
        return api_response(
            message="Project deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting project: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00015.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

@projects_api.route('/api/v1/projects/<project_id>/output-configs', methods=['GET'])
@api_error_handler
def get_project_output_configs(project_id):
    """
    Get output configurations for a project.

    Args:
        project_id: The ID of the project

    Returns:
        A JSON response with the output configurations
    """
    try:
        # Check if project exists
        existing_project = DBProjects.get_config_by_id(id=project_id)
        if not existing_project:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )

        output_configs = DBProjects.get_project_output_configs(id=project_id)
        return api_response(data={"output_configs": output_configs})
    except Exception as e:
        logging.error(f"Error getting project output configs: {str(e)}")
        return api_response(
            message="Error retrieving output configurations",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

@projects_api.route('/api/v1/projects/set-active/<project_id>', methods=['POST'])
@api_error_handler
def set_active_project(project_id):
    """
    Set the active project by setting a cookie.

    Args:
        project_id: The ID of the project to set as active

    Returns:
        A JSON response confirming the active project was set
    """
    try:
        # Check if project exists
        existing_project = DBProjects.get_config_by_id(id=project_id)
        if not existing_project:
            return api_response(
                message=f"Project with ID {project_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
            )

        # Log the schema switch for debugging purposes
        logging.info(f"Switching active project to ID: {project_id}, Name: {existing_project['name']}")

        # Create response with cookie
        response = api_response(
            data={"project_id": project_id, "project_name": existing_project['name']},
            message="Active project set successfully"
        )

        # Convert to a Flask response to set the cookie
        flask_response = make_response(response)
        flask_response.set_cookie(key='project', value=project_id, max_age=None)
        flask_response.set_cookie(key='project_name', value=existing_project['name'], max_age=None)

        return flask_response
    except Exception as e:
        logging.error(f"Error setting active project: {str(e)}")
        return api_response(
            message="Error setting active project",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "project_error", "message": str(e)}]
        )

def _create_example_data(project_id: str) -> None:
    """Create example secrets and integrations for a newly created project.

    Args:
        project_id: The ID of the project that the examples belong to.
    """
    try:
        influxdb_token_example = DBSecrets.save({
            "id": None,
            "key": "[EXAMPLE] INFLUXDB TOKEN FROM DOCKER-COMPOSE",
            "value": "DqwGq5e7Avv9gKYi2NtRtRenOxbvEqXMtg-r4WjNxYlerHMfikeLtCTJwSTzk-5NheVXTOFi0qug5jRGuh8-mw==",
            "project_id": project_id
        })

        fake_token_example = DBSecrets.save({
            "id": None,
            "key": "[EXAMPLE] FAKE TOKEN",
            "value": "123",
            "project_id": project_id
        })

        # InfluxDB integration example
        DBInfluxdb.save(project_id, {
            "id": None,
            "name": "[EXAMPLE] INTEGRATION WITH INFLUXDB FROM DOCKER-COMPOSE",
            "url": "http://influxdb:8086",
            "org_id": "perforge",
            "token": influxdb_token_example,
            "timeout": 60000,
            "bucket": "jmeter",
            "listener": "org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient",
            "tmz": "UTC",
            "test_title_tag_name": "testTitle",
            "is_default": True
        })

        # Grafana integration example
        grafana_integration_example = DBGrafana.save(project_id, {
            "id": None,
            "name": "[EXAMPLE] INTEGRATION WITH GRAFANA FROM DOCKER-COMPOSE",
            "server": "http://grafana:8086",
            "org_id": "1",
            "token": fake_token_example,
            "test_title": "testTitle",
            "baseline_test_title": "baseline_testTitle",
            "is_default": True,
            "dashboards": [
                {
                    "id": 1,
                    "content": "/d/jmeter-test-results-standard-listener/jmeter-test-results-standard-listener",
                    "grafana_id": None
                },
                {
                    "id": 2,
                    "content": "/d/jmeter-test-comparison-standard-listener/jmeter-tests-comparison-standard-listener",
                    "grafana_id": None
                }
            ]
        })

        # NFR example
        nfr_example_id = DBNFRs.save(project_id, {
            "id": None,
            "name": "[EXAMPLE] NFR",
            "metric_type": "backend",
            "rows": [
                {
                    "regex": False,
                    "scope": "each",
                    "metric": "avg",
                    "operation": "<",
                    "threshold": 500,
                    "weight": None
                },
                {
                    "regex": False,
                    "scope": "Dummy Sampler 1",
                    "metric": "pct50",
                    "operation": "<",
                    "threshold": 700,
                    "weight": None
                },
                {
                    "regex": True,
                    "scope": "Dummy.*",
                    "metric": "pct90",
                    "operation": "<",
                    "threshold": 1000,
                    "weight": None
                }
            ]
        })

        grafana_dashboard_id = DBGrafana.get_config_by_id(project_id, id=grafana_integration_example)['dashboards'][0]['id']
        # Graph example
        graph_example_id = DBGraphs.save(project_id, {
            "id": None,
            "name": "[EXAMPLE] TOTAL THROUGHPUT",
            "grafana_id": grafana_integration_example,
            "dash_id": grafana_dashboard_id,
            "view_panel": "6",
            "width": "1000",
            "height": "500",
            "custom_vars": "",
            "prompt_id": None
        })

        # Template example
        DBTemplates.save(project_id, {
            "id": None,
            "name": "[EXAMPLE] TEMPLATE COPY",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": 8,
            "aggregated_prompt_id": 11,
            "system_prompt_id": 13,
            "data": [
                {
                    "content": "Available variables:\nCommon variables:\n${current_test_title} Name of the current test.\n${current_duration} Duration of the current test in seconds.\n${current_start_time} Start time of the current test.\n${current_end_time} End time of the current test.\n${baseline_test_title} Name of the baseline test.\n${baseline_duration} Duration of the baseline test in seconds.\n${baseline_start_time} Start time of the baseline test.\n${baseline_end_time} End time of the baseline test.\nBackend variables:\n${current_max_active_users} Max active users for the current test.\n${current_errors_pct_stats} Error percentage for the current test.\n${current_median_response_time_stats} Median response time for the current test.\n${current_median_throughput} Median throughput for the current test.\n${current_pct90_response_time_stats} 90th percentile response time for the current test.\n${current_grafana_link} Grafana link for the current test.\n${baseline_max_active_users} Max active users for the baseline test.\n${baseline_errors_pct_stats} Error percentage for the baseline test.\n${baseline_median_response_time_stats} Median response time for the baseline test.\n${baseline_median_throughput} Median throughput for the baseline test.\n${baseline_pct90_response_time_stats} 90th percentile response time for the baseline test.\n${baseline_grafana_link} Grafana link for the baseline test.\nSummary variables:\n${nfr_summary} Summary of Non-Functional Requirements validation.\n${ml_summary} Summary of ML-based anomaly detection.\n${ai_summary} Summary generated by AI based on test results.",
                    "graph_id": None,
                    "template_id": None,
                    "type": "text"
                },
                {
                    "content": None,
                    "graph_id": graph_example_id,
                    "template_id": None,
                    "type": "graph"
                }
            ]
        })

    except Exception as exc:
        logging.warning(f"Failed to create example data for project {project_id}: {exc}")
