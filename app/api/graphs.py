"""
Graphs API endpoints.
"""
import logging
from flask import Blueprint, request, current_app
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.graphs.graphs_db import DBGraphs
from app.backend.errors import ErrorMessages
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_OK, HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for graphs API
graphs_api = Blueprint('graphs_api', __name__)

@graphs_api.route('/api/v1/graphs', methods=['GET'])
@api_error_handler
def get_graphs():
    """
    Get all graphs for the current project.

    Returns:
        A JSON response with graphs
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

        graph_configs = DBGraphs.get_configs(schema_name=project_data['name'])
        return api_response(data={"graphs": graph_configs})
    except Exception as e:
        logging.error(f"Error getting graphs: {str(e)}")
        return api_response(
            message="Error retrieving graphs",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "graph_error", "message": str(e)}]
        )

@graphs_api.route('/api/v1/graphs/<graph_id>', methods=['GET'])
@api_error_handler
def get_graph(graph_id):
    """
    Get a specific graph by ID.

    Args:
        graph_id: The ID of the graph to get

    Returns:
        A JSON response with the graph data
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

        graph_data = DBGraphs.get_config_by_id(schema_name=project_data['name'], id=graph_id)
        if not graph_data:
            return api_response(
                message=f"Graph with ID {graph_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Graph with ID {graph_id} not found"}]
            )

        return api_response(data={"graph": graph_data})
    except Exception as e:
        logging.error(f"Error getting graph: {str(e)}")
        return api_response(
            message="Error retrieving graph",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "graph_error", "message": str(e)}]
        )

@graphs_api.route('/api/v1/graphs', methods=['POST'])
@api_error_handler
def create_graph():
    """
    Create a new graph.

    Returns:
        A JSON response with the new graph ID
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

        graph_data = request.get_json()
        if not graph_data:
            return api_response(
                message="No graph data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No graph data provided"}]
            )

        # Clean up empty values
        for key, value in graph_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                graph_data[key] = None

        # Ensure ID is None for new graph
        graph_data["id"] = None

        new_graph_id = DBGraphs.save(
            schema_name=project_data['name'],
            data=graph_data
        )

        return api_response(
            data={"graph_id": new_graph_id},
            message="Graph created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating graph: {str(e)}")
        return api_response(
            message="Error creating graph",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "graph_error", "message": str(e)}]
        )

@graphs_api.route('/api/v1/graphs/<graph_id>', methods=['PUT'])
@api_error_handler
def update_graph(graph_id):
    """
    Update an existing graph.

    Args:
        graph_id: The ID of the graph to update

    Returns:
        A JSON response with the updated graph
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

        # Check if graph exists
        existing_graph = DBGraphs.get_config_by_id(schema_name=project_data['name'], id=graph_id)
        if not existing_graph:
            return api_response(
                message=f"Graph with ID {graph_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Graph with ID {graph_id} not found"}]
            )

        graph_data = request.get_json()
        if not graph_data:
            return api_response(
                message="No graph data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No graph data provided"}]
            )

        # Clean up empty values
        for key, value in graph_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                graph_data[key] = None

        # Ensure ID matches URL
        graph_data["id"] = graph_id

        DBGraphs.update(
            schema_name=project_data['name'],
            data=graph_data
        )

        return api_response(
            data={"graph_id": graph_id},
            message="Graph updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating graph: {str(e)}")
        return api_response(
            message="Error updating graph",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "graph_error", "message": str(e)}]
        )

@graphs_api.route('/api/v1/graphs/<graph_id>', methods=['DELETE'])
@api_error_handler
def delete_graph(graph_id):
    """
    Delete a graph.

    Args:
        graph_id: The ID of the graph to delete

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

        # Check if graph exists
        existing_graph = DBGraphs.get_config_by_id(schema_name=project_data['name'], id=graph_id)
        if not existing_graph:
            return api_response(
                message=f"Graph with ID {graph_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Graph with ID {graph_id} not found"}]
            )

        DBGraphs.delete(schema_name=project_data['name'], id=graph_id)

        return api_response(
            message="Graph deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting graph: {str(e)}")
        return api_response(
            message="Error deleting graph",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "graph_error", "message": str(e)}]
        )
