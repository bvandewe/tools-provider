/**
 * State Manager - Simple Global State Container
 *
 * Provides a centralized state store with reactive updates via the event bus.
 * Used for application-wide state that needs to be shared across modules.
 *
 * @example
 * import { stateManager, StateKeys } from './core/state-manager.js';
 *
 * // Get state
 * const isAuth = stateManager.get(StateKeys.IS_AUTHENTICATED);
 *
 * // Set state (triggers event)
 * stateManager.set(StateKeys.CURRENT_USER, { name: 'John' });
 *
 * // Subscribe to changes
 * stateManager.subscribe(StateKeys.CURRENT_USER, (user) => console.log(user));
 *
 * @module core/state-manager
 */

import { eventBus, Events } from './event-bus.js';

// =============================================================================
// State Keys (Constants)
// =============================================================================

/**
 * Standard state keys used throughout the application.
 * @readonly
 * @enum {string}
 */
export const StateKeys = {
    // Auth state
    IS_AUTHENTICATED: 'isAuthenticated',
    CURRENT_USER: 'currentUser',
    IS_ADMIN: 'isAdmin',

    // Namespace state
    NAMESPACES: 'namespaces',
    CURRENT_NAMESPACE: 'currentNamespace',
    CURRENT_NAMESPACE_ID: 'currentNamespaceId',

    // Term state
    TERMS: 'terms',
    CURRENT_TERM: 'currentTerm',

    // UI state
    CONNECTION_STATUS: 'connectionStatus',
    THEME: 'theme',
    IS_LOADING: 'isLoading',

    // Config state
    APP_CONFIG: 'appConfig',
    APP_VERSION: 'appVersion',

    // Stats
    NAMESPACE_COUNT: 'namespaceCount',
    TERM_COUNT: 'termCount',
    RELATIONSHIP_COUNT: 'relationshipCount',
};

// =============================================================================
// StateManager Class
// =============================================================================

/**
 * Simple state container with reactive updates
 */
class StateManager {
    constructor() {
        /** @type {Map<string, *>} */
        this._state = new Map();

        /** @type {Map<string, Set<Function>>} */
        this._subscribers = new Map();

        /** @type {boolean} */
        this._debug = false;
    }

    /**
     * Enable or disable debug logging
     * @param {boolean} enabled
     */
    setDebug(enabled) {
        this._debug = enabled;
    }

    /**
     * Get a state value
     * @param {string} key - State key (use StateKeys enum)
     * @param {*} [defaultValue] - Default value if key not set
     * @returns {*} State value
     */
    get(key, defaultValue = undefined) {
        return this._state.has(key) ? this._state.get(key) : defaultValue;
    }

    /**
     * Set a state value
     * @param {string} key - State key
     * @param {*} value - New value
     * @param {boolean} [silent=false] - If true, don't notify subscribers
     */
    set(key, value, silent = false) {
        const oldValue = this._state.get(key);

        // Skip if value hasn't changed (shallow comparison)
        if (oldValue === value) return;

        this._state.set(key, value);

        if (this._debug) {
            console.log(`[StateManager] ${key}:`, oldValue, '→', value);
        }

        if (!silent) {
            this._notifySubscribers(key, value, oldValue);
        }
    }

    /**
     * Update a state value using an updater function
     * @param {string} key - State key
     * @param {Function} updater - Function that receives old value and returns new value
     */
    update(key, updater) {
        const oldValue = this.get(key);
        const newValue = updater(oldValue);
        this.set(key, newValue);
    }

    /**
     * Delete a state key
     * @param {string} key - State key
     */
    delete(key) {
        const oldValue = this._state.get(key);
        this._state.delete(key);
        this._notifySubscribers(key, undefined, oldValue);
    }

    /**
     * Subscribe to state changes
     * @param {string} key - State key to watch
     * @param {Function} callback - Callback(newValue, oldValue)
     * @returns {Function} Unsubscribe function
     */
    subscribe(key, callback) {
        if (!this._subscribers.has(key)) {
            this._subscribers.set(key, new Set());
        }
        this._subscribers.get(key).add(callback);

        // Return unsubscribe function
        return () => {
            this._subscribers.get(key)?.delete(callback);
        };
    }

    /**
     * Notify subscribers of state change
     * @private
     * @param {string} key - State key
     * @param {*} newValue - New value
     * @param {*} oldValue - Old value
     */
    _notifySubscribers(key, newValue, oldValue) {
        const subscribers = this._subscribers.get(key);
        if (subscribers) {
            subscribers.forEach(callback => {
                try {
                    callback(newValue, oldValue);
                } catch (error) {
                    console.error(`[StateManager] Error in subscriber for "${key}":`, error);
                }
            });
        }
    }

    /**
     * Get all state as a plain object
     * @returns {Object} State snapshot
     */
    getSnapshot() {
        return Object.fromEntries(this._state);
    }

    /**
     * Clear all state
     */
    clear() {
        this._state.clear();
        this._subscribers.clear();
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

/**
 * Singleton state manager instance
 */
export const stateManager = new StateManager();
