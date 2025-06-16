"""
NFRs (Non-Functional Requirements) API endpoints.
"""
import logging
from flask import Blueprint, request, current_app
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.nfrs.nfrs_db import DBNFRs
from app.backend.errors import ErrorMessages
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_OK, HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for NFRs API
nfrs_api = Blueprint('nfrs_api', __name__)

@nfrs_api.route('/api/v1/nfrs', methods=['GET'])
@api_error_handler
def get_nfrs():
    """
    Get all NFRs for the current project.
    
    Returns:
        A JSON response with NFRs
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
            
        nfr_configs = DBNFRs.get_configs(project_id=project_id)
        return api_response(data={"nfrs": nfr_configs})
    except Exception as e:
        logging.error(f"Error getting NFRs: {str(e)}")
        return api_response(
            message="Error retrieving NFRs",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "nfr_error", "message": str(e)}]
        )

@nfrs_api.route('/api/v1/nfrs/<nfr_id>', methods=['GET'])
@api_error_handler
def get_nfr(nfr_id):
    """
    Get a specific NFR by ID.
    
    Args:
        nfr_id: The ID of the NFR to get
        
    Returns:
        A JSON response with the NFR data
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
            
        nfr_data = DBNFRs.get_config_by_id(project_id=project_id, id=nfr_id)
        if not nfr_data:
            return api_response(
                message=f"NFR with ID {nfr_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"NFR with ID {nfr_id} not found"}]
            )
            
        return api_response(data={"nfr": nfr_data})
    except Exception as e:
        logging.error(f"Error getting NFR: {str(e)}")
        return api_response(
            message="Error retrieving NFR",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "nfr_error", "message": str(e)}]
        )

@nfrs_api.route('/api/v1/nfrs', methods=['POST'])
@api_error_handler
def create_nfr():
    """
    Create a new NFR.
    
    Returns:
        A JSON response with the new NFR ID
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
            
        nfr_data = request.get_json()
        if not nfr_data:
            return api_response(
                message="No NFR data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No NFR data provided"}]
            )
            
        # Clean up empty values
        for key, value in nfr_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                nfr_data[key] = None
                
        # Ensure ID is None for new NFR
        nfr_data["id"] = None
        
        new_nfr_id = DBNFRs.save(
            project_id=project_id,
            data=nfr_data
        )
        
        return api_response(
            data={"nfr_id": new_nfr_id},
            message="NFR created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating NFR: {str(e)}")
        return api_response(
            message="Error creating NFR",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "nfr_error", "message": str(e)}]
        )

@nfrs_api.route('/api/v1/nfrs/<nfr_id>', methods=['PUT'])
@api_error_handler
def update_nfr(nfr_id):
    """
    Update an existing NFR.
    
    Args:
        nfr_id: The ID of the NFR to update
        
    Returns:
        A JSON response with the updated NFR
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
            
        # Check if NFR exists
        existing_nfr = DBNFRs.get_config_by_id(project_id=project_id, id=nfr_id)
        if not existing_nfr:
            return api_response(
                message=f"NFR with ID {nfr_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"NFR with ID {nfr_id} not found"}]
            )
            
        nfr_data = request.get_json()
        if not nfr_data:
            return api_response(
                message="No NFR data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No NFR data provided"}]
            )
            
        # Clean up empty values
        for key, value in nfr_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                nfr_data[key] = None
                
        # Ensure ID matches URL
        nfr_data["id"] = nfr_id
        
        DBNFRs.update(
            project_id=project_id,
            data=nfr_data
        )
        
        return api_response(
            data={"nfr_id": nfr_id},
            message="NFR updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating NFR: {str(e)}")
        return api_response(
            message="Error updating NFR",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "nfr_error", "message": str(e)}]
        )

@nfrs_api.route('/api/v1/nfrs/<nfr_id>', methods=['DELETE'])
@api_error_handler
def delete_nfr(nfr_id):
    """
    Delete an NFR.
    
    Args:
        nfr_id: The ID of the NFR to delete
        
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
            
        # Check if NFR exists
        existing_nfr = DBNFRs.get_config_by_id(project_id=project_id, id=nfr_id)
        if not existing_nfr:
            return api_response(
                message=f"NFR with ID {nfr_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"NFR with ID {nfr_id} not found"}]
            )
            
        DBNFRs.delete(project_id=project_id, id=nfr_id)
        
        return api_response(
            message="NFR deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting NFR: {str(e)}")
        return api_response(
            message="Error deleting NFR",
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "nfr_error", "message": str(e)}]
        )
