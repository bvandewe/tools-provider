/**
 * Storage Utilities - LocalStorage/SessionStorage helpers
 *
 * @module utils/storage
 */

// =============================================================================
// Constants
// =============================================================================

/**
 * Standard storage keys used throughout the application
 * @readonly
 * @enum {string}
 */
export const STORAGE_KEYS = {
    // UI preferences
    SIDEBAR_COLLAPSED: 'agent-host:sidebar-collapsed',
    THEME: 'agent-host:theme',

    // Model selection
    SELECTED_MODEL: 'agent-host:selected-model',

    // Conversation state
    PINNED_CONVERSATIONS: 'agent-host:pinned-conversations',
    PINNED_SESSIONS: 'agent-host:pinned-sessions',

    // Definition state
    SELECTED_DEFINITION: 'agent-host:selected-definition',

    // Draft state
    DRAFT_PREFIX: 'agent-host:draft:',
    CURRENT_DRAFT_KEY: 'agent-host:current-draft-key',

    // Session state
    SESSION_EXPIRY: 'agent-host:session-expiry',
};

// =============================================================================
// LocalStorage Helpers
// =============================================================================

/**
 * Get item from localStorage with JSON parsing
 * @param {string} key - Storage key
 * @param {*} [defaultValue=null] - Default if not found
 * @returns {*} Parsed value or default
 */
export function getItem(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        if (item === null) return defaultValue;
        return JSON.parse(item);
    } catch (e) {
        console.warn(`[Storage] Failed to parse ${key}:`, e);
        return defaultValue;
    }
}

/**
 * Set item in localStorage with JSON stringifying
 * @param {string} key - Storage key
 * @param {*} value - Value to store
 * @returns {boolean} Success status
 */
export function setItem(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.error(`[Storage] Failed to set ${key}:`, e);
        return false;
    }
}

/**
 * Remove item from localStorage
 * @param {string} key - Storage key
 */
export function removeItem(key) {
    localStorage.removeItem(key);
}

/**
 * Check if key exists in localStorage
 * @param {string} key - Storage key
 * @returns {boolean} True if exists
 */
export function hasItem(key) {
    return localStorage.getItem(key) !== null;
}

/**
 * Get all keys matching a prefix
 * @param {string} prefix - Key prefix
 * @returns {string[]} Matching keys
 */
export function getKeysByPrefix(prefix) {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(prefix)) {
            keys.push(key);
        }
    }
    return keys;
}

/**
 * Remove all items matching a prefix
 * @param {string} prefix - Key prefix
 * @returns {number} Number of items removed
 */
export function removeByPrefix(prefix) {
    const keys = getKeysByPrefix(prefix);
    keys.forEach(key => localStorage.removeItem(key));
    return keys.length;
}

// =============================================================================
// Pinned Items Helpers
// =============================================================================

/**
 * Get pinned conversation IDs from localStorage
 * @returns {Set<string>} Set of pinned conversation IDs
 */
export function getPinnedConversations() {
    try {
        const stored = localStorage.getItem(STORAGE_KEYS.PINNED_CONVERSATIONS);
        return new Set(stored ? JSON.parse(stored) : []);
    } catch (e) {
        return new Set();
    }
}

/**
 * Save pinned conversation IDs to localStorage
 * @param {Set<string>} pinnedIds - Set of pinned conversation IDs
 */
export function savePinnedConversations(pinnedIds) {
    localStorage.setItem(
        STORAGE_KEYS.PINNED_CONVERSATIONS,
        JSON.stringify([...pinnedIds])
    );
}

/**
 * Toggle a conversation's pinned state
 * @param {string} conversationId - Conversation ID
 * @returns {boolean} New pinned state
 */
export function togglePinnedConversation(conversationId) {
    const pinned = getPinnedConversations();
    if (pinned.has(conversationId)) {
        pinned.delete(conversationId);
    } else {
        pinned.add(conversationId);
    }
    savePinnedConversations(pinned);
    return pinned.has(conversationId);
}

/**
 * Get pinned session IDs from localStorage
 * @returns {Set<string>} Set of pinned session IDs
 */
export function getPinnedSessions() {
    try {
        const stored = localStorage.getItem(STORAGE_KEYS.PINNED_SESSIONS);
        return new Set(stored ? JSON.parse(stored) : []);
    } catch (e) {
        return new Set();
    }
}

/**
 * Save pinned session IDs to localStorage
 * @param {Set<string>} pinnedIds - Set of pinned session IDs
 */
export function savePinnedSessions(pinnedIds) {
    localStorage.setItem(
        STORAGE_KEYS.PINNED_SESSIONS,
        JSON.stringify([...pinnedIds])
    );
}

// =============================================================================
// Preference Helpers
// =============================================================================

/**
 * Get selected model from localStorage
 * @returns {string|null} Selected model ID
 */
export function getSelectedModel() {
    return localStorage.getItem(STORAGE_KEYS.SELECTED_MODEL);
}

/**
 * Save selected model to localStorage
 * @param {string} modelId - Model ID to save
 */
export function saveSelectedModel(modelId) {
    localStorage.setItem(STORAGE_KEYS.SELECTED_MODEL, modelId);
}

/**
 * Get sidebar collapsed state from localStorage
 * @returns {boolean} Whether sidebar is collapsed
 */
export function getSidebarCollapsed() {
    return localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true';
}

/**
 * Save sidebar collapsed state to localStorage
 * @param {boolean} collapsed - Whether sidebar is collapsed
 */
export function saveSidebarCollapsed(collapsed) {
    localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, collapsed.toString());
}

/**
 * Get theme preference from localStorage
 * @returns {string|null} Theme name ('light', 'dark', or null for system)
 */
export function getTheme() {
    return localStorage.getItem(STORAGE_KEYS.THEME);
}

/**
 * Save theme preference to localStorage
 * @param {string} theme - Theme name
 */
export function saveTheme(theme) {
    localStorage.setItem(STORAGE_KEYS.THEME, theme);
}

/**
 * Get selected definition ID from localStorage
 * @returns {string|null} Definition ID
 */
export function getSelectedDefinitionId() {
    return localStorage.getItem(STORAGE_KEYS.SELECTED_DEFINITION);
}

/**
 * Save selected definition ID to localStorage
 * @param {string} definitionId - Definition ID to save
 */
export function saveSelectedDefinitionId(definitionId) {
    localStorage.setItem(STORAGE_KEYS.SELECTED_DEFINITION, definitionId);
}
