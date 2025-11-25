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
Settings API endpoints for managing project-specific settings.
"""
from flask import Blueprint, request
from app.api.base import (
    api_response,
    api_error_handler,
    get_project_id,
    HTTP_OK,
    HTTP_CREATED,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND
)
from app.backend.components.settings.settings_service import SettingsService

# Create blueprint
settings_api = Blueprint('settings_api', __name__, url_prefix='/api/v1/settings')


@settings_api.route('', methods=['GET'])
@api_error_handler
def get_all_settings():
    """
    Get all settings for the current project.

    Returns:
        JSON response with all settings organized by category
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    settings = SettingsService.get_project_settings(project_id)

    return api_response(
        data={'settings': settings},
        message='Settings retrieved successfully'
    )


@settings_api.route('/<category>', methods=['GET'])
@api_error_handler
def get_category_settings(category):
    """
    Get settings for a specific category.

    Args:
        category: Category name (ml_analysis, transaction_status, data_aggregation)

    Returns:
        JSON response with category settings
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    # Validate category
    valid_categories = ['ml_analysis', 'transaction_status', 'data_aggregation']
    if category not in valid_categories:
        return api_response(
            message=f'Invalid category. Must be one of: {", ".join(valid_categories)}',
            status=HTTP_BAD_REQUEST
        )

    settings = SettingsService.get_project_settings(project_id, category)

    return api_response(
        data={category: settings},
        message=f'Settings for {category} retrieved successfully'
    )


@settings_api.route('/<category>', methods=['PUT'])
@api_error_handler
def update_category_settings(category):
    """
    Update multiple settings within a category.

    Args:
        category: Category name

    Request Body:
        JSON object with key-value pairs to update

    Returns:
        JSON response with updated settings
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    # Validate category
    valid_categories = ['ml_analysis', 'transaction_status', 'data_aggregation']
    if category not in valid_categories:
        return api_response(
            message=f'Invalid category. Must be one of: {", ".join(valid_categories)}',
            status=HTTP_BAD_REQUEST
        )

    # Get settings from request body
    settings = request.get_json()
    if not settings or not isinstance(settings, dict):
        return api_response(
            message='Request body must be a JSON object with settings to update',
            status=HTTP_BAD_REQUEST
        )

    # Update settings
    SettingsService.update_category_settings(project_id, category, settings)

    # Return updated settings
    updated_settings = SettingsService.get_project_settings(project_id, category)

    return api_response(
        data={
            category: updated_settings,
            'updated_keys': list(settings.keys())
        },
        message=f'Settings for {category} updated successfully'
    )


@settings_api.route('/<category>/<key>', methods=['PUT'])
@api_error_handler
def update_single_setting(category, key):
    """
    Update a single setting.

    Args:
        category: Category name
        key: Setting key

    Request Body:
        JSON object with 'value' field

    Returns:
        JSON response with updated setting
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    # Validate category
    valid_categories = ['ml_analysis', 'transaction_status', 'data_aggregation']
    if category not in valid_categories:
        return api_response(
            message=f'Invalid category. Must be one of: {", ".join(valid_categories)}',
            status=HTTP_BAD_REQUEST
        )

    # Get value from request body
    data = request.get_json()
    if not data or 'value' not in data:
        return api_response(
            message='Request body must include "value" field',
            status=HTTP_BAD_REQUEST
        )

    value = data['value']

    # Update setting
    SettingsService.update_setting(project_id, category, key, value)

    # Return updated setting
    updated_value = SettingsService.get_setting(project_id, category, key)

    return api_response(
        data={
            'category': category,
            'key': key,
            'value': updated_value
        },
        message=f'Setting {category}.{key} updated successfully'
    )


@settings_api.route('/reset', methods=['POST'])
@api_error_handler
def reset_settings():
    """
    Reset settings to defaults.

    Request Body (optional):
        JSON object with 'category' field to reset specific category,
        or empty/null to reset all settings

    Returns:
        JSON response confirming reset
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    data = request.get_json() or {}
    category = data.get('category')

    # Validate category if provided
    if category:
        valid_categories = ['ml_analysis', 'transaction_status', 'data_aggregation']
        if category not in valid_categories:
            return api_response(
                message=f'Invalid category. Must be one of: {", ".join(valid_categories)}',
                status=HTTP_BAD_REQUEST
            )

    # Reset settings
    SettingsService.reset_to_defaults(project_id, category)

    # Return new settings
    settings = SettingsService.get_project_settings(project_id, category)

    return api_response(
        data={'settings': settings if not category else {category: settings}},
        message=f'Settings reset to defaults for {category or "all categories"}'
    )


@settings_api.route('/defaults', methods=['GET'])
@api_error_handler
def get_defaults():
    """
    Get default settings structure with metadata.
    Useful for UI rendering and documentation.

    Returns:
        JSON response with default settings and metadata
    """
    defaults = SettingsService.get_defaults()

    return api_response(
        data={'defaults': defaults},
        message='Default settings retrieved successfully'
    )


@settings_api.route('/metadata', methods=['GET'])
@api_error_handler
def get_settings_with_metadata():
    """
    Get current settings with full metadata (type, description, constraints).
    Useful for UI rendering.

    Query Parameters:
        category: Optional category filter

    Returns:
        JSON response with settings and their metadata
    """
    project_id = get_project_id()
    if not project_id:
        return api_response(
            message='No active project selected',
            status=HTTP_BAD_REQUEST
        )

    category = request.args.get('category')

    # Validate category if provided
    if category:
        valid_categories = ['ml_analysis', 'transaction_status', 'data_aggregation']
        if category not in valid_categories:
            return api_response(
                message=f'Invalid category. Must be one of: {", ".join(valid_categories)}',
                status=HTTP_BAD_REQUEST
            )

    settings_metadata = SettingsService.get_settings_with_metadata(project_id, category)

    return api_response(
        data={'settings': settings_metadata},
        message='Settings with metadata retrieved successfully'
    )
