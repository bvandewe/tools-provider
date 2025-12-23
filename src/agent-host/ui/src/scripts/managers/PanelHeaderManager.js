/**
 * PanelHeaderManager - Conversation Header UI
 *
 * Manages the ax-conversation-header component including:
 * - Progress indicator (current/total items)
 * - Panel title
 * - Score display
 *
 * @module managers/PanelHeaderManager
 */

import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * PanelHeaderManager manages the conversation header component
 */
export class PanelHeaderManager {
    /**
     * Create a new PanelHeaderManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {HTMLElement|null} Messages container reference for header insertion */
        this._messagesContainer = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize panel header manager
     * @param {HTMLElement} container - Messages container element (for header insertion)
     */
    init(container) {
        if (this._initialized) {
            console.warn('[PanelHeaderManager] Already initialized');
            return;
        }

        this._messagesContainer = container;
        this._initialized = true;

        console.log('[PanelHeaderManager] Initialized');
    }

    // =========================================================================
    // Header Management
    // =========================================================================

    /**
     * Get or create the conversation header element
     * @returns {HTMLElement} The ax-conversation-header element
     * @private
     */
    _getOrCreateHeader() {
        let header = document.querySelector('ax-conversation-header');
        if (!header) {
            header = document.createElement('ax-conversation-header');
            // Insert header at the top of the messages container
            if (this._messagesContainer) {
                this._messagesContainer.parentElement?.insertBefore(header, this._messagesContainer);
            }
        }
        return header;
    }

    /**
     * Update the conversation header progress indicator
     * @param {number} current - Current item index (0-based)
     * @param {number} total - Total number of items
     * @param {string} [label] - Optional label for the progress
     */
    updateProgress(current, total, label) {
        console.log('[PanelHeaderManager] updateProgress:', { current, total, label });

        const header = this._getOrCreateHeader();

        // Update header attributes
        header.setAttribute('current-item', String(current));
        header.setAttribute('total-items', String(total));
        header.setAttribute('show-progress', 'true');

        if (label) {
            header.setAttribute('title', label);
        }

        // Store in state manager for persistence
        stateManager.set(StateKeys.TEMPLATE_PROGRESS, { current, total, label });
    }

    /**
     * Update the conversation header title
     * @param {string} text - Title text
     * @param {boolean} visible - Whether to show the title
     */
    updatePanelTitle(text, visible) {
        console.log('[PanelHeaderManager] updatePanelTitle:', { text, visible });

        const header = document.querySelector('ax-conversation-header');
        if (header) {
            if (visible && text) {
                header.setAttribute('title', text);
            } else {
                header.removeAttribute('title');
            }
        }
    }

    /**
     * Update the conversation header score display
     * @param {number} current - Current score
     * @param {number} max - Maximum possible score
     * @param {string} [label] - Score label
     * @param {boolean} visible - Whether to show the score
     */
    updatePanelScore(current, max, label, visible) {
        console.log('[PanelHeaderManager] updatePanelScore:', { current, max, label, visible });

        // Store in state and let the header component render it
        stateManager.set('panelScore', { current, max, label, visible });

        // TODO: Extend ax-conversation-header to display score
    }

    /**
     * Remove the conversation header
     */
    removeHeader() {
        const header = document.querySelector('ax-conversation-header');
        if (header) {
            header.remove();
        }
    }

    // =========================================================================
    // Getters
    // =========================================================================

    /**
     * Check if initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this.removeHeader();
        this._messagesContainer = null;
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const panelHeaderManager = new PanelHeaderManager();
