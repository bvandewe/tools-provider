/**
 * UI Managers Index
 *
 * Aggregates all UI managers for convenient import.
 *
 * @module ui/managers
 */

// Chat manager
export {
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
} from './chat-manager.js';

// Sidebar manager
export {
    initSidebarManager,
    updateAuthState as updateSidebarAuthState,
    expandSidebar,
    collapseSidebar,
    closeSidebar,
    toggleSidebar,
    handleResize as handleSidebarResize,
    isSidebarCollapsed,
} from './sidebar-manager.js';
