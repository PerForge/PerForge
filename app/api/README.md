# PerForge RESTful API

This document describes the RESTful API endpoints for the PerForge application.

## API Design Principles

The PerForge API follows these RESTful principles:

1. **Resource-Based URLs**: URLs are structured around resources (projects, templates, reports, etc.)
2. **HTTP Methods**: Uses standard HTTP methods (GET, POST, PUT, DELETE) for CRUD operations
3. **JSON Responses**: All responses are in JSON format with a consistent structure
4. **Proper Status Codes**: Uses appropriate HTTP status codes for different responses
5. **Versioning**: API is versioned to allow for future changes

## API Response Format

All API responses follow this standard format:

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "Optional message",
  "errors": [
    {
      "code": "error_code",
      "message": "Error message"
    }
  ]
}
```

## Available Endpoints

### Projects API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/projects` | GET | Get all projects |
| `/api/v1/projects/<project_id>` | GET | Get a specific project |
| `/api/v1/projects` | POST | Create a new project |
| `/api/v1/projects/<project_id>` | PUT | Update a project |
| `/api/v1/projects/<project_id>` | DELETE | Delete a project |
| `/api/v1/projects/<project_id>/output-configs` | GET | Get output configurations for a project |
| `/api/v1/projects/set-active/<project_id>` | POST | Set a project as the active project |

### Templates API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/templates` | GET | Get all templates |
| `/api/v1/templates/<template_id>` | GET | Get a specific template |
| `/api/v1/templates` | POST | Create a new template |
| `/api/v1/templates/<template_id>` | PUT | Update a template |
| `/api/v1/templates/<template_id>` | DELETE | Delete a template |
| `/api/v1/template-groups` | GET | Get all template groups |
| `/api/v1/template-groups/<group_id>` | GET | Get a specific template group |
| `/api/v1/template-groups` | POST | Create a new template group |
| `/api/v1/template-groups/<group_id>` | PUT | Update a template group |
| `/api/v1/template-groups/<group_id>` | DELETE | Delete a template group |

### Reports API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tests` | GET | Get all test configurations |
| `/api/v1/tests/data` | GET | Get test data for a specific data source |
| `/api/v1/reports` | POST | Generate a report |
| `/api/v1/reports/data` | POST | Get report data for a specific test |

### Graphs API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/graphs` | GET | Get all graphs |
| `/api/v1/graphs/<graph_id>` | GET | Get a specific graph |
| `/api/v1/graphs` | POST | Create a new graph |
| `/api/v1/graphs/<graph_id>` | PUT | Update a graph |
| `/api/v1/graphs/<graph_id>` | DELETE | Delete a graph |

### NFRs API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/nfrs` | GET | Get all NFRs |
| `/api/v1/nfrs/<nfr_id>` | GET | Get a specific NFR |
| `/api/v1/nfrs` | POST | Create a new NFR |
| `/api/v1/nfrs/<nfr_id>` | PUT | Update an NFR |
| `/api/v1/nfrs/<nfr_id>` | DELETE | Delete an NFR |

### Prompts API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prompts` | GET | Get all prompts (can filter by place parameter) |
| `/api/v1/prompts/<prompt_id>` | GET | Get a specific prompt |
| `/api/v1/prompts` | POST | Create a new prompt |
| `/api/v1/prompts/<prompt_id>` | PUT | Update a prompt |
| `/api/v1/prompts/<prompt_id>` | DELETE | Delete a prompt |

### Secrets API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/secrets` | GET | Get all secrets |
| `/api/v1/secrets/<secret_id>` | GET | Get a specific secret |
| `/api/v1/secrets` | POST | Create a new secret |
| `/api/v1/secrets/<secret_id>` | PUT | Update a secret |
| `/api/v1/secrets/<secret_id>` | DELETE | Delete a secret |

### Integrations API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/integrations` | GET | Get all integrations |
| `/api/v1/integrations/<integration_id>` | GET | Get a specific integration |
| `/api/v1/integrations` | POST | Create a new integration |
| `/api/v1/integrations/<integration_id>` | PUT | Update an integration |
| `/api/v1/integrations/<integration_id>` | DELETE | Delete an integration |

### Base API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/` | GET | Get API status |

### Other API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check endpoint |
| `/api/v1/version` | GET | Get application version |
| `/api/v1/config` | GET | Get application configuration |
| `/api/v1/uploads/<filename>` | GET | Get an uploaded file |
| `/api/v1/uploads` | POST | Upload a file |

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request:

- 200 OK: The request was successful
- 201 Created: A new resource was created
- 204 No Content: The request was successful but no content is returned (used for DELETE operations)
- 400 Bad Request: The request was invalid
- 401 Unauthorized: Authentication is required
- 403 Forbidden: The client does not have permission to access the resource
- 404 Not Found: The requested resource was not found
- 500 Internal Server Error: An error occurred on the server

## Authentication

Currently, the API uses cookie-based authentication. The project ID is stored in a cookie and used to determine the current project context.

## Future Improvements

1. Token-based authentication
2. Rate limiting
3. Pagination for large result sets
4. More comprehensive error codes
5. API documentation using Swagger/OpenAPI
