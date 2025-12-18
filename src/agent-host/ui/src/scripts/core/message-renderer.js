/**
 * Message Renderer
 * Handles rendering chat messages and merging tool results
 */

import { showToolDetailsModal } from '../services/modals.js';
import { api } from '../services/api.js';

// =============================================================================
// State
// =============================================================================

let messagesContainer = null;
let welcomeMessage = null;
let isAdminFn = () => false;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize message renderer
 * @param {HTMLElement} container - Messages container element
 * @param {HTMLElement} welcome - Welcome message element
 * @param {Function} isAdmin - Function to check if user is admin
 */
export function initMessageRenderer(container, welcome, isAdmin) {
    messagesContainer = container;
    welcomeMessage = welcome;
    isAdminFn = isAdmin;
}

// =============================================================================
// Message Rendering
// =============================================================================

/**
 * Render messages in the container
 * @param {Array} messages - Array of message objects
 */
export function renderMessages(messages) {
    if (!messagesContainer) return;

    messagesContainer.innerHTML = '';
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    // Pre-process messages to merge tool_results from empty-content assistant messages
    const processedMessages = mergeToolResultsIntoContentMessages(messages);

    processedMessages.forEach(msg => {
        if (msg.role === 'system') return; // Don't show system messages

        const messageEl = createMessageElement(msg);
        messagesContainer.appendChild(messageEl);
    });

    scrollToBottom(true); // Force scroll when loading conversation
}

/**
 * Create a chat message element
 * @param {Object} msg - Message object
 * @returns {HTMLElement} Message element
 */
function createMessageElement(msg) {
    const messageEl = document.createElement('chat-message');
    messageEl.setAttribute('role', msg.role);
    messageEl.setAttribute('content', msg.content);

    // Add created_at timestamp if present
    if (msg.created_at) {
        messageEl.setAttribute('created-at', msg.created_at);
    }

    // Add tool calls data if present (for assistant messages)
    if (msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0) {
        messageEl.setAttribute('tool-calls', JSON.stringify(msg.tool_calls));
    }

    // Add tool results data if present (for assistant messages with executed tools)
    if (msg.role === 'assistant' && msg.tool_results && msg.tool_results.length > 0) {
        messageEl.setAttribute('tool-results', JSON.stringify(msg.tool_results));
    }

    // Listen for tool badge clicks
    messageEl.addEventListener('tool-badge-click', e => {
        showToolDetailsModal(e.detail.toolCalls, e.detail.toolResults, {
            isAdmin: isAdminFn(),
            fetchSourceInfo: async toolName => {
                return await api.getToolSourceInfo(toolName);
            },
        });
    });

    return messageEl;
}

/**
 * Add a user message to the container
 * @param {string} content - Message content
 */
export function addUserMessage(content) {
    const userMsg = document.createElement('chat-message');
    userMsg.setAttribute('role', 'user');
    userMsg.setAttribute('content', content);
    messagesContainer?.appendChild(userMsg);
    scrollToBottom(true);
}

/**
 * Create and add a thinking indicator message
 * @returns {HTMLElement} The thinking element for later updates
 */
export function addThinkingMessage() {
    const thinkingMsg = document.createElement('chat-message');
    thinkingMsg.setAttribute('role', 'assistant');
    thinkingMsg.setAttribute('status', 'thinking');

    // Attach tool-badge-click listener so tool badges work during active streaming
    // This is needed because during streaming, tool-calls are set via setAttribute
    // and the ChatMessage component dispatches tool-badge-click events
    thinkingMsg.addEventListener('tool-badge-click', e => {
        showToolDetailsModal(e.detail.toolCalls, e.detail.toolResults, {
            isAdmin: isAdminFn(),
            fetchSourceInfo: async toolName => {
                return await api.getToolSourceInfo(toolName);
            },
        });
    });

    messagesContainer?.appendChild(thinkingMsg);
    scrollToBottom(true);
    return thinkingMsg;
}

/**
 * Clear all messages from container
 */
export function clearMessages() {
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }
}

/**
 * Append an element to the messages container
 * @param {HTMLElement} element - Element to append
 */
export function appendToContainer(element) {
    messagesContainer?.appendChild(element);
}

/**
 * Get the messages container element
 * @returns {HTMLElement|null} The messages container
 */
export function getMessagesContainer() {
    return messagesContainer;
}

// =============================================================================
// Tool Result Merging
// =============================================================================

/**
 * Merge tool_results from empty-content assistant messages into the next assistant message with content.
 * This handles the case where tool execution creates a message with empty content but tool_results,
 * followed by another message with the actual response content.
 * @param {Array} messages - Array of message objects from the API
 * @returns {Array} - Processed messages with tool_results merged appropriately
 */
function mergeToolResultsIntoContentMessages(messages) {
    const result = [];
    let pendingToolResults = [];
    let pendingToolCalls = [];

    for (let i = 0; i < messages.length; i++) {
        const msg = messages[i];

        // Skip system messages
        if (msg.role === 'system') {
            result.push(msg);
            continue;
        }

        // Check if this is an assistant message with tool_results but empty/no content
        if (msg.role === 'assistant' && (!msg.content || msg.content.trim() === '')) {
            // Collect tool_results and tool_calls from this empty message
            if (msg.tool_results && msg.tool_results.length > 0) {
                pendingToolResults = pendingToolResults.concat(msg.tool_results);
            }
            if (msg.tool_calls && msg.tool_calls.length > 0) {
                pendingToolCalls = pendingToolCalls.concat(msg.tool_calls);
            }
            // Skip adding this empty message to results
            continue;
        }

        // If this is an assistant message with content, merge any pending tool data
        if (msg.role === 'assistant' && msg.content && msg.content.trim() !== '') {
            const mergedMsg = { ...msg };

            // Merge pending tool_results
            if (pendingToolResults.length > 0) {
                mergedMsg.tool_results = pendingToolResults.concat(msg.tool_results || []);
                pendingToolResults = [];
            }

            // Merge pending tool_calls
            if (pendingToolCalls.length > 0) {
                mergedMsg.tool_calls = pendingToolCalls.concat(msg.tool_calls || []);
                pendingToolCalls = [];
            }

            result.push(mergedMsg);
        } else {
            // User message or other - just add it
            result.push(msg);
        }
    }

    // If there are still pending tool results (edge case - tool results at end with no follow-up),
    // create a message for them
    if (pendingToolResults.length > 0 || pendingToolCalls.length > 0) {
        result.push({
            role: 'assistant',
            content: '',
            tool_results: pendingToolResults,
            tool_calls: pendingToolCalls,
        });
    }

    return result;
}

// =============================================================================
// Scrolling
// =============================================================================

let userHasScrolled = false;

/**
 * Handle user scroll event - track if user has manually scrolled up
 * @param {boolean} isStreaming - Whether currently streaming
 */
export function handleUserScroll(isStreaming) {
    if (!messagesContainer) return;

    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    // If user scrolls up during streaming, stop auto-scroll
    if (isStreaming && !isAtBottom) {
        userHasScrolled = true;
    }

    // If user scrolls back to bottom, resume auto-scroll
    if (isAtBottom) {
        userHasScrolled = false;
    }
}

/**
 * Reset user scroll tracking
 */
export function resetUserScroll() {
    userHasScrolled = false;
}

/**
 * Scroll to bottom of messages container
 * @param {boolean} force - Force scroll even if user has scrolled up
 */
export function scrollToBottom(force = false) {
    if (!messagesContainer) return;

    // Don't auto-scroll if user has manually scrolled up (unless forced)
    if (!force && userHasScrolled) return;

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// =============================================================================
// Client Action Widget Rendering
// =============================================================================

let currentWidgetContainer = null;
let currentResponseCallback = null;

/**
 * Show a client action widget
 * @param {Object} action - Client action data
 * @param {string} action.tool_name - Name of the client tool
 * @param {string} action.widget_type - Type of widget (multiple_choice, free_text, code_editor)
 * @param {Object} action.props - Widget properties
 * @param {Function} onResponse - Callback when user responds
 */
export function showClientActionWidget(action, onResponse) {
    if (!messagesContainer) return;

    // Remove any existing widget
    hideClientActionWidget();

    currentResponseCallback = onResponse;

    // Create widget container
    currentWidgetContainer = document.createElement('div');
    currentWidgetContainer.className = 'client-action-widget';
    currentWidgetContainer.setAttribute('data-tool-call-id', action.tool_call_id || '');

    // Create the appropriate widget based on type
    const widgetType = action.widget_type || guessWidgetType(action.tool_name);
    const widget = createWidget(widgetType, action.props);

    if (widget) {
        currentWidgetContainer.appendChild(widget);
        messagesContainer.appendChild(currentWidgetContainer);
        scrollToBottom(true);
    } else {
        console.error('[MessageRenderer] Unknown widget type:', widgetType);
    }
}

/**
 * Hide the current client action widget
 */
export function hideClientActionWidget() {
    if (currentWidgetContainer) {
        currentWidgetContainer.remove();
        currentWidgetContainer = null;
    }
    currentResponseCallback = null;
}

/**
 * Guess widget type from tool name
 * @param {string} toolName - Tool name
 * @returns {string} Widget type
 */
function guessWidgetType(toolName) {
    switch (toolName) {
        case 'present_choices':
            return 'multiple_choice';
        case 'request_free_text':
            return 'free_text';
        case 'present_code_editor':
            return 'code_editor';
        default:
            return 'unknown';
    }
}

/**
 * Create a widget element based on type
 * @param {string} widgetType - Widget type
 * @param {Object} props - Widget properties
 * @returns {HTMLElement|null} Widget element
 */
function createWidget(widgetType, props) {
    switch (widgetType) {
        case 'multiple_choice':
            return createMultipleChoiceWidget(props);
        case 'free_text':
            return createFreeTextWidget(props);
        case 'code_editor':
            return createCodeEditorWidget(props);
        default:
            return null;
    }
}

/**
 * Create multiple choice widget
 * @param {Object} props - Widget props
 * @returns {HTMLElement}
 */
function createMultipleChoiceWidget(props) {
    const widget = document.createElement('ax-multiple-choice');
    widget.setAttribute('prompt', props.prompt || '');
    widget.setAttribute('options', JSON.stringify(props.options || []));

    if (props.allow_multiple) {
        widget.setAttribute('allow-multiple', 'true');
    }

    widget.addEventListener('ax-response', e => {
        if (currentResponseCallback) {
            currentResponseCallback(e.detail);
        }
    });

    return widget;
}

/**
 * Create free text widget
 * @param {Object} props - Widget props
 * @returns {HTMLElement}
 */
function createFreeTextWidget(props) {
    const widget = document.createElement('ax-free-text-prompt');
    widget.setAttribute('prompt', props.prompt || '');

    if (props.placeholder) {
        widget.setAttribute('placeholder', props.placeholder);
    }
    if (props.min_length !== undefined) {
        widget.setAttribute('min-length', props.min_length);
    }
    if (props.max_length !== undefined) {
        widget.setAttribute('max-length', props.max_length);
    }
    if (props.multiline) {
        widget.setAttribute('multiline', 'true');
    }

    widget.addEventListener('ax-response', e => {
        if (currentResponseCallback) {
            currentResponseCallback(e.detail);
        }
    });

    return widget;
}

/**
 * Create code editor widget
 * @param {Object} props - Widget props
 * @returns {HTMLElement}
 */
function createCodeEditorWidget(props) {
    const widget = document.createElement('ax-code-editor');
    widget.setAttribute('prompt', props.prompt || '');

    if (props.language) {
        widget.setAttribute('language', props.language);
    }
    if (props.initial_code) {
        widget.setAttribute('initial-code', props.initial_code);
    }
    if (props.min_lines !== undefined) {
        widget.setAttribute('min-lines', props.min_lines);
    }
    if (props.max_lines !== undefined) {
        widget.setAttribute('max-lines', props.max_lines);
    }

    widget.addEventListener('ax-response', e => {
        if (currentResponseCallback) {
            currentResponseCallback(e.detail);
        }
    });

    return widget;
}
