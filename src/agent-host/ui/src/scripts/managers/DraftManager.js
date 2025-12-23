/**
 * DraftManager - Class-based draft persistence manager
 *
 * Manages persistence of unsent message drafts to localStorage.
 * Drafts are automatically saved when typing and restored after login.
 *
 * Features:
 * - Auto-save drafts on input change (debounced)
 * - Restore drafts after page reload or re-login
 * - Clear drafts when message is sent
 * - Track "dirty" state for session protection
 *
 * @module managers/DraftManager
 */

const STORAGE_PREFIX = 'agent-host:draft:';
const DEBOUNCE_MS = 500;

/**
 * @class DraftManager
 * @description Manages message draft persistence
 */
export class DraftManager {
    /**
     * Create DraftManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {HTMLTextAreaElement|null} */
        this._inputElement = null;

        /** @type {string|null} */
        this._currentConversationId = null;

        /** @type {number|null} */
        this._saveTimeout = null;

        /** @type {boolean} */
        this._isDirty = false;

        // Bind methods
        this._handleInputChange = this._handleInputChange.bind(this);
    }

    /**
     * Initialize draft manager
     * @param {HTMLTextAreaElement} input - The message input element
     */
    init(input) {
        if (this._initialized) {
            console.warn('[DraftManager] Already initialized');
            return;
        }

        this._inputElement = input;

        if (this._inputElement) {
            this._inputElement.addEventListener('input', this._handleInputChange);
        }

        this._initialized = true;
        console.log('[DraftManager] Initialized');
    }

    /**
     * Stop draft manager and cleanup
     */
    destroy() {
        if (this._inputElement) {
            this._inputElement.removeEventListener('input', this._handleInputChange);
        }

        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
            this._saveTimeout = null;
        }

        this._inputElement = null;
        this._currentConversationId = null;
        this._isDirty = false;
        this._initialized = false;

        console.log('[DraftManager] Destroyed');
    }

    // =========================================================================
    // Storage Helpers
    // =========================================================================

    /**
     * Get the storage key for a conversation
     * @private
     */
    _getStorageKey(conversationId) {
        return `${STORAGE_PREFIX}${conversationId || 'new'}`;
    }

    /**
     * Save draft to localStorage
     * @private
     */
    _saveDraftToStorage(conversationId, content) {
        const key = this._getStorageKey(conversationId);
        if (content && content.trim()) {
            localStorage.setItem(key, content);
            console.log(`[DraftManager] Saved draft for ${conversationId || 'new'} (${content.length} chars)`);
        } else {
            localStorage.removeItem(key);
        }
    }

    /**
     * Load draft from localStorage
     * @private
     */
    _loadDraftFromStorage(conversationId) {
        const key = this._getStorageKey(conversationId);
        return localStorage.getItem(key);
    }

    /**
     * Clear draft from localStorage
     * @private
     */
    _clearDraftFromStorage(conversationId) {
        const key = this._getStorageKey(conversationId);
        localStorage.removeItem(key);
        console.log(`[DraftManager] Cleared draft for ${conversationId || 'new'}`);
    }

    // =========================================================================
    // Input Tracking
    // =========================================================================

    /**
     * Handle input change - save draft with debounce
     * @private
     */
    _handleInputChange() {
        if (!this._inputElement) return;

        const content = this._inputElement.value;
        this._isDirty = content && content.trim().length > 0;

        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
        }

        this._saveTimeout = setTimeout(() => {
            this._saveDraftToStorage(this._currentConversationId, content);
        }, DEBOUNCE_MS);
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Set the current conversation ID
     * Also restores any saved draft for the conversation
     * @param {string|null} conversationId - New conversation ID
     * @returns {string|null} Restored draft content, if any
     */
    setConversation(conversationId) {
        // Save current draft before switching
        if (this._inputElement && this._inputElement.value) {
            this._saveDraftToStorage(this._currentConversationId, this._inputElement.value);
        }

        this._currentConversationId = conversationId;

        // Load draft for new conversation
        const draft = this._loadDraftFromStorage(conversationId);
        this._isDirty = draft && draft.trim().length > 0;

        return draft;
    }

    /**
     * Save the current draft immediately (no debounce)
     * @returns {boolean} True if saved
     */
    saveCurrentDraft() {
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
            this._saveTimeout = null;
        }

        if (this._inputElement && this._inputElement.value) {
            this._saveDraftToStorage(this._currentConversationId, this._inputElement.value);
            return true;
        }
        return false;
    }

    /**
     * Restore draft for current conversation
     * @returns {string|null} Draft content, if any
     */
    restoreDraft() {
        const draft = this._loadDraftFromStorage(this._currentConversationId);

        if (draft && this._inputElement) {
            this._inputElement.value = draft;
            this._isDirty = true;
            this._inputElement.dispatchEvent(new Event('input', { bubbles: true }));
        }

        return draft;
    }

    /**
     * Clear draft for current conversation
     */
    clearCurrentDraft() {
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
            this._saveTimeout = null;
        }

        this._clearDraftFromStorage(this._currentConversationId);
        this._isDirty = false;
    }

    /**
     * Check if there's an unsaved/unsent draft
     * @returns {boolean}
     */
    hasDraft() {
        return this._isDirty;
    }

    /**
     * Get current draft content without saving
     * @returns {string}
     */
    getCurrentDraft() {
        return this._inputElement ? this._inputElement.value : '';
    }

    /**
     * Get the current conversation ID
     * @returns {string|null}
     */
    getCurrentConversationId() {
        return this._currentConversationId;
    }

    /**
     * Clear all stored drafts
     */
    clearAllStoredDrafts() {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(STORAGE_PREFIX)) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));
        this._isDirty = false;
        console.log(`[DraftManager] Cleared ${keysToRemove.length} draft(s)`);
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const draftManager = new DraftManager();
export default draftManager;
