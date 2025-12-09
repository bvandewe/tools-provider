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
    }

    /**
     * Set a callback to be invoked when a 401 Unauthorized response is received
     * @param {Function} callback - Function to call on unauthorized
     */
    setUnauthorizedHandler(callback) {
        this.onUnauthorized = callback;
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
        if (response.status === 401 && this.onUnauthorized) {
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

    async createConversation() {
        const response = await this.request('/chat/new', { method: 'POST' });
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

    async clearConversation(conversationId) {
        const response = await this.request(`/chat/conversations/${conversationId}/clear`, {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error('Failed to clear conversation');
        }
        return response.json();
    }

    // Chat
    async sendMessage(message, conversationId, modelId = null) {
        // Create new AbortController for this request
        this.abortController = new AbortController();

        const body = {
            message,
            conversation_id: conversationId,
        };

        // Add model_id if specified
        if (modelId) {
            body.model_id = modelId;
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
}

// Export singleton instance
export const api = new ApiService();
export default ApiService;
