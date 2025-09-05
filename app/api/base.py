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
Base module for API endpoints.
"""
import functools
import traceback
import logging
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_CONFLICT = 409
HTTP_INTERNAL_SERVER_ERROR = 500

def get_project_id():
    """Get the current project ID from cookies as an integer.

    Returns:
        int | None: The project ID if present and valid, otherwise None.
    """
    raw = request.cookies.get('project')
    try:
        return int(raw) if raw is not None else None
    except (ValueError, TypeError):
        return None

def api_response(data=None, message=None, status=HTTP_OK, errors=None):
    """
    Create a standardized API response.

    Args:
        data: The data to return
        message: A message to include in the response
        status: HTTP status code
        errors: Any errors to include in the response

    Returns:
        A JSON response with the standard format
    """
    response = {
        "status": "success" if status < 400 else "error",
    }

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if errors:
        response["errors"] = errors

    return jsonify(response), status

def api_error_handler(f):
    """
    Decorator to handle exceptions in API endpoints.

    Args:
        f: The function to decorate

    Returns:
        The decorated function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HTTPException as e:
            # Handle HTTP exceptions
            logging.warning(f"HTTP Exception: {str(e)}")
            return api_response(
                message=str(e),
                status=e.code,
                errors=[{"code": e.code, "message": str(e)}]
            )
        except Exception as e:
            # Handle all other exceptions
            logging.error(f"API Error: {str(e)}")
            logging.debug(traceback.format_exc())
            return api_response(
                message="An internal server error occurred",
                status=HTTP_INTERNAL_SERVER_ERROR,
                errors=[{"code": "internal_error", "message": str(e)}]
            )
    return decorated_function

class ResourceNotFoundError(Exception):
    """Exception raised when a resource is not found."""
    def __init__(self, resource_type, resource_id):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(self.message)

class ValidationError(Exception):
    """Exception raised when validation fails."""
    def __init__(self, message, errors=None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)
