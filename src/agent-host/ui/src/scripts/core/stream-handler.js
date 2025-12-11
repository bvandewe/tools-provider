/**
 * Stream Handler
 * Handles SSE streaming for chat messages and event processing
 */

import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { notifyTokenExpired } from './session-manager.js';
import { setStatus, showToolExecuting, hideToolExecuting } from './ui-manager.js';
import { scrollToBottom } from './message-renderer.js';

// =============================================================================
// State
// =============================================================================

let streamingState = {
    isStreaming: false,
    conversationId: null,
    reader: null,
    thinkingElement: null,
    content: '',
};

// Callbacks
let onConversationCreated = null;
let onStreamComplete = null;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Set callbacks for stream events
 * @param {Object} callbacks - Callback functions
 */
export function setStreamCallbacks(callbacks) {
    onConversationCreated = callbacks.onConversationCreated || null;
    onStreamComplete = callbacks.onStreamComplete || null;
}

// =============================================================================
// Streaming
// =============================================================================

/**
 * Send a message and handle the streaming response
 * @param {string} message - Message to send
 * @param {string} conversationId - Current conversation ID
 * @param {string} modelId - Selected model ID
 * @param {HTMLElement} thinkingElement - Thinking indicator element
 * @returns {Promise<void>}
 */
export async function sendMessage(message, conversationId, modelId, thinkingElement) {
    setStatus('streaming', 'Streaming...');
    let assistantContent = '';

    // Track streaming state
    streamingState = {
        isStreaming: true,
        conversationId: conversationId,
        reader: null,
        thinkingElement: thinkingElement,
        content: '',
    };

    try {
        const response = await api.sendMessage(message, conversationId, modelId);

        const reader = response.body.getReader();
        streamingState.reader = reader;
        const decoder = new TextDecoder();
        let currentEventType = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split('\n');

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEventType = line.slice(7).trim();
                } else if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        const result = handleStreamEvent(currentEventType, data, thinkingElement, assistantContent);

                        if (result && result.content !== undefined) {
                            assistantContent = result.content;
                            streamingState.content = assistantContent;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e, line);
                    }
                }
            }
        }

        setStatus('connected', 'Connected');
        hideToolExecuting();

        if (onStreamComplete) {
            onStreamComplete();
        }
    } catch (error) {
        handleStreamError(error, thinkingElement, assistantContent);
    }
}

/**
 * Handle SSE stream events
 * @param {string} eventType - Type of event
 * @param {Object} data - Event data
 * @param {HTMLElement} thinkingElement - Thinking indicator element
 * @param {string} currentContent - Current accumulated content
 * @returns {Object|null} Updated content or null
 */
function handleStreamEvent(eventType, data, thinkingElement, currentContent) {
    switch (eventType) {
        case 'stream_started':
            if (data.request_id) {
                api.setCurrentRequestId(data.request_id);
            }
            // Capture conversation_id if this is a new conversation
            if (data.conversation_id && data.conversation_id !== streamingState.conversationId) {
                streamingState.conversationId = data.conversation_id;
                if (onConversationCreated) {
                    onConversationCreated(data.conversation_id);
                }
            }
            return null;

        case 'assistant_thinking':
            return null;

        case 'content_chunk':
            const newContent = currentContent + (data.content || '');
            thinkingElement.setAttribute('content', newContent);
            thinkingElement.setAttribute('status', 'complete');
            scrollToBottom();
            return { content: newContent };

        case 'tool_calls_detected':
            if (data.tool_calls) {
                thinkingElement.setAttribute('tool-calls', JSON.stringify(data.tool_calls));
            }
            return null;

        case 'tool_executing':
            showToolExecuting(data.tool_name);
            return null;

        case 'tool_result':
            hideToolExecuting();
            let toolResults = [];
            try {
                const existingResults = thinkingElement.getAttribute('tool-results');
                if (existingResults) {
                    toolResults = JSON.parse(existingResults);
                }
            } catch (e) {
                toolResults = [];
            }
            toolResults.push({
                call_id: data.call_id,
                tool_name: data.tool_name,
                success: data.success,
                result: data.result,
                error: data.error,
                execution_time_ms: data.execution_time_ms,
            });
            thinkingElement.setAttribute('tool-results', JSON.stringify(toolResults));
            return null;

        case 'message_complete':
            thinkingElement.setAttribute('content', data.content || currentContent);
            thinkingElement.setAttribute('status', 'complete');
            hideToolExecuting();
            return { content: data.content || currentContent };

        case 'message_added':
            return null;

        case 'stream_complete':
            resetStreamingState();
            hideToolExecuting();
            return null;

        case 'cancelled':
            thinkingElement.setAttribute('content', currentContent || '_Response cancelled_');
            thinkingElement.setAttribute('status', 'complete');
            hideToolExecuting();
            resetStreamingState();
            return null;

        case 'error':
            return handleStreamErrorEvent(data, thinkingElement, currentContent);

        default:
            console.log('Unknown SSE event type:', eventType, data);
            return null;
    }
}

/**
 * Handle error events from the stream
 * @param {Object} data - Error data
 * @param {HTMLElement} thinkingElement - Thinking indicator element
 * @param {string} currentContent - Current content
 * @returns {null}
 */
function handleStreamErrorEvent(data, thinkingElement, currentContent) {
    const errorMsg = data.error || 'An unknown error occurred';
    const errorCode = data.error_code;

    // Handle authentication errors from the stream
    if (errorCode === 'unauthorized' || errorCode === 'session_expired') {
        console.log('[StreamHandler] Auth error in stream:', errorCode);
        thinkingElement.setAttribute('content', currentContent || '_Session expired_');
        thinkingElement.setAttribute('status', 'complete');
        notifyTokenExpired();
        return null;
    }

    // Show appropriate toast based on error code
    if (errorCode === 'ollama_unavailable') {
        showToast('AI model service is unavailable. Check the health status.', 'error');
    } else if (errorCode === 'model_not_found') {
        showToast(`Model not found: ${errorMsg}`, 'error');
    } else if (errorCode === 'ollama_timeout') {
        showToast('AI model request timed out. Please try again.', 'warning');
    } else if (errorCode === 'connection_error') {
        showToast('Cannot connect to AI service. Check your connection.', 'error');
    } else if (errorCode === 'timeout') {
        showToast('Request timed out. The AI model may be busy.', 'warning');
    } else {
        showToast(`Error: ${errorMsg}`, 'error');
    }

    thinkingElement.setAttribute('content', `_Error: ${errorMsg}_`);
    thinkingElement.setAttribute('status', 'complete');
    resetStreamingState();
    return null;
}

/**
 * Handle stream errors (exceptions)
 * @param {Error} error - The error
 * @param {HTMLElement} thinkingElement - Thinking indicator element
 * @param {string} assistantContent - Current content
 */
function handleStreamError(error, thinkingElement, assistantContent) {
    // Always reset streaming state on any error
    resetStreamingState();

    if (error.name === 'AbortError') {
        thinkingElement.setAttribute('content', assistantContent || '_Response cancelled_');
        thinkingElement.setAttribute('status', 'complete');
        setStatus('connected', 'Cancelled');
    } else if (error.message?.includes('Rate limit')) {
        showToast(error.message, 'error');
        thinkingElement.remove();
        setStatus('disconnected', 'Rate limited');
    } else if (error.message?.includes('Session expired') || error.message?.includes('401')) {
        console.log('[StreamHandler] Session expired during streaming');
        thinkingElement.setAttribute('content', assistantContent || '_Session expired during response_');
        thinkingElement.setAttribute('status', 'complete');
        setStatus('disconnected', 'Session expired');
        notifyTokenExpired();
    } else {
        console.error('Send message failed:', error);
        thinkingElement.setAttribute('content', 'Sorry, an error occurred. Please try again.');
        thinkingElement.setAttribute('status', 'complete');
        setStatus('disconnected', 'Error');
    }
}

// =============================================================================
// State Management
// =============================================================================

/**
 * Reset streaming state
 */
function resetStreamingState() {
    streamingState = {
        isStreaming: false,
        conversationId: null,
        reader: null,
        thinkingElement: null,
        content: '',
    };
}

/**
 * Check if currently streaming
 * @returns {boolean}
 */
export function isStreaming() {
    return streamingState.isStreaming;
}

/**
 * Get current streaming conversation ID
 * @returns {string|null}
 */
export function getStreamingConversationId() {
    return streamingState.conversationId;
}

/**
 * Get streaming thinking element
 * @returns {HTMLElement|null}
 */
export function getStreamingThinkingElement() {
    return streamingState.thinkingElement;
}

/**
 * Get accumulated streaming content
 * @returns {string}
 */
export function getStreamingContent() {
    return streamingState.content;
}

/**
 * Cancel the current streaming request
 */
export async function cancelCurrentRequest() {
    if (!streamingState.isStreaming) return;

    try {
        await api.cancelCurrentRequest();
        showToast('Request cancelled', 'info');
    } catch (error) {
        console.error('Failed to cancel request:', error);
    }
}
