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
    async sendMessage(message, conversationId) {
        // Create new AbortController for this request
        this.abortController = new AbortController();

        const response = await this.request('/chat/send', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
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
}

// Export singleton instance
export const api = new ApiService();
export default ApiService;
