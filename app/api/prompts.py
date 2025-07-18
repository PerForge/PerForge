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
Prompts API endpoints.
"""
import logging
from flask import Blueprint, request
from app.backend.components.prompts.prompts_db import DBPrompts
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for prompts API
prompts_api = Blueprint('prompts_api', __name__)

@prompts_api.route('/api/v1/prompts', methods=['GET'])
@api_error_handler
def get_prompts():
    """
    Get all prompts for the current project.

    Query Parameters:
        place: Optional filter by place (template, aggregated_data, template_group, system)

    Returns:
        A JSON response with prompts
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        place = request.args.get('place')

        if place:
            prompt_configs = DBPrompts.get_configs_by_place(project_id=project_id, place=place)
            return api_response(data={"prompts": prompt_configs})
        else:
            default_configs, custom_configs = DBPrompts.get_configs(project_id=project_id)
            all_prompts = default_configs + custom_configs
            return api_response(data={"prompts": all_prompts})

    except Exception as e:
        logging.error(f"Error getting prompts: {str(e)}")
        return api_response(
            message="Error retrieving prompts",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "prompt_error", "message": str(e)}]
        )

@prompts_api.route('/api/v1/prompts/<prompt_id>', methods=['GET'])
@api_error_handler
def get_prompt(prompt_id):
    """
    Get a specific prompt by ID.

    Args:
        prompt_id: The ID of the prompt to get

    Returns:
        A JSON response with the prompt data
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        prompt_data = DBPrompts.get_config_by_id(id=prompt_id)
        if not prompt_data:
            return api_response(
                message=f"Prompt with ID {prompt_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Prompt with ID {prompt_id} not found"}]
            )

        return api_response(data={"prompt": prompt_data})
    except Exception as e:
        logging.error(f"Error getting prompt: {str(e)}")
        return api_response(
            message="Error retrieving prompt",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "prompt_error", "message": str(e)}]
        )

@prompts_api.route('/api/v1/prompts', methods=['POST'])
@api_error_handler
def create_prompt():
    """
    Create a new prompt.

    Returns:
        A JSON response with the new prompt ID
    """
    try:
        prompt_data = request.get_json()
        if not prompt_data:
            return api_response(
                message="No prompt data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No prompt data provided"}]
            )

        if prompt_data['project_id']:
            project_id = get_project_id()
            if not project_id:
                return api_response(
                    message="No project selected",
                    status=HTTP_BAD_REQUEST,
                    errors=[{"code": "missing_project", "message": "No project selected"}]
                )
            prompt_data['project_id'] = project_id
        else:
            prompt_data['project_id'] = None

        # Clean up empty values
        for key, value in prompt_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                prompt_data[key] = None

        # Ensure ID is None for new prompt
        prompt_data["id"] = None

        new_prompt_id = DBPrompts.save(data=prompt_data)

        return api_response(
            data={"prompt_id": new_prompt_id},
            message="Prompt created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating prompt: {str(e)}")
        return api_response(
            message="Error creating prompt",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "prompt_error", "message": str(e)}]
        )

@prompts_api.route('/api/v1/prompts/<prompt_id>', methods=['PUT'])
@api_error_handler
def update_prompt(prompt_id):
    """
    Update an existing prompt.

    Args:
        prompt_id: The ID of the prompt to update

    Returns:
        A JSON response with the updated prompt
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        # Check if prompt exists
        existing_prompt = DBPrompts.get_config_by_id(project_id=project_id, id=prompt_id)
        if not existing_prompt:
            return api_response(
                message=f"Prompt with ID {prompt_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Prompt with ID {prompt_id} not found"}]
            )

        prompt_data = request.get_json()
        if not prompt_data:
            return api_response(
                message="No prompt data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No prompt data provided"}]
            )

        if prompt_data['project_id']:
            prompt_data['project_id'] = project_id

        # Clean up empty values
        for key, value in prompt_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                prompt_data[key] = None

        # Ensure ID matches URL
        prompt_data["id"] = prompt_id

        DBPrompts.update(data=prompt_data)

        return api_response(
            data={"prompt_id": prompt_id},
            message="Prompt updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating prompt: {str(e)}")
        return api_response(
            message="Error updating prompt",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "prompt_error", "message": str(e)}]
        )

@prompts_api.route('/api/v1/prompts/<prompt_id>', methods=['DELETE'])
@api_error_handler
def delete_prompt(prompt_id):
    """
    Delete a prompt.

    Args:
        prompt_id: The ID of the prompt to delete

    Returns:
        A JSON response confirming deletion
    """
    try:
        deleted = DBPrompts.delete(id=prompt_id)

        if not deleted:
            return api_response(
                message=f"Prompt with ID {prompt_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Prompt with ID {prompt_id} not found"}]
            )

        return api_response(
            message="Prompt deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting prompt: {str(e)}")
        return api_response(
            message="Error deleting prompt",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "prompt_error", "message": str(e)}]
        )
