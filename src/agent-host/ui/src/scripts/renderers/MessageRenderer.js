/**
 * MessageRenderer - Class-based DOM rendering for chat messages
 *
 * Handles rendering of user messages, assistant messages,
 * thinking indicators, and tool call cards.
 *
 * @module renderers/MessageRenderer
 */

import { eventBus, Events } from '../core/event-bus.js';
import { scrollToBottom } from '../utils/dom.js';
import { showToolDetailsModal } from '../services/modals.js';
import { api } from '../services/api.js';

/**
 * @class MessageRenderer
 * @description Manages rendering of chat messages in the UI
 */
export class MessageRenderer {
    /**
     * Create MessageRenderer instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {HTMLElement|null} */
        this._messagesContainer = null;

        /** @type {HTMLElement|null} */
        this._welcomeMessage = null;

        /** @type {Function|null} */
        this._isAdminFn = null;

        /** @type {HTMLElement|null} */
        this._currentThinkingElement = null;

        /** @type {Map<string, string>} Accumulated streaming content per message ID */
        this._streamingContent = new Map();

        // Bind methods
        this._handleMessageComplete = this._handleMessageComplete.bind(this);
        this._handleMessageStreaming = this._handleMessageStreaming.bind(this);
        this._handleToolCallStarted = this._handleToolCallStarted.bind(this);
        this._handleToolCallCompleted = this._handleToolCallCompleted.bind(this);
    }

    /**
     * Initialize message renderer
     * @param {HTMLElement} container - Messages container element
     * @param {HTMLElement} welcome - Welcome message element
     * @param {Function} isAdmin - Function to check admin status
     */
    init(container, welcome, isAdmin) {
        if (this._initialized) {
            console.warn('[MessageRenderer] Already initialized');
            return;
        }

        this._messagesContainer = container;
        this._welcomeMessage = welcome;
        this._isAdminFn = isAdmin || (() => false);

        this._subscribeToEvents();
        this._initialized = true;

        console.log('[MessageRenderer] Initialized');
    }

    /**
     * Subscribe to event bus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.MESSAGE_COMPLETE, this._handleMessageComplete),
            eventBus.on(Events.MESSAGE_STREAMING, this._handleMessageStreaming),
            eventBus.on(Events.TOOL_CALL_STARTED, this._handleToolCallStarted),
            eventBus.on(Events.TOOL_CALL_COMPLETED, this._handleToolCallCompleted)
        );
    }

    /**
     * Handle message complete event
     * @private
     */
    _handleMessageComplete({ messageId, content, finalContent }) {
        // Use finalContent if available, otherwise use content, otherwise accumulated
        const displayContent = finalContent || content || this._streamingContent.get(messageId) || '';
        this._completeThinkingElement(displayContent);

        // Clear accumulated content for this message
        if (messageId) {
            this._streamingContent.delete(messageId);
        }
    }

    /**
     * Handle message streaming event - accumulate and display content chunks
     * @private
     * @param {Object} payload - Event payload
     * @param {string} payload.messageId - Message ID
     * @param {string} payload.content - Content chunk
     * @param {string} [payload.contentType] - Content type (text, markdown, code)
     */
    _handleMessageStreaming(payload) {
        const { messageId, content, contentType = 'text' } = payload;

        if (!content) return;

        // Accumulate content
        const existing = this._streamingContent.get(messageId) || '';
        const accumulated = existing + content;
        this._streamingContent.set(messageId, accumulated);

        // Ensure thinking element exists
        if (!this._currentThinkingElement) {
            this.addThinkingMessage();
        }

        // Update thinking element with accumulated content
        if (this._currentThinkingElement) {
            if (this._currentThinkingElement.getAttribute('status') !== 'streaming') {
                this._currentThinkingElement.setAttribute('status', 'streaming');
            }
            this._currentThinkingElement.setAttribute('content', accumulated);
        }
    }

    /**
     * Handle tool call started event
     * @private
     */
    _handleToolCallStarted(payload) {
        this._updateThinkingToolCall(payload.name, 'calling', payload);
    }

    /**
     * Handle tool call completed event
     * @private
     */
    _handleToolCallCompleted(payload) {
        this._updateThinkingToolCall(payload.name, payload.status || 'completed', payload);
        this._updateThinkingToolResult(payload);
    }

    // =========================================================================
    // Message Rendering
    // =========================================================================

    /**
     * Clear all messages (preserves welcome message element)
     */
    clearMessages() {
        if (this._messagesContainer) {
            const welcomeMessage = this._messagesContainer.querySelector('#welcome-message');
            this._messagesContainer.innerHTML = '';
            if (welcomeMessage) {
                this._messagesContainer.appendChild(welcomeMessage);
            }
        }
        this._currentThinkingElement = null;
    }

    /**
     * Render messages from conversation history
     * @param {Array} messages - Message objects
     */
    renderMessages(messages) {
        this.clearMessages();

        if (!messages || messages.length === 0) return;

        messages.forEach(msg => {
            if (msg.role === 'user') {
                this.addUserMessage(msg.content);
            } else if (msg.role === 'assistant') {
                this.addAssistantMessage(msg.content, msg.tool_calls);
            }
        });

        scrollToBottom(this._messagesContainer);
    }

    /**
     * Add a user message
     * @param {string} content - Message content
     * @returns {HTMLElement} Created element
     */
    addUserMessage(content) {
        console.log('[MessageRenderer] addUserMessage called, content:', content);

        const message = document.createElement('chat-message');
        message.setAttribute('role', 'user');
        message.setAttribute('content', content);

        this.appendToContainer(message);
        scrollToBottom(this._messagesContainer);

        return message;
    }

    /**
     * Add an assistant message
     * @param {string} content - Message content
     * @param {Array} [toolCalls] - Tool calls
     * @returns {HTMLElement} Created element
     */
    addAssistantMessage(content, toolCalls) {
        console.log('[MessageRenderer] addAssistantMessage called');

        const message = document.createElement('chat-message');
        message.setAttribute('role', 'assistant');
        message.setAttribute('content', content || '');
        message.setAttribute('status', 'complete');

        if (toolCalls) {
            message.setAttribute('tool-calls', JSON.stringify(toolCalls));
        }

        this.appendToContainer(message);
        scrollToBottom(this._messagesContainer);

        return message;
    }

    /**
     * Add a thinking message (streaming placeholder)
     * @returns {HTMLElement} Created element
     */
    addThinkingMessage() {
        console.log('[MessageRenderer] addThinkingMessage called');

        const message = document.createElement('chat-message');
        message.setAttribute('role', 'assistant');
        message.setAttribute('status', 'thinking');
        message.setAttribute('content', '');

        // Attach tool-badge-click listener
        message.addEventListener('tool-badge-click', e => {
            showToolDetailsModal(e.detail.toolCalls, e.detail.toolResults, {
                isAdmin: this._isAdminFn ? this._isAdminFn() : false,
                fetchSourceInfo: async toolName => {
                    return await api.getToolSourceInfo(toolName);
                },
            });
        });

        this._currentThinkingElement = message;
        this.appendToContainer(message);
        scrollToBottom(this._messagesContainer);

        return message;
    }

    /**
     * Update thinking element with tool call info
     * @private
     */
    _updateThinkingToolCall(toolName, status, payload = {}) {
        // Ensure thinking element exists
        if (!this._currentThinkingElement) {
            this.addThinkingMessage();
        }
        if (!this._currentThinkingElement) return;

        try {
            let toolCalls = [];
            const existing = this._currentThinkingElement.getAttribute('tool-calls');
            if (existing) {
                toolCalls = JSON.parse(existing);
            }

            const existingIdx = toolCalls.findIndex(t => t.name === toolName || t.tool_name === toolName);
            if (existingIdx >= 0) {
                toolCalls[existingIdx].status = status;
                if (payload.callId) toolCalls[existingIdx].call_id = payload.callId;
                if (payload.arguments) toolCalls[existingIdx].arguments = payload.arguments;
            } else {
                toolCalls.push({
                    name: toolName,
                    tool_name: toolName,
                    status,
                    call_id: payload.callId || null,
                    arguments: payload.arguments || null,
                });
            }

            this._currentThinkingElement.setAttribute('tool-calls', JSON.stringify(toolCalls));
            this._currentThinkingElement.setAttribute('status', status === 'calling' ? 'tool-calling' : 'streaming');
        } catch (e) {
            console.warn('[MessageRenderer] Failed to update tool call:', e);
        }
    }

    /**
     * Update thinking element with tool result info
     * @private
     */
    _updateThinkingToolResult(payload) {
        // Ensure thinking element exists
        if (!this._currentThinkingElement) {
            this.addThinkingMessage();
        }
        if (!this._currentThinkingElement) return;

        try {
            let toolResults = [];
            const existing = this._currentThinkingElement.getAttribute('tool-results');
            if (existing) {
                toolResults = JSON.parse(existing);
            }

            const existingIdx = toolResults.findIndex(t => t.call_id === payload.callId);
            const resultEntry = {
                call_id: payload.callId,
                tool_name: payload.name,
                success: payload.success,
                result: payload.result,
                error: payload.success === false ? payload.result || 'Tool execution failed' : null,
                execution_time_ms: payload.executionTimeMs || null,
            };

            if (existingIdx >= 0) {
                toolResults[existingIdx] = resultEntry;
            } else {
                toolResults.push(resultEntry);
            }

            this._currentThinkingElement.setAttribute('tool-results', JSON.stringify(toolResults));
        } catch (e) {
            console.warn('[MessageRenderer] Failed to update tool result:', e);
        }
    }

    /**
     * Complete thinking element
     * @private
     */
    _completeThinkingElement(content) {
        if (this._currentThinkingElement) {
            if (content) {
                this._currentThinkingElement.setAttribute('content', content);
            }
            this._currentThinkingElement.setAttribute('status', 'complete');
            this._currentThinkingElement = null;
        }
    }

    /**
     * Get current thinking element
     * @returns {HTMLElement|null}
     */
    getThinkingElement() {
        return this._currentThinkingElement;
    }

    // =========================================================================
    // Container Helpers
    // =========================================================================

    /**
     * Append element to messages container
     * @param {HTMLElement} element - Element to append
     */
    appendToContainer(element) {
        if (this._messagesContainer) {
            this._messagesContainer.appendChild(element);
        }
    }

    /**
     * Scroll messages container to bottom
     * @param {boolean} [smooth=true] - Use smooth scrolling
     */
    scrollMessagesToBottom(smooth = true) {
        scrollToBottom(this._messagesContainer, smooth);
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._messagesContainer = null;
        this._welcomeMessage = null;
        this._isAdminFn = null;
        this._currentThinkingElement = null;
        this._streamingContent.clear();
        this._initialized = false;
        console.log('[MessageRenderer] Destroyed');
    }

    /**
     * Check if renderer is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const messageRenderer = new MessageRenderer();
export default messageRenderer;
