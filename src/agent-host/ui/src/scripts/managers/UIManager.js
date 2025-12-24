/**
 * UIManager - Class-based UI state manager
 *
 * Handles UI state updates, status indicator, health check, and button states.
 *
 * Key responsibilities:
 * - Update UI based on authentication state
 * - Manage send/cancel button visibility
 * - Control status indicator
 * - Handle tool executing indicator
 * - Run health checks
 * - Manage input helpers
 * - Lock/unlock chat input for widgets
 *
 * @module managers/UIManager
 */

import { api } from '../services/api.js';
import { settingsService } from '../services/SettingsService.js';

/**
 * @class UIManager
 * @description Manages UI state and interactions
 */
export class UIManager {
    /**
     * Create UIManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {boolean} */
        this._isStreaming = false;

        /** @type {boolean} */
        this._chatInputLocked = false;

        /** @type {HTMLElement|null} */
        this._inputLockedMessage = null;

        /** @type {Object} DOM elements */
        this._elements = {
            userDropdown: null,
            themeToggle: null,
            dropdownUserName: null,
            loginBtn: null,
            messageInput: null,
            sendBtn: null,
            cancelBtn: null,
            statusIndicator: null,
            welcomeMessage: null,
            toolExecutingEl: null,
            chatForm: null,
        };
    }

    /**
     * Initialize UI manager with DOM elements
     * @param {Object} domElements - DOM element references
     */
    init(domElements = {}) {
        if (this._initialized) {
            console.warn('[UIManager] Already initialized');
            return;
        }

        this._elements = { ...this._elements, ...domElements };
        this._initialized = true;
        console.log('[UIManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._elements = {};
        this._isStreaming = false;
        this._chatInputLocked = false;
        this._inputLockedMessage = null;
        this._initialized = false;
        console.log('[UIManager] Destroyed');
    }

    // =========================================================================
    // UI State Updates
    // =========================================================================

    /**
     * Update UI based on authentication state
     * @param {boolean} isAuthenticated - Whether user is authenticated
     * @param {Object|null} currentUser - Current user object
     * @param {boolean} isAdmin - Whether user is admin
     * @param {string} toolsProviderUrl - Tools provider URL for admin settings
     */
    updateAuthUI(isAuthenticated, currentUser, isAdmin, toolsProviderUrl) {
        const userName = currentUser?.name || currentUser?.username || 'User';

        // Agent/mode selector - show when authenticated
        const agentSelector = document.getElementById('agent-selector');

        // Session type cards - show when authenticated
        const sessionTypeCards = document.getElementById('session-type-cards');

        if (isAuthenticated) {
            // Show user dropdown and theme toggle
            this._elements.userDropdown?.classList.remove('d-none');
            this._elements.themeToggle?.classList.remove('d-none');

            // Show agent selector when authenticated
            agentSelector?.classList.remove('d-none');

            // Show session type cards when authenticated
            sessionTypeCards?.classList.remove('d-none');

            // Show admin settings button if user is admin
            settingsService.updateAdminButtonVisibility(isAdmin, true, toolsProviderUrl);

            // Update username in dropdown
            if (this._elements.dropdownUserName) {
                this._elements.dropdownUserName.textContent = userName;
            }

            this._elements.loginBtn?.classList.add('d-none');
            if (this._elements.messageInput) this._elements.messageInput.disabled = false;
            this.updateSendButton(false);

            // Update login prompt - hide it when authenticated
            const loginPrompt = this._elements.welcomeMessage?.querySelector('.login-prompt');
            if (loginPrompt) {
                loginPrompt.classList.add('d-none');
            }

            // Note: Status indicator is driven by WebSocket events (connected/disconnected)
            // and Auth events (authenticated/unauthenticated) via ChatManager
        } else {
            this._elements.userDropdown?.classList.add('d-none');
            this._elements.themeToggle?.classList.add('d-none');

            // Hide agent selector when not authenticated
            agentSelector?.classList.add('d-none');

            // Hide session type cards when not authenticated
            sessionTypeCards?.classList.add('d-none');

            settingsService.updateAdminButtonVisibility(false, false);
            this._elements.loginBtn?.classList.remove('d-none');
            if (this._elements.messageInput) this._elements.messageInput.disabled = true;
            this.updateSendButton(true);

            // Note: Status indicator is driven by Auth events (unauthenticated)
            // via ChatManager

            // Show login prompt
            const loginPrompt = this._elements.welcomeMessage?.querySelector('.login-prompt');
            if (loginPrompt) {
                loginPrompt.classList.remove('d-none');
            }
        }
    }

    /**
     * Update send/cancel button visibility based on streaming state
     * @param {boolean} disabled - Whether send button should be disabled
     */
    updateSendButton(disabled) {
        if (this._elements.sendBtn) {
            this._elements.sendBtn.disabled = disabled;
            this._elements.sendBtn.classList.toggle('d-none', this._isStreaming);
        }
        if (this._elements.cancelBtn) {
            this._elements.cancelBtn.classList.toggle('d-none', !this._isStreaming);
        }
    }

    /**
     * Set streaming state for UI updates
     * @param {boolean} streaming - Whether currently streaming
     */
    setStreamingState(streaming) {
        this._isStreaming = streaming;
    }

    /**
     * Get streaming state
     * @returns {boolean}
     */
    isStreaming() {
        return this._isStreaming;
    }

    /**
     * Set status indicator state and text
     * @param {string} state - Status state (connected, disconnected, streaming)
     * @param {string} text - Status text
     */
    setStatus(state, text) {
        if (!this._elements.statusIndicator) return;
        this._elements.statusIndicator.className = `status-indicator ${state}`;
        const statusText = this._elements.statusIndicator.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = text;
        }
    }

    // =========================================================================
    // Tool Executing Indicator
    // =========================================================================

    /**
     * Show tool executing indicator in status bar
     * @param {string} toolName - Name of the tool being executed
     */
    showToolExecuting(toolName) {
        if (!this._elements.toolExecutingEl) return;

        const toolNameEl = this._elements.toolExecutingEl.querySelector('.tool-name');
        if (toolNameEl) {
            toolNameEl.textContent = toolName;
        }
        this._elements.toolExecutingEl.classList.remove('d-none');
    }

    /**
     * Hide tool executing indicator
     */
    hideToolExecuting() {
        if (!this._elements.toolExecutingEl) return;
        this._elements.toolExecutingEl.classList.add('d-none');
    }

    // =========================================================================
    // Health Check
    // =========================================================================

    /**
     * Run health check and update the health icon color
     */
    async runHealthCheck() {
        const healthLink = document.getElementById('health-link');
        if (!healthLink) return;

        // Remove previous health status classes and add checking state
        healthLink.classList.remove('health-healthy', 'health-degraded', 'health-unhealthy', 'health-error', 'health-unknown');
        healthLink.classList.add('health-checking');

        try {
            const health = await api.checkHealth();
            healthLink.classList.remove('health-checking');

            // Map overall_status to CSS class
            const status = health.overall_status || 'unknown';
            healthLink.classList.add(`health-${status}`);

            // Update tooltip
            const statusText = status.charAt(0).toUpperCase() + status.slice(1);
            healthLink.title = `Service Health: ${statusText}`;
        } catch (error) {
            console.error('Health check failed:', error);
            healthLink.classList.remove('health-checking');
            healthLink.classList.add('health-error');
            healthLink.title = 'Service Health: Error';
        }
    }

    // =========================================================================
    // Input Helpers
    // =========================================================================

    /**
     * Auto-resize message input based on content
     */
    autoResizeInput() {
        if (!this._elements.messageInput) return;
        this._elements.messageInput.style.height = 'auto';
        this._elements.messageInput.style.height = Math.min(this._elements.messageInput.scrollHeight, 120) + 'px';
    }

    /**
     * Clear and disable message input
     */
    clearAndDisableInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.value = '';
            this._elements.messageInput.disabled = true;
        }
        this.autoResizeInput();
    }

    /**
     * Enable message input and focus
     */
    enableAndFocusInput() {
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = false;
            this._elements.messageInput.focus();
        }
    }

    /**
     * Get message input value
     * @returns {string} Trimmed input value
     */
    getInputValue() {
        return this._elements.messageInput?.value.trim() || '';
    }

    /**
     * Set message input value
     * @param {string} value - Input value
     */
    setInputValue(value) {
        if (this._elements.messageInput) {
            this._elements.messageInput.value = value;
        }
    }

    /**
     * Hide welcome message
     */
    hideWelcomeMessage() {
        if (this._elements.welcomeMessage) {
            this._elements.welcomeMessage.style.display = 'none';
        }
    }

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        if (this._elements.welcomeMessage) {
            this._elements.welcomeMessage.style.display = '';
        }
    }

    // =========================================================================
    // Chat Input Lock (for Client Actions)
    // =========================================================================

    /**
     * Lock the chat input while a widget is active or session is starting
     * Shows a visual indicator that input is disabled
     * @param {string} [message] - Optional custom message to display
     */
    lockChatInput(message = 'Please respond to the widget above...') {
        this._chatInputLocked = true;

        // Hide the entire chat form
        if (this._elements.chatForm) {
            this._elements.chatForm.classList.add('d-none');
        }

        // Create and show the locked message if it doesn't exist
        if (!this._inputLockedMessage) {
            this._inputLockedMessage = document.createElement('div');
            this._inputLockedMessage.className = 'input-locked-message';
            this._inputLockedMessage.id = 'input-locked-message';
            // Insert after the chat form
            this._elements.chatForm?.parentNode?.insertBefore(this._inputLockedMessage, this._elements.chatForm.nextSibling);
        }

        // Update message content
        this._inputLockedMessage.innerHTML = `
            <i class="bi bi-hourglass-split"></i>
            <span>${message}</span>
        `;
        this._inputLockedMessage.classList.remove('d-none');
    }

    /**
     * Unlock the chat input after widget response
     */
    unlockChatInput() {
        this._chatInputLocked = false;

        // Show the chat form
        if (this._elements.chatForm) {
            this._elements.chatForm.classList.remove('d-none');
        }

        // Hide the locked message
        if (this._inputLockedMessage) {
            this._inputLockedMessage.classList.add('d-none');
        }

        // Re-enable and focus input
        if (this._elements.messageInput) {
            this._elements.messageInput.disabled = false;
            this._elements.messageInput.placeholder = 'Type a message...';
            this._elements.messageInput.classList.remove('input-locked');
            this._elements.messageInput.focus();
        }
        if (this._elements.sendBtn) {
            this._elements.sendBtn.disabled = false;
        }
    }

    /**
     * Check if chat input is currently locked
     * @returns {boolean}
     */
    isChatInputLocked() {
        return this._chatInputLocked;
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
export const uiManager = new UIManager();
export default uiManager;
