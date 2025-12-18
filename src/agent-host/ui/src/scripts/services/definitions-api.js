/**
 * Definitions API Service
 * Provides API methods for fetching AgentDefinitions
 *
 * AgentDefinitions replace the old Agent aggregate pattern.
 * They define what kind of assistant the user interacts with.
 */

import { api } from './api.js';

// =============================================================================
// Definitions API Class
// =============================================================================

class DefinitionsApiService {
    constructor() {
        this.baseUrl = '/definitions';
    }

    /**
     * Make an authenticated request using the main API service
     * @param {string} path - API path (appended to baseUrl)
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>}
     */
    async request(path, options = {}) {
        return api.request(`${this.baseUrl}${path}`, options);
    }

    // =========================================================================
    // Definition Queries
    // =========================================================================

    /**
     * List all accessible definitions for the current user
     * @returns {Promise<Array>} List of definition summaries
     */
    async getDefinitions() {
        const response = await this.request('/');
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to list definitions');
        }
        return response.json();
    }

    /**
     * Get a specific definition by ID
     * @param {string} definitionId - Definition ID
     * @returns {Promise<Object>} Definition details
     */
    async getDefinition(definitionId) {
        const response = await this.request(`/${definitionId}`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to get definition');
        }
        return response.json();
    }
}

// =============================================================================
// Export Singleton
// =============================================================================

export const definitionsApi = new DefinitionsApiService();
