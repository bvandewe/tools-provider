/**
 * Message Router - WebSocket Message Dispatch
 *
 * Routes incoming WebSocket messages to appropriate handlers.
 * Decouples connection management from message processing.
 *
 * @module protocol/message-router
 */

import { eventBus, Events } from '../core/event-bus.js';

// =============================================================================
// Handler Registry
// =============================================================================

/**
 * @typedef {Object} MessageHandlers
 * @property {Function} [connected] - Handle connected message
 * @property {Function} [content] - Handle content (streaming text)
 * @property {Function} [widget] - Handle widget render
 * @property {Function} [progress] - Handle template progress
 * @property {Function} [message_complete] - Handle message complete
 * @property {Function} [complete] - Handle template complete
 * @property {Function} [template_config] - Handle template config
 * @property {Function} [tool_call] - Handle tool call start
 * @property {Function} [tool_result] - Handle tool result
 * @property {Function} [error] - Handle error
 */

/** @type {MessageHandlers} */
const handlers = {};

// =============================================================================
// Public API
// =============================================================================

/**
 * Register a handler for a message type
 * @param {string} messageType - Message type to handle
 * @param {Function} handler - Handler function
 */
export function registerHandler(messageType, handler) {
    handlers[messageType] = handler;
    console.log(`[MessageRouter] Registered handler for: ${messageType}`);
}

/**
 * Register multiple handlers at once
 * @param {MessageHandlers} handlerMap - Map of message types to handlers
 */
export function registerHandlers(handlerMap) {
    Object.entries(handlerMap).forEach(([type, handler]) => {
        handlers[type] = handler;
    });
}

/**
 * Route an incoming message to appropriate handler
 * @param {Object} message - Parsed message object
 */
export function routeMessage(message) {
    const { type, data } = message;

    if (!type) {
        console.warn('[MessageRouter] Message without type:', message);
        return;
    }

    console.log('[MessageRouter] Routing:', type);

    // Look up handler
    const handler = handlers[type];

    if (handler) {
        try {
            // Handler receives the data payload (or full message if no data property)
            handler(data !== undefined ? data : message);
        } catch (error) {
            console.error(`[MessageRouter] Error in handler for ${type}:`, error);
            eventBus.emit(Events.WS_ERROR, {
                message: `Handler error for ${type}: ${error.message}`,
            });
        }
    } else {
        // Message types handled elsewhere (event bus) or safely ignored
        // System plane messages are handled via event bus in system-handlers.js
        // Control plane messages are handled via event bus in control-handlers.js
        const handledElsewhere = [
            // System plane
            'system.ping',
            'system.pong',
            'system.connection.established',
            'system.connection.resumed',
            'system.connection.close',
            'system.error',
            // Control plane - Conversation
            'control.conversation.config',
            'control.conversation.display',
            'control.conversation.deadline',
            'control.conversation.started',
            'control.conversation.paused',
            'control.conversation.resumed',
            'control.conversation.completed',
            'control.conversation.terminated',
            'control.conversation.model',
            'control.conversation.model.ack',
            // Control plane - Item
            'control.item.context',
            'control.item.score',
            'control.item.timeout',
            'control.item.expired',
            // Control plane - Widget
            'control.widget.state',
            'control.widget.render',
            'control.widget.dismiss',
            'control.widget.update',
            // Control plane - Navigation
            'control.navigation.request',
            'control.navigation.ack',
            'control.navigation.denied',
            // Control plane - Flow
            'control.flow.chatInput',
            'control.flow.progress',
            // Data plane - Content
            'data.content.chunk',
            'data.content.complete',
            // Data plane - Tool
            'data.tool.call',
            'data.tool.result',
            // Data plane - Message
            'data.message.send',
            'data.message.ack',
            // Data plane - Response
            'data.response.submit',
            'data.response.ack',
            // Data plane - Audit
            'data.audit.batch',
            'data.audit.ack',
            // Legacy formats
            'pong',
            'message_added',
        ];
        if (!handledElsewhere.includes(type)) {
            console.warn('[MessageRouter] No handler for type:', type);
        }
    }
}

/**
 * Clear all handlers
 */
export function clearHandlers() {
    Object.keys(handlers).forEach(key => delete handlers[key]);
}

/**
 * Get registered handler types
 * @returns {string[]} Array of registered message types
 */
export function getRegisteredTypes() {
    return Object.keys(handlers);
}

export default {
    registerHandler,
    registerHandlers,
    routeMessage,
    clearHandlers,
    getRegisteredTypes,
};
