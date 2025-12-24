/**
 * Event Bus - Centralized Pub/Sub System
 *
 * Provides decoupled communication between modules using an event-driven pattern.
 * Singleton instance ensures all modules share the same bus.
 *
 * @example
 * import { eventBus, Events } from './core/event-bus.js';
 *
 * // Subscribe to event
 * eventBus.on(Events.NAMESPACE_LOADED, (data) => console.log(data));
 *
 * // Publish event
 * eventBus.emit(Events.NAMESPACE_LOADED, { id: '123' });
 *
 * // Unsubscribe
 * const unsub = eventBus.on(Events.NAMESPACE_CREATED, handler);
 * unsub(); // Remove listener
 *
 * @module core/event-bus
 */

// =============================================================================
// Event Names (Constants)
// =============================================================================

/**
 * Standard event names used throughout the application.
 * Use these constants instead of magic strings.
 *
 * @readonly
 * @enum {string}
 */
export const Events = {
    // =========================================================================
    // AUTHENTICATION EVENTS
    // =========================================================================
    AUTH_STATE_CHANGED: 'auth:state-changed',
    AUTH_SESSION_EXPIRED: 'auth:session-expired',

    // =========================================================================
    // NAMESPACE EVENTS
    // =========================================================================
    NAMESPACE_SELECTED: 'namespace:selected',
    NAMESPACE_CREATED: 'namespace:created',
    NAMESPACE_LOADED: 'namespace:loaded',
    NAMESPACE_UPDATED: 'namespace:updated',
    NAMESPACE_DELETED: 'namespace:deleted',
    NAMESPACES_LOADED: 'namespaces:loaded',

    // =========================================================================
    // TERM EVENTS
    // =========================================================================
    TERM_CREATED: 'term:created',
    TERM_LOADED: 'term:loaded',
    TERM_UPDATED: 'term:updated',
    TERM_DELETED: 'term:deleted',
    TERMS_LOADED: 'terms:loaded',

    // =========================================================================
    // RELATIONSHIP EVENTS
    // =========================================================================
    RELATIONSHIP_CREATED: 'relationship:created',
    RELATIONSHIP_DELETED: 'relationship:deleted',

    // =========================================================================
    // UI EVENTS
    // =========================================================================
    UI_STATUS_CHANGED: 'ui:status-changed',
    UI_TOAST: 'ui:toast',
    UI_LOADING_START: 'ui:loading-start',
    UI_LOADING_END: 'ui:loading-end',
    UI_PAGE_CHANGED: 'ui:page-changed',

    // =========================================================================
    // MODAL EVENTS
    // =========================================================================
    MODAL_NAMESPACE_OPEN: 'modal:namespace-open',
    MODAL_NAMESPACE_CLOSE: 'modal:namespace-close',
    MODAL_TERM_OPEN: 'modal:term-open',
    MODAL_TERM_CLOSE: 'modal:term-close',
    MODAL_DELETE_OPEN: 'modal:delete-open',
    MODAL_DELETE_CONFIRM: 'modal:delete-confirm',

    // =========================================================================
    // CONNECTION EVENTS
    // =========================================================================
    CONNECTION_STATUS_CHANGED: 'connection:status-changed',
};

// =============================================================================
// EventBus Class
// =============================================================================

/**
 * Simple event bus implementation
 */
class EventBus {
    constructor() {
        /** @type {Map<string, Set<Function>>} */
        this._listeners = new Map();

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
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {Function} callback - Event handler
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, new Set());
        }
        this._listeners.get(event).add(callback);

        // Return unsubscribe function
        return () => {
            this._listeners.get(event)?.delete(callback);
        };
    }

    /**
     * Subscribe to an event once
     * @param {string} event - Event name
     * @param {Function} callback - Event handler
     * @returns {Function} Unsubscribe function
     */
    once(event, callback) {
        const wrapper = (...args) => {
            callback(...args);
            this._listeners.get(event)?.delete(wrapper);
        };
        return this.on(event, wrapper);
    }

    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {*} [payload] - Event data
     */
    emit(event, payload) {
        if (this._debug) {
            console.log(`[EventBus] ${event}`, payload);
        }

        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.forEach(callback => {
                try {
                    callback(payload);
                } catch (error) {
                    console.error(`[EventBus] Error in handler for "${event}":`, error);
                }
            });
        }
    }

    /**
     * Remove all listeners for an event
     * @param {string} event - Event name
     */
    off(event) {
        this._listeners.delete(event);
    }

    /**
     * Remove all listeners
     */
    clear() {
        this._listeners.clear();
    }

    /**
     * Get listener count for an event
     * @param {string} event - Event name
     * @returns {number} Number of listeners
     */
    listenerCount(event) {
        return this._listeners.get(event)?.size || 0;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

/**
 * Singleton event bus instance
 */
export const eventBus = new EventBus();
