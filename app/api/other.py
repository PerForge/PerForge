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
import re
import pandas as pd
from flask import Blueprint, request, current_app
from app.api.base import (
    api_response, api_error_handler,
    HTTP_BAD_REQUEST,
    get_project_id,
)
from app.backend.integrations.data_sources.influxdb_v2.influxdb_insertion import InfluxdbV2Insertion
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.parsers.jmeter import parse_uploaded_results

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

@other_api.route('/api/v1/uploads/test', methods=['POST'])
@api_error_handler
def receive_test_upload():
    """
    Receive a test upload with file, InfluxDB integration ID, and test title.

    Process: validates input, parses CSV/JTL, aggregates using the provided
    'aggregation_window' (default '5s'), and writes points to InfluxDB via
    InfluxdbV2Insertion. Returns write statistics.

    Expected multipart/form-data fields:
      - file: The results file (.csv or .jtl)
      - influxdb_id: ID of the selected InfluxDB integration
      - test_title: Title of the test
      - aggregation_window: Optional pandas offset string (e.g., '5s', '30s', '1min', '500ms')
    """
    try:
        influxdb_id = request.form.get('influxdb_id')
        test_title = request.form.get('test_title')
        # optional aggregation window for resampling (e.g., '5s', '30s', '1min', '500ms')
        aggregation_window = (request.form.get('aggregation_window') or '5s').strip().lower()
        file = request.files.get('file')

        errors = []
        if not influxdb_id:
            errors.append({"code": "missing_influxdb_id", "message": "Parameter 'influxdb_id' is required"})
        if not test_title:
            errors.append({"code": "missing_test_title", "message": "Parameter 'test_title' is required"})
        if file is None or file.filename == '':
            errors.append({"code": "missing_file", "message": "A file must be provided"})

        project_id = get_project_id()
        if not project_id:
            errors.append({"code": "missing_project", "message": "No 'project' cookie found; select a project and retry"})

        # aggregation_window validation is handled in InfluxdbV2Insertion.write_upload()

        if errors:
            return api_response(
                message="Invalid request",
                status=HTTP_BAD_REQUEST,
                errors=errors
            )

        # Parse uploaded file into a normalized DataFrame of JMeter samples
        df = parse_uploaded_results(file)

        if df.empty:
            return api_response(
                message="Uploaded file contains no parsable samples",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "empty_file", "message": "No rows parsed from file"}]
            )

        # Build aggregates using requested 'aggregation_window' and write via insertion module
        # Normalization and type coercion are handled inside insertion layer

        # Compute test title prefix from the earliest timestamp in the file and prepend it.
        # Avoid double-prefixing if the UI already sent one.
        try:
            if "timestamp" in df.columns and not df.empty:
                ts_min = pd.to_datetime(df["timestamp"], utc=True).min()
                if pd.notna(ts_min):
                    prefix = pd.Timestamp(ts_min).strftime('%Y-%m-%d_%H:%M@')
                    # Strip any existing date prefix like 2025-08-13_12:29@
                    base_title = re.sub(r'^\d{4}-\d{2}-\d{2}_\d{2}:\d{2}@\s*', '', (test_title or ''))
                    test_title = f"{prefix}{base_title}"
        except Exception:
            # Non-fatal; keep user-provided title as is
            pass

        # Check uniqueness of the prefixed test_title in InfluxDB
        try:
            with InfluxdbV2(project=project_id, id=int(influxdb_id)) as extractor:
                existing = extractor.get_tests_titles() or []
                existing_titles = {rec.get("test_title") for rec in existing if isinstance(rec, dict)}
                if test_title in existing_titles:
                    return api_response(
                        message="Test title already exists",
                        status=HTTP_BAD_REQUEST,
                        errors=[{"code": "duplicate_test_title", "message": f"Prefixed title '{test_title}' already exists in InfluxDB. Choose a different title or adjust file timestamps."}]
                    )
        except Exception as er:
            logging.error(f"Failed to check test title uniqueness: {er}")
            return api_response(
                message="Failed to verify test title uniqueness",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "uniqueness_check_failed", "message": str(er)}]
            )

        written = 0
        try:
            with InfluxdbV2Insertion(project=project_id, id=int(influxdb_id)) as inserter:
                result = inserter.write_upload(df=df, test_title=test_title, write_events=True, aggregation_window=aggregation_window)
                written = int(result.get("points_written", 0))
        except ValueError as ve:
            # Validation error from insertion layer (e.g., bad aggregation_window or missing columns)
            logging.error(f"Validation error processing upload: {ve}")
            return api_response(
                message="Invalid upload payload",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_upload", "message": str(ve)}]
            )
        except Exception as er:
            logging.error(f"Failed to write to InfluxDB: {er}")
            return api_response(
                message="Failed to write to InfluxDB",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "influx_write_failed", "message": str(er)}]
            )

        return api_response(
            data={
                "received": True,
                "influxdb_id": influxdb_id,
                "test_title": test_title,
                "filename": file.filename,
                "content_type": getattr(file, 'mimetype', None),
                "points_written": written,
                "aggregation_window": aggregation_window,
            },
            message=f"Upload processed successfully; wrote {written} points to InfluxDB"
        )
    except Exception as e:
        logging.error(f"Error processing test upload: {str(e)}")
        return api_response(
            message="Error processing upload",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "upload_error", "message": str(e)}]
        )
