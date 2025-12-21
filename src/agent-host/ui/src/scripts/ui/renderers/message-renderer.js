/**
 * Message Renderer - DOM rendering for chat messages
 *
 * Handles rendering of user messages, assistant messages,
 * thinking indicators, and tool call cards.
 *
 * @module ui/renderers/message-renderer
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { scrollToBottom } from '../../utils/dom.js';
import { showToolDetailsModal } from '../../services/modals.js';
import { api } from '../../services/api.js';

// =============================================================================
// State
// =============================================================================

/** @type {HTMLElement|null} */
let messagesContainer = null;

/** @type {HTMLElement|null} */
let welcomeMessage = null;

/** @type {Function|null} */
let isAdminFn = null;

/** @type {HTMLElement|null} Current thinking element */
let currentThinkingElement = null;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize message renderer
 * @param {HTMLElement} container - Messages container element
 * @param {HTMLElement} welcome - Welcome message element
 * @param {Function} isAdmin - Function to check admin status
 */
export function initMessageRenderer(container, welcome, isAdmin) {
    messagesContainer = container;
    welcomeMessage = welcome;
    isAdminFn = isAdmin || (() => false);

    subscribeToEvents();

    console.log('[MessageRenderer] Initialized');
}

/**
 * Subscribe to event bus events
 */
function subscribeToEvents() {
    // NOTE: MESSAGE_STREAMING content updates are handled by ChatApp.appendStreamingContent()
    // which accumulates content properly. We only subscribe to events that don't conflict.

    // Handle message complete
    eventBus.on(Events.MESSAGE_COMPLETE, ({ content }) => {
        completeThinkingElement(content);
    });

    // Handle tool calls - include full payload for modal display
    eventBus.on(Events.TOOL_CALL_STARTED, payload => {
        updateThinkingToolCall(payload.name, 'calling', payload);
    });

    // Handle tool results - include full payload for modal display
    eventBus.on(Events.TOOL_CALL_COMPLETED, payload => {
        updateThinkingToolCall(payload.name, payload.status || 'completed', payload);
        updateThinkingToolResult(payload);
    });
}

// =============================================================================
// Message Rendering
// =============================================================================

/**
 * Clear all messages
 */
export function clearMessages() {
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }
    currentThinkingElement = null;
}

/**
 * Render messages from conversation history
 * @param {Array} messages - Message objects
 */
export function renderMessages(messages) {
    clearMessages();

    if (!messages || messages.length === 0) return;

    messages.forEach(msg => {
        if (msg.role === 'user') {
            addUserMessage(msg.content);
        } else if (msg.role === 'assistant') {
            addAssistantMessage(msg.content, msg.tool_calls);
        }
    });

    scrollToBottom(messagesContainer);
}

/**
 * Add a user message
 * @param {string} content - Message content
 * @returns {HTMLElement} Created element
 */
export function addUserMessage(content) {
    console.log('[MessageRenderer] addUserMessage called, content:', content);
    console.log('[MessageRenderer] messagesContainer:', messagesContainer);

    const message = document.createElement('chat-message');
    message.setAttribute('role', 'user');
    message.setAttribute('content', content);

    appendToContainer(message);
    scrollToBottom(messagesContainer);

    console.log('[MessageRenderer] User message appended:', message);
    return message;
}

/**
 * Add an assistant message
 * @param {string} content - Message content
 * @param {Array} [toolCalls] - Tool calls
 * @returns {HTMLElement} Created element
 */
export function addAssistantMessage(content, toolCalls) {
    console.log('[MessageRenderer] addAssistantMessage called, content:', content, 'toolCalls:', toolCalls);

    const message = document.createElement('chat-message');
    message.setAttribute('role', 'assistant');
    message.setAttribute('content', content || '');
    message.setAttribute('status', 'complete');

    if (toolCalls) {
        message.setAttribute('tool-calls', JSON.stringify(toolCalls));
    }

    appendToContainer(message);
    scrollToBottom(messagesContainer);

    console.log('[MessageRenderer] Assistant message appended:', message);
    return message;
}

/**
 * Add a thinking message (streaming placeholder)
 * @returns {HTMLElement} Created element
 */
export function addThinkingMessage() {
    console.log('[MessageRenderer] addThinkingMessage called');
    console.log('[MessageRenderer] messagesContainer:', messagesContainer);

    const message = document.createElement('chat-message');
    message.setAttribute('role', 'assistant');
    message.setAttribute('status', 'thinking');
    message.setAttribute('content', '');

    // Attach tool-badge-click listener so tool badges work during active streaming
    // This is needed because during streaming, tool-calls are set via setAttribute
    // and the ChatMessage component dispatches tool-badge-click events
    message.addEventListener('tool-badge-click', e => {
        showToolDetailsModal(e.detail.toolCalls, e.detail.toolResults, {
            isAdmin: isAdminFn ? isAdminFn() : false,
            fetchSourceInfo: async toolName => {
                return await api.getToolSourceInfo(toolName);
            },
        });
    });

    currentThinkingElement = message;
    appendToContainer(message);
    scrollToBottom(messagesContainer);

    console.log('[MessageRenderer] Thinking message appended:', message);
    return message;
}

/**
 * Update thinking element with content
 * @param {string} content - Content to display
 */
function updateThinkingContent(content) {
    if (currentThinkingElement) {
        currentThinkingElement.setAttribute('content', content);
        currentThinkingElement.setAttribute('status', 'streaming');
    }
}

/**
 * Update thinking element with tool call info
 * @param {string} toolName - Tool name
 * @param {string} status - Tool call status
 * @param {Object} [payload] - Full tool call payload for modal display
 */
function updateThinkingToolCall(toolName, status, payload = {}) {
    if (!currentThinkingElement) return;

    try {
        let toolCalls = [];
        const existing = currentThinkingElement.getAttribute('tool-calls');
        if (existing) {
            toolCalls = JSON.parse(existing);
        }

        // Update or add tool call
        // Use both 'name' and 'tool_name' for compatibility (renderToolBadges checks both)
        const existing_idx = toolCalls.findIndex(t => t.name === toolName || t.tool_name === toolName);
        if (existing_idx >= 0) {
            toolCalls[existing_idx].status = status;
            // Merge additional payload data (use snake_case for modal compatibility)
            if (payload.callId) toolCalls[existing_idx].call_id = payload.callId;
            if (payload.arguments) toolCalls[existing_idx].arguments = payload.arguments;
        } else {
            toolCalls.push({
                name: toolName,
                tool_name: toolName,
                status,
                call_id: payload.callId || null,
                arguments: payload.arguments || null,
            });
        }

        currentThinkingElement.setAttribute('tool-calls', JSON.stringify(toolCalls));
        currentThinkingElement.setAttribute('status', status === 'calling' ? 'tool-calling' : 'streaming');
    } catch (e) {
        console.warn('[MessageRenderer] Failed to update tool call:', e);
    }
}

/**
 * Update thinking element with tool result info
 * @param {Object} payload - Tool result payload
 */
function updateThinkingToolResult(payload) {
    if (!currentThinkingElement) return;

    try {
        let toolResults = [];
        const existing = currentThinkingElement.getAttribute('tool-results');
        if (existing) {
            toolResults = JSON.parse(existing);
        }

        // Add or update tool result
        // Use snake_case to match showToolDetailsModal expected format
        const existing_idx = toolResults.findIndex(t => t.call_id === payload.callId);
        const resultEntry = {
            call_id: payload.callId,
            tool_name: payload.name,
            success: payload.success,
            result: payload.result,
            error: payload.success === false ? payload.result || 'Tool execution failed' : null,
            execution_time_ms: payload.executionTimeMs || null,
        };

        if (existing_idx >= 0) {
            toolResults[existing_idx] = resultEntry;
        } else {
            toolResults.push(resultEntry);
        }

        currentThinkingElement.setAttribute('tool-results', JSON.stringify(toolResults));
    } catch (e) {
        console.warn('[MessageRenderer] Failed to update tool result:', e);
    }
}

/**
 * Complete thinking element
 * @param {string} [content] - Final content
 */
function completeThinkingElement(content) {
    if (currentThinkingElement) {
        if (content) {
            currentThinkingElement.setAttribute('content', content);
        }
        currentThinkingElement.setAttribute('status', 'complete');
        currentThinkingElement = null;
    }
}

/**
 * Get current thinking element
 * @returns {HTMLElement|null}
 */
export function getThinkingElement() {
    return currentThinkingElement;
}

// =============================================================================
// Container Helpers
// =============================================================================

/**
 * Append element to messages container
 * @param {HTMLElement} element - Element to append
 */
export function appendToContainer(element) {
    if (messagesContainer) {
        messagesContainer.appendChild(element);
    }
}

/**
 * Scroll messages container to bottom
 * @param {boolean} [smooth=true] - Use smooth scrolling
 */
export function scrollMessagesToBottom(smooth = true) {
    scrollToBottom(messagesContainer, smooth);
}

export default {
    initMessageRenderer,
    clearMessages,
    renderMessages,
    addUserMessage,
    addAssistantMessage,
    addThinkingMessage,
    getThinkingElement,
    appendToContainer,
    scrollMessagesToBottom,
};
