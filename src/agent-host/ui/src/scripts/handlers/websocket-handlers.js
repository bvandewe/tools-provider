/**
 * WebSocket Event Handlers
 *
 * Handles WebSocket connection lifecycle events.
 *
 * @module handlers/websocket-handlers
 */

import { Events } from '../core/event-bus.js';
import { setCurrentConversationId } from '../domain/conversation.js';
import { updateStreamingState } from '../ui/managers/chat-manager.js';
import { setUploadEnabled } from '../components/FileUpload.js';
import { showToast } from '../services/modals.js';

// =============================================================================
// Handler Functions
// =============================================================================

/**
 * Handle WebSocket connected
 * Note: The WS_CONNECTED event may be emitted without a payload.
 * The conversationId is typically set via the system.connection.established handler.
 * @param {Object|null} [payload] - Event payload (may be null/undefined)
 * @param {string} [payload.conversationId] - Connected conversation ID
 */
function handleWsConnected(payload) {
    const conversationId = payload?.conversationId;
    console.log('[WebSocketHandlers] Connected, conversation:', conversationId);
    if (conversationId) {
        setCurrentConversationId(conversationId);
    }
}

/**
 * Handle WebSocket disconnected
 */
function handleWsDisconnected() {
    console.log('[WebSocketHandlers] Disconnected');
}

/**
 * Handle WebSocket error
 * @param {Object|null} [payload] - Event payload (may be null/undefined)
 * @param {string} [payload.message] - Error message
 * @param {string} [payload.code] - Error code
 */
function handleWsError(payload) {
    const message = payload?.message;
    const code = payload?.code;
    console.error('[WebSocketHandlers] Error:', message, code);
    showToast(message || 'Connection error', 'error');
    updateStreamingState(false);
    setUploadEnabled(true);
}

// =============================================================================
// Handler Registrations
// =============================================================================

/**
 * Exported handlers for registry auto-discovery.
 * @type {import('./index.js').HandlerRegistration[]}
 */
export const handlers = [
    {
        event: Events.WS_CONNECTED,
        handler: handleWsConnected,
        description: 'Handle WebSocket connection established',
        isFactory: false,
    },
    {
        event: Events.WS_DISCONNECTED,
        handler: handleWsDisconnected,
        description: 'Handle WebSocket disconnection',
        isFactory: false,
    },
    {
        event: Events.WS_ERROR,
        handler: handleWsError,
        description: 'Handle WebSocket errors',
        isFactory: false,
    },
];

export default handlers;
