/**
 * Protocol Module - WebSocket Communication Layer
 *
 * Handles WebSocket protocol communication:
 * - websocket-client: Connection management
 * - message-router: Message dispatch to event bus handlers
 *
 * Message handlers are registered via the handlers/ module which subscribes
 * to protocol events emitted by the websocket-client.
 *
 * @module protocol
 */

// WebSocket client
export { setMessageHandler, connect, disconnect, isConnected, getConversationId, send, sendMessage, startTemplate } from './websocket-client.js';

// Message router
export { registerHandler, registerHandlers, routeMessage, clearHandlers, getRegisteredTypes } from './message-router.js';

// =============================================================================
// Protocol Initialization
// =============================================================================

import { setMessageHandler } from './websocket-client.js';
import { routeMessage } from './message-router.js';

/**
 * Initialize the protocol layer
 *
 * Connects the message router to the WebSocket client.
 * Protocol message handlers are registered separately via the handlers/ module
 * which subscribes to Events emitted by dispatchProtocolEvent() in websocket-client.
 */
export function initProtocol() {
    // Connect router to client for legacy message routing (if any)
    setMessageHandler(routeMessage);

    console.log('[Protocol] Initialized - handlers registered via event bus');
}
