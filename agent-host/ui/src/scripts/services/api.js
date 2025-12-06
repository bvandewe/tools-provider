/**
 * API Service
 * Handles all HTTP communication with the backend
 */
class ApiService {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
        this.onUnauthorized = null; // Callback for 401 responses
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
        const response = await this.request('/chat/send', {
            method: 'POST',
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
            }),
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response;
    }

    // Tools
    async getTools() {
        const response = await this.request('/chat/tools');
        if (!response.ok) {
            throw new Error('Failed to load tools');
        }
        return response.json();
    }
}

// Export singleton instance
export const api = new ApiService();
export default ApiService;
