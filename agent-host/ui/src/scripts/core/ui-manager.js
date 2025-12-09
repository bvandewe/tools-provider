/**
 * UI Manager
 * Handles UI state updates, status indicator, health check, and button states
 */

import { api } from '../services/api.js';
import { updateAdminButtonVisibility } from '../services/settings.js';

// =============================================================================
// State
// =============================================================================

let elements = {
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
};

let isStreaming = false;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize UI manager with DOM elements
 * @param {Object} domElements - DOM element references
 */
export function initUIManager(domElements) {
    elements = { ...domElements };
}

// =============================================================================
// UI State Updates
// =============================================================================

/**
 * Update UI based on authentication state
 * @param {boolean} isAuthenticated - Whether user is authenticated
 * @param {Object|null} currentUser - Current user object
 * @param {boolean} isAdmin - Whether user is admin
 * @param {string} toolsProviderUrl - Tools provider URL for admin settings
 */
export function updateAuthUI(isAuthenticated, currentUser, isAdmin, toolsProviderUrl) {
    const userName = currentUser?.name || currentUser?.username || 'User';

    if (isAuthenticated) {
        // Show user dropdown and theme toggle
        elements.userDropdown?.classList.remove('d-none');
        elements.themeToggle?.classList.remove('d-none');

        // Show admin settings button if user is admin
        updateAdminButtonVisibility(isAdmin, true, toolsProviderUrl);

        // Update username in dropdown
        if (elements.dropdownUserName) {
            elements.dropdownUserName.textContent = userName;
        }

        elements.loginBtn?.classList.add('d-none');
        if (elements.messageInput) elements.messageInput.disabled = false;
        updateSendButton(false);

        // Update login prompt - remove animation and change text
        const loginPrompt = elements.welcomeMessage?.querySelector('.login-prompt');
        if (loginPrompt) {
            loginPrompt.classList.remove('login-prompt');
            loginPrompt.innerHTML = 'Type a message to start chatting.';
        }

        setStatus('connected', 'Connected');
    } else {
        elements.userDropdown?.classList.add('d-none');
        elements.themeToggle?.classList.add('d-none');
        updateAdminButtonVisibility(false, false);
        elements.loginBtn?.classList.remove('d-none');
        if (elements.messageInput) elements.messageInput.disabled = true;
        updateSendButton(true);
        setStatus('disconnected', 'Not authenticated');
    }
}

/**
 * Update send/cancel button visibility based on streaming state
 * @param {boolean} disabled - Whether send button should be disabled
 */
export function updateSendButton(disabled) {
    if (elements.sendBtn) {
        elements.sendBtn.disabled = disabled;
        elements.sendBtn.classList.toggle('d-none', isStreaming);
    }
    if (elements.cancelBtn) {
        elements.cancelBtn.classList.toggle('d-none', !isStreaming);
    }
}

/**
 * Set streaming state for UI updates
 * @param {boolean} streaming - Whether currently streaming
 */
export function setStreamingState(streaming) {
    isStreaming = streaming;
}

/**
 * Set status indicator state and text
 * @param {string} state - Status state (connected, disconnected, streaming)
 * @param {string} text - Status text
 */
export function setStatus(state, text) {
    if (!elements.statusIndicator) return;
    elements.statusIndicator.className = `status-indicator ${state}`;
    const statusText = elements.statusIndicator.querySelector('.status-text');
    if (statusText) {
        statusText.textContent = text;
    }
}

// =============================================================================
// Tool Executing Indicator
// =============================================================================

/**
 * Show tool executing indicator in status bar
 * @param {string} toolName - Name of the tool being executed
 */
export function showToolExecuting(toolName) {
    if (!elements.toolExecutingEl) return;

    const toolNameEl = elements.toolExecutingEl.querySelector('.tool-name');
    if (toolNameEl) {
        toolNameEl.textContent = toolName;
    }
    elements.toolExecutingEl.classList.remove('d-none');
}

/**
 * Hide tool executing indicator
 */
export function hideToolExecuting() {
    if (!elements.toolExecutingEl) return;
    elements.toolExecutingEl.classList.add('d-none');
}

// =============================================================================
// Health Check
// =============================================================================

/**
 * Run health check and update the health icon color
 */
export async function runHealthCheck() {
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

// =============================================================================
// Input Helpers
// =============================================================================

/**
 * Auto-resize message input based on content
 */
export function autoResizeInput() {
    if (!elements.messageInput) return;
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 120) + 'px';
}

/**
 * Clear and disable message input
 */
export function clearAndDisableInput() {
    if (elements.messageInput) {
        elements.messageInput.value = '';
        elements.messageInput.disabled = true;
    }
    autoResizeInput();
}

/**
 * Enable message input and focus
 */
export function enableAndFocusInput() {
    if (elements.messageInput) {
        elements.messageInput.disabled = false;
        elements.messageInput.focus();
    }
}

/**
 * Get message input value
 * @returns {string} Trimmed input value
 */
export function getInputValue() {
    return elements.messageInput?.value.trim() || '';
}

/**
 * Hide welcome message
 */
export function hideWelcomeMessage() {
    if (elements.welcomeMessage) {
        elements.welcomeMessage.style.display = 'none';
    }
}

/**
 * Show welcome message
 */
export function showWelcomeMessage() {
    if (elements.welcomeMessage) {
        elements.welcomeMessage.style.display = '';
    }
}
