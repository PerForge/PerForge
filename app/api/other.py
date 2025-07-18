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
Other miscellaneous API endpoints.
"""
import logging
import os
from flask import Blueprint, request, current_app, send_from_directory
from app.api.base import (
    api_response, api_error_handler,
    HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for other API
other_api = Blueprint('other_api', __name__)

@other_api.route('/api/v1/health', methods=['GET'])
@api_error_handler
def health_check():
    """
    Health check endpoint.

    Returns:
        A JSON response with health status
    """
    try:
        return api_response(
            data={"status": "healthy"},
            message="System is healthy"
        )
    except Exception as e:
        logging.error(f"Health check error: {str(e)}")
        return api_response(
            message="System health check failed",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "health_error", "message": str(e)}]
        )

@other_api.route('/api/v1/version', methods=['GET'])
@api_error_handler
def get_version():
    """
    Get application version.

    Returns:
        A JSON response with version information
    """
    try:
        version = current_app.config.get('VERSION', 'Unknown')
        return api_response(
            data={"version": version},
            message="Version information"
        )
    except Exception as e:
        logging.error(f"Error getting version: {str(e)}")
        return api_response(
            message="Error retrieving version information",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "version_error", "message": str(e)}]
        )

@other_api.route('/api/v1/config', methods=['GET'])
@api_error_handler
def get_config():
    """
    Get application configuration.

    Returns:
        A JSON response with configuration information
    """
    try:
        # Filter out sensitive configuration
        safe_config = {
            'DEBUG': current_app.config.get('DEBUG', False),
            'TESTING': current_app.config.get('TESTING', False),
            'VERSION': current_app.config.get('VERSION', 'Unknown'),
            'UPLOAD_FOLDER': current_app.config.get('UPLOAD_FOLDER', ''),
            'ALLOWED_EXTENSIONS': current_app.config.get('ALLOWED_EXTENSIONS', [])
        }

        return api_response(
            data={"config": safe_config},
            message="Configuration information"
        )
    except Exception as e:
        logging.error(f"Error getting configuration: {str(e)}")
        return api_response(
            message="Error retrieving configuration information",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "config_error", "message": str(e)}]
        )

@other_api.route('/api/v1/uploads/<filename>', methods=['GET'])
@api_error_handler
def get_uploaded_file(filename):
    """
    Get an uploaded file.

    Args:
        filename: The name of the file to get

    Returns:
        The file content
    """
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        logging.error(f"Error getting uploaded file: {str(e)}")
        return api_response(
            message=f"Error retrieving file {filename}",
            status=HTTP_NOT_FOUND,
            errors=[{"code": "file_error", "message": str(e)}]
        )

@other_api.route('/api/v1/uploads', methods=['POST'])
@api_error_handler
def upload_file():
    """
    Upload a file.

    Returns:
        A JSON response with the uploaded file information
    """
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return api_response(
                message="No file part in the request",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_file", "message": "No file part in the request"}]
            )

        file = request.files['file']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return api_response(
                message="No selected file",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_filename", "message": "No selected file"}]
            )

        if file:
            filename = file.filename
            upload_folder = current_app.config['UPLOAD_FOLDER']

            # Create upload folder if it doesn't exist
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            return api_response(
                data={"filename": filename, "path": file_path},
                message="File uploaded successfully"
            )
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        return api_response(
            message="Error uploading file",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "upload_error", "message": str(e)}]
        )
