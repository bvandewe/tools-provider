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
 * eventBus.on(Events.CONVERSATION_LOADED, (data) => console.log(data));
 *
 * // Publish event
 * eventBus.emit(Events.CONVERSATION_LOADED, { id: '123' });
 *
 * // Unsubscribe
 * const unsub = eventBus.on(Events.MESSAGE_SENT, handler);
 * unsub(); // Remove listener
 */

// =============================================================================
// Event Names (Constants)
// =============================================================================

/**
 * Standard event names used throughout the application.
 * Use these constants instead of magic strings.
 *
 * Naming convention mirrors backend protocol:
 * - Protocol messages: {plane}.{category}.{action} (e.g., "system.connection.established")
 * - Local UI events: {domain}:{action} (e.g., "auth:state-changed")
 *
 * @readonly
 * @enum {string}
 */
export const Events = {
    // =========================================================================
    // PROTOCOL MESSAGES - SYSTEM PLANE
    // Server → Client connection lifecycle and errors
    // =========================================================================
    SYSTEM_CONNECTION_ESTABLISHED: 'system.connection.established',
    SYSTEM_CONNECTION_RESUMED: 'system.connection.resumed',
    SYSTEM_CONNECTION_CLOSE: 'system.connection.close',
    SYSTEM_PING: 'system.ping',
    SYSTEM_PONG: 'system.pong',
    SYSTEM_ERROR: 'system.error',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: CONVERSATION
    // Conversation-level configuration and lifecycle
    // =========================================================================
    CONTROL_CONVERSATION_CONFIG: 'control.conversation.config',
    CONTROL_CONVERSATION_DISPLAY: 'control.conversation.display',
    CONTROL_CONVERSATION_DEADLINE: 'control.conversation.deadline',
    CONTROL_CONVERSATION_STARTED: 'control.conversation.started',
    CONTROL_CONVERSATION_PAUSED: 'control.conversation.paused',
    CONTROL_CONVERSATION_RESUMED: 'control.conversation.resumed',
    CONTROL_CONVERSATION_COMPLETED: 'control.conversation.completed',
    CONTROL_CONVERSATION_TERMINATED: 'control.conversation.terminated',
    CONTROL_CONVERSATION_MODEL: 'control.conversation.model',
    CONTROL_CONVERSATION_MODEL_ACK: 'control.conversation.model.ack',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: ITEM
    // Item-level context and scoring
    // =========================================================================
    CONTROL_ITEM_CONTEXT: 'control.item.context',
    CONTROL_ITEM_SCORE: 'control.item.score',
    CONTROL_ITEM_TIMEOUT: 'control.item.timeout',
    CONTROL_ITEM_EXPIRED: 'control.item.expired',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: WIDGET
    // Widget state and lifecycle
    // =========================================================================
    CONTROL_WIDGET_STATE: 'control.widget.state',
    CONTROL_WIDGET_RENDER: 'control.widget.render',
    CONTROL_WIDGET_DISMISS: 'control.widget.dismiss',
    CONTROL_WIDGET_UPDATE: 'control.widget.update',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: NAVIGATION
    // Navigation requests and acknowledgments
    // =========================================================================
    CONTROL_NAVIGATION_REQUEST: 'control.navigation.request',
    CONTROL_NAVIGATION_ACK: 'control.navigation.ack',
    CONTROL_NAVIGATION_DENIED: 'control.navigation.denied',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: FLOW
    // Chat input and flow control
    // =========================================================================
    CONTROL_FLOW_CHAT_INPUT: 'control.flow.chatInput',
    CONTROL_FLOW_PROGRESS: 'control.flow.progress',

    // =========================================================================
    // PROTOCOL MESSAGES - CONTROL PLANE: PANEL
    // Chat panel header state (progress, title, score)
    // =========================================================================
    CONTROL_PANEL_HEADER: 'control.panel.header',

    // =========================================================================
    // PROTOCOL MESSAGES - DATA PLANE: CONTENT
    // Streaming content from LLM
    // =========================================================================
    DATA_CONTENT_CHUNK: 'data.content.chunk',
    DATA_CONTENT_COMPLETE: 'data.content.complete',

    // =========================================================================
    // PROTOCOL MESSAGES - DATA PLANE: TOOL
    // Tool call lifecycle
    // =========================================================================
    DATA_TOOL_CALL: 'data.tool.call',
    DATA_TOOL_RESULT: 'data.tool.result',

    // =========================================================================
    // PROTOCOL MESSAGES - DATA PLANE: MESSAGE
    // User message acknowledgment
    // =========================================================================
    DATA_MESSAGE_SEND: 'data.message.send',
    DATA_MESSAGE_ACK: 'data.message.ack',

    // =========================================================================
    // PROTOCOL MESSAGES - DATA PLANE: RESPONSE
    // Widget response submission
    // =========================================================================
    DATA_RESPONSE_SUBMIT: 'data.response.submit',
    DATA_RESPONSE_ACK: 'data.response.ack',

    // =========================================================================
    // PROTOCOL MESSAGES - DATA PLANE: AUDIT
    // User interaction auditing
    // =========================================================================
    DATA_AUDIT_BATCH: 'data.audit.batch',
    DATA_AUDIT_ACK: 'data.audit.ack',

    // =========================================================================
    // LOCAL UI EVENTS - Authentication
    // =========================================================================
    AUTH_STATE_CHANGED: 'auth:state-changed',
    AUTH_SESSION_EXPIRED: 'auth:session-expired',
    AUTH_BEFORE_REDIRECT: 'auth:before-redirect',

    // =========================================================================
    // LOCAL UI EVENTS - Conversation (client-side state)
    // =========================================================================
    CONVERSATION_CREATED: 'conversation:created',
    CONVERSATION_LOADED: 'conversation:loaded',
    CONVERSATION_UPDATED: 'conversation:updated',
    CONVERSATION_DELETED: 'conversation:deleted',
    CONVERSATION_LIST_UPDATED: 'conversation:list-updated',

    // =========================================================================
    // LOCAL UI EVENTS - Message (client-side state)
    // =========================================================================
    MESSAGE_SENT: 'message:sent',
    MESSAGE_RECEIVED: 'message:received',
    MESSAGE_STREAMING: 'message:streaming',
    MESSAGE_COMPLETE: 'message:complete',

    // =========================================================================
    // LOCAL UI EVENTS - Definition
    // =========================================================================
    DEFINITION_SELECTED: 'definition:selected',
    DEFINITION_LIST_LOADED: 'definition:list-loaded',

    // =========================================================================
    // LOCAL UI EVENTS - Model Selection
    // =========================================================================
    MODEL_CHANGED: 'model:changed',
    MODEL_CHANGE_REQUESTED: 'model:change-requested',
    MODEL_CHANGE_FAILED: 'model:change-failed',

    // =========================================================================
    // LOCAL UI EVENTS - WebSocket (transport layer)
    // =========================================================================
    WS_CONNECTED: 'ws:connected',
    WS_DISCONNECTED: 'ws:disconnected',
    WS_MESSAGE: 'ws:message',
    WS_ERROR: 'ws:error',

    // =========================================================================
    // LOCAL UI EVENTS - Widget (client-side)
    // =========================================================================
    WIDGET_RENDERED: 'widget:rendered',
    WIDGET_RESPONSE: 'widget:response',
    WIDGET_VALIDATED: 'widget:validated',
    WIDGET_SELECTION_CHANGED: 'widget:selection-changed',

    // =========================================================================
    // LOCAL UI EVENTS - Template (client-side state)
    // =========================================================================
    TEMPLATE_CONFIG: 'template:config',
    TEMPLATE_PROGRESS: 'template:progress',
    TEMPLATE_COMPLETE: 'template:complete',

    // =========================================================================
    // LOCAL UI EVENTS - UI State
    // =========================================================================
    UI_STREAMING_STATE: 'ui:streaming-state',
    UI_STATUS_CHANGED: 'ui:status-changed',
    UI_SIDEBAR_TOGGLE: 'ui:sidebar-toggle',
    UI_THEME_CHANGED: 'ui:theme-changed',
    UI_TOAST: 'ui:toast',
    UI_RESIZE: 'ui:resize',

    // UI Rendering Commands (for decoupled handler → renderer communication)
    UI_RENDER_DEFINITION_TILES: 'ui:render-definition-tiles',
    UI_UPDATE_DEFINITION_SELECTION: 'ui:update-definition-selection',
    UI_RENDER_MESSAGES: 'ui:render-messages',
    UI_CLEAR_MESSAGES: 'ui:clear-messages',

    // =========================================================================
    // LOCAL UI EVENTS - Draft
    // =========================================================================
    DRAFT_SAVED: 'draft:saved',
    DRAFT_RESTORED: 'draft:restored',
    DRAFT_CLEARED: 'draft:cleared',

    // =========================================================================
    // LOCAL UI EVENTS - Tool (client-side state)
    // =========================================================================
    TOOL_CALL_STARTED: 'tool:call-started',
    TOOL_CALL_COMPLETED: 'tool:call-completed',

    // =========================================================================
    // LOCAL UI EVENTS - Canvas (Phase 5D)
    // =========================================================================
    CANVAS_ELEMENT_ADDED: 'canvas:element-added',
    CANVAS_ELEMENT_MOVED: 'canvas:element-moved',
    CANVAS_CONNECTION_CREATED: 'canvas:connection-created',
    CANVAS_GROUP_CREATED: 'canvas:group-created',
    CANVAS_LAYER_CHANGED: 'canvas:layer-changed',
};

// =============================================================================
// EventBus Class
// =============================================================================

/**
 * Simple event bus implementation with typed events
 */
class EventBus {
    constructor() {
        /** @type {Map<string, Set<Function>>} */
        this._listeners = new Map();

        /** @type {Map<string, *>} */
        this._lastEmitted = new Map();

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
     * @param {string} event - Event name (use Events enum)
     * @param {Function} callback - Handler function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        if (!this._listeners.has(event)) {
            this._listeners.set(event, new Set());
        }
        this._listeners.get(event).add(callback);

        if (this._debug) {
            console.log(`[EventBus] Subscribed to: ${event}`);
        }

        // Return unsubscribe function
        return () => this.off(event, callback);
    }

    /**
     * Subscribe to an event, but only fire once
     * @param {string} event - Event name
     * @param {Function} callback - Handler function
     * @returns {Function} Unsubscribe function
     */
    once(event, callback) {
        const wrapper = (...args) => {
            this.off(event, wrapper);
            callback(...args);
        };
        return this.on(event, wrapper);
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {Function} callback - Handler to remove
     */
    off(event, callback) {
        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.delete(callback);
            if (listeners.size === 0) {
                this._listeners.delete(event);
            }
        }

        if (this._debug) {
            console.log(`[EventBus] Unsubscribed from: ${event}`);
        }
    }

    /**
     * Emit an event to all subscribers
     * @param {string} event - Event name
     * @param {*} data - Event payload
     */
    emit(event, data = null) {
        if (this._debug) {
            console.log(`[EventBus] Emit: ${event}`, data);
        }

        // Store last emitted value (useful for late subscribers)
        this._lastEmitted.set(event, data);

        const listeners = this._listeners.get(event);
        if (listeners) {
            listeners.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[EventBus] Error in handler for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Emit event asynchronously (non-blocking)
     * @param {string} event - Event name
     * @param {*} data - Event payload
     */
    emitAsync(event, data = null) {
        queueMicrotask(() => this.emit(event, data));
    }

    /**
     * Get the last emitted value for an event
     * Useful for late subscribers to get current state
     * @param {string} event - Event name
     * @returns {*} Last emitted data or undefined
     */
    getLastEmitted(event) {
        return this._lastEmitted.get(event);
    }

    /**
     * Check if an event has any listeners
     * @param {string} event - Event name
     * @returns {boolean}
     */
    hasListeners(event) {
        return this._listeners.has(event) && this._listeners.get(event).size > 0;
    }

    /**
     * Remove all listeners for an event (or all events)
     * @param {string} [event] - Optional event name. If omitted, clears all.
     */
    clear(event) {
        if (event) {
            this._listeners.delete(event);
            this._lastEmitted.delete(event);
        } else {
            this._listeners.clear();
            this._lastEmitted.clear();
        }
    }

    /**
     * Get count of listeners for debugging
     * @returns {Object} Map of event name to listener count
     */
    getListenerCounts() {
        const counts = {};
        this._listeners.forEach((listeners, event) => {
            counts[event] = listeners.size;
        });
        return counts;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

/** @type {EventBus} */
export const eventBus = new EventBus();

// Enable debug mode in development
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    // Uncomment to enable debug logging:
    // eventBus.setDebug(true);
}

export default eventBus;
