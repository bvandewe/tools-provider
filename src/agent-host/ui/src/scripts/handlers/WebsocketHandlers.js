/**
 * WebSocket Event Handlers (Class-based)
 *
 * Handles WebSocket connection lifecycle events using class-based architecture
 * with dependency injection via imported singletons.
 *
 * @module handlers/WebsocketHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { setCurrentConversationId } from '../domain/conversation.js';

// Import class-based managers
import { chatManager } from '../managers/ChatManager.js';
import { setUploadEnabled } from '../components/FileUpload.js';
import { showToast } from '../services/modals.js';

/**
 * @class WebsocketHandlers
 * @description Handles all WebSocket connection lifecycle events
 */
export class WebsocketHandlers {
    /**
     * Create WebsocketHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind methods to preserve context
        this._handleWsConnected = this._handleWsConnected.bind(this);
        this._handleWsDisconnected = this._handleWsDisconnected.bind(this);
        this._handleWsError = this._handleWsError.bind(this);
    }

    /**
     * Initialize handlers and subscribe to events
     * @returns {void}
     */
    init() {
        if (this._initialized) {
            console.warn('[WebsocketHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[WebsocketHandlers] Initialized');
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.WS_CONNECTED, this._handleWsConnected),
            eventBus.on(Events.WS_DISCONNECTED, this._handleWsDisconnected),
            eventBus.on(Events.WS_ERROR, this._handleWsError)
        );
    }

    /**
     * Handle WebSocket connected event
     * Note: The WS_CONNECTED event may be emitted without a payload.
     * The conversationId is typically set via the system.connection.established handler.
     *
     * @private
     * @param {Object|null} [payload] - Event payload (may be null/undefined)
     * @param {string} [payload.conversationId] - Connected conversation ID
     */
    _handleWsConnected(payload) {
        const conversationId = payload?.conversationId;
        console.log('[WebsocketHandlers] Connected, conversation:', conversationId);

        if (conversationId) {
            setCurrentConversationId(conversationId);
        }
    }

    /**
     * Handle WebSocket disconnected event
     * @private
     * @param {Object} [payload] - Event payload
     */
    _handleWsDisconnected(payload) {
        console.log('[WebsocketHandlers] Disconnected');

        // Reset UI state on disconnect
        chatManager.updateStreamingState(false);
        setUploadEnabled(true);
    }

    /**
     * Handle WebSocket error event
     * @private
     * @param {Object|null} [payload] - Event payload (may be null/undefined)
     * @param {string} [payload.message] - Error message
     * @param {string} [payload.code] - Error code
     */
    _handleWsError(payload) {
        const message = payload?.message;
        const code = payload?.code;

        console.error('[WebsocketHandlers] Error:', message, code);

        // Show error toast to user
        showToast(message || 'Connection error', 'error');

        // Reset UI state on error
        chatManager.updateStreamingState(false);
        setUploadEnabled(true);
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[WebsocketHandlers] Destroyed');
    }

    /**
     * Check if handlers are initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const websocketHandlers = new WebsocketHandlers();
export default websocketHandlers;
