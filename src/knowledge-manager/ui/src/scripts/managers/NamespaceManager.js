/**
 * NamespaceManager - Namespace Data Management
 *
 * Handles namespace data loading, caching, and state management.
 *
 * @module managers/NamespaceManager
 */

import { apiService } from '../services/ApiService.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * NamespaceManager handles namespace data operations
 */
export class NamespaceManager {
    /**
     * Create NamespaceManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Array} */
        this._namespaces = [];
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize namespace manager
     */
    init() {
        if (this._initialized) {
            console.warn('[NamespaceManager] Already initialized');
            return;
        }

        this._initialized = true;
        console.log('[NamespaceManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._namespaces = [];
        this._initialized = false;
        console.log('[NamespaceManager] Destroyed');
    }

    // =========================================================================
    // Namespace Operations
    // =========================================================================

    /**
     * Load all namespaces
     * @returns {Promise<Array>}
     */
    async loadNamespaces() {
        console.log('[NamespaceManager] Loading namespaces...');

        try {
            this._namespaces = await apiService.getNamespaces();
            stateManager.set(StateKeys.NAMESPACES, this._namespaces);
            stateManager.set(StateKeys.NAMESPACE_COUNT, this._namespaces.length);

            // Calculate total term count
            let termCount = 0;
            for (const ns of this._namespaces) {
                termCount += ns.term_count || 0;
            }
            stateManager.set(StateKeys.TERM_COUNT, termCount);

            eventBus.emit(Events.NAMESPACES_LOADED, { namespaces: this._namespaces });
            console.log(`[NamespaceManager] Loaded ${this._namespaces.length} namespaces`);

            return this._namespaces;
        } catch (error) {
            console.error('[NamespaceManager] Failed to load namespaces:', error);
            eventBus.emit(Events.NAMESPACES_LOADED, { namespaces: [], error });
            throw error;
        }
    }

    /**
     * Get cached namespaces
     * @returns {Array}
     */
    getNamespaces() {
        return this._namespaces;
    }

    /**
     * Load a single namespace by slug
     * @param {string} slug - Namespace slug
     * @returns {Promise<Object>}
     */
    async loadNamespace(slug) {
        console.log(`[NamespaceManager] Loading namespace: ${slug}`);

        try {
            const namespace = await apiService.getNamespace(slug);
            stateManager.set(StateKeys.CURRENT_NAMESPACE, namespace);
            stateManager.set(StateKeys.CURRENT_NAMESPACE_ID, namespace.id);

            eventBus.emit(Events.NAMESPACE_LOADED, { namespace });
            return namespace;
        } catch (error) {
            console.error(`[NamespaceManager] Failed to load namespace ${slug}:`, error);
            throw error;
        }
    }

    /**
     * Create a new namespace
     * @param {Object} data - Namespace data (name, slug, description, status)
     * @returns {Promise<Object>}
     */
    async createNamespace(data) {
        console.log('[NamespaceManager] Creating namespace:', data.name);

        try {
            const namespace = await apiService.createNamespace(data);

            // Add to local cache
            this._namespaces.push(namespace);
            stateManager.set(StateKeys.NAMESPACES, this._namespaces);
            stateManager.set(StateKeys.NAMESPACE_COUNT, this._namespaces.length);

            eventBus.emit(Events.NAMESPACE_CREATED, { namespace });
            console.log(`[NamespaceManager] Created namespace: ${namespace.id}`);

            return namespace;
        } catch (error) {
            console.error('[NamespaceManager] Failed to create namespace:', error);
            throw error;
        }
    }

    /**
     * Update a namespace
     * @param {string} namespaceId - Namespace ID
     * @param {Object} data - Updated data
     * @returns {Promise<Object>}
     */
    async updateNamespace(namespaceId, data) {
        console.log(`[NamespaceManager] Updating namespace: ${namespaceId}`);

        try {
            const namespace = await apiService.updateNamespace(namespaceId, data);

            // Update local cache
            const index = this._namespaces.findIndex(ns => ns.id === namespaceId);
            if (index >= 0) {
                this._namespaces[index] = namespace;
                stateManager.set(StateKeys.NAMESPACES, this._namespaces);
            }

            eventBus.emit(Events.NAMESPACE_UPDATED, { namespace });
            return namespace;
        } catch (error) {
            console.error(`[NamespaceManager] Failed to update namespace ${namespaceId}:`, error);
            throw error;
        }
    }

    /**
     * Delete a namespace
     * @param {string} namespaceId - Namespace ID
     * @returns {Promise<void>}
     */
    async deleteNamespace(namespaceId) {
        console.log(`[NamespaceManager] Deleting namespace: ${namespaceId}`);

        try {
            await apiService.deleteNamespace(namespaceId);

            // Remove from local cache
            this._namespaces = this._namespaces.filter(ns => ns.id !== namespaceId);
            stateManager.set(StateKeys.NAMESPACES, this._namespaces);
            stateManager.set(StateKeys.NAMESPACE_COUNT, this._namespaces.length);

            eventBus.emit(Events.NAMESPACE_DELETED, { namespaceId });
            console.log(`[NamespaceManager] Deleted namespace: ${namespaceId}`);
        } catch (error) {
            console.error(`[NamespaceManager] Failed to delete namespace ${namespaceId}:`, error);
            throw error;
        }
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const namespaceManager = new NamespaceManager();
