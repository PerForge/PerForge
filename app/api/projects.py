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

        new_project_id = DBProjects.save(data=project_data)

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
