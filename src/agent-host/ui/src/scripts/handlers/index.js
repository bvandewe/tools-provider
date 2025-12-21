/**
 * Event Handlers Registry
 *
 * Centralized registration of event handlers following the backend pattern
 * (application.events.websocket). Each handler is a separate module that:
 * - Handles a single event type
 * - Is auto-discovered via this registry
 * - Has a consistent interface
 *
 * Pattern mirrors backend:
 * - Backend: DomainEventHandler[TEvent] classes in application/events/websocket/
 * - Frontend: Handler modules in scripts/handlers/
 *
 * Handler Organization:
 * - Protocol handlers (system, control, data): Handle WebSocket protocol messages
 * - Domain handlers: Handle local UI events and client-side state changes
 *
 * @module handlers
 */

import { eventBus, Events } from '../core/event-bus.js';

// =============================================================================
// Protocol Plane Handlers (WebSocket Protocol v1.0.0)
// =============================================================================
import * as systemHandlers from './system-handlers.js';
import * as controlHandlers from './control-handlers.js';
import * as dataHandlers from './data-handlers.js';

// =============================================================================
// Domain Handlers (Local UI Events)
// =============================================================================
import * as authHandlers from './auth-handlers.js';
import * as conversationHandlers from './conversation-handlers.js';
import * as definitionHandlers from './definition-handlers.js';
import * as websocketHandlers from './websocket-handlers.js';
import * as messageHandlers from './message-handlers.js';
import * as widgetHandlers from './widget-handlers.js';

// =============================================================================
// Handler Registry
// =============================================================================

/**
 * @typedef {Object} HandlerRegistration
 * @property {string} event - Event name from Events enum
 * @property {Function} handler - Handler function or factory function(context) => handler
 * @property {string} [description] - Optional description
 */

/**
 * All registered handlers organized by category.
 * Each module exports a `handlers` array of HandlerRegistration objects.
 * @type {HandlerRegistration[]}
 */
const allHandlers = [
    // Protocol handlers (receive WebSocket messages from server)
    ...systemHandlers.handlers,
    ...controlHandlers.handlers,
    ...dataHandlers.handlers,

    // Domain handlers (local UI events)
    ...authHandlers.handlers,
    ...conversationHandlers.handlers,
    ...definitionHandlers.handlers,
    ...websocketHandlers.handlers,
    ...messageHandlers.handlers,
    ...widgetHandlers.handlers,
];

// =============================================================================
// Registration
// =============================================================================

/** @type {Function[]} */
let unsubscribeFunctions = [];

/**
 * Register all event handlers with the event bus.
 * Should be called during app initialization.
 *
 * Protocol handlers receive a context object and return the actual handler function.
 * This allows handlers to access application state and methods.
 *
 * @param {Object} context - Application context (e.g., ChatApp instance)
 * @returns {number} Number of handlers registered
 */
export function registerHandlers(context) {
    // Unregister any existing handlers first
    unregisterHandlers();

    let count = 0;

    for (const registration of allHandlers) {
        const { event, handler, description, isFactory = true } = registration;

        if (!event || !handler) {
            console.warn('[Handlers] Invalid registration:', registration);
            continue;
        }

        // Handler can be:
        // 1. A factory function (isFactory=true): (context) => (payload) => void
        // 2. A standalone function (isFactory=false): (payload) => void
        let boundHandler;

        if (typeof handler !== 'function') {
            console.warn(`[Handlers] Handler for ${event} is not a function`);
            continue;
        }

        if (isFactory) {
            // Factory function - call with context to get the actual handler
            boundHandler = handler(context);
            if (typeof boundHandler !== 'function') {
                console.warn(`[Handlers] Factory for ${event} did not return a function`);
                continue;
            }
        } else {
            // Standalone function - use as-is (doesn't need context)
            boundHandler = handler;
        }

        const unsubscribe = eventBus.on(event, boundHandler);
        unsubscribeFunctions.push(unsubscribe);
        count++;

        if (process.env.NODE_ENV === 'development') {
            console.debug(`[Handlers] Registered: ${event}${description ? ` (${description})` : ''}`);
        }
    }

    console.log(`[Handlers] Registered ${count} event handlers`);
    return count;
}

/**
 * Unregister all event handlers.
 * Useful for cleanup or hot-reloading.
 */
export function unregisterHandlers() {
    for (const unsub of unsubscribeFunctions) {
        unsub();
    }
    unsubscribeFunctions = [];
}

/**
 * Get all registered handler names for debugging.
 * @returns {string[]} Array of event names with handlers
 */
export function getRegisteredEvents() {
    return allHandlers.map(h => h.event);
}

/**
 * Get handler count by domain.
 * @returns {Object} Domain -> count mapping
 */
export function getHandlerStats() {
    return {
        // Protocol handlers
        system: systemHandlers.handlers.length,
        control: controlHandlers.handlers.length,
        data: dataHandlers.handlers.length,

        // Domain handlers
        auth: authHandlers.handlers.length,
        conversation: conversationHandlers.handlers.length,
        definition: definitionHandlers.handlers.length,
        websocket: websocketHandlers.handlers.length,
        message: messageHandlers.handlers.length,
        widget: widgetHandlers.handlers.length,

        // Total
        total: allHandlers.length,
    };
}

export default {
    registerHandlers,
    unregisterHandlers,
    getRegisteredEvents,
    getHandlerStats,
};
