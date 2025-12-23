/**
 * Message Event Handlers (Class-based)
 *
 * Handles message-related events using class-based architecture
 * with dependency injection via imported singletons.
 *
 * @module handlers/MessageHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { loadConversations } from '../domain/conversation.js';

// Import class-based managers
import { chatManager } from '../managers/ChatManager.js';
import { setUploadEnabled } from '../components/FileUpload.js';

/**
 * @class MessageHandlers
 * @description Handles all message-related events (streaming, complete, etc.)
 */
export class MessageHandlers {
    /**
     * Create MessageHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind methods to preserve context
        this._handleMessageComplete = this._handleMessageComplete.bind(this);
        this._handleMessageStreaming = this._handleMessageStreaming.bind(this);
    }

    /**
     * Initialize handlers and subscribe to events
     * @returns {void}
     */
    init() {
        if (this._initialized) {
            console.warn('[MessageHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[MessageHandlers] Initialized');
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.MESSAGE_COMPLETE, this._handleMessageComplete), eventBus.on(Events.MESSAGE_STREAMING, this._handleMessageStreaming));
    }

    /**
     * Handle message complete - reset UI state and refresh conversations
     * @private
     * @param {Object} [payload] - Event payload
     */
    _handleMessageComplete(payload) {
        console.log('[MessageHandlers] Message complete');

        // Update streaming state
        chatManager.updateStreamingState(false);

        // Re-enable file uploads
        setUploadEnabled(true);

        // Refresh conversation list to update timestamps
        loadConversations();
    }

    /**
     * Handle message streaming content chunk
     * Updates UI streaming state when content starts flowing
     * @private
     * @param {Object} payload - Event payload with messageId and content
     */
    _handleMessageStreaming(payload) {
        // Content is streaming - ensure UI reflects streaming state
        if (payload?.content) {
            chatManager.updateStreamingState(true);
            setUploadEnabled(false);
        }
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[MessageHandlers] Destroyed');
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
export const messageHandlers = new MessageHandlers();
export default messageHandlers;
