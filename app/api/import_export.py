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
Import / Export API endpoints.

Endpoints
---------
GET  /api/v1/projects/<project_id>/export
    Download full project configuration as a JSON file.

POST /api/v1/projects/import/check
    Dry-run: analyse an uploaded JSON file and return a list of
    entities that would be overridden.  No data is written.
    Body: multipart/form-data with field "file" (JSON) and
          field "project_id" (integer).

POST /api/v1/projects/import
    Execute the import.
    Body: multipart/form-data with field "file" (JSON),
          field "project_id" (integer), and
          field "confirmed" ("true" | "false").
    When confirmed == "false", behaves like /import/check.
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, request, send_file
import io

from app.api.base import (
    api_response, api_error_handler,
    HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)
from app.backend.components.projects.projects_db                   import DBProjects
from app.backend.components.import_export.export_service           import ExportService
from app.backend.components.import_export.import_service           import ImportService

import_export_api = Blueprint('import_export_api', __name__)

SUPPORTED_VERSIONS = {"1.0"}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@import_export_api.route('/api/v1/projects/<int:project_id>/export', methods=['GET'])
@api_error_handler
def export_project(project_id: int):
    """
    Export all project configuration as a downloadable JSON file.
    """
    project = DBProjects.get_config_by_id(id=project_id)
    if not project:
        return api_response(
            message=f"Project with ID {project_id} not found",
            status=HTTP_NOT_FOUND,
            errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
        )

    try:
        payload = ExportService.export_project(project_id)
    except ValueError as exc:
        return api_response(
            message=str(exc),
            status=HTTP_NOT_FOUND,
            errors=[{"code": "not_found", "message": str(exc)}]
        )

    project_name_safe = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in project["name"]
    )
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{project_name_safe}_export_{timestamp}.json"

    json_bytes = json.dumps(payload, indent=2, default=str).encode("utf-8")
    buf = io.BytesIO(json_bytes)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# Import – conflict check
# ---------------------------------------------------------------------------

@import_export_api.route('/api/v1/projects/import/check', methods=['POST'])
@api_error_handler
def import_check():
    """
    Dry-run: parse the uploaded JSON and return a list of conflicts.
    """
    data, project_id, error_response = _parse_import_request()
    if error_response:
        return error_response

    conflicts = ImportService.check_conflicts(data, project_id)
    return api_response(data={"conflicts": conflicts})


# ---------------------------------------------------------------------------
# Import – execute
# ---------------------------------------------------------------------------

@import_export_api.route('/api/v1/projects/import', methods=['POST'])
@api_error_handler
def import_project():
    """
    Execute the import.  Requires the client to pass confirmed=true after
    reviewing conflicts; otherwise behaves like /import/check.
    """
    data, project_id, error_response = _parse_import_request()
    if error_response:
        return error_response

    confirmed_raw = request.form.get("confirmed", "false")
    confirmed = confirmed_raw.lower() in ("true", "1", "yes")

    if not confirmed:
        # Return conflicts for the UI to show the confirmation dialog.
        conflicts = ImportService.check_conflicts(data, project_id)
        return api_response(
            data={"conflicts": conflicts, "confirmed": False},
            message="Confirmation required before import"
        )

    try:
        summary = ImportService.execute_import(data, project_id)
    except Exception as exc:
        logging.error(f"Import failed: {exc}")
        return api_response(
            message=f"Import failed: {exc}",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "import_error", "message": str(exc)}]
        )

    return api_response(
        data={"summary": summary},
        message="Import completed successfully"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_import_request():
    """
    Parse multipart form request common to both import endpoints.

    Returns:
        (data_dict, project_id, error_response)
        error_response is None on success, or a Flask response tuple on failure.
    """
    if "file" not in request.files:
        return None, None, api_response(
            message="No file provided",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "missing_file", "message": "A JSON export file must be uploaded as 'file'"}]
        )

    file = request.files["file"]
    if not file.filename:
        return None, None, api_response(
            message="Empty filename",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "empty_filename", "message": "Uploaded file has no name"}]
        )

    try:
        raw = file.read().decode("utf-8")
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, api_response(
            message="Invalid JSON file",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "invalid_json", "message": str(exc)}]
        )

    version = data.get("version")
    if version not in SUPPORTED_VERSIONS:
        return None, None, api_response(
            message=f"Unsupported export version: {version}",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "unsupported_version", "message": f"Expected one of {SUPPORTED_VERSIONS}"}]
        )

    project_id_raw = request.form.get("project_id")
    if not project_id_raw:
        return None, None, api_response(
            message="project_id is required",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "missing_project_id", "message": "project_id form field is required"}]
        )

    try:
        project_id = int(project_id_raw)
    except (TypeError, ValueError):
        return None, None, api_response(
            message="project_id must be an integer",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "invalid_project_id", "message": "project_id must be an integer"}]
        )

    project = DBProjects.get_config_by_id(id=project_id)
    if not project:
        return None, None, api_response(
            message=f"Project with ID {project_id} not found",
            status=HTTP_NOT_FOUND,
            errors=[{"code": "not_found", "message": f"Project with ID {project_id} not found"}]
        )

    return data, project_id, None
