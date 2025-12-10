/**
 * Draft Manager for Agent Host
 *
 * Manages persistence of unsent message drafts to localStorage.
 * Drafts are automatically saved when typing and restored after login.
 * Using localStorage (instead of sessionStorage) ensures drafts survive:
 * - Token refresh cycles
 * - Browser tab closes/reopens
 * - Session expiration and re-login
 *
 * Storage key format: agent-host:draft:{conversationId|'new'}
 *
 * Features:
 * - Auto-save drafts on input change (debounced)
 * - Restore drafts after page reload or re-login
 * - Clear drafts when message is sent
 * - Track "dirty" state for session protection
 * - saveImmediately() for pre-logout preservation
 */

// =============================================================================
// Configuration
// =============================================================================

const STORAGE_PREFIX = 'agent-host:draft:';
const DEBOUNCE_MS = 500; // Save after 500ms of no typing

// =============================================================================
// State
// =============================================================================

let inputElement = null;
let currentConversationId = null;
let saveTimeout = null;
let isDirty = false;

// =============================================================================
// Storage Helpers
// =============================================================================

/**
 * Get the storage key for a conversation
 * @param {string|null} conversationId - Conversation ID or null for new conversation
 * @returns {string} Storage key
 */
function getStorageKey(conversationId) {
    return `${STORAGE_PREFIX}${conversationId || 'new'}`;
}

/**
 * Save draft to localStorage
 * @param {string|null} conversationId - Conversation ID
 * @param {string} content - Draft content
 */
function saveDraftToStorage(conversationId, content) {
    const key = getStorageKey(conversationId);
    if (content && content.trim()) {
        localStorage.setItem(key, content);
        console.log(`[DraftManager] Saved draft for ${conversationId || 'new'} (${content.length} chars)`);
    } else {
        localStorage.removeItem(key);
    }
}

/**
 * Load draft from localStorage
 * @param {string|null} conversationId - Conversation ID
 * @returns {string|null} Draft content or null
 */
function loadDraftFromStorage(conversationId) {
    const key = getStorageKey(conversationId);
    return localStorage.getItem(key);
}

/**
 * Clear draft from localStorage
 * @param {string|null} conversationId - Conversation ID
 */
function clearDraftFromStorage(conversationId) {
    const key = getStorageKey(conversationId);
    localStorage.removeItem(key);
    console.log(`[DraftManager] Cleared draft for ${conversationId || 'new'}`);
}

/**
 * Clear all drafts from localStorage
 */
function clearAllDrafts() {
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(STORAGE_PREFIX)) {
            keysToRemove.push(key);
        }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    console.log(`[DraftManager] Cleared ${keysToRemove.length} draft(s)`);
}

// =============================================================================
// Input Tracking
// =============================================================================

/**
 * Handle input change - save draft with debounce
 */
function handleInputChange() {
    if (!inputElement) return;

    const content = inputElement.value;
    isDirty = content && content.trim().length > 0;

    // Clear existing timeout
    if (saveTimeout) {
        clearTimeout(saveTimeout);
    }

    // Debounce save
    saveTimeout = setTimeout(() => {
        saveDraftToStorage(currentConversationId, content);
    }, DEBOUNCE_MS);
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Initialize draft manager
 * @param {HTMLTextAreaElement} input - The message input element
 */
export function initDraftManager(input) {
    inputElement = input;

    if (inputElement) {
        inputElement.addEventListener('input', handleInputChange);
        console.log('[DraftManager] Initialized');
    }
}

/**
 * Stop draft manager and cleanup
 */
export function stopDraftManager() {
    if (inputElement) {
        inputElement.removeEventListener('input', handleInputChange);
    }

    if (saveTimeout) {
        clearTimeout(saveTimeout);
        saveTimeout = null;
    }

    inputElement = null;
    currentConversationId = null;
    isDirty = false;

    console.log('[DraftManager] Stopped');
}

/**
 * Set the current conversation ID
 * Also restores any saved draft for the conversation
 * @param {string|null} conversationId - New conversation ID
 * @returns {string|null} Restored draft content, if any
 */
export function setConversation(conversationId) {
    // Save current draft before switching
    if (inputElement && inputElement.value) {
        saveDraftToStorage(currentConversationId, inputElement.value);
    }

    currentConversationId = conversationId;

    // Load draft for new conversation
    const draft = loadDraftFromStorage(conversationId);
    isDirty = draft && draft.trim().length > 0;

    return draft;
}

/**
 * Save the current draft immediately (no debounce)
 * Call this before session expiration redirect
 */
export function saveCurrentDraft() {
    if (saveTimeout) {
        clearTimeout(saveTimeout);
        saveTimeout = null;
    }

    if (inputElement && inputElement.value) {
        saveDraftToStorage(currentConversationId, inputElement.value);
        return true;
    }
    return false;
}

/**
 * Restore draft for current conversation
 * @returns {string|null} Draft content, if any
 */
export function restoreDraft() {
    const draft = loadDraftFromStorage(currentConversationId);

    if (draft && inputElement) {
        inputElement.value = draft;
        isDirty = true;
        // Trigger resize if needed
        inputElement.dispatchEvent(new Event('input', { bubbles: true }));
    }

    return draft;
}

/**
 * Clear draft for current conversation
 * Call this after successfully sending a message
 */
export function clearCurrentDraft() {
    if (saveTimeout) {
        clearTimeout(saveTimeout);
        saveTimeout = null;
    }

    clearDraftFromStorage(currentConversationId);
    isDirty = false;
}

/**
 * Check if there's an unsaved/unsent draft
 * @returns {boolean} True if input has content
 */
export function hasDraft() {
    return isDirty;
}

/**
 * Get current draft content without saving
 * @returns {string} Current input value
 */
export function getCurrentDraft() {
    return inputElement ? inputElement.value : '';
}

/**
 * Get the current conversation ID
 * @returns {string|null}
 */
export function getCurrentConversationId() {
    return currentConversationId;
}

/**
 * Clear all stored drafts
 * Call this on explicit logout
 */
export function clearAllStoredDrafts() {
    clearAllDrafts();
    isDirty = false;
}
