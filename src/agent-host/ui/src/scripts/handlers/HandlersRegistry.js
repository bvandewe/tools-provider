/**
 * HandlersRegistry - Event Handlers Registration Module
 *
 * Provides a unified way to initialize all class-based handlers.
 * This is the new pattern that replaces the legacy factory-based registration.
 *
 * MIGRATION NOTE:
 * The old index.js uses factory functions with context injection.
 * This new registry uses class-based handlers with DI via singletons.
 *
 * Usage:
 *   import { initAllHandlers, destroyAllHandlers } from './handlers/HandlersRegistry.js';
 *
 *   // During app init
 *   initAllHandlers();
 *
 *   // During app cleanup
 *   destroyAllHandlers();
 *
 * @module handlers/HandlersRegistry
 */

// Import class-based handlers
import { authHandlers } from './AuthHandlers.js';
import { definitionHandlers } from './DefinitionHandlers.js';
import { systemHandlers } from './SystemHandlers.js';
import { controlHandlers } from './ControlHandlers.js';
import { dataHandlers } from './DataHandlers.js';
import { conversationHandlers } from './ConversationHandlers.js';
import { messageHandlers } from './MessageHandlers.js';
import { websocketHandlers } from './WebsocketHandlers.js';
import { widgetHandlers } from './WidgetHandlers.js';

/**
 * All class-based handlers in initialization order
 *
 * Order matters:
 * 1. Auth handlers first (session management)
 * 2. System handlers (WebSocket protocol system plane)
 * 3. Data handlers (content streaming, tool calls)
 * 4. Control handlers (conversation/item/widget control)
 * 5. Conversation handlers (lifecycle events)
 * 6. Message handlers (message streaming/complete)
 * 7. WebSocket handlers (connection lifecycle)
 * 8. Widget handlers (widget events)
 * 9. Definition handlers (definition selection)
 */
const allHandlers = [
    { name: 'AuthHandlers', instance: authHandlers },
    { name: 'SystemHandlers', instance: systemHandlers },
    { name: 'DataHandlers', instance: dataHandlers },
    { name: 'ControlHandlers', instance: controlHandlers },
    { name: 'ConversationHandlers', instance: conversationHandlers },
    { name: 'MessageHandlers', instance: messageHandlers },
    { name: 'WebsocketHandlers', instance: websocketHandlers },
    { name: 'WidgetHandlers', instance: widgetHandlers },
    { name: 'DefinitionHandlers', instance: definitionHandlers },
];

/**
 * Initialize all class-based handlers
 * @returns {number} Number of handlers initialized
 */
export function initAllHandlers() {
    let count = 0;

    for (const { name, instance } of allHandlers) {
        try {
            instance.init();
            count++;
            console.log(`[HandlersRegistry] Initialized: ${name}`);
        } catch (error) {
            console.error(`[HandlersRegistry] Failed to initialize ${name}:`, error);
        }
    }

    console.log(`[HandlersRegistry] Initialized ${count} handlers`);
    return count;
}

/**
 * Destroy all class-based handlers
 */
export function destroyAllHandlers() {
    for (const { name, instance } of allHandlers) {
        try {
            instance.destroy();
            console.log(`[HandlersRegistry] Destroyed: ${name}`);
        } catch (error) {
            console.error(`[HandlersRegistry] Failed to destroy ${name}:`, error);
        }
    }
}

/**
 * Get handler statistics
 * @returns {Object} Handler statistics
 */
export function getHandlerStats() {
    return {
        total: allHandlers.length,
        handlers: allHandlers.map(h => ({
            name: h.name,
            initialized: h.instance._initialized,
        })),
    };
}

// Export individual handler instances for direct access
export { authHandlers } from './AuthHandlers.js';
export { definitionHandlers } from './DefinitionHandlers.js';
export { systemHandlers } from './SystemHandlers.js';

export default {
    initAllHandlers,
    destroyAllHandlers,
    getHandlerStats,
};
