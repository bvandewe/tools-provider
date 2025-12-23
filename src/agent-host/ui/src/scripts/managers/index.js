/**
 * Managers Module - UI State Management Layer
 *
 * Provides class-based managers for UI state management.
 * All managers are singleton instances that can be imported directly.
 *
 * @module managers
 */

// Core UI Managers
export { ChatManager, chatManager } from './ChatManager.js';
export { SidebarManager, sidebarManager } from './SidebarManager.js';
export { PanelHeaderManager, panelHeaderManager } from './PanelHeaderManager.js';
export { UIManager, uiManager } from './UIManager.js';

// Session & Config Managers
export { SessionManager, sessionManager } from './SessionManager.js';
export { ConfigManager, configManager } from './ConfigManager.js';

// Definition & Draft Managers
export { DefinitionManager, definitionManager } from './DefinitionManager.js';
export { DraftManager, draftManager } from './DraftManager.js';

// Agent & Conversation Managers
export { AgentManager, agentManager } from './AgentManager.js';
export { ConversationManager, conversationManager } from './ConversationManager.js';
