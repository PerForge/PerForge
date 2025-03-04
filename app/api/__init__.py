"""
API module for PerForge application.
"""
from flask import Blueprint

# Import API blueprints
from app.api.projects import projects_api
from app.api.graphs import graphs_api
from app.api.reports import reports_api
from app.api.templates import templates_api
from app.api.integrations import integrations_api
from app.api.nfrs import nfrs_api
# from app.api.other import other_api
from app.api.prompts import prompts_api
from app.api.secrets import secrets_api

# Create a combined API blueprint
api = Blueprint('api', __name__)

# Register API blueprints
def register_blueprints(app):
    """
    Register all API blueprints with the Flask app.

    Args:
        app: The Flask application
    """
    app.register_blueprint(projects_api)
    app.register_blueprint(graphs_api)
    app.register_blueprint(reports_api)
    app.register_blueprint(templates_api)
    app.register_blueprint(integrations_api)
    app.register_blueprint(nfrs_api)
    # app.register_blueprint(other_api)
    app.register_blueprint(prompts_api)
    app.register_blueprint(secrets_api)

    # Register the combined API blueprint
    app.register_blueprint(api)

    return app
