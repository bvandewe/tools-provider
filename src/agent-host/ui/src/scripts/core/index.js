/**
 * Core Module - Infrastructure Layer
 *
 * Exports core infrastructure components:
 * - Event Bus: Pub/sub system for decoupled communication
 * - State Manager: Global state container with reactive updates
 *
 * Note: Individual managers (sidebar, session, draft, etc.) remain in this folder
 * but are imported directly where needed rather than re-exported here to avoid
 * circular dependencies.
 */

export { eventBus, Events } from './event-bus.js';
export { stateManager, StateKeys } from './state-manager.js';
