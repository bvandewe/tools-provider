/**
 * Utility helpers for the Agent Host UI
 */

// =============================================================================
// Constants
// =============================================================================

export const STORAGE_KEYS = {
    SIDEBAR_COLLAPSED: 'agent-host:sidebar-collapsed',
    SELECTED_MODEL: 'agent-host:selected-model',
    PINNED_CONVERSATIONS: 'agent-host:pinned-conversations',
};

export const MOBILE_BREAKPOINT = 768;

// =============================================================================
// HTML Helpers
// =============================================================================

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// Storage Helpers
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
    localStorage.setItem(STORAGE_KEYS.PINNED_CONVERSATIONS, JSON.stringify([...pinnedIds]));
}

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

// =============================================================================
// Device Helpers
// =============================================================================

/**
 * Check if current viewport is mobile
 * @returns {boolean} True if mobile viewport
 */
export function isMobile() {
    return window.innerWidth < MOBILE_BREAKPOINT;
}
