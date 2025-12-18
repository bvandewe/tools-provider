/**
 * WebSocket Handler
 * Handles bidirectional WebSocket communication for template-based conversations.
 *
 * This module provides a cleaner alternative to SSE for proactive agent flows,
 * where the server pushes content/widgets and receives user responses through
 * the same persistent connection.
 */

import { showToast } from '../services/modals.js';
import { setStatus, showToolExecuting, hideToolExecuting } from './ui-manager.js';
import { scrollToBottom, appendToContainer, addThinkingMessage, showClientActionWidget, hideClientActionWidget } from './message-renderer.js';

// =============================================================================
// State
// =============================================================================

let wsState = {
    socket: null,
    conversationId: null,
    definitionId: null,
    isConnected: false,
    isConnecting: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 1000,
    pingInterval: null,
    thinkingElement: null,
    currentContent: '',
    currentWidgetShowUserResponse: true, // Whether to show user's widget response as a bubble
};

// Callbacks
let callbacks = {
    onConnected: null,
    onMessage: null,
    onWidget: null,
    onProgress: null,
    onComplete: null,
    onError: null,
    onDisconnected: null,
};

// =============================================================================
// Configuration
// =============================================================================

/**
 * Set callbacks for WebSocket events
 * @param {Object} newCallbacks - Callback functions
 */
export function setWebSocketCallbacks(newCallbacks) {
    callbacks = { ...callbacks, ...newCallbacks };
}

// =============================================================================
// Connection Management
// =============================================================================

/**
 * Connect to the WebSocket chat endpoint
 * @param {Object} options - Connection options
 * @param {string} options.definitionId - Agent definition ID for new conversation
 * @param {string} options.conversationId - Existing conversation ID to continue
 * @returns {Promise<boolean>} True if connected successfully
 */
export async function connect(options = {}) {
    // Check if we need to reconnect to a different conversation
    const newConversationId = options.conversationId || null;
    const newDefinitionId = options.definitionId || null;

    if (wsState.isConnected) {
        // If connecting to a different conversation, disconnect first
        if (newConversationId && newConversationId !== wsState.conversationId) {
            console.log('[WebSocket] Switching conversation, disconnecting old connection');
            disconnect();
        } else if (!newConversationId && wsState.conversationId) {
            // New conversation with definition, disconnect old
            console.log('[WebSocket] Starting new conversation, disconnecting old connection');
            disconnect();
        } else {
            console.log('[WebSocket] Already connected to the same conversation');
            return true;
        }
    }

    if (wsState.isConnecting) {
        console.log('[WebSocket] Already connecting');
        return false;
    }

    wsState.isConnecting = true;
    wsState.definitionId = newDefinitionId;
    wsState.conversationId = newConversationId;

    try {
        // Build WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        let url = `${protocol}//${host}/api/chat/ws`;

        // Add query parameters
        const params = new URLSearchParams();
        if (options.definitionId) {
            params.set('definition_id', options.definitionId);
        }
        if (options.conversationId) {
            params.set('conversation_id', options.conversationId);
        }

        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }

        console.log('[WebSocket] Connecting to:', url);
        setStatus('connecting', 'Connecting...');

        return new Promise((resolve, reject) => {
            wsState.socket = new WebSocket(url);

            wsState.socket.onopen = () => {
                console.log('[WebSocket] Connected');
                wsState.isConnected = true;
                wsState.isConnecting = false;
                wsState.reconnectAttempts = 0;
                setStatus('connected', 'Connected');

                // Start ping interval to keep connection alive
                startPingInterval();

                resolve(true);
            };

            wsState.socket.onclose = event => {
                console.log('[WebSocket] Disconnected:', event.code, event.reason);
                wsState.isConnected = false;
                wsState.isConnecting = false;
                stopPingInterval();
                setStatus('disconnected', 'Disconnected');

                if (callbacks.onDisconnected) {
                    callbacks.onDisconnected(event);
                }

                // Attempt reconnection if not a clean close
                if (event.code !== 1000 && wsState.reconnectAttempts < wsState.maxReconnectAttempts) {
                    scheduleReconnect();
                }
            };

            wsState.socket.onerror = error => {
                console.error('[WebSocket] Error:', error);
                wsState.isConnecting = false;
                setStatus('error', 'Connection error');

                if (callbacks.onError) {
                    callbacks.onError({ message: 'WebSocket connection error' });
                }

                reject(error);
            };

            wsState.socket.onmessage = event => {
                handleMessage(event);
            };
        });
    } catch (error) {
        console.error('[WebSocket] Connection failed:', error);
        wsState.isConnecting = false;
        setStatus('error', 'Connection failed');
        throw error;
    }
}

/**
 * Disconnect from the WebSocket
 */
export function disconnect() {
    stopPingInterval();

    if (wsState.socket) {
        wsState.socket.close(1000, 'Client disconnect');
        wsState.socket = null;
    }

    wsState.isConnected = false;
    wsState.isConnecting = false;
    wsState.conversationId = null;
    wsState.definitionId = null;
    wsState.reconnectAttempts = 0;
}

/**
 * Check if WebSocket is connected
 * @returns {boolean}
 */
export function isConnected() {
    return wsState.isConnected && wsState.socket?.readyState === WebSocket.OPEN;
}

/**
 * Get the current conversation ID
 * @returns {string|null}
 */
export function getConversationId() {
    return wsState.conversationId;
}

// =============================================================================
// Sending Messages
// =============================================================================

/**
 * Start the template flow (proactive agent)
 */
export function startTemplate() {
    if (!isConnected()) {
        console.error('[WebSocket] Not connected');
        showToast('Not connected to server', 'error');
        return;
    }

    console.log('[WebSocket] Starting template flow');

    // Show thinking indicator
    wsState.thinkingElement = addThinkingMessage();
    wsState.currentContent = '';

    send({ type: 'start' });
}

/**
 * Send a user message or widget response
 * @param {string} content - The message content
 */
export function sendMessage(content) {
    if (!isConnected()) {
        console.error('[WebSocket] Not connected');
        showToast('Not connected to server', 'error');
        return;
    }

    if (!content || !content.trim()) {
        console.warn('[WebSocket] Empty message, ignoring');
        return;
    }

    console.log('[WebSocket] Sending message:', content);

    // Show thinking indicator
    wsState.thinkingElement = addThinkingMessage();
    wsState.currentContent = '';

    send({ type: 'message', content: content.trim() });
}

/**
 * Send a raw message to the WebSocket
 * @param {Object} data - Message data
 */
function send(data) {
    if (!wsState.socket || wsState.socket.readyState !== WebSocket.OPEN) {
        console.error('[WebSocket] Cannot send - not connected');
        return;
    }

    wsState.socket.send(JSON.stringify(data));
}

// =============================================================================
// Message Handling
// =============================================================================

/**
 * Handle incoming WebSocket message
 * @param {MessageEvent} event - WebSocket message event
 */
function handleMessage(event) {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (e) {
        console.error('[WebSocket] Invalid JSON:', event.data);
        return;
    }

    console.log('[WebSocket] Received:', data.type, data);

    switch (data.type) {
        case 'connected':
            handleConnected(data);
            break;

        case 'content':
            handleContent(data.data);
            break;

        case 'widget':
            handleWidget(data.data);
            break;

        case 'progress':
            handleProgress(data.data);
            break;

        case 'message_complete':
            handleMessageComplete(data.data);
            break;

        case 'complete':
            handleComplete(data.data);
            break;

        case 'message_added':
            // User message acknowledged - no action needed
            break;

        case 'template_config':
            handleTemplateConfig(data.data);
            break;

        case 'tool_call':
            handleToolCall(data.data);
            break;

        case 'tool_result':
            handleToolResult(data.data);
            break;

        case 'error':
            handleError(data);
            break;

        case 'pong':
            // Keepalive response - no action needed
            break;

        default:
            console.warn('[WebSocket] Unknown message type:', data.type);
    }
}

/**
 * Handle connected message
 * @param {Object} data - Connection data
 */
function handleConnected(data) {
    wsState.conversationId = data.conversation_id;
    console.log('[WebSocket] Session established, conversation:', wsState.conversationId);

    if (callbacks.onConnected) {
        callbacks.onConnected(data);
    }
}

/**
 * Handle content message (text streaming)
 * @param {Object} data - Content data
 */
function handleContent(data) {
    const content = data.content || '';
    wsState.currentContent += content;

    // Update thinking element with accumulated content
    if (wsState.thinkingElement) {
        wsState.thinkingElement.setAttribute('content', wsState.currentContent);
        wsState.thinkingElement.setAttribute('status', 'streaming');
    }

    scrollToBottom();

    if (callbacks.onMessage) {
        callbacks.onMessage(data);
    }
}

/**
 * Handle widget message (multiple choice, free text, etc.)
 * @param {Object} data - Widget data
 */
function handleWidget(data) {
    console.log('[WebSocket] Widget received:', data);

    // Remove or complete any thinking element
    if (wsState.thinkingElement) {
        if (wsState.currentContent) {
            // If there's content, mark as complete
            wsState.thinkingElement.setAttribute('content', wsState.currentContent);
            wsState.thinkingElement.setAttribute('status', 'complete');
        } else {
            // If no content, remove the empty thinking element entirely
            wsState.thinkingElement.remove();
        }
        wsState.thinkingElement = null;
        wsState.currentContent = '';
    }

    // Store the show_user_response flag for when widget response is handled
    // Default to true if not specified
    wsState.currentWidgetShowUserResponse = data.show_user_response !== false;

    // Convert to the format expected by showClientActionWidget
    const action = {
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
    };

    // Show the widget
    showClientActionWidget(action, response => {
        handleWidgetResponse(response);
    });

    scrollToBottom();

    if (callbacks.onWidget) {
        callbacks.onWidget(data);
    }
}

/**
 * Handle user's widget response
 * @param {Object} response - Widget response
 */
function handleWidgetResponse(response) {
    console.log('[WebSocket] Widget response:', response);

    // Hide widget
    hideClientActionWidget();

    // Extract message text from response
    let messageText;
    if (typeof response === 'string') {
        messageText = response;
    } else if (response.selected) {
        // Multiple choice response
        messageText = Array.isArray(response.selected) ? response.selected.join(', ') : response.selected;
    } else if (response.text) {
        // Free text response
        messageText = response.text;
    } else if (response.code) {
        // Code editor response
        messageText = response.code;
    } else if (response.value !== undefined) {
        messageText = String(response.value);
    } else {
        messageText = JSON.stringify(response);
    }

    // Add user message bubble only if show_user_response is true
    if (wsState.currentWidgetShowUserResponse) {
        const userBubble = document.createElement('ax-chat-message');
        userBubble.setAttribute('role', 'user');
        userBubble.setAttribute('content', messageText);
        appendToContainer(userBubble);
    }

    // Reset the flag
    wsState.currentWidgetShowUserResponse = true;

    // Send to server
    sendMessage(messageText);
}

/**
 * Handle template_config message
 * @param {Object} data - Template configuration data
 */
function handleTemplateConfig(data) {
    console.log('[WebSocket] Template config:', data);

    // Dispatch event for UI components (matching stream-handler pattern)
    window.dispatchEvent(
        new CustomEvent('ax-template-config', {
            detail: {
                title: data.title,
                totalItems: data.total_items,
                allowNavigation: data.allow_navigation,
                allowBackwardNavigation: data.allow_backward_navigation,
                displayProgressIndicator: data.display_progress_indicator,
                displayFinalScoreReport: data.display_final_score_report,
                continueAfterCompletion: data.continue_after_completion,
                conversationId: wsState.conversationId,
            },
        })
    );
}

/**
 * Handle progress update
 * @param {Object} data - Progress data
 */
function handleProgress(data) {
    console.log('[WebSocket] Progress:', data.current_item + 1, '/', data.total_items);

    // Dispatch event for the conversation header component (matching stream-handler pattern)
    window.dispatchEvent(
        new CustomEvent('ax-template-progress', {
            detail: {
                currentItem: data.current_item,
                totalItems: data.total_items,
                itemId: data.item_id,
                itemTitle: data.item_title,
                enableChatInput: data.enable_chat_input,
                displayProgressIndicator: data.display_progress_indicator,
                allowBackwardNavigation: data.allow_backward_navigation,
                conversationId: wsState.conversationId,
            },
        })
    );

    if (callbacks.onProgress) {
        callbacks.onProgress(data);
    }
}

/**
 * Handle message complete
 * @param {Object} data - Message data
 */
function handleMessageComplete(data) {
    // Mark thinking element as complete
    if (wsState.thinkingElement) {
        const content = data.content || wsState.currentContent;
        if (content) {
            wsState.thinkingElement.setAttribute('content', content);
        }
        wsState.thinkingElement.setAttribute('status', 'complete');
        wsState.thinkingElement = null;
        wsState.currentContent = '';
    }

    scrollToBottom();
}

/**
 * Handle template complete
 * @param {Object} data - Completion data
 */
function handleComplete(data) {
    console.log('[WebSocket] Template complete:', data);

    // Mark any thinking element as complete
    if (wsState.thinkingElement) {
        wsState.thinkingElement.setAttribute('status', 'complete');
        wsState.thinkingElement = null;
        wsState.currentContent = '';
    }

    setStatus('connected', 'Complete');

    // Dispatch event for UI components (matching stream-handler pattern)
    window.dispatchEvent(
        new CustomEvent('ax-template-complete', {
            detail: {
                totalItems: data.total_items,
                totalScore: data.total_score,
                maxPossibleScore: data.max_possible_score,
                displayFinalScoreReport: data.display_final_score_report,
                continueAfterCompletion: data.continue_after_completion,
                conversationId: wsState.conversationId,
            },
        })
    );

    if (callbacks.onComplete) {
        callbacks.onComplete(data);
    }
}

/**
 * Handle error message
 * @param {Object} data - Error data
 */
function handleError(data) {
    console.error('[WebSocket] Error:', data.message);

    // Mark thinking element as error
    if (wsState.thinkingElement) {
        wsState.thinkingElement.setAttribute('content', `Error: ${data.message}`);
        wsState.thinkingElement.setAttribute('status', 'error');
        wsState.thinkingElement = null;
        wsState.currentContent = '';
    }

    showToast(data.message || 'An error occurred', 'error');

    if (callbacks.onError) {
        callbacks.onError(data);
    }
}

/**
 * Handle tool call notification
 * @param {Object} data - Tool call data
 */
function handleToolCall(data) {
    console.log('[WebSocket] Tool call:', data.name);

    // Show tool executing indicator
    showToolExecuting(data.name);

    // Update thinking element status to show tool is being called
    if (wsState.thinkingElement) {
        wsState.thinkingElement.setAttribute('status', 'tool-calling');

        // Add tool call info to the thinking element
        try {
            let toolCalls = [];
            const existingCalls = wsState.thinkingElement.getAttribute('tool-calls');
            if (existingCalls) {
                toolCalls = JSON.parse(existingCalls);
            }
            toolCalls.push({
                name: data.name,
                status: data.status || 'calling',
            });
            wsState.thinkingElement.setAttribute('tool-calls', JSON.stringify(toolCalls));
        } catch (e) {
            console.warn('[WebSocket] Failed to update tool-calls attribute:', e);
        }
    }
}

/**
 * Handle tool result notification
 * @param {Object} data - Tool result data
 */
function handleToolResult(data) {
    console.log('[WebSocket] Tool result:', data.name, data.status);

    // Hide tool executing indicator
    hideToolExecuting();

    // Update thinking element with tool result
    if (wsState.thinkingElement) {
        wsState.thinkingElement.setAttribute('status', 'streaming');

        // Add tool result info to the thinking element
        try {
            let toolResults = [];
            const existingResults = wsState.thinkingElement.getAttribute('tool-results');
            if (existingResults) {
                toolResults = JSON.parse(existingResults);
            }
            toolResults.push({
                name: data.name,
                status: data.status || 'complete',
                success: data.success !== false,
            });
            wsState.thinkingElement.setAttribute('tool-results', JSON.stringify(toolResults));
        } catch (e) {
            console.warn('[WebSocket] Failed to update tool-results attribute:', e);
        }
    }
}

// =============================================================================
// Keepalive
// =============================================================================

/**
 * Start ping interval for keepalive
 */
function startPingInterval() {
    stopPingInterval();

    wsState.pingInterval = setInterval(() => {
        if (isConnected()) {
            send({ type: 'ping' });
        }
    }, 30000); // Ping every 30 seconds
}

/**
 * Stop ping interval
 */
function stopPingInterval() {
    if (wsState.pingInterval) {
        clearInterval(wsState.pingInterval);
        wsState.pingInterval = null;
    }
}

// =============================================================================
// Reconnection
// =============================================================================

/**
 * Schedule a reconnection attempt
 */
function scheduleReconnect() {
    wsState.reconnectAttempts++;
    const delay = wsState.reconnectDelay * Math.pow(2, wsState.reconnectAttempts - 1);

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${wsState.reconnectAttempts})`);
    setStatus('reconnecting', `Reconnecting (${wsState.reconnectAttempts})...`);

    setTimeout(() => {
        if (!wsState.isConnected && !wsState.isConnecting) {
            connect({
                definitionId: wsState.definitionId,
                conversationId: wsState.conversationId,
            }).catch(error => {
                console.error('[WebSocket] Reconnection failed:', error);
            });
        }
    }, delay);
}

// =============================================================================
// Exports
// =============================================================================

export default {
    connect,
    disconnect,
    isConnected,
    getConversationId,
    startTemplate,
    sendMessage,
    setWebSocketCallbacks,
};
