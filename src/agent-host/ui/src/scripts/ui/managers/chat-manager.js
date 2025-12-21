/**
 * Chat Manager - Chat UI State Management
 *
 * Manages DOM elements and UI state for the chat interface.
 * Listens to events from domain/protocol layers and updates DOM.
 *
 * @module ui/managers/chat-manager
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager, StateKeys } from '../../core/state-manager.js';
import { scrollToBottom, isNearBottom } from '../../utils/dom.js';

// =============================================================================
// State
// =============================================================================

/** @type {Object} DOM element references */
let elements = {
    messagesContainer: null,
    welcomeMessage: null,
    chatForm: null,
    messageInput: null,
    sendBtn: null,
    cancelBtn: null,
    statusIndicator: null,
    attachedFilesContainer: null,
};

/** @type {boolean} User has scrolled up during streaming */
let userScrolledUp = false;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize chat manager with DOM elements
 * @param {Object} domElements - DOM element references
 */
export function initChatManager(domElements) {
    elements = { ...elements, ...domElements };

    // Subscribe to events
    subscribeToEvents();

    console.log('[ChatManager] Initialized');
}

/**
 * Subscribe to event bus events
 */
function subscribeToEvents() {
    // Streaming state changes
    eventBus.on(Events.UI_STREAMING_STATE, ({ isStreaming }) => {
        updateStreamingState(isStreaming);
    });

    // Status changes
    eventBus.on(Events.UI_STATUS_CHANGED, ({ status, message }) => {
        updateStatusIndicator(status, message);
    });

    // Message streaming - auto scroll
    eventBus.on(Events.MESSAGE_STREAMING, () => {
        if (!userScrolledUp) {
            scrollToBottom(elements.messagesContainer);
        }
    });

    // Message complete - scroll to bottom
    eventBus.on(Events.MESSAGE_COMPLETE, () => {
        scrollToBottom(elements.messagesContainer);
        userScrolledUp = false;
    });

    // Widget rendered - scroll to bottom
    eventBus.on(Events.WIDGET_RENDERED, () => {
        scrollToBottom(elements.messagesContainer);
    });
}

// =============================================================================
// UI State Updates
// =============================================================================

/**
 * Update streaming state UI
 * @param {boolean} isStreaming - Whether currently streaming
 */
export function updateStreamingState(isStreaming) {
    stateManager.set(StateKeys.IS_STREAMING, isStreaming);

    if (elements.sendBtn) {
        elements.sendBtn.classList.toggle('d-none', isStreaming);
        elements.sendBtn.disabled = isStreaming;
    }
    if (elements.cancelBtn) {
        elements.cancelBtn.classList.toggle('d-none', !isStreaming);
    }
    if (elements.messageInput) {
        elements.messageInput.disabled = isStreaming;
    }
}

/**
 * Update send button state
 * @param {boolean} isStreaming - Whether currently streaming
 */
export function updateSendButton(isStreaming) {
    updateStreamingState(isStreaming);
}

/**
 * Update status indicator
 * @param {string} status - Status code
 * @param {string} message - Status message
 */
export function updateStatusIndicator(status, message) {
    if (!elements.statusIndicator) return;

    // Update indicator class
    elements.statusIndicator.className = 'status-indicator';
    elements.statusIndicator.classList.add(`status-${status}`);

    // Update tooltip
    elements.statusIndicator.title = message;
}

// =============================================================================
// Welcome Message
// =============================================================================

/**
 * Show welcome message
 */
export function showWelcomeMessage() {
    if (elements.welcomeMessage) {
        elements.welcomeMessage.classList.remove('d-none');
    }
    if (elements.messagesContainer) {
        elements.messagesContainer.innerHTML = '';
    }
}

/**
 * Hide welcome message
 */
export function hideWelcomeMessage() {
    if (elements.welcomeMessage) {
        elements.welcomeMessage.classList.add('d-none');
    }
}

// =============================================================================
// Input Management
// =============================================================================

/**
 * Get current input value
 * @returns {string} Input value
 */
export function getInputValue() {
    return elements.messageInput?.value?.trim() || '';
}

/**
 * Set input value
 * @param {string} value - Value to set
 */
export function setInputValue(value) {
    if (elements.messageInput) {
        elements.messageInput.value = value;
        autoResizeInput();
    }
}

/**
 * Clear input
 */
export function clearInput() {
    if (elements.messageInput) {
        elements.messageInput.value = '';
        autoResizeInput();
    }
}

/**
 * Focus input
 */
export function focusInput() {
    elements.messageInput?.focus();
}

/**
 * Disable input
 * @param {string} [placeholder] - Optional placeholder while disabled
 */
export function disableInput(placeholder) {
    if (elements.messageInput) {
        elements.messageInput.disabled = true;
        if (placeholder) {
            elements.messageInput.placeholder = placeholder;
        }
    }
}

/**
 * Enable input
 * @param {string} [placeholder] - Optional new placeholder
 */
export function enableInput(placeholder) {
    if (elements.messageInput) {
        elements.messageInput.disabled = false;
        if (placeholder) {
            elements.messageInput.placeholder = placeholder;
        }
    }
}

/**
 * Clear and disable input
 */
export function clearAndDisableInput() {
    clearInput();
    disableInput();
}

/**
 * Enable and focus input
 * @param {string} [placeholder] - Optional placeholder
 */
export function enableAndFocusInput(placeholder) {
    enableInput(placeholder);
    focusInput();
}

/**
 * Lock chat input (widget mode)
 * @param {string} placeholder - Placeholder text
 */
export function lockChatInput(placeholder) {
    disableInput(placeholder);
    if (elements.chatForm) {
        elements.chatForm.classList.add('input-locked');
    }
}

/**
 * Unlock chat input
 */
export function unlockChatInput() {
    enableInput('Type a message...');
    if (elements.chatForm) {
        elements.chatForm.classList.remove('input-locked');
    }
}

/**
 * Auto-resize textarea input
 */
export function autoResizeInput() {
    const input = elements.messageInput;
    if (!input) return;

    // Reset height to auto to get the correct scrollHeight
    input.style.height = 'auto';

    // Calculate new height (capped at max)
    const maxHeight = 200;
    const newHeight = Math.min(input.scrollHeight, maxHeight);

    input.style.height = `${newHeight}px`;
    input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
}

// =============================================================================
// Scroll Management
// =============================================================================

/**
 * Handle user scroll during streaming
 * @param {boolean} isStreaming - Whether currently streaming
 */
export function handleUserScroll(isStreaming) {
    if (!isStreaming) return;

    // If user scrolled up, don't auto-scroll
    userScrolledUp = !isNearBottom(elements.messagesContainer);
}

/**
 * Reset user scroll state
 */
export function resetUserScroll() {
    userScrolledUp = false;
}

/**
 * Get messages container element
 * @returns {HTMLElement|null} Messages container
 */
export function getMessagesContainer() {
    return elements.messagesContainer;
}

export default {
    initChatManager,
    updateStreamingState,
    updateSendButton,
    updateStatusIndicator,
    showWelcomeMessage,
    hideWelcomeMessage,
    getInputValue,
    setInputValue,
    clearInput,
    focusInput,
    disableInput,
    enableInput,
    clearAndDisableInput,
    enableAndFocusInput,
    lockChatInput,
    unlockChatInput,
    autoResizeInput,
    handleUserScroll,
    resetUserScroll,
    getMessagesContainer,
};
