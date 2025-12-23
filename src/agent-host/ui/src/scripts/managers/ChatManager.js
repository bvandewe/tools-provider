/**
 * ChatManager - Chat UI State Management
 *
 * Manages DOM elements and UI state for the chat interface.
 * Listens to events from domain/protocol layers and updates DOM.
 *
 * @module managers/ChatManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { scrollToBottom, isNearBottom } from '../utils/dom.js';

/**
 * ChatManager manages the chat input/output UI state
 */
export class ChatManager {
    /**
     * Create a new ChatManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Object} DOM element references */
        this._elements = {
            messagesContainer: null,
            welcomeMessage: null,
            chatForm: null,
            messageInput: null,
            sendBtn: null,
            cancelBtn: null,
            statusIndicator: null,
            attachedFilesContainer: null,
        };

        /** @type {boolean} User has scrolled up during streaming */
        this._userScrolledUp = false;

        /** @type {Function[]} Event unsubscribe functions */
        this._unsubscribers = [];

        // Bind methods for callbacks
        this._handleStreamingState = this._handleStreamingState.bind(this);
        this._handleStatusChanged = this._handleStatusChanged.bind(this);
        this._handleMessageStreaming = this._handleMessageStreaming.bind(this);
        this._handleMessageComplete = this._handleMessageComplete.bind(this);
        this._handleWidgetRendered = this._handleWidgetRendered.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize chat manager with DOM elements
     * @param {Object} domElements - DOM element references
     */
    init(domElements = {}) {
        if (this._initialized) {
            console.warn('[ChatManager] Already initialized');
            return;
        }

        this._elements = { ...this._elements, ...domElements };
        this._subscribeToEvents();
        this._initialized = true;

        console.log('[ChatManager] Initialized');
    }

    /**
     * Subscribe to event bus events
     * @private
     */
    _subscribeToEvents() {
        // Streaming state changes
        this._unsubscribers.push(eventBus.on(Events.UI_STREAMING_STATE, this._handleStreamingState));

        // Status changes
        this._unsubscribers.push(eventBus.on(Events.UI_STATUS_CHANGED, this._handleStatusChanged));

        // Message streaming - auto scroll
        this._unsubscribers.push(eventBus.on(Events.MESSAGE_STREAMING, this._handleMessageStreaming));

        // Message complete - scroll to bottom
        this._unsubscribers.push(eventBus.on(Events.MESSAGE_COMPLETE, this._handleMessageComplete));

        // Widget rendered - scroll to bottom
        this._unsubscribers.push(eventBus.on(Events.WIDGET_RENDERED, this._handleWidgetRendered));
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle streaming state event
     * @private
     * @param {Object} payload - Event payload
     */
    _handleStreamingState({ isStreaming }) {
        this.updateStreamingState(isStreaming);
    }

    /**
     * Handle status changed event
     * @private
     * @param {Object} payload - Event payload
     */
    _handleStatusChanged({ status, message }) {
        this._updateStatusIndicator(status, message);
    }

    /**
     * Handle message streaming event
     * @private
     */
    _handleMessageStreaming() {
        if (!this._userScrolledUp) {
            scrollToBottom(this._elements.messagesContainer);
        }
    }

    /**
     * Handle message complete event
     * @private
     */
    _handleMessageComplete() {
        scrollToBottom(this._elements.messagesContainer);
        this._userScrolledUp = false;
    }

    /**
     * Handle widget rendered event
     * @private
     */
    _handleWidgetRendered() {
        scrollToBottom(this._elements.messagesContainer);
    }

    // =========================================================================
    // UI State Updates
    // =========================================================================

    /**
     * Update streaming state UI
     * Only affects enabled/disabled state, NOT button visibility.
     * Button visibility is controlled solely by showAllChatInputButtons/hideAllChatInputButtons.
     * @param {boolean} isStreaming - Whether currently streaming
     */
    updateStreamingState(isStreaming) {
        stateManager.set(StateKeys.IS_STREAMING, isStreaming);

        // Only toggle send/cancel if buttons are currently visible (not hidden by backend)
        const buttonsAreVisible = this._elements.sendBtn && !this._elements.sendBtn.classList.contains('chat-input-hidden');

        if (buttonsAreVisible) {
            if (this._elements.sendBtn) {
                this._elements.sendBtn.classList.toggle('d-none', isStreaming);
                this._elements.sendBtn.disabled = isStreaming;
            }
            if (this._elements.cancelBtn) {
                this._elements.cancelBtn.classList.toggle('d-none', !isStreaming);
            }
        }

        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = isStreaming;
        }
    }

    /**
     * Hide all chat input buttons (when backend disables chat)
     * @param {string} [placeholder] - Optional placeholder text for the input
     */
    hideAllChatInputButtons(placeholder = '') {
        console.log('[ChatManager] Hiding all chat input buttons');

        if (this._elements.sendBtn) {
            this._elements.sendBtn.classList.add('d-none', 'chat-input-hidden');
            this._elements.sendBtn.disabled = true;
        }
        if (this._elements.cancelBtn) {
            this._elements.cancelBtn.classList.add('d-none');
        }
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = true;
            this._elements.messageInput.placeholder = placeholder;
        }
        // Hide file upload button if present
        const uploadBtn = document.querySelector('.upload-btn, #upload-btn, .file-upload-btn, #file-upload-btn, [data-upload-btn]');
        if (uploadBtn) {
            uploadBtn.classList.add('d-none');
        }
    }

    /**
     * Show all chat input buttons (when backend enables chat)
     */
    showAllChatInputButtons() {
        console.log('[ChatManager] Showing all chat input buttons');

        if (this._elements.sendBtn) {
            this._elements.sendBtn.classList.remove('d-none', 'chat-input-hidden');
            this._elements.sendBtn.disabled = false;
        }
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = false;
            this._elements.messageInput.placeholder = 'Type your message...';
        }
        // Show and enable file upload button if present
        const uploadBtn = document.querySelector('.upload-btn, #upload-btn, .file-upload-btn, #file-upload-btn, [data-upload-btn]');
        if (uploadBtn) {
            uploadBtn.classList.remove('d-none');
            uploadBtn.disabled = false;
        }
    }

    /**
     * Update status indicator
     * @private
     * @param {string} status - Status code
     * @param {string} message - Status message
     */
    _updateStatusIndicator(status, message) {
        if (!this._elements.statusIndicator) return;

        // Update indicator class
        this._elements.statusIndicator.className = 'status-indicator';
        this._elements.statusIndicator.classList.add(`status-${status}`);

        // Update tooltip
        this._elements.statusIndicator.title = message;
    }

    // =========================================================================
    // Welcome Message
    // =========================================================================

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        if (this._elements.welcomeMessage) {
            this._elements.welcomeMessage.classList.remove('d-none');
        }
    }

    /**
     * Hide welcome message
     */
    hideWelcomeMessage() {
        if (this._elements.welcomeMessage) {
            this._elements.welcomeMessage.classList.add('d-none');
        }
    }

    // =========================================================================
    // Input Management
    // =========================================================================

    /**
     * Enable the input field
     */
    enableInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = false;
        }
        if (this._elements.sendBtn) {
            this._elements.sendBtn.disabled = false;
        }
    }

    /**
     * Disable the input field
     */
    disableInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = true;
        }
        if (this._elements.sendBtn) {
            this._elements.sendBtn.disabled = true;
        }
    }

    /**
     * Focus the input field
     */
    focusInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.focus();
        }
    }

    /**
     * Clear the input field
     */
    clearInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.value = '';
        }
    }

    /**
     * Get the input value
     * @returns {string} Input value
     */
    getInputValue() {
        return this._elements.messageInput?.value || '';
    }

    /**
     * Update connection status indicator
     * @param {string} status - Connection status
     */
    updateConnectionStatus(status) {
        const indicator = this._elements.statusIndicator || document.querySelector('.connection-indicator');
        if (!indicator) return;

        indicator.className = 'connection-indicator';
        indicator.classList.add(`status-${status}`);
    }

    // =========================================================================
    // Getters
    // =========================================================================

    /**
     * Get DOM elements
     * @returns {Object} DOM elements
     */
    get elements() {
        return this._elements;
    }

    /**
     * Check if initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        // Unsubscribe from all events
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];

        this._elements = {
            messagesContainer: null,
            welcomeMessage: null,
            chatForm: null,
            messageInput: null,
            sendBtn: null,
            cancelBtn: null,
            statusIndicator: null,
            attachedFilesContainer: null,
        };

        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const chatManager = new ChatManager();
