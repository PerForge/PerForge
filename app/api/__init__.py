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
API module for PerForge application.
"""
from flask import Blueprint, request, current_app
from flask_login import current_user

# Import API blueprints
from app.api.projects import projects_api
from app.api.graphs import graphs_api
from app.api.reports import reports_api
from app.api.templates import templates_api
from app.api.integrations import integrations_api
from app.api.nfrs import nfrs_api
from app.api.other import other_api
from app.api.prompts import prompts_api
from app.api.secrets import secrets_api


def _api_basic_auth_guard():
    """HTTP Basic Auth guard for API blueprints.

    - Enabled when Config.BASIC_AUTH_ENABLED is True
    - Allows public access to health/version endpoints
    - Validates Authorization header against DBUsers using bcrypt
    """
    try:
        if not current_app.config.get('BASIC_AUTH_ENABLED', False):
            return None

        # Public endpoints that should remain unauthenticated
        public_paths = {
            '/api/v1/health',
            '/api/v1/version',
        }
        if request.path in public_paths:
            return None

        # If user is authenticated via Flask-Login session, allow without Basic Auth
        try:
            if current_user.is_authenticated:
                return None
        except Exception:
            # If any issue determining session auth, fall back to Basic Auth
            pass

        auth = request.authorization  # Parsed from Authorization: Basic <base64>

        # Lazy imports to avoid circular dependencies during app startup
        from app.api.base import api_response, HTTP_UNAUTHORIZED
        from app.backend.components.users.users_db import DBUsers
        from app import bc

        if not auth or not auth.username or not auth.password:
            realm = current_app.config.get('BASIC_AUTH_REALM', 'PerForge API')
            resp, code = api_response(message='Basic authentication required', status=HTTP_UNAUTHORIZED)
            resp.headers['WWW-Authenticate'] = f'Basic realm="{realm}"'
            resp.status_code = code
            return resp

        user = DBUsers.get_config_by_username(user=auth.username)
        if user and bc.check_password_hash(user['password'], auth.password):
            return None

        # Invalid credentials
        realm = current_app.config.get('BASIC_AUTH_REALM', 'PerForge API')
        resp, code = api_response(message='Invalid Basic authentication credentials', status=HTTP_UNAUTHORIZED)
        resp.headers['WWW-Authenticate'] = f'Basic realm="{realm}"'
        resp.status_code = code
        return resp
    except Exception:
        # Fail closed on unexpected errors (challenge again)
        from app.api.base import api_response, HTTP_UNAUTHORIZED
        realm = current_app.config.get('BASIC_AUTH_REALM', 'PerForge API')
        resp, code = api_response(message='Authentication error', status=HTTP_UNAUTHORIZED)
        resp.headers['WWW-Authenticate'] = f'Basic realm="{realm}"'
        resp.status_code = code
        return resp

# Create a combined API blueprint
api = Blueprint('api', __name__)

# Register API blueprints
def register_blueprints(app):
    """
    Register all API blueprints with the Flask app.

    Args:
        app: The Flask application
    """
    # Attach Basic Auth guard to all API blueprints (executes only if enabled)
    for bp in (
        projects_api,
        graphs_api,
        reports_api,
        templates_api,
        integrations_api,
        nfrs_api,
        other_api,
        prompts_api,
        secrets_api,
    ):
        bp.before_request(_api_basic_auth_guard)

    app.register_blueprint(projects_api)
    app.register_blueprint(graphs_api)
    app.register_blueprint(reports_api)
    app.register_blueprint(templates_api)
    app.register_blueprint(integrations_api)
    app.register_blueprint(nfrs_api)
    app.register_blueprint(other_api)
    app.register_blueprint(prompts_api)
    app.register_blueprint(secrets_api)

    # Register the combined API blueprint
    app.register_blueprint(api)

    return app
