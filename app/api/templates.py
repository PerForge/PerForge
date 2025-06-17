"""
Templates API endpoints.
"""
import logging
from flask import Blueprint, request, current_app
from app.backend.components.projects.projects_db import DBProjects
from app.backend.components.templates.templates_db import DBTemplates
from app.backend.components.templates.template_groups_db import DBTemplateGroups
from app.backend.components.nfrs.nfrs_db import DBNFRs
from app.backend.components.prompts.prompts_db import DBPrompts
from app.backend.components.graphs.graphs_db import DBGraphs
from app.backend.errors import ErrorMessages
from app.api.base import (
    api_response, api_error_handler, get_project_id,
    HTTP_OK, HTTP_CREATED, HTTP_NO_CONTENT, HTTP_BAD_REQUEST, HTTP_NOT_FOUND
)

# Create a Blueprint for templates API
templates_api = Blueprint('templates_api', __name__)

@templates_api.route('/api/v1/templates', methods=['GET'])
@api_error_handler
def get_templates():
    """
    Get all templates for the current project.
    
    Returns:
        A JSON response with templates
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
            
        template_configs = DBTemplates.get_configs(project_id=project_id)
        return api_response(data={"templates": template_configs})
    except Exception as e:
        logging.error(f"Error getting templates: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00007.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/templates/<template_id>', methods=['GET'])
@api_error_handler
def get_template(template_id):
    """
    Get a specific template by ID.
    
    Args:
        template_id: The ID of the template to get
        
    Returns:
        A JSON response with the template data
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
            
        template_data = DBTemplates.get_config_by_id(project_id=project_id, id=template_id)
        if not template_data:
            return api_response(
                message=f"Template with ID {template_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template with ID {template_id} not found"}]
            )
            
        return api_response(data={"template": template_data})
    except Exception as e:
        logging.error(f"Error getting template: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00002.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/templates', methods=['POST'])
@api_error_handler
def create_template():
    """
    Create a new template.
    
    Returns:
        A JSON response with the new template ID
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
            
        template_data = request.get_json()
        if not template_data:
            return api_response(
                message="No template data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No template data provided"}]
            )
            
        # Clean up empty values
        for key, value in template_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                template_data[key] = None
                
        # Ensure ID is None for new template
        template_data["id"] = None
        
        new_template_id = DBTemplates.save(
            project_id=project_id,
            data=template_data
        )
        
        return api_response(
            data={"template_id": new_template_id},
            message="Template created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating template: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00001.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/templates/<template_id>', methods=['PUT'])
@api_error_handler
def update_template(template_id):
    """
    Update an existing template.
    
    Args:
        template_id: The ID of the template to update
        
    Returns:
        A JSON response with the updated template
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
            
        # Check if template exists
        existing_template = DBTemplates.get_config_by_id(project_id=project_id, id=template_id)
        if not existing_template:
            return api_response(
                message=f"Template with ID {template_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template with ID {template_id} not found"}]
            )
            
        template_data = request.get_json()
        if not template_data:
            return api_response(
                message="No template data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No template data provided"}]
            )
            
        # Clean up empty values
        for key, value in template_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                template_data[key] = None
                
        # Ensure ID matches URL
        template_data["id"] = template_id
        
        DBTemplates.update(
            project_id=project_id,
            data=template_data
        )
        
        return api_response(
            data={"template_id": template_id},
            message="Template updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating template: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00001.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/templates/<template_id>', methods=['DELETE'])
@api_error_handler
def delete_template(template_id):
    """
    Delete a template.
    
    Args:
        template_id: The ID of the template to delete
        
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
            
        # Check if template exists
        existing_template = DBTemplates.get_config_by_id(project_id=project_id, id=template_id)
        if not existing_template:
            return api_response(
                message=f"Template with ID {template_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template with ID {template_id} not found"}]
            )
            
        DBTemplates.delete(project_id=project_id, id=template_id)
        
        return api_response(
            message="Template deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting template: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00003.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_error", "message": str(e)}]
        )

# Template Groups API

@templates_api.route('/api/v1/template-groups', methods=['GET'])
@api_error_handler
def get_template_groups():
    """
    Get all template groups for the current project.
    
    Returns:
        A JSON response with template groups
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
            
        template_group_configs = DBTemplateGroups.get_configs(project_id=project_id)
        return api_response(data={"template_groups": template_group_configs})
    except Exception as e:
        logging.error(f"Error getting template groups: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00005.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_group_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/template-groups/<group_id>', methods=['GET'])
@api_error_handler
def get_template_group(group_id):
    """
    Get a specific template group by ID.
    
    Args:
        group_id: The ID of the template group to get
        
    Returns:
        A JSON response with the template group data
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
            
        template_group_data = DBTemplateGroups.get_config_by_id(project_id=project_id, id=group_id)
        if not template_group_data:
            return api_response(
                message=f"Template group with ID {group_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template group with ID {group_id} not found"}]
            )
            
        return api_response(data={"template_group": template_group_data})
    except Exception as e:
        logging.error(f"Error getting template group: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00005.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_group_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/template-groups', methods=['POST'])
@api_error_handler
def create_template_group():
    """
    Create a new template group.
    
    Returns:
        A JSON response with the new template group ID
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
            
        template_group_data = request.get_json()
        if not template_group_data:
            return api_response(
                message="No template group data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No template group data provided"}]
            )
            
        # Clean up empty values
        for key, value in template_group_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # Ensure ID is None for all data items
                        if 'id' in item:
                            item['id'] = None
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                template_group_data[key] = None
                
        # Ensure ID is None for new template group
        template_group_data["id"] = None
        
        new_group_id = DBTemplateGroups.save(
            project_id=project_id,
            data=template_group_data
        )
        
        return api_response(
            data={"template_group_id": new_group_id},
            message="Template group created successfully",
            status=HTTP_CREATED
        )
    except Exception as e:
        logging.error(f"Error creating template group: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00004.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_group_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/template-groups/<group_id>', methods=['PUT'])
@api_error_handler
def update_template_group(group_id):
    """
    Update an existing template group.
    
    Args:
        group_id: The ID of the template group to update
        
    Returns:
        A JSON response with the updated template group
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
            
        # Check if template group exists
        existing_group = DBTemplateGroups.get_config_by_id(project_id=project_id, id=group_id)
        if not existing_group:
            return api_response(
                message=f"Template group with ID {group_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template group with ID {group_id} not found"}]
            )
            
        template_group_data = request.get_json()
        if not template_group_data:
            return api_response(
                message="No template group data provided",
                status=HTTP_BAD_REQUEST,
                errors=[{"code": "missing_data", "message": "No template group data provided"}]
            )
            
        # Clean up empty values
        for key, value in template_group_data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # Ensure ID is None for all data items to let the database auto-generate new IDs
                        if 'id' in item:
                            item['id'] = None
                        for k, v in item.items():
                            if v == '':
                                item[k] = None
            elif value == '':
                template_group_data[key] = None
                
        # Ensure ID matches URL
        template_group_data["id"] = group_id
        
        DBTemplateGroups.update(
            project_id=project_id,
            data=template_group_data
        )
        
        return api_response(
            data={"template_group_id": group_id},
            message="Template group updated successfully"
        )
    except Exception as e:
        logging.error(f"Error updating template group: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00004.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_group_error", "message": str(e)}]
        )

@templates_api.route('/api/v1/template-groups/<group_id>', methods=['DELETE'])
@api_error_handler
def delete_template_group(group_id):
    """
    Delete a template group.
    
    Args:
        group_id: The ID of the template group to delete
        
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
            
        # Check if template group exists
        existing_group = DBTemplateGroups.get_config_by_id(project_id=project_id, id=group_id)
        if not existing_group:
            return api_response(
                message=f"Template group with ID {group_id} not found",
                status=HTTP_NOT_FOUND,
                errors=[{"code": "not_found", "message": f"Template group with ID {group_id} not found"}]
            )
            
        DBTemplateGroups.delete(project_id=project_id, id=group_id)
        
        return api_response(
            message="Template group deleted successfully",
            status=HTTP_NO_CONTENT
        )
    except Exception as e:
        logging.error(f"Error deleting template group: {str(e)}")
        return api_response(
            message=ErrorMessages.ER00006.value,
            status=HTTP_BAD_REQUEST,
            errors=[{"code": "template_group_error", "message": str(e)}]
        )
