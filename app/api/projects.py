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
            "server": "http://grafana:3000",
            "org_id": "1",
            "token": fake_token_example,
            "test_title": "testTitle",
            "baseline_test_title": "baseline_testTitle",
            "is_default": True,
            "dashboards": [
                {
                    "id": 1,
                    "content": "/d/jmeter-test-results/jmeter-test-results",
                    "grafana_id": None
                },
                {
                    "id": 2,
                    "content": "/d/jmeter-test-comparison/jmeter-tests-comparison",
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
                    "threshold": 500
                },
                {
                    "regex": False,
                    "scope": "Dummy Sampler 1",
                    "metric": "pct50",
                    "operation": "<",
                    "threshold": 700
                },
                {
                    "regex": True,
                    "scope": "Dummy.*",
                    "metric": "pct90",
                    "operation": "<",
                    "threshold": 1000
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

        # Use existing default graphs (loaded via DBGraphs.load_default_graphs_from_yaml)
        default_graphs = []
        try:
            default_graph_data = DBGraphs.get_configs(project_id, include_defaults=True)
            default_graphs = [{'id': g['id'], 'name': g['name']} for g in default_graph_data if g.get('project_id') is None and g.get('type') == 'default']
        except Exception as e:
            logging.warning(f"Failed to fetch default graphs for project {project_id}: {e}")

        # Template example for Confluence
        confluence_template = {
            "id": None,
            "name": "[EXAMPLE] REPORT for Confluence",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT for Confluence",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": None,
            "aggregated_prompt_id": None,
            "system_prompt_id": None,
            "data": [
                {"content":"<h2>Executive summaries</h2>\nTimestamp when report was generated: ${report_timestamp}<br/>\n<strong>Current run:</strong> from ${current_start_time} to ${current_end_time}<br/>\n<strong>Baseline run:</strong> from ${baseline_start_time} to ${baseline_end_time}<br/>\n<h2>Summary</h2>\n<h3>AI insights</h3>\n<p>${ai_summary}</p>\n<h3>NFR compliance</h3>\n<ac:structured-macro ac:name=\"expand\" xmlns:ac=\"http://atlassian.com/schema/confluence/4/ac\">\n  <ac:parameter ac:name=\"title\">Click to open..</ac:parameter>\n  <ac:rich-text-body>\n${nfr_summary}\n</ac:rich-text-body>\n</ac:structured-macro>\n<h3>ML anomalies</h3>\n<ac:structured-macro ac:name=\"expand\" xmlns:ac=\"http://atlassian.com/schema/confluence/4/ac\">\n  <ac:parameter ac:name=\"title\">Click to open..</ac:parameter>\n  <ac:rich-text-body>\n${ml_summary}\n</ac:rich-text-body>\n</ac:structured-macro>\n<h2>Key KPI comparison</h2>\n<table>\n  <thead>\n    <tr><th>KPI</th><th>Baseline</th><th>Current</th></tr>\n  </thead>\n  <tbody>\n    <tr><td>Max active users</td>\n<td>${baseline_max_active_users}</td>\n<td>${current_max_active_users}</td></tr>\n    <tr><td>Median throughput (RPS)</td>\n<td>${baseline_median_throughput}</td>\n<td>${current_median_throughput}</td></tr>\n    <tr><td>Median response time (ms)</td>\n<td>${baseline_median_response_time_stats}</td>\n<td>${current_median_response_time_stats}</td></tr>\n    <tr><td>P90 response time (ms)</td>\n<td>${baseline_pct90_response_time_stats}</td>\n<td>${current_pct90_response_time_stats}</td></tr>\n    <tr><td>Error rate&nbsp;%</td>\n<td>${baseline_errors_pct_stats}</td>\n<td>${current_errors_pct_stats}</td></tr>\n  </tbody>\n</table>\n<h3>Grafana dashboards</h3>\n<ul>\n<li>Baseline: <a href=\"${baseline_grafana_link}\">baseline_grafana_link</a></li>\n<li>Current: <a href=\"${current_grafana_link}\">current_grafana_link</a></li>\n</ul>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h2>Example graph using Expand:</h2>\n<ac:structured-macro ac:name=\"expand\" xmlns:ac=\"http://atlassian.com/schema/confluence/4/ac\">\n  <ac:parameter ac:name=\"title\">Click to open..</ac:parameter>\n  <ac:rich-text-body>","graph_id":None,"template_id":None,"type":"text"},
                {"content":None,"graph_id":graph_example_id,"template_id":None,"type":"graph"},
                {"content":"</ac:rich-text-body>\n</ac:structured-macro>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h2>Aggregated data example in Expand</h2>\n<ac:structured-macro ac:name=\"expand\" xmlns:ac=\"http://atlassian.com/schema/confluence/4/ac\">\n  <ac:parameter ac:name=\"title\">Click to open..</ac:parameter>\n  <ac:rich-text-body>\n${aggregated_data_table_}\n</ac:rich-text-body>\n</ac:structured-macro>","graph_id":None,"template_id":None,"type":"text"}]
        }

        for default_graph in default_graphs:
            confluence_template['data'].append({"content":f"<h2>{default_graph['name']}</h2>","graph_id":None,"template_id":None,"type":"text"})
            confluence_template['data'].append({"content":None,"graph_id":default_graph['id'],"template_id":None,"type":"graph"})

        DBTemplates.save(project_id, confluence_template)

        # Template example for Jira
        jira_template = {
            "id": None,
            "name": "[EXAMPLE] REPORT for Jira",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT for Jira",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": None,
            "aggregated_prompt_id": None,
            "system_prompt_id": None,
            "data": [
                {"content":"h2. Executive summaries\n\nTimestamp when report was generated: ${report_timestamp}\\\n*Current run:* from ${current_start_time} to ${current_end_time}\\\n*Baseline run:* from ${baseline_start_time} to ${baseline_end_time}\n\nh2. Summary\n{code:title=AI insights|borderStyle=solid}\n${ai_summary}\n{code}\n\n{code:title=NFR compliance|borderStyle=solid}\n${nfr_summary}\n{code}\n\n{code:title=ML anomalies|borderStyle=solid}\n${ml_summary}\n{code}\n\nh2. Key KPI comparison\n\n|| KPI || Baseline || Current ||\n| Max active users | ${baseline_max_active_users} | ${current_max_active_users} |\n| Median throughput (RPS) | ${baseline_median_throughput} | ${current_median_throughput} |\n| Median response time (ms) | ${baseline_median_response_time_stats} | ${current_median_response_time_stats} |\n| P90 response time (ms) | ${baseline_pct90_response_time_stats} | ${current_pct90_response_time_stats} |\n| Error rate % | ${baseline_errors_pct_stats} | ${current_errors_pct_stats} |\n\nh3. Grafana dashboards\n\n*Baseline:* [baseline_grafana_link|${baseline_grafana_link}]. \\\n*Current:* [current_grafana_link|${current_grafana_link}].\n\nh2. Example graph","graph_id":None,"template_id":None,"type":"text"},
                {"content":None,"graph_id":graph_example_id,"template_id":None,"type":"graph"},
                {"content":"h2. Aggregated data\n${aggregated_data_table_}","graph_id":None,"template_id":None,"type":"text"}
                ]
        }

        for default_graph in default_graphs:
            jira_template['data'].append({"content":f"h2. {default_graph['name']}","graph_id":None,"template_id":None,"type":"text"})
            jira_template['data'].append({"content":None,"graph_id":default_graph['id'],"template_id":None,"type":"graph"})

        DBTemplates.save(project_id, jira_template)

        # Template example for Azure
        azure_template = {
            "id": None,
            "name": "[EXAMPLE] REPORT for Azure",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT for Azure",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": None,
            "aggregated_prompt_id": None,
            "system_prompt_id": None,
            "data": [
                {"content":"# Executive summaries\nTimestamp when report was generated: ${report_timestamp}  \n**Current run:** from ${current_start_time} to ${current_end_time}  \n**Baseline run:** from ${baseline_start_time} to ${baseline_end_time}  \n\n# Summary\n---\n## AI insights  \n${ai_summary}  \n\n## NFR compliance  \n```${nfr_summary}```\n\n## ML anomalies  \n```${ml_summary}```\n\n## Key KPI comparison  \n| KPI                      | Baseline                      | Current                       |\n|---------------------------|-------------------------------|-------------------------------|\n| Max active users         | ${baseline_max_active_users}  | ${current_max_active_users}  |\n| Median throughput (RPS)  | ${baseline_median_throughput} | ${current_median_throughput} |\n| Median response time (ms)| ${baseline_median_response_time_stats} | ${current_median_response_time_stats} |\n| P90 response time (ms)   | ${baseline_pct90_response_time_stats} | ${current_pct90_response_time_stats} |\n| Error rate %             | ${baseline_errors_pct_stats} | ${current_errors_pct_stats}  |\n\n### Grafana dashboards  \n- **Baseline:** [baseline_grafana_link](${baseline_grafana_link})  \n- **Current:** [current_grafana_link](${current_grafana_link})","graph_id":None,"template_id":None,"type":"text"},
                {"content":"## Throughput graph:","graph_id":None,"template_id":None,"type":"text"},
                {"content":None,"graph_id":graph_example_id,"template_id":None,"type":"graph"},
                {"content":"## Aggregated data:\n${aggregated_data_table_}","graph_id":None,"template_id":None,"type":"text"}
            ]
        }

        for default_graph in default_graphs:
            azure_template['data'].append({"content":f"## {default_graph['name']}","graph_id":None,"template_id":None,"type":"text"})
            azure_template['data'].append({"content":None,"graph_id":default_graph['id'],"template_id":None,"type":"graph"})

        DBTemplates.save(project_id, azure_template)

        # Template example for PDF
        pdf_template = {
            "id": None,
            "name": "[EXAMPLE] REPORT for PDF",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT for PDF",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": None,
            "aggregated_prompt_id": None,
            "system_prompt_id": None,
            "data": [
                {"content":"<h2>Executive summaries</h2>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"Timestamp when report was generated: ${report_timestamp}  \nCurrent run: from ${current_start_time} to ${current_end_time}  \nBaseline run: from ${baseline_start_time} to ${baseline_end_time}","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h2>Summary</h2>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"AI insights:\n${ai_summary}  \n\nNFR compliance:\n${nfr_summary}\n\nML anomalies:\n${ml_summary}","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h2>Key KPI comparison</h2>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"[[\"KPI\", \"Baseline Value\", \"Current Value\"],\n[\"Max active users\", \"${baseline_max_active_users}\", \"${current_max_active_users}\"],\n[\"Median throughput (RPS)\", \"${baseline_median_throughput}\", \"${current_median_throughput}\"],\n[\"Median response time (ms)\", \"${baseline_median_response_time_stats}\", \"${current_median_response_time_stats}\"],\n[\"P90 response time (ms)\", \"${baseline_pct90_response_time_stats}\", \"${current_pct90_response_time_stats}\"],\n[\"Error rate %\", \"${baseline_errors_pct_stats}\", \"${current_errors_pct_stats}\"]]","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h2>Throughput graph</h2>","graph_id":None,"template_id":None,"type":"text"},
                {"content":None,"graph_id":graph_example_id,"template_id":None,"type":"graph"},
                {"content":"<h2>Aggregated data</h2>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"${aggregated_data_table_}","graph_id":None,"template_id":None,"type":"text"}
            ]
        }

        for default_graph in default_graphs:
            pdf_template['data'].append({"content":f"<h2>{default_graph['name']}</h2>","graph_id":None,"template_id":None,"type":"text"})
            pdf_template['data'].append({"content":None,"graph_id":default_graph['id'],"template_id":None,"type":"graph"})

        DBTemplates.save(project_id, pdf_template)

        # Template example for SMTP
        smtp_template = {
            "id": None,
            "name": "[EXAMPLE] REPORT for SMTP",
            "nfr": nfr_example_id,
            "title": "[EXAMPLE] REPORT for SMTP",
            "ai_switch": False,
            "ai_aggregated_data_switch": False,
            "ai_graph_switch": False,
            "ai_to_graphs_switch": False,
            "nfrs_switch": True,
            "ml_switch": True,
            "template_prompt_id": None,
            "aggregated_prompt_id": None,
            "system_prompt_id": None,
            "data": [
                {"content":"<h1>Executive Summaries</h1>\n<p><strong>Timestamp when report was generated:</strong> ${report_timestamp}</p>\n<p><strong>Current run:</strong> from ${current_start_time} to ${current_end_time}</p>\n<p><strong>Baseline run:</strong> from ${baseline_start_time} to ${baseline_end_time}</p>\n<h1>Summary</h1>\n<hr>\n<h2>AI Insights</h2>\n<p>${ai_summary}</p>\n<h2>NFR Compliance</h2>\n<pre>${nfr_summary}</pre>\n<h2>ML Anomalies</h2>\n<pre>${ml_summary}</pre>\n<h2>Key KPI Comparison</h2>\n<table>\n        <thead>\n            <tr>\n                <th>KPI</th>\n                <th>Baseline</th>\n                <th>Current</th>\n            </tr>\n        </thead>\n        <tbody>\n            <tr>\n                <td>Max active users</td>\n                <td>${baseline_max_active_users}</td>\n                <td>${current_max_active_users}</td>\n            </tr>\n            <tr>\n                <td>Median throughput (RPS)</td>\n                <td>${baseline_median_throughput}</td>\n                <td>${current_median_throughput}</td>\n            </tr>\n            <tr>\n                <td>Median response time (ms)</td>\n                <td>${baseline_median_response_time_stats}</td>\n                <td>${current_median_response_time_stats}</td>\n            </tr>\n            <tr>\n                <td>P90 response time (ms)</td>\n                <td>${baseline_pct90_response_time_stats}</td>\n                <td>${current_pct90_response_time_stats}</td>\n            </tr>\n            <tr>\n                <td>Error rate %</td>\n                <td>${baseline_errors_pct_stats}</td>\n                <td>${current_errors_pct_stats}</td>\n            </tr>\n        </tbody>\n</table>\n<h3>Grafana Dashboards</h3>\n<p>\n    <strong>Baseline:</strong> <a href=\"${baseline_grafana_link}\" target=\"_blank\">baseline_grafana_link</a>\n</p>\n<p>\n    <strong>Current:</strong> <a href=\"${current_grafana_link}\" target=\"_blank\">current_grafana_link</a>\n</p>","graph_id":None,"template_id":None,"type":"text"},
                {"content":"<h1>Throughput graph</h1>","graph_id":None,"template_id":None,"type":"text"},
                {"content":None,"graph_id":graph_example_id,"template_id":None,"type":"graph"},
                {"content":"<h1>Aggregated data</h1>\n${aggregated_data_table_}","graph_id":None,"template_id":None,"type":"text"}
            ]
        }

        for default_graph in default_graphs:
            smtp_template['data'].append({"content":f"<h1>{default_graph['name']}</h1>","graph_id":None,"template_id":None,"type":"text"})
            smtp_template['data'].append({"content":None,"graph_id":default_graph['id'],"template_id":None,"type":"graph"})

        DBTemplates.save(project_id, smtp_template)

    except Exception as exc:
        logging.warning(f"Failed to create example data for project {project_id}: {exc}")
