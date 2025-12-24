/**
 * HandlersRegistry - Event Handlers Registration Module
 *
 * Provides a unified way to initialize all class-based handlers.
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
import { namespaceHandlers } from './NamespaceHandlers.js';

/**
 * All class-based handlers in initialization order
 *
 * Order matters:
 * 1. Auth handlers first (session management)
 * 2. Namespace handlers (data display)
 */
const allHandlers = [
    { name: 'AuthHandlers', instance: authHandlers },
    { name: 'NamespaceHandlers', instance: namespaceHandlers },
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
        handlers: allHandlers.map(({ name, instance }) => ({
            name,
            initialized: instance._initialized || false,
        })),
    };
}
