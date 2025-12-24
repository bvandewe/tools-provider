/**
 * Managers Module - UI State Management Layer
 *
 * Provides class-based managers for UI state management.
 * All managers are singleton instances that can be imported directly.
 *
 * @module managers
 */

// Core UI Managers
export { UIManager, uiManager } from './UIManager.js';
export { StatsManager, statsManager } from './StatsManager.js';
export { ViewManager, viewManager } from './ViewManager.js';

// Data Managers
export { NamespaceManager, namespaceManager } from './NamespaceManager.js';
