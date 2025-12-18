/**
 * API Service
 * Handles all HTTP communication with the backend
 */
class ApiService {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
        this.onUnauthorized = null; // Callback for 401 responses
        this.currentRequestId = null; // Track current streaming request for cancellation
        this.abortController = null; // AbortController for current request
        this.suppressUnauthorizedHandler = false; // Suppress during streaming
    }

    /**
     * Set a callback to be invoked when a 401 Unauthorized response is received
     * @param {Function} callback - Function to call on unauthorized
     */
    setUnauthorizedHandler(callback) {
        this.onUnauthorized = callback;
    }

    /**
     * Suppress the unauthorized handler (e.g., during streaming)
     * @param {boolean} suppress - Whether to suppress
     */
    setSuppressUnauthorizedHandler(suppress) {
        this.suppressUnauthorizedHandler = suppress;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        const response = await fetch(url, config);

        // Handle 401 Unauthorized - session expired or token invalid
        if (response.status === 401 && this.onUnauthorized && !this.suppressUnauthorizedHandler) {
            this.onUnauthorized();
            throw new Error('Session expired');
        }

        return response;
    }

    // App Configuration (no auth required)
    async getConfig() {
        const response = await fetch(`${this.baseUrl}/config`);
        if (!response.ok) {
            throw new Error('Failed to load configuration');
        }
        return response.json();
    }

    /**
     * Get available models for selection
     * @returns {Promise<Array>} List of model options
     */
    async getModels() {
        const response = await fetch(`${this.baseUrl}/config/models`);
        if (!response.ok) {
            throw new Error('Failed to load models');
        }
        return response.json();
    }

    /**
     * Check health status of all dependent services
     * @returns {Promise<Object>} Health check results
     */
    async checkHealth() {
        const response = await this.request('/health/components');
        if (!response.ok) {
            throw new Error('Failed to check health');
        }
        return response.json();
    }

    // Authentication
    async checkAuth() {
        const response = await fetch(`${this.baseUrl}/auth/me`); // Direct fetch to avoid triggering unauthorized handler
        if (!response.ok) {
            throw new Error('Not authenticated');
        }
        return response.json();
    }

    logout() {
        window.location.href = `${this.baseUrl}/auth/logout`;
    }

    // Conversations
    async getConversations() {
        const response = await this.request('/chat/conversations');
        if (!response.ok) {
            throw new Error('Failed to load conversations');
        }
        return response.json();
    }

    async getConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}`);
        if (!response.ok) {
            throw new Error('Failed to load conversation');
        }
        return response.json();
    }

    /**
     * Create a new conversation
     * @param {string|null} definitionId - Optional agent definition ID for the conversation
     * @returns {Promise<Object>} Created conversation data
     */
    async createConversation(definitionId = null) {
        const body = definitionId ? { definition_id: definitionId } : {};
        const response = await this.request('/chat/new', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw new Error('Failed to create conversation');
        }
        return response.json();
    }

    async renameConversation(conversationId, title) {
        const response = await this.request(`/chat/conversations/${conversationId}/rename`, {
            method: 'PUT',
            body: JSON.stringify({ title }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to rename conversation');
        }
        return response.json();
    }

    async deleteConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to delete conversation');
        }
        return true;
    }

    /**
     * Delete multiple conversations by their IDs
     * @param {string[]} conversationIds - Array of conversation IDs to delete
     * @returns {Promise<{deleted_count: number, failed_ids: string[]}>} Delete result
     */
    async deleteConversations(conversationIds) {
        const response = await this.request('/chat/conversations', {
            method: 'DELETE',
            body: JSON.stringify({ conversation_ids: conversationIds }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to delete conversations');
        }
        return response.json();
    }

    async clearConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}/clear`, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error('Failed to clear conversation');
        }
        return response.json();
    }

    /**
     * Navigate backward to the previous template item
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Navigation result
     */
    async navigateBack(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}/navigate-back`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to navigate back');
        }
        return response.json();
    }

    /**
     * Pause a templated conversation
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Pause result with paused_at timestamp
     */
    async pauseConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}/pause`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to pause conversation');
        }
        return response.json();
    }

    /**
     * Resume a paused templated conversation
     * @param {string} conversationId - Conversation ID
     * @returns {Promise<Object>} Resume result with new_deadline if applicable
     */
    async resumeConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}/resume`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to resume conversation');
        }
        return response.json();
    }

    // Chat
    async sendMessage(message, conversationId, modelId = null, definitionId = null) {
        // Create new AbortController for this request
        this.abortController = new AbortController();

        // Suppress unauthorized handler during streaming - let it complete
        this.suppressUnauthorizedHandler = true;

        const body = {
            message,
            conversation_id: conversationId,
        };

        // Add model_id if specified
        if (modelId) {
            body.model_id = modelId;
        }

        // Add definition_id if specified (for selecting agent definition)
        if (definitionId) {
            body.definition_id = definitionId;
        }

        const response = await this.request('/chat/send', {
            method: 'POST',
            body: JSON.stringify(body),
            signal: this.abortController.signal,
        });

        if (!response.ok) {
            // Handle rate limiting
            if (response.status === 429) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Rate limit exceeded. Please wait before sending another message.');
            }
            throw new Error(`HTTP ${response.status}`);
        }
        return response;
    }

    /**
     * Cancel the current streaming request
     * @returns {Promise<boolean>} True if cancellation was successful
     */
    async cancelCurrentRequest() {
        // Abort the fetch request client-side
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }

        // Also notify the server if we have a request ID
        if (this.currentRequestId) {
            try {
                const response = await this.request(`/chat/cancel/${this.currentRequestId}`, {
                    method: 'POST',
                });
                this.currentRequestId = null;
                return response.ok;
            } catch (e) {
                console.error('Failed to cancel request on server:', e);
                this.currentRequestId = null;
                return false;
            }
        }
        return true;
    }

    /**
     * Set the current request ID (called when stream starts)
     * @param {string} requestId - The request ID from the server
     */
    setCurrentRequestId(requestId) {
        this.currentRequestId = requestId;
    }

    /**
     * Check if there's an active request
     * @returns {boolean}
     */
    hasActiveRequest() {
        return this.currentRequestId !== null || this.abortController !== null;
    }

    /**
     * Clear request tracking state
     */
    clearRequestState() {
        this.currentRequestId = null;
        this.abortController = null;
        this.suppressUnauthorizedHandler = false; // Re-enable unauthorized handler
    }

    // Tools
    async getTools(forceRefresh = false) {
        const url = forceRefresh ? '/chat/tools?refresh=true' : '/chat/tools';
        const response = await this.request(url);
        if (!response.ok) {
            throw new Error('Failed to load tools');
        }
        return response.json();
    }

    /**
     * Get source information for a tool (admin only)
     * @param {string} toolName - Tool name (format: source_id:operation_id)
     * @returns {Promise<Object>} Source information
     */
    async getToolSourceInfo(toolName) {
        const encodedName = encodeURIComponent(toolName);
        const response = await this.request(`/chat/tools/${encodedName}/source`);
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Admin access required');
            }
            throw new Error('Failed to load source information');
        }
        return response.json();
    }

    // ==========================================================================
    // Admin Settings API
    // ==========================================================================

    /**
     * Get application settings (admin only)
     * @returns {Promise<Object>} Application settings
     */
    async getSettings() {
        const response = await this.request('/settings');
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Admin access required');
            }
            throw new Error('Failed to load settings');
        }
        return response.json();
    }

    /**
     * Update application settings (admin only)
     * @param {Object} settings - Settings to update
     * @returns {Promise<Object>} Updated settings
     */
    async updateSettings(settings) {
        const response = await this.request('/settings', {
            method: 'PUT',
            body: JSON.stringify(settings),
        });
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Admin access required');
            }
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to update settings');
        }
        return response.json();
    }

    /**
     * Reset settings to defaults (admin only)
     * @returns {Promise<Object>} Default settings
     */
    async resetSettings() {
        const response = await this.request('/settings', {
            method: 'DELETE',
        });
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Admin access required');
            }
            throw new Error('Failed to reset settings');
        }
        return response.json();
    }

    /**
     * Get available Ollama models (admin only)
     * @returns {Promise<Array>} List of available models
     */
    async getOllamaModels() {
        const response = await this.request('/settings/ollama/models');
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('Admin access required');
            }
            if (response.status === 503) {
                throw new Error('Ollama server not available');
            }
            throw new Error('Failed to load Ollama models');
        }
        return response.json();
    }

    // ==========================================================================
    // Session API (Proactive Agent)
    // ==========================================================================

    /**
     * Create a new proactive session
     * @param {Object} params - Session parameters
     * @param {string} params.session_type - Type of session (learning, thought, validation)
     * @param {Object} params.config - Session configuration
     * @param {string} [params.initial_message] - Optional initial message
     * @returns {Promise<Object>} Created session
     */
    async createSession(params) {
        const response = await this.request('/session/', {
            method: 'POST',
            body: JSON.stringify(params),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to create session');
        }
        return response.json();
    }

    /**
     * Get a session by ID
     * @param {string} sessionId - Session ID
     * @returns {Promise<Object>} Session data
     */
    async getSession(sessionId) {
        const response = await this.request(`/session/${sessionId}`);
        if (!response.ok) {
            throw new Error('Failed to load session');
        }
        return response.json();
    }

    /**
     * Get all sessions for the current user
     * @returns {Promise<Array>} List of sessions
     */
    async getSessions() {
        const response = await this.request('/session/');
        if (!response.ok) {
            throw new Error('Failed to load sessions');
        }
        return response.json();
    }

    /**
     * Get current session state
     * @param {string} sessionId - Session ID
     * @returns {Promise<Object>} Session state including pending action
     */
    async getSessionState(sessionId) {
        const response = await this.request(`/session/${sessionId}/state`);
        if (!response.ok) {
            throw new Error('Failed to load session state');
        }
        return response.json();
    }

    /**
     * Submit a response to a client action
     * @param {string} sessionId - Session ID
     * @param {Object} response - Client response
     * @param {string} response.tool_call_id - ID of the tool call being responded to
     * @param {Object} response.response - Response data
     * @param {string} response.timestamp - ISO timestamp
     * @returns {Promise<Object>} Updated session
     */
    async submitSessionResponse(sessionId, response) {
        const apiResponse = await this.request(`/session/${sessionId}/respond`, {
            method: 'POST',
            body: JSON.stringify(response),
        });
        if (!apiResponse.ok) {
            const error = await apiResponse.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to submit response');
        }
        return apiResponse.json();
    }

    /**
     * Terminate a session
     * @param {string} sessionId - Session ID
     * @returns {Promise<boolean>} Success
     */
    async terminateSession(sessionId) {
        const response = await this.request(`/session/${sessionId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to terminate session');
        }
        return true;
    }

    /**
     * Connect to session SSE stream
     * @param {string} sessionId - Session ID
     * @returns {Promise<Response>} SSE stream response
     */
    async connectSessionStream(sessionId) {
        const response = await this.request(`/session/${sessionId}/stream`);
        if (!response.ok) {
            throw new Error('Failed to connect to session stream');
        }
        return response;
    }

    /**
     * Get available exam blueprints for validation sessions
     * @returns {Promise<Array>} List of exam summaries
     */
    async getExams() {
        const response = await this.request('/session/exams');
        if (!response.ok) {
            throw new Error('Failed to load exams');
        }
        return response.json();
    }

    // =========================================================================
    // File Operations (via Tools Provider)
    // =========================================================================

    /**
     * Upload a file for agent processing
     * Files are stored temporarily (24h) in the user's workspace
     * @param {File} file - The file to upload
     * @returns {Promise<Object>} Upload result with filename and expiry info
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Proxy to tools-provider via /api/tools
        const response = await fetch('/api/tools/files/upload', {
            method: 'POST',
            body: formData,
            // Don't set Content-Type - browser will set it with boundary for multipart
        });

        if (!response.ok) {
            if (response.status === 401) {
                if (this.onUnauthorized && !this.suppressUnauthorizedHandler) {
                    this.onUnauthorized();
                }
                throw new Error('Session expired');
            }
            if (response.status === 413) {
                throw new Error('File too large. Maximum size is 10MB.');
            }
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to upload file');
        }
        return response.json();
    }

    /**
     * List files in the user's workspace
     * @returns {Promise<Object>} List of files with metadata
     */
    async listFiles() {
        const response = await fetch('/api/tools/files/');
        if (!response.ok) {
            if (response.status === 401) {
                if (this.onUnauthorized && !this.suppressUnauthorizedHandler) {
                    this.onUnauthorized();
                }
                throw new Error('Session expired');
            }
            throw new Error('Failed to list files');
        }
        return response.json();
    }

    /**
     * Get download URL for a file
     * @param {string} filename - The filename to download
     * @returns {string} Download URL
     */
    getFileDownloadUrl(filename) {
        return `/api/tools/files/${encodeURIComponent(filename)}`;
    }
}

// Export singleton instance
export const api = new ApiService();
export default ApiService;
