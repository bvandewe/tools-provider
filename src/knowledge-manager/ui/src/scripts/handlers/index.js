/**
 * Handlers Module - Event Handlers Layer
 *
 * Provides class-based event handlers that subscribe to EventBus events.
 * All handlers are singleton instances with init/destroy lifecycle.
 *
 * @module handlers
 */

export { AuthHandlers, authHandlers } from './AuthHandlers.js';
export { NamespaceHandlers, namespaceHandlers } from './NamespaceHandlers.js';
export { initAllHandlers, destroyAllHandlers, getHandlerStats } from './HandlersRegistry.js';
