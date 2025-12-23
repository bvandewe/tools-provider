/**
 * SystemHandlers - System Plane Event Handler Class
 *
 * Handles WebSocket protocol system-level messages:
 * - Connection lifecycle (establish, resume, close)
 * - Heartbeat (ping/pong)
 * - System errors
 *
 * Uses dependency injection via imported singletons instead of factory pattern.
 *
 * @module handlers/SystemHandlers
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { ConnectionState } from '../core/constants.js';
import { showToast } from '../services/modals.js';
import { chatManager } from '../managers/ChatManager.js';

// Note: WebSocket client for sending pong responses
import * as websocketClient from '../protocol/websocket-client.js';

/**
 * SystemHandlers manages event handlers for WebSocket system-level messages
 */
export class SystemHandlers {
    /**
     * Create a new SystemHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {string} */
        this._connectionState = ConnectionState.DISCONNECTED;

        /** @type {number|null} */
        this._lastLatency = null;

        /** @type {string[]|null} */
        this._serverCapabilities = null;

        // Bind handlers
        this._handleConnectionEstablished = this._handleConnectionEstablished.bind(this);
        this._handleConnectionResumed = this._handleConnectionResumed.bind(this);
        this._handleConnectionClose = this._handleConnectionClose.bind(this);
        this._handlePing = this._handlePing.bind(this);
        this._handlePong = this._handlePong.bind(this);
        this._handleSystemError = this._handleSystemError.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize and register event handlers
     */
    init() {
        if (this._initialized) {
            console.warn('[SystemHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;

        console.log('[SystemHandlers] Initialized');
    }

    /**
     * Subscribe to events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.SYSTEM_CONNECTION_ESTABLISHED, this._handleConnectionEstablished));

        this._unsubscribers.push(eventBus.on(Events.SYSTEM_CONNECTION_RESUMED, this._handleConnectionResumed));

        this._unsubscribers.push(eventBus.on(Events.SYSTEM_CONNECTION_CLOSE, this._handleConnectionClose));

        this._unsubscribers.push(eventBus.on(Events.SYSTEM_PING, this._handlePing));

        this._unsubscribers.push(eventBus.on(Events.SYSTEM_PONG, this._handlePong));

        this._unsubscribers.push(eventBus.on(Events.SYSTEM_ERROR, this._handleSystemError));
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle system.connection.established
     * @private
     * @param {Object} payload - Event payload
     */
    _handleConnectionEstablished(payload) {
        console.log('[SystemHandlers] Connection established:', {
            connectionId: payload.connectionId?.slice(0, 8) + '...',
            conversationId: payload.conversationId,
            resuming: payload.resuming,
            capabilities: payload.serverCapabilities?.length || 0,
            currentModel: payload.currentModel,
            availableModels: payload.availableModels?.length || 0,
            allowModelSelection: payload.allowModelSelection,
        });

        // Store session info for reconnection
        if (payload.sessionId) {
            sessionStorage.setItem('ws_session_id', payload.sessionId);
        }

        // Update connection state
        this._connectionState = ConnectionState.CONNECTED;

        // Store server capabilities in state manager
        if (payload.serverCapabilities) {
            stateManager.set(StateKeys.SERVER_CAPABILITIES, payload.serverCapabilities);
            this._serverCapabilities = payload.serverCapabilities;
        }

        // Store conversation ID in state manager
        if (payload.conversationId) {
            stateManager.set(StateKeys.WS_CONVERSATION_ID, payload.conversationId);
        }

        // Store model information in state manager
        if (payload.availableModels) {
            stateManager.set(StateKeys.AVAILABLE_MODELS, payload.availableModels);
        }
        if (payload.currentModel) {
            stateManager.set(StateKeys.SELECTED_MODEL_ID, payload.currentModel);
        }
        if (typeof payload.allowModelSelection === 'boolean') {
            stateManager.set(StateKeys.ALLOW_MODEL_SELECTION, payload.allowModelSelection);
        }

        // Update UI to show connected state
        chatManager.updateConnectionStatus('connected');

        // Update tools indicator with tool count from server
        if (typeof payload.toolCount === 'number') {
            this._updateToolsIndicator(payload.toolCount);
            stateManager.set(StateKeys.TOOL_COUNT, payload.toolCount);
        }

        // Emit connected event with full payload for other components
        eventBus.emit(Events.WS_CONNECTED, {
            connectionId: payload.connectionId,
            conversationId: payload.conversationId,
            userId: payload.userId,
            definitionId: payload.definitionId,
            resuming: payload.resuming,
            serverCapabilities: payload.serverCapabilities,
            currentModel: payload.currentModel,
            availableModels: payload.availableModels,
            allowModelSelection: payload.allowModelSelection,
            toolCount: payload.toolCount,
        });
    }

    /**
     * Handle system.connection.resumed
     * @private
     * @param {Object} payload - Event payload
     */
    _handleConnectionResumed(payload) {
        console.log('[SystemHandlers] Connection resumed:', payload);

        this._connectionState = ConnectionState.CONNECTED;

        // Handle missed messages if any
        if (payload.missedMessages > 0) {
            console.log(`[SystemHandlers] ${payload.missedMessages} messages missed during disconnect`);
        }

        chatManager.updateConnectionStatus('connected');
    }

    /**
     * Handle system.connection.close
     * @private
     * @param {Object} payload - Event payload
     */
    _handleConnectionClose(payload) {
        console.log('[SystemHandlers] Connection close requested:', payload);

        this._connectionState = ConnectionState.DISCONNECTED;

        // Clear session if server says no reconnect
        if (!payload.canReconnect) {
            sessionStorage.removeItem('ws_session_id');
        }

        chatManager.updateConnectionStatus('disconnected');

        // Show user-friendly message for specific close codes
        if (payload.code >= 4000) {
            showToast(payload.reason || 'Connection closed by server', 'error');
        }
    }

    /**
     * Handle system.ping - respond with pong
     * @private
     * @param {Object} payload - Event payload
     */
    _handlePing(payload) {
        // Respond with pong immediately using send() not sendMessage()
        websocketClient.send('system.pong', {
            timestamp: payload?.timestamp,
            sequence: payload?.sequence,
        });
    }

    /**
     * Handle system.pong - measure latency
     * @private
     * @param {Object} payload - Event payload
     */
    _handlePong(payload) {
        // Calculate round-trip latency
        if (payload.timestamp) {
            const latency = Date.now() - new Date(payload.timestamp).getTime();
            this._lastLatency = latency;
            console.debug(`[SystemHandlers] Pong received, latency: ${latency}ms`);
        }
    }

    /**
     * Handle system.error
     * @private
     * @param {Object} payload - Event payload
     */
    _handleSystemError(payload) {
        console.error('[SystemHandlers] System error:', payload);

        // Handle specific error codes
        switch (payload.code) {
            case 'AUTH_EXPIRED':
            case 'AUTH_INVALID':
                // Trigger re-authentication
                eventBus.emit(Events.AUTH_SESSION_EXPIRED, payload);
                break;

            case 'RATE_LIMITED':
                // Show rate limit message with retry time
                const retryMsg = payload.retryAfter ? `Rate limited. Retry in ${payload.retryAfter}s` : 'Rate limited. Please slow down.';
                showToast(retryMsg, 'warning');
                break;

            case 'INTERNAL_ERROR':
                showToast('Server error. Please try again.', 'error');
                break;

            default:
                if (payload.message) {
                    showToast(payload.message, 'error');
                }
        }

        // If not recoverable, may need to reconnect
        if (!payload.recoverable) {
            console.warn('[SystemHandlers] Non-recoverable error, may need reconnection');
        }
    }

    // =========================================================================
    // Private Helpers
    // =========================================================================

    /**
     * Update tools indicator UI
     * @private
     * @param {number} toolCount - Number of tools
     */
    _updateToolsIndicator(toolCount) {
        const toolsIndicator = document.querySelector('.tools-indicator');
        const toolsCountEl = document.querySelector('.tools-count');

        if (toolsCountEl) {
            toolsCountEl.textContent = toolCount.toString();
            console.log(`[SystemHandlers] Updated tools count: ${toolCount}`);
        }

        if (toolsIndicator) {
            toolsIndicator.classList.toggle('has-tools', toolCount > 0);
        }
    }

    // =========================================================================
    // Getters
    // =========================================================================

    /**
     * Get current connection state
     * @returns {string}
     */
    get connectionState() {
        return this._connectionState;
    }

    /**
     * Get last measured latency
     * @returns {number|null}
     */
    get lastLatency() {
        return this._lastLatency;
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._connectionState = ConnectionState.DISCONNECTED;
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const systemHandlers = new SystemHandlers();

// =============================================================================
// Legacy Compatibility - Handler Registrations for old index.js
// =============================================================================

/**
 * @deprecated Use systemHandlers.init() instead
 */
export const handlers = [
    {
        event: Events.SYSTEM_CONNECTION_ESTABLISHED,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handleConnectionEstablished(payload);
        },
        description: 'Server confirms WebSocket connection with session info',
        isFactory: true,
    },
    {
        event: Events.SYSTEM_CONNECTION_RESUMED,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handleConnectionResumed(payload);
        },
        description: 'Server confirms reconnection with previous session state',
        isFactory: true,
    },
    {
        event: Events.SYSTEM_CONNECTION_CLOSE,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handleConnectionClose(payload);
        },
        description: 'Server initiates graceful connection close',
        isFactory: true,
    },
    {
        event: Events.SYSTEM_PING,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handlePing(payload);
        },
        description: 'Server heartbeat - respond with pong',
        isFactory: true,
    },
    {
        event: Events.SYSTEM_PONG,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handlePong(payload);
        },
        description: 'Response to client ping for latency measurement',
        isFactory: true,
    },
    {
        event: Events.SYSTEM_ERROR,
        handler: context => payload => {
            console.warn('[SystemHandlers] DEPRECATED: Using legacy factory pattern');
            systemHandlers._handleSystemError(payload);
        },
        description: 'Server-side error notification',
        isFactory: true,
    },
];

export default handlers;
