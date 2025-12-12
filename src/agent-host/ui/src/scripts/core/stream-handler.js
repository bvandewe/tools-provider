/**
 * Stream Handler
 * Handles SSE streaming for chat messages and event processing
 */

import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { notifyTokenExpired } from './session-manager.js';
import { setStatus, showToolExecuting, hideToolExecuting, lockChatInput, unlockChatInput } from './ui-manager.js';
import { scrollToBottom, showClientActionWidget, hideClientActionWidget } from './message-renderer.js';
import { getCurrentMode, SessionMode } from './session-mode-manager.js';

// =============================================================================
// State
// =============================================================================

let streamingState = {
    isStreaming: false,
    conversationId: null,
    sessionId: null,
    reader: null,
    thinkingElement: null,
    content: '',
    isSuspended: false,
    pendingAction: null,
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

        case 'client_action':
            return handleClientAction(data, thinkingElement);

        case 'run_suspended':
            return handleRunSuspended(data);

        case 'run_resumed':
            return handleRunResumed(data);

        case 'state':
            return handleStateEvent(data);

        case 'connected':
            // Session stream connected - informational, no action needed
            console.log('[StreamHandler] Session stream connected:', data.session_id);
            return null;

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

// =============================================================================
// Client Action Handlers (Proactive Agent)
// =============================================================================

/**
 * Handle client_action event - display widget for user interaction
 * @param {Object} data - Event data containing action details
 * @param {HTMLElement} thinkingElement - Thinking indicator element
 * @returns {null}
 */
function handleClientAction(data, thinkingElement) {
    console.log('[StreamHandler] Client action received:', data);

    const action = data.action;
    if (!action) {
        console.error('[StreamHandler] No action in client_action event');
        return null;
    }

    // Store session ID if provided
    if (data.session_id) {
        streamingState.sessionId = data.session_id;
    }

    // Store pending action
    streamingState.pendingAction = action;

    // Note: Tool calls are already added by tool_calls_detected event,
    // so we don't need to add them again here to avoid duplicates.

    // Lock the chat input while widget is active
    lockChatInput();

    // Show the widget in the message area
    showClientActionWidget(action, response => {
        handleWidgetResponse(response);
    });

    scrollToBottom();
    return null;
}

/**
 * Handle run_suspended event - agent is waiting for user input
 * @param {Object} data - Event data
 * @returns {null}
 */
function handleRunSuspended(data) {
    console.log('[StreamHandler] Run suspended:', data);

    streamingState.isSuspended = true;

    if (data.session_id) {
        streamingState.sessionId = data.session_id;
    }

    // Update thinking element to waiting state
    if (streamingState.thinkingElement) {
        streamingState.thinkingElement.setAttribute('status', 'waiting');
    }

    setStatus('suspended', 'Waiting for input');
    return null;
}

/**
 * Handle run_resumed event - agent resumed after user response
 * @param {Object} data - Event data
 * @returns {null}
 */
function handleRunResumed(data) {
    console.log('[StreamHandler] Run resumed:', data);

    streamingState.isSuspended = false;
    streamingState.pendingAction = null;

    // Restore thinking element to streaming state
    if (streamingState.thinkingElement) {
        streamingState.thinkingElement.setAttribute('status', 'thinking');
    }

    // Hide widget
    hideClientActionWidget();

    // In validation mode, keep input locked with a waiting message
    // In other modes, unlock the input
    if (getCurrentMode() === SessionMode.VALIDATION) {
        lockChatInput('Processing... Please wait for the next question.');
    } else {
        unlockChatInput();
    }

    setStatus('streaming', 'Streaming...');
    return null;
}

/**
 * Handle state event - session state update
 * @param {Object} data - State data
 * @returns {null}
 */
function handleStateEvent(data) {
    console.log('[StreamHandler] State update:', data);

    // If there's a pending action in the state, show it
    if (data.pending_action) {
        streamingState.pendingAction = data.pending_action;
        streamingState.isSuspended = true;

        lockChatInput();
        showClientActionWidget(data.pending_action, response => {
            handleWidgetResponse(response);
        });
    }

    return null;
}

/**
 * Handle widget response from user
 * @param {Object} response - User's response from widget
 */
async function handleWidgetResponse(response) {
    console.log('[StreamHandler] Widget response:', response);

    const sessionId = streamingState.sessionId;
    const pendingAction = streamingState.pendingAction;

    if (!sessionId || !pendingAction) {
        console.error('[StreamHandler] No session or pending action for response');
        showToast('Error: No active session', 'error');
        return;
    }

    try {
        // Submit response to server
        const clientResponse = {
            tool_call_id: pendingAction.tool_call_id,
            response: response,
            timestamp: new Date().toISOString(),
        };

        await api.submitSessionResponse(sessionId, clientResponse);

        // Hide widget after successful submission
        hideClientActionWidget();

        // In validation mode, keep input locked until next question
        // In other modes, unlock the input
        if (getCurrentMode() === SessionMode.VALIDATION) {
            lockChatInput('Processing... Please wait for the next question.');
        } else {
            unlockChatInput();
        }
    } catch (error) {
        console.error('[StreamHandler] Failed to submit response:', error);
        showToast('Failed to submit response. Please try again.', 'error');
    }
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
        sessionId: null,
        reader: null,
        thinkingElement: null,
        content: '',
        isSuspended: false,
        pendingAction: null,
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

/**
 * Check if the stream is currently suspended waiting for user input
 * @returns {boolean}
 */
export function isSuspended() {
    return streamingState.isSuspended;
}

/**
 * Get the current session ID
 * @returns {string|null}
 */
export function getSessionId() {
    return streamingState.sessionId;
}

/**
 * Get the pending client action
 * @returns {Object|null}
 */
export function getPendingAction() {
    return streamingState.pendingAction;
}

// =============================================================================
// Session Stream Connection
// =============================================================================

/**
 * Connect to a session's SSE stream
 * @param {string} sessionId - Session ID to connect to
 * @param {HTMLElement} messagesContainer - Container for messages
 * @returns {Promise<void>}
 */
export async function connectToSessionStream(sessionId, messagesContainer) {
    setStatus('connecting', 'Connecting to session...');

    // Create a thinking element for the session
    const thinkingElement = document.createElement('chat-message');
    thinkingElement.setAttribute('role', 'assistant');
    thinkingElement.setAttribute('status', 'thinking');
    thinkingElement.setAttribute('content', '');
    messagesContainer.appendChild(thinkingElement);

    streamingState = {
        isStreaming: true,
        conversationId: null,
        sessionId: sessionId,
        reader: null,
        thinkingElement: thinkingElement,
        content: '',
        isSuspended: false,
        pendingAction: null,
    };

    try {
        const response = await api.connectSessionStream(sessionId);

        if (!response.ok) {
            throw new Error(`Failed to connect to session stream: ${response.status}`);
        }

        const reader = response.body.getReader();
        streamingState.reader = reader;
        const decoder = new TextDecoder();
        let currentEventType = '';
        let assistantContent = '';

        setStatus('streaming', 'Session active');

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
                        console.error('Error parsing session SSE data:', e, line);
                    }
                }
            }
        }

        setStatus('connected', 'Session complete');
        hideToolExecuting();

        if (onStreamComplete) {
            onStreamComplete();
        }
    } catch (error) {
        console.error('[StreamHandler] Session stream error:', error);
        handleStreamError(error, thinkingElement, streamingState.content);
    }
}

/**
 * Disconnect from the current session stream
 */
export function disconnectSessionStream() {
    if (streamingState.reader) {
        streamingState.reader.cancel();
    }
    resetStreamingState();
    setStatus('connected', 'Disconnected from session');
}
