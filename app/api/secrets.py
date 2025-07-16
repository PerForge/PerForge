"""
Secrets API endpoints.
"""
import logging
from flask import Blueprint, request
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.secrets.secrets_db import DBSecrets
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for secrets API
secrets_api = Blueprint('secrets_api', __name__)

@secrets_api.route('/api/v1/secrets', methods=['GET'])
@api_error_handler
def get_secrets():
    """
    Get all secrets for the current project.

    Returns:
        A JSON response with secrets
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

        secret_configs = DBSecrets.get_configs(project_id=project_id)

        # Remove sensitive data from response
        for secret in secret_configs:
            if 'value' in secret:
                secret['value'] = '********'

        return api_response(data={"secrets": secret_configs})
    except Exception as e:
        logging.error(f"Error getting secrets: {str(e)}")
        return api_response(
            message="Error retrieving secrets",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "secret_error", "message": str(e)}]
        )

@secrets_api.route('/api/v1/secrets/<secret_id>', methods=['GET'])
@api_error_handler
def get_secret(secret_id):
    """
    Get a specific secret by ID.

    Args:
        secret_id: The ID of the secret to get

    Returns:
        A JSON response with the secret data (without the actual secret value)
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

        secret_data = DBSecrets.get_config_by_id(project_id=project_id, id=secret_id)
        if not secret_data:
            return api_response(
                message=f"Secret with ID {secret_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Secret with ID {secret_id} not found"}]
            )

        # Remove sensitive data from response
        if 'value' in secret_data:
            secret_data['value'] = '********'

        return api_response(data={"secret": secret_data})
    except Exception as e:
        logging.error(f"Error getting secret: {str(e)}")
        return api_response(
            message="Error retrieving secret",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "secret_error", "message": str(e)}]
        )

@secrets_api.route('/api/v1/secrets', methods=['POST'])
@api_error_handler
def create_secret():
    """
    Create a new secret.

    Returns:
        A JSON response with the new secret ID
    """
    try:
        secret_data = request.get_json()
        if not secret_data:
            return api_response(
                message="No secret data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No secret data provided"}]
            )

        if secret_data['project_id']:
            project_id = get_project_id()
            if not project_id:
                return api_response(
                    message="No project selected",
                    status=HTTP_BAD_REQUEST,
                    errors=[{"code": "missing_project", "message": "No project selected"}]
                )
            secret_data['project_id'] = project_id
        else:
            secret_data['project_id'] = None

        # Clean up empty values
        for key, value in secret_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                secret_data[key] = None

        # Ensure ID is None for new secret
        secret_data["id"] = None

        new_secret_id = DBSecrets.save(
            data=secret_data
        )

        return api_response(
            data={"secret_id": new_secret_id},
            message="Secret created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating secret: {str(e)}")
        return api_response(
            message="Error creating secret",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "secret_error", "message": str(e)}]
        )

@secrets_api.route('/api/v1/secrets/<secret_id>', methods=['PUT'])
@api_error_handler
def update_secret(secret_id):
    """
    Update an existing secret.

    Args:
        secret_id: The ID of the secret to update

    Returns:
        A JSON response with the updated secret
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        # Check if secret exists
        existing_secret = DBSecrets.get_config_by_id(project_id=project_id, id=secret_id)
        if not existing_secret:
            return api_response(
                message=f"Secret with ID {secret_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Secret with ID {secret_id} not found"}]
            )

        secret_data = request.get_json()
        if not secret_data:
            return api_response(
                message="No secret data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No secret data provided"}]
            )

        if secret_data['project_id']:
            secret_data['project_id'] = project_id

        # Clean up empty values
        for key, value in secret_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                secret_data[key] = None

        # If value is not provided, keep the existing value
        if 'value' not in secret_data or secret_data['value'] is None:
            secret_data['value'] = existing_secret['value']

        # Ensure ID matches URL
        secret_data["id"] = secret_id

        DBSecrets.update(
            data=secret_data
        )

        return api_response(
            data={"secret_id": secret_id},
            message="Secret updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating secret: {str(e)}")
        return api_response(
            message="Error updating secret",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "secret_error", "message": str(e)}]
        )

@secrets_api.route('/api/v1/secrets/<secret_id>', methods=['DELETE'])
@api_error_handler
def delete_secret(secret_id):
    """
    Delete a secret.

    Args:
        secret_id: The ID of the secret to delete

    Returns:
        A JSON response confirming deletion
    """
    try:
        # Delete the secret by its unique ID, regardless of project context
        deleted = DBSecrets.delete(id=secret_id)

        if not deleted:
            return api_response(
                message=f"Secret with ID {secret_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Secret with ID {secret_id} not found"}]
            )

        return api_response(
            message="Secret deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting secret: {str(e)}")
        return api_response(
            message="Error deleting secret",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "secret_error", "message": str(e)}]
        )
