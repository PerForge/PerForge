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
from flask import Blueprint, request
from app.backend.components.projects.projects_db import DBProjects
from app.backend.integrations.ai_support.ai_support_db import DBAISupport
from app.backend.integrations.data_sources.influxdb_v2.influxdb_db import DBInfluxdb
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.integrations.atlassian_jira.atlassian_jira_db import DBAtlassianJira
from app.backend.integrations.azure_wiki.azure_wiki_db import DBAzureWiki
from app.backend.integrations.grafana.grafana_db import DBGrafana
from app.backend.integrations.smtp_mail.smtp_mail_db import DBSMTPMail
from app.backend.components.secrets.secrets_db import DBSecrets
from influxdb_client import InfluxDBClient
from app.api.base import (
    api_response, api_error_handler, get_project_id,
   HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

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
            resp = requests.get(f"{url.rstrip('/')}/api/org", headers=headers, timeout=5)
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
        token = data.get('token')
        token_id = data.get('token_id')
        org_id = data.get('org_id')

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

        # Attempt connection
        try:
            client = InfluxDBClient(url=url, org=org_id, token=token, timeout=5000)
            # Simple health check plus bucket existence validation
            health = client.health()
            if health.status != 'pass':
                raise RuntimeError(f"Health check failed: {health.message}")

            # Validate organization exists
            org_api = client.organizations_api()
            orgs_res = org_api.find_organizations()
            org_list = orgs_res if isinstance(orgs_res, list) else getattr(orgs_res, 'orgs', [])
            org_obj = next((o for o in org_list if getattr(o, 'name', None) == org_id), None)
            if not org_obj:
                raise RuntimeError(f"Organization '{org_id}' not found or not accessible with provided credentials")

            buckets_api = client.buckets_api()
            bucket_obj = next((b for b in buckets_api.find_buckets().buckets if b.name == bucket), None)
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
