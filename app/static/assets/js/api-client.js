/**
 * PerForge API Client
 *
 * A JavaScript client for interacting with the PerForge RESTful API
 */

const apiClient = {
    /**
     * Base API URL
     */
    baseUrl: '/api/v1',

    /**
     * Make a GET request to the API
     *
     * @param {string} endpoint - API endpoint to call
     * @param {Object} params - Query parameters
     * @returns {Promise} - Promise that resolves with the API response
     */
    get: function(endpoint, params = {}) {
        const url = new URL(this.baseUrl + endpoint, window.location.origin);

        // Add query parameters
        if (params) {
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });
        }

        return fetch(url.toString(), {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw err;
                });
            }
            return response.json();
        });
    },

    /**
     * Make a POST request to the API
     *
     * @param {string} endpoint - API endpoint to call
     * @param {Object} data - Data to send in the request body
     * @returns {Promise} - Promise that resolves with the API response
     */
    post: function(endpoint, data = {}) {
        return fetch(this.baseUrl + endpoint, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw err;
                });
            }
            return response.json();
        });
    },

    /**
     * Make a PUT request to the API
     *
     * @param {string} endpoint - API endpoint to call
     * @param {Object} data - Data to send in the request body
     * @returns {Promise} - Promise that resolves with the API response
     */
    put: function(endpoint, data = {}) {
        return fetch(this.baseUrl + endpoint, {
            method: 'PUT',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw err;
                });
            }
            return response.json();
        });
    },

    /**
     * Make a DELETE request to the API
     *
     * @param {string} endpoint - API endpoint to call
     * @returns {Promise} - Promise that resolves with the API response
     */
    delete: function(endpoint) {
        return fetch(this.baseUrl + endpoint, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw err;
                });
            }
            // Check if there's content to parse
            if (response.status === 204) {
                // No content, return empty object
                return {};
            }
            return response.json();
        });
    },

    /**
     * Projects API
     */
    projects: {
        /**
         * Get all projects
         *
         * @returns {Promise} - Promise that resolves with projects data
         */
        getAll: function() {
            return apiClient.get('/projects');
        },

        /**
         * Get a project by ID
         *
         * @param {string} id - Project ID
         * @returns {Promise} - Promise that resolves with project data
         */
        getById: function(id) {
            return apiClient.get(`/projects/${id}`);
        },

        /**
         * Create a new project
         *
         * @param {Object} data - Project data
         * @returns {Promise} - Promise that resolves with the new project ID
         */
        create: function(data) {
            return apiClient.post('/projects', data);
        },

        /**
         * Update a project
         *
         * @param {string} id - Project ID
         * @param {Object} data - Project data
         * @returns {Promise} - Promise that resolves with the updated project
         */
        update: function(id, data) {
            return apiClient.put(`/projects/${id}`, data);
        },

        /**
         * Delete a project
         *
         * @param {string} id - Project ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/projects/${id}`);
        },

        /**
         * Set the active project
         *
         * @param {string} id - Project ID to set as active
         * @returns {Promise} - Promise that resolves with success message
         */
        setActive: function(id) {
            return apiClient.post(`/projects/set-active/${id}`)
                .then(response => {
                    // After successfully setting the active project, redirect to the home page
                    window.location.href = '/';
                    return response;
                });
        },

        /**
         * Get output configurations for a project
         *
         * @param {string} id - Project ID
         * @returns {Promise} - Promise that resolves with output configurations
         */
        getOutputConfigs: function(id) {
            return apiClient.get(`/projects/${id}/output-configs`);
        }
    },

    /**
     * Templates API
     */
    templates: {
        /**
         * Get all templates
         *
         * @returns {Promise} - Promise that resolves with templates data
         */
        getAll: function() {
            return apiClient.get('/templates');
        },

        /**
         * Get a template by ID
         *
         * @param {string} id - Template ID
         * @returns {Promise} - Promise that resolves with template data
         */
        getById: function(id) {
            return apiClient.get(`/templates/${id}`);
        },

        /**
         * Create a new template
         *
         * @param {Object} data - Template data
         * @returns {Promise} - Promise that resolves with the new template ID
         */
        create: function(data) {
            return apiClient.post('/templates', data);
        },

        /**
         * Update a template
         *
         * @param {string} id - Template ID
         * @param {Object} data - Template data
         * @returns {Promise} - Promise that resolves with the updated template
         */
        update: function(id, data) {
            return apiClient.put(`/templates/${id}`, data);
        },

        /**
         * Delete a template
         *
         * @param {string} id - Template ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/templates/${id}`);
        }
    },

    /**
     * Graphs API
     */
    graphs: {
        /**
         * Get all graphs
         *
         * @returns {Promise} - Promise that resolves with graphs data
         */
        getAll: function() {
            return apiClient.get('/graphs');
        },

        /**
         * Get a graph by ID
         *
         * @param {string} id - Graph ID
         * @returns {Promise} - Promise that resolves with graph data
         */
        getById: function(id) {
            return apiClient.get(`/graphs/${id}`);
        },

        /**
         * Create a new graph
         *
         * @param {Object} data - Graph data
         * @returns {Promise} - Promise that resolves with the new graph ID
         */
        create: function(data) {
            return apiClient.post('/graphs', data);
        },

        /**
         * Update a graph
         *
         * @param {string} id - Graph ID
         * @param {Object} data - Graph data
         * @returns {Promise} - Promise that resolves with the updated graph
         */
        update: function(id, data) {
            return apiClient.put(`/graphs/${id}`, data);
        },

        /**
         * Delete a graph
         *
         * @param {string} id - Graph ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/graphs/${id}`);
        }
    },

    /**
     * Template Groups API
     */
    templateGroups: {
        /**
         * Get all template groups
         *
         * @returns {Promise} - Promise that resolves with template groups data
         */
        getAll: function() {
            return apiClient.get('/template-groups');
        },

        /**
         * Get a template group by ID
         *
         * @param {string} id - Template group ID
         * @returns {Promise} - Promise that resolves with template group data
         */
        getById: function(id) {
            return apiClient.get(`/template-groups/${id}`);
        },

        /**
         * Create a new template group
         *
         * @param {Object} data - Template group data
         * @returns {Promise} - Promise that resolves with the new template group ID
         */
        create: function(data) {
            return apiClient.post('/template-groups', data);
        },

        /**
         * Update a template group
         *
         * @param {string} id - Template group ID
         * @param {Object} data - Template group data
         * @returns {Promise} - Promise that resolves with the updated template group
         */
        update: function(id, data) {
            return apiClient.put(`/template-groups/${id}`, data);
        },

        /**
         * Delete a template group
         *
         * @param {string} id - Template group ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/template-groups/${id}`);
        }
    },

    /**
     * Integrations API
     */
    integrations: {
        /**
         * Get all integrations
         *
         * @returns {Promise} - Promise that resolves with integrations data
         */
        getAll: function() {
            return apiClient.get('/integrations');
        },

        /**
         * Get an integration by ID
         *
         * @param {string} id - Integration ID
         * @param {string} type - Integration type (ai_support, influxdb, etc.)
         * @returns {Promise} - Promise that resolves with integration data
         */
        getById: function(id, type) {
            return apiClient.get(`/integrations/${id}?type=${type}`);
        },

        /**
         * Create a new integration
         *
         * @param {Object} data - Integration data
         * @param {string} type - Integration type (ai_support, influxdb, etc.)
         * @returns {Promise} - Promise that resolves with the new integration ID
         */
        create: function(data, type) {
            // Add integration type to data
            const integrationData = { ...data, integration_type: type };
            return apiClient.post('/integrations', integrationData);
        },

        /**
         * Update an integration
         *
         * @param {string} id - Integration ID
         * @param {Object} data - Integration data
         * @param {string} type - Integration type (ai_support, influxdb, etc.)
         * @returns {Promise} - Promise that resolves with the updated integration
         */
        update: function(id, data, type) {
            // Add integration type to data
            const integrationData = { ...data, integration_type: type };
            return apiClient.put(`/integrations/${id}`, integrationData);
        },

        /**
         * Delete an integration
         *
         * @param {string} id - Integration ID
         * @param {string} type - Integration type (ai_support, influxdb, etc.)
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id, type) {
            return apiClient.delete(`/integrations/${id}?type=${type}`);
        }
    },

    /**
     * NFRs API
     */
    nfrs: {
        /**
         * Get all NFRs
         *
         * @returns {Promise} - Promise that resolves with NFRs data
         */
        getAll: function() {
            return apiClient.get('/nfrs');
        },

        /**
         * Get an NFR by ID
         *
         * @param {string} id - NFR ID
         * @returns {Promise} - Promise that resolves with NFR data
         */
        getById: function(id) {
            return apiClient.get(`/nfrs/${id}`);
        },

        /**
         * Create a new NFR
         *
         * @param {Object} data - NFR data
         * @returns {Promise} - Promise that resolves with the new NFR ID
         */
        create: function(data) {
            return apiClient.post('/nfrs', data);
        },

        /**
         * Update an NFR
         *
         * @param {string} id - NFR ID
         * @param {Object} data - NFR data
         * @returns {Promise} - Promise that resolves with the updated NFR
         */
        update: function(id, data) {
            return apiClient.put(`/nfrs/${id}`, data);
        },

        /**
         * Delete an NFR
         *
         * @param {string} id - NFR ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/nfrs/${id}`);
        }
    },

    /**
     * Prompts API
     */
    prompts: {
        /**
         * Get all prompts
         * 
         * @param {Object} params - Optional parameters (place)
         * @returns {Promise} - Promise that resolves with prompts data
         */
        getAll: function(params = {}) {
            return apiClient.get('/prompts', params);
        },

        /**
         * Get a prompt by ID
         *
         * @param {string} id - Prompt ID
         * @returns {Promise} - Promise that resolves with prompt data
         */
        getById: function(id) {
            return apiClient.get(`/prompts/${id}`);
        },

        /**
         * Create a new prompt
         *
         * @param {Object} data - Prompt data
         * @returns {Promise} - Promise that resolves with the new prompt ID
         */
        create: function(data) {
            return apiClient.post('/prompts', data);
        },

        /**
         * Update a prompt
         *
         * @param {string} id - Prompt ID
         * @param {Object} data - Prompt data
         * @returns {Promise} - Promise that resolves with the updated prompt
         */
        update: function(id, data) {
            return apiClient.put(`/prompts/${id}`, data);
        },

        /**
         * Delete a prompt
         *
         * @param {string} id - Prompt ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/prompts/${id}`);
        }
    },

    /**
     * Secrets API
     */
    secrets: {
        /**
         * Get all secrets
         *
         * @returns {Promise} - Promise that resolves with secrets data
         */
        getAll: function() {
            return apiClient.get('/secrets');
        },

        /**
         * Get a secret by ID
         *
         * @param {string} id - Secret ID
         * @returns {Promise} - Promise that resolves with secret data
         */
        getById: function(id) {
            return apiClient.get(`/secrets/${id}`);
        },

        /**
         * Create a new secret
         *
         * @param {Object} data - Secret data
         * @returns {Promise} - Promise that resolves with the new secret ID
         */
        create: function(data) {
            return apiClient.post('/secrets', data);
        },

        /**
         * Update a secret
         *
         * @param {string} id - Secret ID
         * @param {Object} data - Secret data
         * @returns {Promise} - Promise that resolves with the updated secret
         */
        update: function(id, data) {
            return apiClient.put(`/secrets/${id}`, data);
        },

        /**
         * Delete a secret
         *
         * @param {string} id - Secret ID
         * @returns {Promise} - Promise that resolves with success message
         */
        delete: function(id) {
            return apiClient.delete(`/secrets/${id}`);
        }
    },

    /**
     * Reports API
     */
    reports: {
        /**
         * Get report data for a specific test
         *
         * @param {string} testTitle - Test title
         * @param {string} sourceType - Source type (e.g., "influxdb_v2", "timescaledb")
         * @param {string} id - Optional ID
         * @returns {Promise} - Promise that resolves with report data
         */
        getReportData: function(testTitle, sourceType, id) {
            return apiClient.post('/reports/data', {
                test_title: testTitle,
                source_type: sourceType,
                id: id
            });
        }
    },
    
    /**
     * Tests API
     */
    tests: {
        /**
         * Get test configurations
         *
         * @returns {Promise} - Promise that resolves with test configurations
         */
        getConfigurations: function() {
            return apiClient.get('/tests');
        },
        
        /**
         * Get test data for a specific data source
         *
         * @param {string} sourceType - Source type (e.g., "influxdb_v2", "timescaledb")
         * @param {string} id - Optional ID for the data source
         * @returns {Promise} - Promise that resolves with test data
         */
        getTestData: function(sourceType, id) {
            return apiClient.get('/tests/data', {
                source_type: sourceType,
                id: id
            });
        },
        
        /**
         * Generate a report
         *
         * @param {Object} data - Report generation data
         * @returns {Promise} - Promise that resolves with the generated report
         */
        generateReport: function(data) {
            return apiClient.post('/reports', data);
        }
    }
};

/**
 * Show a flash message using the existing flashed-msg.html elements
 *
 * @param {string} message - The message to display
 * @param {string} type - The type of message ('success' or 'error')
 */
function showFlashMessage(message, type) {
    // Determine which message container to use based on the type
    const messageType = type === 'error' ? 'bad-msg' : 'good-msg';
    const messageContainer = document.getElementById(messageType);

    if (messageContainer) {
        // Set the message text
        const msgElement = messageContainer.querySelector("#msg");
        if (msgElement) {
            msgElement.textContent = message;
        }

        // Show the message
        messageContainer.style.display = "flex";

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            messageContainer.style.display = "none";
        }, 5000);
    }
}

// Add to global scope
window.apiClient = apiClient;
window.showFlashMessage = showFlashMessage;
