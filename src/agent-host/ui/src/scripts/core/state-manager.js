/**
 * State Manager - Simple Global State Container
 *
 * Provides a centralized state store with reactive updates via the event bus.
 * Used for application-wide state that needs to be shared across modules.
 *
 * @example
 * import { stateManager } from './core/state-manager.js';
 *
 * // Get state
 * const isAuth = stateManager.get('isAuthenticated');
 *
 * // Set state (triggers event)
 * stateManager.set('currentUser', { name: 'John' });
 *
 * // Subscribe to changes
 * stateManager.subscribe('currentUser', (user) => console.log(user));
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

    // Conversation state
    CURRENT_CONVERSATION_ID: 'currentConversationId',
    CONVERSATIONS: 'conversations',

    // Definition state
    SELECTED_DEFINITION_ID: 'selectedDefinitionId',
    SELECTED_DEFINITION: 'selectedDefinition',
    DEFINITIONS: 'definitions',

    // UI state
    IS_STREAMING: 'isStreaming',
    CONNECTION_STATUS: 'connectionStatus',
    SIDEBAR_COLLAPSED: 'sidebarCollapsed',
    THEME: 'theme',

    // Config state
    APP_CONFIG: 'appConfig',
    SELECTED_MODEL_ID: 'selectedModelId',
    AVAILABLE_MODELS: 'availableModels',
    ALLOW_MODEL_SELECTION: 'allowModelSelection',

    // Template state
    TEMPLATE_CONFIG: 'templateConfig',
    TEMPLATE_PROGRESS: 'templateProgress',
    CURRENT_ITEM_CONTEXT: 'currentItemContext', // Current item settings (enable_chat, require_confirmation, etc.)

    // Tools state
    TOOL_COUNT: 'toolCount',

    // WebSocket state
    WS_CONNECTED: 'wsConnected',
    WS_CONVERSATION_ID: 'wsConversationId',

    // Capability negotiation (from REST /chat/new response)
    SERVER_CAPABILITIES: 'serverCapabilities',
    CLIENT_CAPABILITIES: 'clientCapabilities',
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
     * Check if a state key exists
     * @param {string} key - State key
     * @returns {boolean}
     */
    has(key) {
        return this._state.has(key);
    }

    /**
     * Subscribe to changes for a specific key
     * @param {string} key - State key to watch
     * @param {Function} callback - Handler (receives newValue, oldValue)
     * @returns {Function} Unsubscribe function
     */
    subscribe(key, callback) {
        if (!this._subscribers.has(key)) {
            this._subscribers.set(key, new Set());
        }
        this._subscribers.get(key).add(callback);

        // Return unsubscribe function
        return () => {
            const subs = this._subscribers.get(key);
            if (subs) {
                subs.delete(callback);
                if (subs.size === 0) {
                    this._subscribers.delete(key);
                }
            }
        };
    }

    /**
     * Notify subscribers of a state change
     * @private
     * @param {string} key - State key
     * @param {*} newValue - New value
     * @param {*} oldValue - Previous value
     */
    _notifySubscribers(key, newValue, oldValue) {
        const subs = this._subscribers.get(key);
        if (subs) {
            subs.forEach(callback => {
                try {
                    callback(newValue, oldValue);
                } catch (error) {
                    console.error(`[StateManager] Error in subscriber for ${key}:`, error);
                }
            });
        }
    }

    /**
     * Set multiple state values at once
     * @param {Object} values - Object with key-value pairs
     * @param {boolean} [silent=false] - If true, don't notify subscribers
     */
    setMany(values, silent = false) {
        Object.entries(values).forEach(([key, value]) => {
            this.set(key, value, silent);
        });
    }

    /**
     * Get multiple state values at once
     * @param {string[]} keys - Array of state keys
     * @returns {Object} Object with key-value pairs
     */
    getMany(keys) {
        const result = {};
        keys.forEach(key => {
            result[key] = this.get(key);
        });
        return result;
    }

    /**
     * Get a snapshot of all state
     * @returns {Object} Copy of all state
     */
    getSnapshot() {
        const snapshot = {};
        this._state.forEach((value, key) => {
            snapshot[key] = value;
        });
        return snapshot;
    }

    /**
     * Clear all state
     */
    clear() {
        this._state.clear();
        this._subscribers.clear();
    }

    /**
     * Initialize with default values (doesn't overwrite existing)
     * @param {Object} defaults - Default values
     */
    initDefaults(defaults) {
        Object.entries(defaults).forEach(([key, value]) => {
            if (!this.has(key)) {
                this.set(key, value, true);
            }
        });
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

/** @type {StateManager} */
export const stateManager = new StateManager();

// Initialize with sensible defaults
stateManager.initDefaults({
    [StateKeys.IS_AUTHENTICATED]: false,
    [StateKeys.IS_STREAMING]: false,
    [StateKeys.SIDEBAR_COLLAPSED]: false,
    [StateKeys.WS_CONNECTED]: false,
    [StateKeys.CONNECTION_STATUS]: 'disconnected',
});

export default stateManager;
