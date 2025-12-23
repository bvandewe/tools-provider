/**
 * WebSocket Client - Connection Management
 *
 * Handles WebSocket connection lifecycle: connect, disconnect, reconnect.
 * Delegates message handling to message-router.
 *
 * @module protocol/websocket-client
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

// =============================================================================
// Configuration
// =============================================================================

const WS_CONFIG = {
    maxReconnectAttempts: 5,
    reconnectDelay: 1000, // Base delay in ms
    pingInterval: 30000, // 30 seconds
};

// =============================================================================
// State
// =============================================================================

/**
 * @typedef {Object} WebSocketState
 * @property {WebSocket|null} socket - WebSocket instance
 * @property {string|null} conversationId - Current conversation ID
 * @property {string|null} definitionId - Current definition ID
 * @property {boolean} isConnected - Connection status
 * @property {boolean} isConnecting - Connecting status
 * @property {number} reconnectAttempts - Current reconnect attempt count
 * @property {number|null} pingInterval - Ping interval ID
 */

/** @type {WebSocketState} */
const state = {
    socket: null,
    conversationId: null,
    definitionId: null,
    isConnected: false,
    isConnecting: false,
    reconnectAttempts: 0,
    pingInterval: null,
};

/** @type {Function|null} */
let messageHandler = null;

// =============================================================================
// Public API
// =============================================================================

/**
 * Set the message handler for incoming WebSocket messages
 * @param {Function} handler - Message handler function
 */
export function setMessageHandler(handler) {
    messageHandler = handler;
}

/**
 * Connect to WebSocket endpoint
 * @param {Object} options - Connection options
 * @param {string} [options.definitionId] - Agent definition ID
 * @param {string} [options.conversationId] - Existing conversation ID
 * @returns {Promise<boolean>} Connection success
 */
export async function connect(options = {}) {
    const { definitionId, conversationId } = options;

    // Check if already connected to same conversation
    if (state.isConnected && state.socket?.readyState === WebSocket.OPEN) {
        if (conversationId && conversationId === state.conversationId) {
            console.log('[WS] Already connected to same conversation');
            return true;
        }
        // Different conversation - disconnect first
        console.log('[WS] Switching conversation, disconnecting...');
        disconnect();
    }

    if (state.isConnecting) {
        console.log('[WS] Already connecting...');
        return false;
    }

    state.isConnecting = true;
    state.definitionId = definitionId || null;
    state.conversationId = conversationId || null;

    try {
        const url = buildWebSocketUrl(options);
        console.log('[WS] Connecting to:', url);

        updateStatus('connecting', 'Connecting...');

        return new Promise((resolve, reject) => {
            state.socket = new WebSocket(url);

            state.socket.onopen = () => handleOpen(resolve);
            state.socket.onclose = event => handleClose(event);
            state.socket.onerror = error => handleError(error, reject);
            state.socket.onmessage = event => handleMessage(event);
        });
    } catch (error) {
        console.error('[WS] Connection failed:', error);
        state.isConnecting = false;
        updateStatus('error', 'Connection failed');
        throw error;
    }
}

/**
 * Disconnect from WebSocket
 */
export function disconnect() {
    stopPingInterval();

    if (state.socket) {
        state.socket.close(1000, 'Client disconnect');
        state.socket = null;
    }

    state.isConnected = false;
    state.isConnecting = false;
    state.conversationId = null;
    state.definitionId = null;
    state.reconnectAttempts = 0;

    stateManager.set(StateKeys.WS_CONNECTED, false);
    stateManager.set(StateKeys.WS_CONVERSATION_ID, null);
}

/**
 * Check if WebSocket is connected
 * @returns {boolean} Connection status
 */
export function isConnected() {
    return state.isConnected && state.socket?.readyState === WebSocket.OPEN;
}

/**
 * Get current conversation ID
 * @returns {string|null} Conversation ID
 */
export function getConversationId() {
    return state.conversationId;
}

/**
 * Generate a unique message ID
 * @returns {string} UUID v4
 */
function generateMessageId() {
    return crypto.randomUUID
        ? crypto.randomUUID()
        : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
              const r = (Math.random() * 16) | 0;
              const v = c === 'x' ? r : (r & 0x3) | 0x8;
              return v.toString(16);
          });
}

/**
 * Create a CloudEvent-style protocol message envelope
 * @param {string} type - Message type (e.g., 'system.ping', 'data.message.send')
 * @param {Object} payload - Message payload
 * @returns {Object} Wrapped message
 */
function createProtocolMessage(type, payload = {}) {
    return {
        id: generateMessageId(),
        type: type,
        version: '1.0',
        timestamp: new Date().toISOString(),
        source: 'client',
        conversationId: state.conversationId || null,
        payload: payload,
    };
}

/**
 * Send a raw message through WebSocket (internal use)
 * @param {Object} data - Raw message data
 * @returns {boolean} Send success
 */
function sendRaw(data) {
    if (!isConnected()) {
        console.error('[WS] Cannot send - not connected');
        return false;
    }

    try {
        state.socket.send(JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('[WS] Send failed:', error);
        return false;
    }
}

/**
 * Send a protocol message through WebSocket
 * Wraps the message in CloudEvent envelope format
 * @param {string} type - Message type
 * @param {Object} payload - Message payload
 * @returns {boolean} Send success
 */
export function send(type, payload = {}) {
    // If type is an object (legacy call), extract type and treat rest as payload
    if (typeof type === 'object') {
        const data = type;
        const msgType = data.type || 'data.message.send';
        const msgPayload = { ...data };
        delete msgPayload.type;
        return sendRaw(createProtocolMessage(msgType, msgPayload));
    }

    const message = createProtocolMessage(type, payload);
    console.debug('[WS] Sending:', message.type);
    return sendRaw(message);
}

/**
 * Send a user message
 * @param {string} content - Message content
 * @returns {boolean} Send success
 */
export function sendMessage(content) {
    if (!content?.trim()) {
        console.warn('[WS] Empty message, ignoring');
        return false;
    }

    console.log('[WS] Sending message');
    return send('data.message.send', { content: content.trim() });
}

/**
 * Start template flow (proactive agent)
 * @returns {boolean} Send success
 */
export function startTemplate() {
    console.log('[WS] Starting template flow');
    return send('control.flow.start', {});
}

/**
 * Submit a widget response
 * @param {string} itemId - Item ID containing the widget
 * @param {string} widgetId - Widget ID
 * @param {string} widgetType - Widget type (e.g., 'multiple_choice', 'free_text', 'button')
 * @param {any} value - Widget response value
 * @param {Object} [metadata] - Optional response metadata
 * @returns {boolean} Send success
 */
export function submitWidgetResponse(itemId, widgetId, widgetType, value, metadata = null) {
    if (!widgetId) {
        console.warn('[WS] No widget ID, ignoring');
        return false;
    }
    if (!itemId) {
        console.warn('[WS] No item ID, ignoring');
        return false;
    }

    console.log('[WS] Submitting widget response:', { itemId, widgetId, widgetType });
    const payload = {
        itemId: itemId,
        widgetId: widgetId,
        widgetType: widgetType,
        value: value,
    };
    if (metadata) {
        payload.metadata = metadata;
    }
    return send('data.response.submit', payload);
}

/**
 * Submit batch widget responses (for confirmation mode)
 * Sends all widget responses in a single message
 * @param {string} itemId - Item ID
 * @param {Object} responses - Map of widgetId -> { widgetType, value }
 * @returns {boolean} Send success
 */
export function submitBatchResponse(itemId, responses) {
    if (!itemId) {
        console.warn('[WS] No item ID for batch, ignoring');
        return false;
    }

    console.log('[WS] Submitting batch response:', { itemId, responseCount: Object.keys(responses).length });

    const payload = {
        itemId: itemId,
        widgetId: `${itemId}-confirm`,
        widgetType: 'button',
        value: { confirmed: true },
        responses: responses,
    };

    return send('data.response.submit', payload);
}

/**
 * Pause the current flow
 * @returns {boolean} Send success
 */
export function pauseFlow() {
    console.log('[WS] Pausing flow');
    return send('control.flow.pause', {});
}

/**
 * Cancel the current flow
 * @param {string} [reason] - Cancellation reason
 * @returns {boolean} Send success
 */
export function cancelFlow(reason = 'User cancelled') {
    console.log('[WS] Cancelling flow');
    return send('control.flow.cancel', { reason: reason });
}

/**
 * Change the LLM model for the current conversation
 * @param {string} modelId - The qualified model ID (e.g., "openai:gpt-4o", "ollama:llama3.2:3b")
 * @returns {boolean} Send success
 */
export function changeModel(modelId) {
    if (!modelId) {
        console.warn('[WS] No model ID provided, ignoring');
        return false;
    }

    console.log('[WS] Changing model to:', modelId);
    return send('control.conversation.model', { modelId: modelId });
}

// =============================================================================
// Internal Functions
// =============================================================================

/**
 * Build WebSocket URL with query parameters
 * @param {Object} options - Connection options
 * @param {string} [options.wsUrl] - Full WebSocket URL from backend (preferred)
 * @param {string} [options.conversationId] - Conversation ID (fallback)
 * @param {string} [options.definitionId] - Definition ID (fallback)
 * @returns {string} WebSocket URL
 */
function buildWebSocketUrl(options) {
    // If backend provided a full ws_url, use it directly
    // The backend URL is HTTP(S), we need to convert to WS(S)
    if (options.wsUrl) {
        let url = options.wsUrl;
        // Convert http(s) to ws(s) if needed
        if (url.startsWith('http://')) {
            url = 'ws://' + url.slice(7);
        } else if (url.startsWith('https://')) {
            url = 'wss://' + url.slice(8);
        }
        console.log('[WS] Using backend-provided URL:', url);
        return url;
    }

    // Fallback: build URL from options (legacy mode)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    let url = `${protocol}//${host}/api/chat/ws`;

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

    console.log('[WS] Built fallback URL:', url);
    return url;
}

/**
 * Update connection status
 * @param {string} status - Status code
 * @param {string} message - Status message
 */
function updateStatus(status, message) {
    stateManager.set(StateKeys.CONNECTION_STATUS, status);
    eventBus.emit(Events.UI_STATUS_CHANGED, { status, message });
}

// =============================================================================
// Event Handlers
// =============================================================================

/**
 * Handle WebSocket open
 * @param {Function} resolve - Promise resolve
 */
function handleOpen(resolve) {
    console.log('[WS] Connected');
    state.isConnected = true;
    state.isConnecting = false;
    state.reconnectAttempts = 0;

    stateManager.set(StateKeys.WS_CONNECTED, true);
    updateStatus('connected', 'Connected');

    startPingInterval();

    eventBus.emit(Events.WS_CONNECTED);
    resolve(true);
}

/**
 * Handle WebSocket close
 * @param {CloseEvent} event - Close event
 */
function handleClose(event) {
    console.log('[WS] Disconnected:', event.code, event.reason);
    state.isConnected = false;
    state.isConnecting = false;
    stopPingInterval();

    stateManager.set(StateKeys.WS_CONNECTED, false);
    updateStatus('disconnected', 'Disconnected');

    eventBus.emit(Events.WS_DISCONNECTED, { code: event.code, reason: event.reason });

    // Attempt reconnection if not clean close
    if (event.code !== 1000 && state.reconnectAttempts < WS_CONFIG.maxReconnectAttempts) {
        scheduleReconnect();
    }
}

/**
 * Handle WebSocket error
 * @param {Event} error - Error event
 * @param {Function} reject - Promise reject
 */
function handleError(error, reject) {
    console.error('[WS] Error:', error);
    state.isConnecting = false;

    updateStatus('error', 'Connection error');
    eventBus.emit(Events.WS_ERROR, { message: 'WebSocket connection error' });

    reject(error);
}

/**
 * Handle incoming WebSocket message
 * @param {MessageEvent} event - Message event
 */
function handleMessage(event) {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (e) {
        console.error('[WS] Invalid JSON:', event.data);
        return;
    }

    // Handle protocol message: system.connection.established
    // This is the new format with CloudEvent-inspired envelope
    if (data.type === 'system.connection.established') {
        const payload = data.payload || data;
        state.conversationId = payload.conversationId || payload.conversation_id;
        stateManager.set(StateKeys.WS_CONVERSATION_ID, state.conversationId);

        // Store server capabilities from the WebSocket handshake
        if (payload.serverCapabilities) {
            stateManager.set(StateKeys.SERVER_CAPABILITIES, payload.serverCapabilities);
        }
        console.log('[WS] Connection established:', {
            conversationId: state.conversationId,
            capabilities: payload.serverCapabilities?.length || 0,
        });
    }

    // Handle legacy connected message (backwards compatibility)
    if (data.type === 'connected') {
        state.conversationId = data.conversation_id;
        stateManager.set(StateKeys.WS_CONVERSATION_ID, data.conversation_id);
    }

    // Delegate to message handler
    if (messageHandler) {
        messageHandler(data);
    }

    // Emit generic WS_MESSAGE event
    eventBus.emit(Events.WS_MESSAGE, data);

    // Dispatch protocol-specific event based on message type
    // This enables handlers to subscribe to specific protocol messages
    dispatchProtocolEvent(data);
}

/**
 * Dispatch protocol-specific event based on message type
 *
 * Maps incoming message types to Events enum values.
 * Protocol message types follow the pattern: {plane}.{category}.{action}
 *
 * @param {Object} data - Parsed message data
 */
function dispatchProtocolEvent(data) {
    if (!data.type) {
        return;
    }

    // Map protocol message types to Events enum
    // The message type from server matches the event name format
    const eventMap = {
        // System plane
        'system.connection.established': Events.SYSTEM_CONNECTION_ESTABLISHED,
        'system.connection.resumed': Events.SYSTEM_CONNECTION_RESUMED,
        'system.connection.close': Events.SYSTEM_CONNECTION_CLOSE,
        'system.ping': Events.SYSTEM_PING,
        'system.pong': Events.SYSTEM_PONG,
        'system.error': Events.SYSTEM_ERROR,

        // Control plane - Conversation
        'control.conversation.config': Events.CONTROL_CONVERSATION_CONFIG,
        'control.conversation.display': Events.CONTROL_CONVERSATION_DISPLAY,
        'control.conversation.deadline': Events.CONTROL_CONVERSATION_DEADLINE,
        'control.conversation.started': Events.CONTROL_CONVERSATION_STARTED,
        'control.conversation.paused': Events.CONTROL_CONVERSATION_PAUSED,
        'control.conversation.resumed': Events.CONTROL_CONVERSATION_RESUMED,
        'control.conversation.completed': Events.CONTROL_CONVERSATION_COMPLETED,
        'control.conversation.terminated': Events.CONTROL_CONVERSATION_TERMINATED,

        // Control plane - Item
        'control.item.context': Events.CONTROL_ITEM_CONTEXT,
        'control.item.score': Events.CONTROL_ITEM_SCORE,
        'control.item.timeout': Events.CONTROL_ITEM_TIMEOUT,
        'control.item.expired': Events.CONTROL_ITEM_EXPIRED,

        // Control plane - Widget
        'control.widget.state': Events.CONTROL_WIDGET_STATE,
        'control.widget.render': Events.CONTROL_WIDGET_RENDER,
        'control.widget.dismiss': Events.CONTROL_WIDGET_DISMISS,
        'control.widget.update': Events.CONTROL_WIDGET_UPDATE,

        // Control plane - Navigation
        'control.navigation.request': Events.CONTROL_NAVIGATION_REQUEST,
        'control.navigation.ack': Events.CONTROL_NAVIGATION_ACK,
        'control.navigation.denied': Events.CONTROL_NAVIGATION_DENIED,

        // Control plane - Flow
        'control.flow.chatInput': Events.CONTROL_FLOW_CHAT_INPUT,
        'control.flow.progress': Events.CONTROL_FLOW_PROGRESS,

        // Control plane - Panel
        'control.panel.header': Events.CONTROL_PANEL_HEADER,

        // Data plane - Content
        'data.content.chunk': Events.DATA_CONTENT_CHUNK,
        'data.content.complete': Events.DATA_CONTENT_COMPLETE,

        // Data plane - Tool
        'data.tool.call': Events.DATA_TOOL_CALL,
        'data.tool.result': Events.DATA_TOOL_RESULT,

        // Data plane - Message
        'data.message.send': Events.DATA_MESSAGE_SEND,
        'data.message.ack': Events.DATA_MESSAGE_ACK,

        // Data plane - Response
        'data.response.submit': Events.DATA_RESPONSE_SUBMIT,
        'data.response.ack': Events.DATA_RESPONSE_ACK,

        // Data plane - Audit
        'data.audit.batch': Events.DATA_AUDIT_BATCH,
        'data.audit.ack': Events.DATA_AUDIT_ACK,
    };

    const eventName = eventMap[data.type];

    if (eventName) {
        // Emit with payload (data.payload or data itself if no payload property)
        const payload = data.payload || data;
        eventBus.emit(eventName, payload);
    } else if (data.type && data.type.includes('.')) {
        // Unknown protocol message - log for debugging
        console.debug('[WS] Unknown protocol message type:', data.type);
    }
    // Non-protocol messages (like 'connected', 'message', 'ping', 'pong') are handled elsewhere
}

// =============================================================================
// Keepalive
// =============================================================================

/**
 * Start ping interval
 */
function startPingInterval() {
    stopPingInterval();

    state.pingInterval = setInterval(() => {
        if (isConnected()) {
            send('system.ping', { timestamp: new Date().toISOString() });
        }
    }, WS_CONFIG.pingInterval);
}

/**
 * Stop ping interval
 */
function stopPingInterval() {
    if (state.pingInterval) {
        clearInterval(state.pingInterval);
        state.pingInterval = null;
    }
}

// =============================================================================
// Reconnection
// =============================================================================

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect() {
    state.reconnectAttempts++;
    const delay = WS_CONFIG.reconnectDelay * Math.pow(2, state.reconnectAttempts - 1);

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts})`);
    updateStatus('reconnecting', `Reconnecting (${state.reconnectAttempts})...`);

    setTimeout(() => {
        if (!state.isConnected && !state.isConnecting) {
            connect({
                definitionId: state.definitionId,
                conversationId: state.conversationId,
            }).catch(error => {
                console.error('[WS] Reconnection failed:', error);
            });
        }
    }, delay);
}

export default {
    setMessageHandler,
    connect,
    disconnect,
    isConnected,
    getConversationId,
    send,
    sendMessage,
    startTemplate,
};
