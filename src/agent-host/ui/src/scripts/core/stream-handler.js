/**
 * Stream Handler
 * Handles SSE streaming for chat messages and event processing.
 *
 * This module handles streaming chat messages via api.sendMessage().
 */

import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { notifyTokenExpired } from './session-manager.js';
import { setStatus, showToolExecuting, hideToolExecuting, lockChatInput, unlockChatInput } from './ui-manager.js';
import { scrollToBottom, showClientActionWidget, hideClientActionWidget, appendToContainer, addThinkingMessage } from './message-renderer.js';

// =============================================================================
// State
// =============================================================================

let streamingState = {
    isStreaming: false,
    conversationId: null,
    definitionId: null, // Definition ID for agent definition context
    reader: null,
    thinkingElement: null,
    content: '',
    isSuspended: false,
    pendingAction: null,
    templateConfig: null, // Template configuration for the current conversation
    templateProgress: null, // Current progress in the template
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
 * @param {string} definitionId - Optional agent definition ID
 * @returns {Promise<void>}
 */
export async function sendMessage(message, conversationId, modelId, thinkingElement, definitionId = null) {
    setStatus('streaming', 'Streaming...');
    let assistantContent = '';

    // Track streaming state
    streamingState = {
        isStreaming: true,
        conversationId: conversationId,
        definitionId: definitionId,
        reader: null,
        thinkingElement: thinkingElement,
        content: '',
    };

    try {
        const response = await api.sendMessage(message, conversationId, modelId, definitionId);

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

        case 'proactive_start':
            // Agent is starting the conversation - update UI to show agent is preparing
            console.log('[StreamHandler] Proactive agent start - agent will speak first');
            thinkingElement.setAttribute('status', 'thinking');
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
            // Unlock chat input so user can respond to the agent
            unlockChatInput();
            console.log('[StreamHandler] Stream complete - chat input unlocked');
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

        case 'template_config':
            return handleTemplateConfig(data);

        case 'template_progress':
            return handleTemplateProgress(data);

        case 'template_complete':
            return handleTemplateComplete(data);

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

    // Support both formats:
    // 1. Legacy format: { action: { ... } }
    // 2. New template format: { action_type: "widget", widget_type: "...", ... }
    let action;
    if (data.action) {
        action = data.action;
    } else if (data.action_type === 'widget') {
        // Convert template format to widget action format
        action = {
            widget_type: data.widget_type,
            content_id: data.content_id,
            item_id: data.item_id,
            props: {
                prompt: data.stem,
                options: data.options,
                required: data.required,
                skippable: data.skippable,
                initial_value: data.initial_value,
                widget_config: data.widget_config,
            },
            // Mark as template-based action (not session-based tool call)
            isTemplateAction: true,
        };
    } else {
        console.error('[StreamHandler] Invalid client_action event format:', data);
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

    // For template actions, don't lock the chat input - the user can respond via chat
    if (!action.isTemplateAction) {
        lockChatInput();
    }

    // Show the widget in the message area
    showClientActionWidget(action, response => {
        handleWidgetResponse(response, action.isTemplateAction);
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

    // Unlock the chat input
    unlockChatInput();

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

// =============================================================================
// Template Event Handlers
// =============================================================================

/**
 * Handle template_config event - store template configuration and update UI
 * @param {Object} data - Template configuration data
 * @returns {null}
 */
function handleTemplateConfig(data) {
    console.log('[StreamHandler] Template config received:', data);

    // Store the template configuration
    streamingState.templateConfig = data;

    // Dispatch event for UI components to respond
    window.dispatchEvent(
        new CustomEvent('ax-template-config', {
            detail: {
                config: data,
                conversationId: streamingState.conversationId,
            },
        })
    );

    // Update sidebar visibility based on allow_navigation
    if (data.allow_navigation === false) {
        // Hide sidebar for this conversation
        window.dispatchEvent(new CustomEvent('ax-sidebar-visibility', { detail: { visible: false } }));
    }

    return null;
}

/**
 * Handle template_progress event - update progress indicator
 * @param {Object} data - Progress data (current_item, total_items, item_id, item_title, deadline, etc.)
 * @returns {null}
 */
function handleTemplateProgress(data) {
    console.log('[StreamHandler] Template progress:', data);

    // Store current progress
    streamingState.templateProgress = data;

    // Dispatch event for the conversation header component
    window.dispatchEvent(
        new CustomEvent('ax-template-progress', {
            detail: {
                currentItem: data.current_item,
                totalItems: data.total_items,
                itemId: data.item_id,
                itemTitle: data.item_title,
                enableChatInput: data.enable_chat_input,
                deadline: data.deadline,
                displayProgressIndicator: data.display_progress_indicator,
                allowBackwardNavigation: data.allow_backward_navigation,
                conversationId: streamingState.conversationId,
            },
        })
    );

    return null;
}

/**
 * Handle template_complete event - template conversation finished
 * @param {Object} data - Completion data (total_items, total_score, max_possible_score, continue_after_completion)
 * @returns {null}
 */
function handleTemplateComplete(data) {
    console.log('[StreamHandler] Template complete:', data);

    // Dispatch event for UI components
    window.dispatchEvent(
        new CustomEvent('ax-template-complete', {
            detail: {
                totalItems: data.total_items,
                totalScore: data.total_score,
                maxPossibleScore: data.max_possible_score,
                displayFinalScoreReport: data.display_final_score_report,
                continueAfterCompletion: data.continue_after_completion,
                conversationId: streamingState.conversationId,
            },
        })
    );

    // If continue_after_completion is false, disable chat input
    if (!data.continue_after_completion) {
        lockChatInput();
    }

    // Clear template state
    streamingState.templateConfig = null;
    streamingState.templateProgress = null;

    return null;
}

/**
 * Handle widget response from user
 * @param {Object} response - User's response from widget
 * @param {boolean} isTemplateAction - Whether this is a template-based action
 */
async function handleWidgetResponse(response, isTemplateAction = false) {
    console.log('[StreamHandler] Widget response:', response, 'isTemplateAction:', isTemplateAction);

    // Hide widget after user response
    hideClientActionWidget();

    if (isTemplateAction) {
        // For template actions, send the response as a regular chat message
        // The response object contains the selected option(s)
        let messageText;
        if (typeof response === 'string') {
            messageText = response;
        } else if (response.selected) {
            // Multiple choice response
            messageText = Array.isArray(response.selected) ? response.selected.join(', ') : response.selected;
        } else if (response.value !== undefined) {
            messageText = String(response.value);
        } else {
            messageText = JSON.stringify(response);
        }

        console.log('[StreamHandler] Sending template response as chat message:', messageText);

        // Dispatch a custom event that the app can listen for to send the message
        // This avoids circular dependencies and works with the existing app flow
        window.dispatchEvent(
            new CustomEvent('ax-send-message', {
                detail: { message: messageText },
            })
        );
        return;
    }

    // Session-based tool call response (legacy) - requires pendingAction
    const pendingAction = streamingState.pendingAction;
    if (!pendingAction) {
        console.error('[StreamHandler] No pending action for response');
        showToast('Error: No pending action', 'error');
        return;
    }

    const sessionId = streamingState.sessionId;
    if (!sessionId) {
        console.error('[StreamHandler] No session for response');
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
        unlockChatInput();
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
        definitionId: null,
        reader: null,
        thinkingElement: null,
        content: '',
        isSuspended: false,
        pendingAction: null,
        templateConfig: null,
        templateProgress: null,
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
 * Get the current definition ID
 * @returns {string|null}
 */
export function getDefinitionId() {
    return streamingState.definitionId;
}

/**
 * Get the pending client action
 * @returns {Object|null}
 */
export function getPendingAction() {
    return streamingState.pendingAction;
}
/**
 * Get the current template configuration
 * @returns {Object|null}
 */
export function getTemplateConfig() {
    return streamingState.templateConfig;
}

/**
 * Get the current template progress
 * @returns {Object|null}
 */
export function getTemplateProgress() {
    return streamingState.templateProgress;
}
