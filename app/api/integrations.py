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
Integrations API endpoints.
"""
import logging
import re
import concurrent.futures
from urllib.parse import urlparse
from flask import Blueprint, request
from app.backend.components.projects.projects_db import DBProjects
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db import DBAzureWiki
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.integrations.smtp_mail.smtp_mail_db import DBSMTPMail
from app.backend.integrations.ai_support.providers.provider_factory import ProviderFactory
from app.backend.components.secrets.secrets_db import DBSecrets
from influxdb_client import InfluxDBClient
from influxdb import InfluxDBClient as InfluxDBClient18
from app.backend.integrations.data_sources.influxdb_v2.influxdb_extraction import InfluxdbV2
from app.backend.integrations.data_sources.influxdb_v1_8.influxdb_extraction_1_8 import InfluxdbV18
from app.api.base import (
    api_response, api_error_handler, get_project_id,
   HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)
from atlassian import Confluence

# Create a Blueprint for integrations API
integrations_api = Blueprint('integrations_api', __name__)

# Helper function to get the appropriate DB class based on integration type
def get_db_class(integration_type):
    """
    Get the appropriate database class based on integration type.

    Args:
        integration_type: The type of integration (ai_support, influxdb, etc.)

    Returns:
        The appropriate database class
    """
    integration_type = integration_type.lower() if integration_type else ""

    if integration_type == "ai_support":
        return DBAISupport
    elif integration_type == "influxdb":
        return DBInfluxdb
    elif integration_type == "atlassian_confluence":
        return DBAtlassianConfluence
    elif integration_type == "atlassian_jira":
        return DBAtlassianJira
    elif integration_type == "azure" or integration_type == "azure_wiki":
        return DBAzureWiki
    elif integration_type == "grafana":
        return DBGrafana
    elif integration_type == "smtp_mail":
        return DBSMTPMail
    # Add other integration types as needed
    else:
        raise ValueError(f"Unsupported integration type: {integration_type}")

@integrations_api.route('/api/v1/integrations', methods=['GET'])
@api_error_handler
def get_integrations():
    """
    Get all integrations for the current project.

    Returns:
        A JSON response with integrations
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

        # Get all integrations from different integration types
        all_integrations = []

        # Get AI Support integrations
        try:
            ai_support_configs = DBAISupport.get_configs(project_id=project_id)
            for config in ai_support_configs:
                config['integration_type'] = 'ai_support'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting AI Support integrations: {str(e)}")

        # Get InfluxDB integrations
        try:
            influxdb_configs = DBInfluxdb.get_configs(project_id=project_id)
            for config in influxdb_configs:
                config['integration_type'] = 'influxdb'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting InfluxDB integrations: {str(e)}")

        # Get Atlassian Confluence integrations
        try:
            atlassian_confluence_configs = DBAtlassianConfluence.get_configs(project_id=project_id)
            for config in atlassian_confluence_configs:
                config['integration_type'] = 'atlassian_confluence'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting Atlassian Confluence integrations: {str(e)}")

        # Get Atlassian Jira integrations
        try:
            atlassian_jira_configs = DBAtlassianJira.get_configs(project_id=project_id)
            for config in atlassian_jira_configs:
                config['integration_type'] = 'atlassian_jira'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting Atlassian Jira integrations: {str(e)}")

        # Get Azure Wiki integrations
        try:
            azure_wiki_configs = DBAzureWiki.get_configs(project_id=project_id)
            for config in azure_wiki_configs:
                config['integration_type'] = 'azure_wiki'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting Azure Wiki integrations: {str(e)}")

        # Get Grafana integrations
        try:
            grafana_configs = DBGrafana.get_configs(project_id=project_id)
            for config in grafana_configs:
                config['integration_type'] = 'grafana'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting Grafana integrations: {str(e)}")

        # Get SMTP Mail integrations
        try:
            smtp_mail_configs = DBSMTPMail.get_configs(project_id=project_id)
            for config in smtp_mail_configs:
                config['integration_type'] = 'smtp_mail'
                all_integrations.append(config)
        except Exception as e:
            logging.warning(f"Error getting SMTP Mail integrations: {str(e)}")

        # Add other integration types as needed

        return api_response(data={"integrations": all_integrations})
    except Exception as e:
        logging.error(f"Error getting integrations: {str(e)}")
        return api_response(
            message="Error retrieving integrations",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/<integration_id>', methods=['GET'])
@api_error_handler
def get_integration(integration_id):
    """
    Get a specific integration by ID.

    Args:
        integration_id: The ID of the integration to get

    Returns:
        A JSON response with the integration data
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

        # Get integration type from query parameters
        integration_type = request.args.get('type')
        if not integration_type:
            return api_response(
                message="Integration type not specified",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_type", "message": "Integration type must be specified in the query parameters"}]
            )

        try:
            db_class = get_db_class(integration_type)
            integration_data = db_class.get_config_by_id(project_id=project_id, id=integration_id)

            if not integration_data:
                return api_response(
                    message=f"Integration with ID {integration_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Integration with ID {integration_id} not found"}]
                )

            # Add integration type to response
            integration_data['integration_type'] = integration_type

            return api_response(data={"integration": integration_data})
        except ValueError as e:
            return api_response(
                message=str(e),
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_type", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error getting integration: {str(e)}")
        return api_response(
            message="Error retrieving integration",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/type/<integration_type>', methods=['GET'])
@api_error_handler
def get_integrations_by_type(integration_type):
    """
    Get integrations of a specific type for the current project.

    Path params:
        integration_type: Integration type (e.g., influxdb, grafana, ...)

    Returns:
        JSON response with a list of integrations of the requested type.
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

        try:
            db_class = get_db_class(integration_type)
            configs = db_class.get_configs(project_id=project_id)
            # annotate with type for consistency
            for cfg in configs:
                cfg['integration_type'] = integration_type

            # For influxdb type: if bucket_regex_bool is true on a config,
            # fetch actual bucket names from InfluxDB and attach them to the config.
            # Choose InfluxdbV2 or InfluxdbV18 based on source_type/listener.
            if integration_type.lower() == 'influxdb':
                for cfg in configs:
                    try:
                        if not cfg.get('bucket_regex_bool'):
                            continue

                        name_regex = cfg.get('bucket') or None
                        source_type = cfg.get('source_type') or ''
                        listener = cfg.get('listener') or ''

                        is_v18 = (
                            source_type == 'influxdb_v1.8'
                            or 'v1.8' in listener
                        )

                        if is_v18:
                            with InfluxdbV18(project=project_id, id=cfg.get('id')) as ds:
                                buckets = ds.list_buckets(name_regex=name_regex)
                        else:
                            with InfluxdbV2(project=project_id, id=cfg.get('id')) as ds:
                                buckets = ds.list_buckets(name_regex=name_regex)

                        cfg['buckets'] = buckets
                    except Exception as e:
                        logging.warning(f"Failed to list buckets for influxdb config id={cfg.get('id')}: {e}")
                        cfg['buckets'] = []

            return api_response(data={"integrations": configs, "integration_type": integration_type})
        except ValueError as e:
            return api_response(
                message=str(e),
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_type", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error getting integrations by type: {str(e)}")
        return api_response(
            message="Error retrieving integrations by type",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/outputs', methods=['GET'])
@api_error_handler
def get_output_integrations():
    """
    Get output configurations for the current project.

    Returns:
        JSON response with a list of output configurations.
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

        output_configs = DBProjects.get_project_output_configs(project_id=project_id)
        return api_response(data={"output_configs": output_configs})
    except Exception as e:
        logging.error(f"Error getting output integrations: {str(e)}")
        return api_response(
            message="Error retrieving output integrations",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations', methods=['POST'])
@api_error_handler
def create_integration():
    """
    Create a new integration.

    Returns:
        A JSON response with the new integration ID
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

        integration_data = request.get_json()
        if not integration_data:
            return api_response(
                message="No integration data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No integration data provided"}]
            )

        # Get integration type from request data
        integration_type = integration_data.pop('integration_type', None)
        if not integration_type:
            return api_response(
                message="Integration type not specified",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_type", "message": "Integration type must be specified in the request data"}]
            )

        # Clean up empty values
        for key, value in integration_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                integration_data[key] = None

        # Ensure ID is None for new integration
        integration_data["id"] = None

        try:
            db_class = get_db_class(integration_type)
            new_integration_id = db_class.save(
                project_id=project_id,
                data=integration_data
            )

            return api_response(
                data={"integration_id": new_integration_id, "integration_type": integration_type},
                message="Integration created successfully",
                status=HTTP_CREATED
            )
        except ValueError as e:
            return api_response(
                message=str(e),
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_type", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error creating integration: {str(e)}")
        return api_response(
            message="Error creating integration",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/<integration_id>', methods=['PUT'])
@api_error_handler
def update_integration(integration_id):
    """
    Update an existing integration.

    Args:
        integration_id: The ID of the integration to update

    Returns:
        A JSON response with the updated integration
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

        integration_data = request.get_json()
        if not integration_data:
            return api_response(
                message="No integration data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No integration data provided"}]
            )

        # Get integration type from request data
        integration_type = integration_data.pop('integration_type', None)
        if not integration_type:
            return api_response(
                message="Integration type not specified",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_type", "message": "Integration type must be specified in the request data"}]
            )

        try:
            db_class = get_db_class(integration_type)

            # Check if integration exists
            existing_integration = db_class.get_config_by_id(project_id=project_id, id=integration_id)
            if not existing_integration:
                return api_response(
                    message=f"Integration with ID {integration_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Integration with ID {integration_id} not found"}]
                )

            # Clean up empty values
            for key, value in integration_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if v == '':
                                    item[k] = None
                elif value == '':
                    integration_data[key] = None

            # Ensure ID matches URL
            integration_data["id"] = integration_id

            db_class.update(
                project_id=project_id,
                data=integration_data
            )

            return api_response(
                data={"integration_id": integration_id, "integration_type": integration_type},
                message="Integration updated successfully"
            )
        except ValueError as e:
            return api_response(
                message=str(e),
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_type", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error updating integration: {str(e)}")
        return api_response(
            message="Error updating integration",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/grafana/ping', methods=['POST'])
@api_error_handler
def ping_grafana():
    """Ping Grafana by calling its /api/health endpoint with provided URL and optional API key."""
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(message="No project selected", status=HTTP_BAD_REQUEST,
                                 errors=[{"code": "missing_project", "message": "No project selected"}])

        data = request.get_json(silent=True) or {}
        url = data.get('url')
        token = data.get('token')
        token_id = data.get('token_id')
        org_id = data.get('org_id')

        if not url or (not token and not token_id):
            return api_response(message="Required parameters are missing (url, token/token_id)", status=HTTP_BAD_REQUEST,
                                 errors=[{"code": "missing_params", "message": "url and token/token_id are required"}])

        if not token and token_id:
            secret = DBSecrets.get_config_by_id(project_id=project_id, id=token_id)
            if not secret:
                return api_response(message=f"Secret with ID {token_id} not found", status=HTTP_NOT_FOUND,
                                     errors=[{"code": "not_found", "message": f"Secret with ID {token_id} not found"}])
            token = secret['value']

        try:
            import requests
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = requests.get(f"{url.rstrip('/')}/api/org", headers=headers, timeout=30, verify=False)
            if resp.status_code == 200:
                if org_id:
                    try:
                        expected = str(org_id)
                        actual = str(resp.json().get('id'))
                    except Exception:
                        raise RuntimeError("Unable to parse organization id from response")
                    if expected != actual:
                        raise RuntimeError(f"Organization ID mismatch (expected {expected}, got {actual})")
                return api_response(message="Ping successful")
            elif resp.status_code in (401, 403):
                raise RuntimeError("Invalid token")
            else:
                raise RuntimeError(f"Unexpected response: {resp.status_code} {resp.text}")
        except Exception as e:
            logging.error(f"Grafana ping failed: {str(e)}")
            return api_response(message="Unable to reach Grafana", status=HTTP_BAD_REQUEST,
                                 errors=[{"code": "ping_failed", "message": str(e)}])
    except Exception as e:
        logging.error(f"Error pinging Grafana: {str(e)}")
        return api_response(message="Error pinging Grafana", status=HTTP_BAD_REQUEST,
                             errors=[{"code": "integration_error", "message": str(e)}])


@integrations_api.route('/api/v1/integrations/influxdb/ping', methods=['POST'])
@api_error_handler
def ping_influxdb():
    """Ping InfluxDB using connection parameters supplied in the request body.
    Expected JSON payload:
        {
            "url": "http://localhost:8086",
            "org_id": "my-org",
            "bucket": "my-bucket",
            "token": "<optional: raw token>",
            "token_id": "<optional: id of secret>"
        }
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        data = request.get_json(silent=True) or {}
        url = data.get('url')
        org_id = data.get('org_id')
        bucket = data.get('bucket')
        bucket_regex_bool = bool(data.get('bucket_regex_bool'))
        token = data.get('token')
        token_id = data.get('token_id')
        listener = data.get('listener') or ""
        source_type = data.get('source_type') or ""

        if not all([url, org_id, bucket]) or (not token and not token_id):
            return api_response(
                message="Required parameters are missing (url, org_id, bucket, token/token_id)",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_params", "message": "url, org_id, bucket and token/token_id are required"}]
            )

        # Retrieve token value from DB if token_id provided
        if not token and token_id:
            secret = DBSecrets.get_config_by_id(project_id=project_id, id=token_id)
            if not secret:
                return api_response(
                    message=f"Secret with ID {token_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Secret with ID {token_id} not found"}]
                )
            token = secret['value']

        is_v18 = (
            source_type == 'influxdb_v1.8'
            or 'v1.8' in listener
        )

        try:
            if is_v18:
                parsed = urlparse(url)
                host = parsed.hostname or url
                port = parsed.port or 8086
                client18 = None
                try:
                    client18 = InfluxDBClient18(
                        host=host,
                        port=port,
                        username=org_id,
                        password=token,
                        database=bucket,
                        timeout=30,
                        ssl=parsed.scheme == "https",
                        verify_ssl=False,
                    )
                    if not client18.ping():
                        raise RuntimeError("Ping failed")

                    databases = client18.get_list_database() or []
                    names = [db.get("name") for db in databases if isinstance(db, dict)]

                    if bucket_regex_bool:
                        pattern = bucket or ''
                        anchored = pattern
                        if not pattern.startswith('^'):
                            anchored = '^' + anchored
                        if not pattern.endswith('$'):
                            anchored = anchored + '$'
                        try:
                            rgx = re.compile(anchored)
                        except re.error as e:
                            raise RuntimeError(f"Invalid bucket regex: {pattern} ({e})")

                        matched = [name for name in names if name and rgx.search(name)]
                        if not matched:
                            raise RuntimeError(f"No databases matching regex '{pattern}' for provided credentials")
                    else:
                        if bucket not in names:
                            raise RuntimeError(f"Database '{bucket}' not found for provided credentials")
                finally:
                    if client18 is not None:
                        try:
                            client18.close()
                        except Exception:
                            pass

                return api_response(message="Ping successful")
            else:
                client = InfluxDBClient(
                    url=url,
                    org=org_id,
                    token=token,
                    timeout=30000,
                    verify_ssl=False,
                )
                health = client.health()
                if health.status != 'pass':
                    raise RuntimeError(f"Health check failed: {health.message}")

                org_api = client.organizations_api()
                orgs_res = org_api.find_organizations()
                org_list = orgs_res if isinstance(orgs_res, list) else getattr(orgs_res, 'orgs', [])
                org_obj = next((o for o in org_list if getattr(o, 'name', None) == org_id), None)
                if not org_obj:
                    raise RuntimeError(f"Organization '{org_id}' not found or not accessible with provided credentials")

                buckets_api = client.buckets_api()
                all_buckets = buckets_api.find_buckets_iter()

                if bucket_regex_bool:
                    pattern = bucket or ''
                    anchored = pattern
                    if not pattern.startswith('^'):
                        anchored = '^' + anchored
                    if not pattern.endswith('$'):
                        anchored = anchored + '$'
                    try:
                        rgx = re.compile(anchored)
                    except re.error as e:
                        raise RuntimeError(f"Invalid bucket regex: {pattern} ({e})")

                    matched = [b for b in all_buckets if b and getattr(b, 'name', None) and rgx.search(b.name)]
                    if not matched:
                        raise RuntimeError(f"No buckets matching regex '{pattern}' for provided credentials")
                else:
                    bucket_obj = None
                    for b in all_buckets:
                        if b.name == bucket:
                            bucket_obj = b
                    if not bucket_obj:
                        raise RuntimeError(f"Bucket '{bucket}' not found for provided credentials")

                client.close()
                return api_response(message="Ping successful")
        except Exception as e:
            logging.error(f"InfluxDB ping failed: {str(e)}")
            return api_response(
                message="Unable to reach InfluxDB",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "ping_failed", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error pinging InfluxDB: {str(e)}")
        return api_response(
            message="Error pinging InfluxDB",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/atlassian_confluence/ping', methods=['POST'])
@api_error_handler
def ping_atlassian_confluence():
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        data = request.get_json(silent=True) or {}
        org_url = (data.get('org_url') or '').strip()
        space_key = (data.get('space_key') or '').strip()
        token_type = (data.get('token_type') or '').strip().lower()
        email = (data.get('email') or '').strip()
        token = data.get('token')
        token_id = data.get('token_id')

        if not org_url or not space_key or not token_type or (not token and not token_id):
            return api_response(
                message="Required parameters are missing (org_url, space_key, token_type, token/token_id)",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_params", "message": "org_url, space_key, token_type and token/token_id are required"}]
            )

        if token_type == 'api_token' and not email:
            return api_response(
                message="Email is required for api_token authentication",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_params", "message": "email is required for api_token"}]
            )

        if not token and token_id:
            secret = DBSecrets.get_config_by_id(project_id=project_id, id=token_id)
            if not secret:
                return api_response(
                    message=f"Secret with ID {token_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Secret with ID {token_id} not found"}]
                )
            token = secret['value']

        try:
            if token_type == 'api_token':
                client = Confluence(url=org_url, username=email, password=token)
            else:
                client = Confluence(url=org_url, token=token)

            space = client.get_space(space_key)

            if isinstance(space, dict):
                status_code = str(space.get('statusCode') or space.get('status') or '')
                if status_code in ('401', '403'):
                    return api_response(
                        message="Invalid credentials or access denied",
                        status=int(status_code),
                        errors=[{"code": "unauthorized", "message": str(space.get('message') or 'Access denied')}]
                    )
                if status_code == '404':
                    return api_response(
                        message="Space not found",
                        status=HTTP_NOT_FOUND,
                        errors=[{"code": "not_found", "message": "Space not found"}]
                    )
                if space.get('key') and str(space.get('key')).lower() == space_key.lower():
                    return api_response(message="Ping successful")

            if space:
                return api_response(message="Ping successful")

            return api_response(
                message="Unable to reach Confluence or space not accessible",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "ping_failed", "message": "No data returned"}]
            )
        except Exception as e:
            logging.error(f"Confluence ping failed: {str(e)}")
            status = getattr(e, 'status_code', None) or getattr(e, 'status', None)
            if status is None and hasattr(e, 'response'):
                try:
                    status = getattr(e.response, 'status_code', None)
                except Exception:
                    status = None
            return api_response(
                message="Unable to reach Confluence",
                status=int(status) if isinstance(status, int) else HTTP_BAD_REQUEST,
                errors=[{"code": "ping_failed", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error pinging Confluence: {str(e)}")
        return api_response(
            message="Error pinging Confluence",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/ai_support/ping', methods=['POST'])
@api_error_handler
def ping_ai_support():
    """Ping AI Support provider by attempting a minimal text request using provided settings.
    Expected JSON payload:
        {
            "ai_provider": "openai|azure_openai|gemini",
            "ai_text_model": "...",
            "ai_image_model": "...",   # optional for ping
            "token": "<optional: raw token>",
            "token_id": "<optional: id of secret>",
            "azure_url": "<required for azure_openai>",
            "api_version": "<required for azure_openai>"
        }
    """
    try:
        project_id = get_project_id()
        if not project_id:
            return api_response(
                message="No project selected",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_project", "message": "No project selected"}]
            )

        data = request.get_json(silent=True) or {}
        ai_provider = (data.get('ai_provider') or '').strip().lower()
        ai_text_model = (data.get('ai_text_model') or '').strip()
        ai_image_model = (data.get('ai_image_model') or '').strip()
        token = data.get('token')
        token_id = data.get('token_id')
        azure_url = (data.get('azure_url') or '').strip()
        api_version = (data.get('api_version') or '').strip()

        if not ai_provider or not ai_text_model or (not token and not token_id):
            return api_response(
                message="Required parameters are missing (ai_provider, ai_text_model, token/token_id)",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_params", "message": "ai_provider, ai_text_model and token/token_id are required"}]
            )

        if ai_provider == 'azure_openai' and (not azure_url or not api_version):
            return api_response(
                message="Azure parameters missing (azure_url, api_version)",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_params", "message": "azure_url and api_version are required for azure_openai"}]
            )

        # Resolve token from secrets if only token_id provided
        if not token and token_id:
            secret = DBSecrets.get_config_by_id(project_id=project_id, id=token_id)
            if not secret:
                return api_response(
                    message=f"Secret with ID {token_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Secret with ID {token_id} not found"}]
                )
            token = secret['value']

        # Prepare provider args
        provider_args = {
            'ai_text_model': ai_text_model,
            'ai_image_model': ai_image_model or ai_text_model,
            'token': token,
            'temperature': 1,
            'system_prompt': 'You are a diagnostics helper. Reply briefly.'
        }
        if ai_provider == 'azure_openai':
            provider_args['azure_url'] = azure_url
            provider_args['api_version'] = api_version

        try:
            provider = ProviderFactory.create_provider(provider_type=ai_provider, **provider_args)
            if provider is None:
                return api_response(
                    message=f"Unsupported AI provider: {ai_provider}",
                    status=HTTP_BAD_REQUEST,
                    errors=[{"code": "invalid_provider", "message": f"Unsupported provider {ai_provider}"}]
                )

            # Minimal request to verify credentials/connectivity with explicit 30s timeout
            def _do_ping():
                return provider.send_prompt("ping")

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_ping)
                try:
                    if hasattr(provider, 'clear_last_error'):
                        provider.clear_last_error()
                    resp_text = future.result(timeout=30)
                except concurrent.futures.TimeoutError:
                    return api_response(
                        message="Ping timed out after 30 seconds",
                        status=HTTP_BAD_REQUEST,
                        errors=[{"code": "timeout", "message": "AI provider did not respond within 30 seconds"}]
                    )

            if isinstance(resp_text, str):
                cleaned = resp_text.strip().lower()
                if cleaned and not cleaned.startswith("error:") and not cleaned.startswith("failed"):
                    return api_response(message="Ping successful")

            status_override = getattr(provider, 'get_last_error_status', None)
            status = status_override() if callable(status_override) else None
            status = status or HTTP_BAD_REQUEST
            detail = getattr(provider, 'last_error_message', None)
            if not detail and isinstance(resp_text, str):
                detail = resp_text
            return api_response(
                message="Unable to reach AI provider",
                status=status,
                errors=[{"code": "ping_failed", "message": str(detail or "Ping failed")}]
            )
        except Exception as e:
            logging.error(f"AI Support ping failed: {str(e)}")
            return api_response(
                message="Unable to reach AI provider",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "ping_failed", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error pinging AI Support: {str(e)}")
        return api_response(
            message="Error pinging AI Support",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )

@integrations_api.route('/api/v1/integrations/<integration_id>', methods=['DELETE'])
@api_error_handler
def delete_integration(integration_id):
    """
    Delete an integration.

    Args:
        integration_id: The ID of the integration to delete

    Returns:
        A JSON response confirming deletion
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

        # Get integration type from query parameters
        integration_type = request.args.get('type')
        if not integration_type:
            return api_response(
                message="Integration type not specified",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_type", "message": "Integration type must be specified in the query parameters"}]
            )

        try:
            db_class = get_db_class(integration_type)

            # Check if integration exists
            existing_integration = db_class.get_config_by_id(project_id=project_id, id=integration_id)
            if not existing_integration:
                return api_response(
                    message=f"Integration with ID {integration_id} not found",
                    status=HTTP_NOT_FOUND,
                    errors=[{"code": "not_found", "message": f"Integration with ID {integration_id} not found"}]
                )

            db_class.delete(project_id=project_id, id=integration_id)

            return api_response(
                message="Integration deleted successfully",
                status=HTTP_NO_CONTENT
            )
        except ValueError as e:
            return api_response(
                message=str(e),
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "invalid_type", "message": str(e)}]
            )
    except Exception as e:
        logging.error(f"Error deleting integration: {str(e)}")
        return api_response(
            message="Error deleting integration",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "integration_error", "message": str(e)}]
        )
