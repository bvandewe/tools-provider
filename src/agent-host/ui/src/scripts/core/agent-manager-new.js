/**
 * Agent Manager (Simplified)
 *
 * Lightweight manager for coordinating between definitions and conversations.
 * Replaces the complex session-based agent-manager.
 *
 * In the simplified architecture:
 * - AgentDefinition defines WHAT kind of assistant (reactive or proactive)
 * - Conversation is the single AggregateRoot that holds all state
 * - Agent is a stateless service that executes conversations
 *
 * This module handles:
 * - Tracking which definition is being used for the current conversation
 * - Managing UI restrictions based on definition type
 * - Coordinating between definition-manager and conversation-manager
 */

import { getSelectedDefinition, getSelectedDefinitionId, isProactiveDefinition } from './definition-manager.js';
import { showToast } from '../services/modals.js';

// =============================================================================
// State
// =============================================================================

let state = {
    /** Current conversation ID (if any) */
    currentConversationId: null,

    /** Definition ID associated with current conversation */
    currentDefinitionId: null,

    /** Whether we're in a proactive flow (agent leads) */
    isProactiveMode: false,

    /** Current UI restrictions */
    restrictions: {
        canSwitchDefinitions: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    },

    /** Whether manager is initialized */
    isInitialized: false,
};

// Callbacks
let callbacks = {
    onRestrictionsChange: null,
    onModeChange: null,
};

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the agent manager
 * @param {Object} callbackFunctions - Callback functions
 */
export function initAgentManager(callbackFunctions = {}) {
    callbacks = { ...callbacks, ...callbackFunctions };
    state.isInitialized = true;
    console.log('[AgentManager] Initialized (simplified)');
}

/**
 * Reset the agent manager state
 */
export function resetAgentManager() {
    state = {
        currentConversationId: null,
        currentDefinitionId: null,
        isProactiveMode: false,
        restrictions: {
            canSwitchDefinitions: true,
            canAccessConversations: true,
            canTypeFreeText: true,
            canEndEarly: true,
        },
        isInitialized: true,
    };
    console.log('[AgentManager] State reset');
}

// =============================================================================
// Conversation Context
// =============================================================================

/**
 * Set the current conversation context
 * Updates restrictions based on the conversation's definition
 * @param {string} conversationId - Conversation ID
 * @param {string} definitionId - Definition ID associated with conversation
 * @param {boolean} skipRestrictions - If true, skip updating restrictions (used when loading existing conversations)
 */
export function setConversationContext(conversationId, definitionId, skipRestrictions = false) {
    const previousDefinitionId = state.currentDefinitionId;

    state.currentConversationId = conversationId;
    state.currentDefinitionId = definitionId;
    state.isProactiveMode = isProactiveDefinition(definitionId);

    // Update restrictions based on definition type (skip for existing conversations)
    if (!skipRestrictions) {
        updateRestrictionsForDefinition(definitionId);
    }

    if (previousDefinitionId !== definitionId && callbacks.onModeChange) {
        callbacks.onModeChange(definitionId, previousDefinitionId);
    }

    console.log(`[AgentManager] Context set: conversation=${conversationId}, definition=${definitionId}, proactive=${state.isProactiveMode}, skipRestrictions=${skipRestrictions}`);
}

/**
 * Clear the current conversation context
 */
export function clearConversationContext() {
    state.currentConversationId = null;
    state.currentDefinitionId = null;
    state.isProactiveMode = false;

    // Reset to default restrictions
    state.restrictions = {
        canSwitchDefinitions: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    };

    if (callbacks.onRestrictionsChange) {
        callbacks.onRestrictionsChange(state.restrictions);
    }

    console.log('[AgentManager] Context cleared');
}

/**
 * Update UI restrictions based on definition type
 * @param {string} definitionId - Definition ID
 */
function updateRestrictionsForDefinition(definitionId) {
    // For proactive definitions, restrict some UI elements
    if (isProactiveDefinition(definitionId)) {
        state.restrictions = {
            canSwitchDefinitions: false, // Can't switch mid-session
            canAccessConversations: false, // Hide conversation list
            canTypeFreeText: false, // Only respond via widgets
            canEndEarly: true, // Can always quit
        };
    } else {
        // Reactive (chat) mode - full access
        state.restrictions = {
            canSwitchDefinitions: true,
            canAccessConversations: true,
            canTypeFreeText: true,
            canEndEarly: true,
        };
    }

    if (callbacks.onRestrictionsChange) {
        callbacks.onRestrictionsChange(state.restrictions);
    }
}

// =============================================================================
// Definition Selection for New Conversations
// =============================================================================

/**
 * Get the definition ID to use for a new conversation
 * Uses the currently selected definition from definition-manager
 * @returns {string|null} Definition ID or null
 */
export function getDefinitionForNewConversation() {
    return getSelectedDefinitionId();
}

/**
 * Get the full definition object for new conversations
 * @returns {Object|null} Definition or null
 */
export function getSelectedDefinitionForNewConversation() {
    return getSelectedDefinition();
}

// =============================================================================
// Restriction Checks
// =============================================================================

/**
 * Check if user can switch to a different definition
 * @returns {boolean}
 */
export function canSwitchDefinitions() {
    return state.restrictions.canSwitchDefinitions;
}

/**
 * Check if user can access the conversations sidebar
 * @returns {boolean}
 */
export function canAccessConversations() {
    return state.restrictions.canAccessConversations;
}

/**
 * Check if user can type free text (vs widget-only)
 * @returns {boolean}
 */
export function canTypeFreeText() {
    return state.restrictions.canTypeFreeText;
}

/**
 * Check if user can end the conversation early
 * @returns {boolean}
 */
export function canEndEarly() {
    return state.restrictions.canEndEarly;
}

/**
 * Get all current restrictions
 * @returns {Object} Restrictions object
 */
export function getRestrictions() {
    return { ...state.restrictions };
}

// =============================================================================
// State Getters
// =============================================================================

/**
 * Get the current conversation ID
 * @returns {string|null}
 */
export function getCurrentConversationId() {
    return state.currentConversationId;
}

/**
 * Get the current definition ID
 * @returns {string|null}
 */
export function getCurrentDefinitionId() {
    return state.currentDefinitionId;
}

/**
 * Check if we're in proactive mode
 * @returns {boolean}
 */
export function isInProactiveMode() {
    return state.isProactiveMode;
}

/**
 * Check if we have an active conversation context
 * @returns {boolean}
 */
export function hasActiveContext() {
    return state.currentConversationId !== null;
}

// =============================================================================
// Legacy Compatibility (for gradual migration)
// =============================================================================

/**
 * @deprecated Use canSwitchDefinitions() instead
 */
export function canSwitchAgents() {
    return canSwitchDefinitions();
}

/**
 * @deprecated Use isInProactiveMode() instead
 */
export function isInAgentMode() {
    return state.isProactiveMode;
}

/**
 * @deprecated Use hasActiveContext() instead
 */
export function hasActiveSession() {
    return hasActiveContext();
}

/**
 * @deprecated No longer needed - definitions don't have separate IDs
 */
export function getActiveAgentId() {
    return state.currentDefinitionId;
}

/**
 * @deprecated Use getCurrentDefinitionId() instead
 */
export function getActiveAgentType() {
    return state.currentDefinitionId;
}
