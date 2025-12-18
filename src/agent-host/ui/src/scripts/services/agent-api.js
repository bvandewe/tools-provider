/**
 * Agent API Service
 * Provides API methods for Agent-based interactions (TUTOR, THOUGHT, EVALUATOR)
 *
 * This module handles all communication with the /api/agents/* endpoints
 * for the new Agent aggregate pattern. For stateless chat, use api.js.
 */

import { api } from './api.js';

// =============================================================================
// Constants
// =============================================================================

/**
 * Agent types matching backend AgentType enum
 */
export const AgentType = {
    TUTOR: 'tutor',
    THOUGHT: 'thought',
    EVALUATOR: 'evaluator',
    COACH: 'coach',
};

/**
 * Map frontend SessionMode to backend AgentType
 */
export const SessionModeToAgentType = {
    learning: AgentType.TUTOR,
    thought: AgentType.THOUGHT,
    validation: AgentType.EVALUATOR,
};

// =============================================================================
// Agent API Class
// =============================================================================

class AgentApiService {
    constructor() {
        // Note: api.request() already prepends '/api', so we only need '/agents'
        this.baseUrl = '/agents';
    }

    /**
     * Make an authenticated request using the main API service
     * @param {string} path - API path (appended to baseUrl)
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>}
     */
    async request(path, options = {}) {
        // Use the main api service's request method for auth handling
        return api.request(`${this.baseUrl}${path}`, options);
    }

    // =========================================================================
    // Agent Management
    // =========================================================================

    /**
     * List all agents for the current user
     * @returns {Promise<Array>} List of agent summaries
     */
    async getAgents() {
        const response = await this.request('/');
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to list agents');
        }
        return response.json();
    }

    /**
     * Get or create an agent by type
     * Uses get-or-create pattern - returns existing agent or creates new one
     * @param {string} agentType - Agent type (tutor, thought, evaluator, coach)
     * @returns {Promise<Object>} Agent details
     */
    async getOrCreateAgent(agentType) {
        const response = await this.request('/', {
            method: 'POST',
            body: JSON.stringify({ agent_type: agentType }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get or create agent');
        }
        return response.json();
    }

    /**
     * Get detailed information about an agent
     * @param {string} agentId - Agent ID
     * @returns {Promise<Object>} Agent details
     */
    async getAgent(agentId) {
        const response = await this.request(`/${agentId}`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get agent');
        }
        return response.json();
    }

    /**
     * Update agent preferences
     * @param {string} agentId - Agent ID
     * @param {Object} preferences - Preferences to merge
     * @returns {Promise<Object>} Updated agent
     */
    async updatePreferences(agentId, preferences) {
        const response = await this.request(`/${agentId}/preferences`, {
            method: 'PATCH',
            body: JSON.stringify({ preferences }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to update preferences');
        }
        return response.json();
    }

    /**
     * Archive (soft-delete) an agent
     * @param {string} agentId - Agent ID
     * @param {string} reason - Reason for archiving
     * @returns {Promise<boolean>} Success
     */
    async archiveAgent(agentId, reason = 'User requested reset') {
        const response = await this.request(`/${agentId}`, {
            method: 'DELETE',
            body: JSON.stringify({ reason }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to archive agent');
        }
        return true;
    }

    // =========================================================================
    // Session Management
    // =========================================================================

    /**
     * Start a new session with an agent
     * @param {string} agentId - Agent ID
     * @param {Object} options - Session options
     * @param {string} [options.system_prompt] - Optional custom system prompt
     * @param {Object} [options.config] - Optional session configuration
     * @param {string} [options.model_id] - Optional model override
     * @returns {Promise<Object>} Session details with stream_url
     */
    async startSession(agentId, options = {}) {
        const response = await this.request(`/${agentId}/sessions`, {
            method: 'POST',
            body: JSON.stringify(options),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to start session');
        }
        return response.json();
    }

    /**
     * Get the current active session for an agent
     * @param {string} agentId - Agent ID
     * @returns {Promise<Object|null>} Session details or null if no active session
     */
    async getCurrentSession(agentId) {
        const response = await this.request(`/${agentId}/sessions/current`);
        if (response.status === 404) {
            return null;
        }
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get current session');
        }
        return response.json();
    }

    /**
     * Submit a response to a pending widget/client action
     * @param {string} agentId - Agent ID
     * @param {Object} response - Response data
     * @param {string} response.tool_call_id - Tool call ID being responded to
     * @param {*} response.response - The user's response
     * @returns {Promise<Object>} Updated session state
     */
    async submitResponse(agentId, responseData) {
        const response = await this.request(`/${agentId}/respond`, {
            method: 'POST',
            body: JSON.stringify(responseData),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to submit response');
        }
        return response.json();
    }

    /**
     * Terminate the current session for an agent
     * @param {string} agentId - Agent ID
     * @param {string} reason - Reason for termination
     * @returns {Promise<boolean>} Success
     */
    async terminateSession(agentId, reason = 'User terminated') {
        const response = await this.request(`/${agentId}/sessions/current`, {
            method: 'DELETE',
            body: JSON.stringify({ reason }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to terminate session');
        }
        return true;
    }

    /**
     * Get session history for an agent
     * @param {string} agentId - Agent ID
     * @param {number} limit - Maximum number of sessions to return
     * @returns {Promise<Array>} List of session history items
     */
    async getHistory(agentId, limit = 20) {
        const response = await this.request(`/${agentId}/history?limit=${limit}`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get session history');
        }
        return response.json();
    }

    // =========================================================================
    // SSE Streaming
    // =========================================================================

    /**
     * Connect to an agent's SSE event stream
     * @param {string} agentId - Agent ID
     * @returns {Promise<Response>} SSE stream response
     */
    async connectStream(agentId) {
        const response = await this.request(`/${agentId}/stream`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to connect to agent stream');
        }
        return response;
    }

    /**
     * Create an EventSource for real-time agent events
     * Note: This bypasses the request() method since EventSource handles its own connection
     * @param {string} agentId - Agent ID
     * @param {string} [sessionId] - Optional session ID (currently unused, kept for future use)
     * @returns {EventSource} EventSource instance
     */
    createEventSource(agentId, sessionId = null) {
        // Always use the agent stream endpoint - it has the full ProactiveAgent execution
        // The session stream endpoint is for legacy Session entities, not Agent aggregate sessions
        const url = `/api${this.baseUrl}/${agentId}/stream`;
        console.log(`[AgentAPI] Creating EventSource for agent ${agentId}: ${url}`);
        return new EventSource(url, { withCredentials: true });
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const agentApi = new AgentApiService();
export default agentApi;
