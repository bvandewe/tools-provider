/**
 * ApiService - HTTP API Client
 *
 * Handles all HTTP communication with the backend.
 * Class-based service following the singleton pattern.
 *
 * @module services/ApiService
 */

import { eventBus, Events } from '../core/event-bus.js';

/**
 * ApiService handles all HTTP communication with the backend
 */
export class ApiService {
    /**
     * Create a new ApiService instance
     * @param {string} [baseUrl='/api'] - Base URL for API endpoints
     */
    constructor(baseUrl = '/api') {
        /** @type {string} */
        this.baseUrl = baseUrl;

        /** @type {Function|null} Callback for 401 responses */
        this.onUnauthorized = null;

        /** @type {boolean} */
        this._initialized = false;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the API service
     */
    init() {
        if (this._initialized) {
            console.warn('[ApiService] Already initialized');
            return;
        }

        this._initialized = true;
        console.log('[ApiService] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._initialized = false;
        console.log('[ApiService] Destroyed');
    }

    // =========================================================================
    // Authorization Handling
    // =========================================================================

    /**
     * Set a callback to be invoked when a 401 Unauthorized response is received
     * @param {Function} callback - Function to call on unauthorized
     */
    setUnauthorizedHandler(callback) {
        this.onUnauthorized = callback;
    }

    // =========================================================================
    // Core Request Method
    // =========================================================================

    /**
     * Make an authenticated API request
     * @param {string} endpoint - API endpoint (relative to baseUrl)
     * @param {Object} [options] - Fetch options
     * @returns {Promise<Response>}
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        const response = await fetch(url, config);

        // Handle 401 Unauthorized
        if (response.status === 401) {
            console.log('[ApiService] Received 401 Unauthorized');
            if (this.onUnauthorized) {
                this.onUnauthorized();
            }
            eventBus.emit(Events.AUTH_SESSION_EXPIRED);
        }

        return response;
    }

    // =========================================================================
    // Convenience Methods
    // =========================================================================

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @returns {Promise<Response>}
     */
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body
     * @returns {Promise<Response>}
     */
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body
     * @returns {Promise<Response>}
     */
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    /**
     * PATCH request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body
     * @returns {Promise<Response>}
     */
    async patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     * @returns {Promise<Response>}
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // =========================================================================
    // Domain-Specific Methods
    // =========================================================================

    /**
     * Check authentication status
     * @returns {Promise<{user: Object}>}
     */
    async checkAuth() {
        const response = await this.get('/auth/me');
        if (!response.ok) {
            throw new Error(`Auth check failed: ${response.status}`);
        }
        const user = await response.json();
        return { user };
    }

    /**
     * Get app info (version, etc.)
     * @returns {Promise<Object>}
     */
    async getAppInfo() {
        const response = await this.get('/app/info');
        if (!response.ok) {
            throw new Error(`Failed to fetch app info: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Health check
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const response = await this.get('/app/health');
            return response.ok;
        } catch (error) {
            console.error('[ApiService] Health check failed:', error);
            return false;
        }
    }

    // =========================================================================
    // Namespace API
    // =========================================================================

    /**
     * Get all namespaces
     * @returns {Promise<Array>}
     */
    async getNamespaces() {
        const response = await this.get('/namespaces');
        if (!response.ok) {
            throw new Error(`Failed to fetch namespaces: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Get a single namespace by ID
     * @param {string} namespaceId - Namespace ID
     * @returns {Promise<Object>}
     */
    async getNamespace(namespaceId) {
        const response = await this.get(`/namespaces/${encodeURIComponent(namespaceId)}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch namespace: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Create a new namespace
     * @param {Object} data - Namespace data
     * @returns {Promise<Object>}
     */
    async createNamespace(data) {
        const response = await this.post('/namespaces', data);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to create namespace: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Update a namespace
     * @param {string} namespaceId - Namespace ID
     * @param {Object} data - Namespace data
     * @returns {Promise<Object>}
     */
    async updateNamespace(namespaceId, data) {
        const response = await this.patch(`/namespaces/${encodeURIComponent(namespaceId)}`, data);
        if (!response.ok) {
            throw new Error(`Failed to update namespace: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Delete a namespace
     * @param {string} namespaceId - Namespace ID
     * @returns {Promise<void>}
     */
    async deleteNamespace(namespaceId) {
        const response = await this.delete(`/namespaces/${encodeURIComponent(namespaceId)}`);
        if (!response.ok) {
            throw new Error(`Failed to delete namespace: ${response.status}`);
        }
    }

    // =========================================================================
    // Term API
    // =========================================================================

    /**
     * Get terms for a namespace
     * @param {string} namespaceId - Namespace ID
     * @returns {Promise<Array>}
     */
    async getTerms(namespaceId) {
        const response = await this.get(`/namespaces/${encodeURIComponent(namespaceId)}/terms`);
        if (!response.ok) {
            throw new Error(`Failed to fetch terms: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Create a term
     * @param {string} namespaceId - Namespace ID
     * @param {Object} data - Term data
     * @returns {Promise<Object>}
     */
    async createTerm(namespaceId, data) {
        const response = await this.post(`/namespaces/${encodeURIComponent(namespaceId)}/terms`, data);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to create term: ${response.status}`);
        }
        return response.json();
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const apiService = new ApiService();

/**
 * Convenience alias for backward compatibility
 */
export const api = apiService;
