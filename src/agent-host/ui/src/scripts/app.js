/**
 * ChatApp - Main Application Class
 * Orchestrates the chat interface by coordinating modular components
 */
import { api } from './services/api.js';
import { initModals, showToolsModal, showToast, showHealthModal } from './services/modals.js';
import { initSettings } from './services/settings.js';
import { startSessionMonitoring, stopSessionMonitoring, enableProtection, disableProtection, hasPendingExpiration } from './core/session-manager.js';
import { initDraftManager, stopDraftManager, saveCurrentDraft, restoreDraft, clearCurrentDraft, hasDraft, clearAllStoredDrafts } from './core/draft-manager.js';
import { initSidebarManager, updateAuthState as updateSidebarAuth, collapseSidebar, expandSidebar, closeSidebar, handleResize as handleSidebarResize } from './core/sidebar-manager.js';
import { loadAppConfig, handleModelChange, getAppConfig, getSelectedModelId } from './core/config-manager.js';
import {
    initUIManager,
    updateAuthUI,
    updateSendButton,
    setStreamingState,
    setStatus,
    runHealthCheck,
    autoResizeInput,
    clearAndDisableInput,
    enableAndFocusInput,
    getInputValue,
    hideWelcomeMessage,
    showWelcomeMessage,
} from './core/ui-manager.js';
import { initMessageRenderer, addUserMessage, addThinkingMessage, handleUserScroll as handleMessageScroll, resetUserScroll } from './core/message-renderer.js';
import { sendMessage, cancelCurrentRequest, isStreaming, setStreamCallbacks } from './core/stream-handler.js';
import { initConversationManager, loadConversations, loadConversation, newConversation, getCurrentConversationId, setCurrentConversationId } from './core/conversation-manager.js';

// =============================================================================
// ChatApp Class
// =============================================================================

export class ChatApp {
    constructor() {
        this.isAuthenticated = false;
        this.currentUser = null;
        this.availableTools = null;
    }

    async init() {
        // Get DOM elements
        const elements = this.getDOMElements();

        // Initialize modals
        initModals();

        // Initialize settings service (admin only)
        initSettings(() => this.isAdmin());

        // Load app configuration first
        await loadAppConfig(elements.modelSelector);

        // Initialize UI manager
        initUIManager({
            userDropdown: elements.userDropdown,
            themeToggle: elements.themeToggle,
            dropdownUserName: elements.dropdownUserName,
            loginBtn: elements.loginBtn,
            messageInput: elements.messageInput,
            sendBtn: elements.sendBtn,
            cancelBtn: elements.cancelBtn,
            statusIndicator: elements.statusIndicator,
            welcomeMessage: elements.welcomeMessage,
            toolExecutingEl: elements.toolExecutingEl,
        });

        // Initialize sidebar manager
        initSidebarManager(
            {
                chatSidebar: elements.chatSidebar,
                sidebarOverlay: elements.sidebarOverlay,
                sidebarToggleBtn: elements.sidebarToggleBtn,
                collapseSidebarBtn: elements.collapseSidebarBtn,
                headerNewChatBtn: elements.headerNewChatBtn,
            },
            this.isAuthenticated
        );

        // Initialize message renderer
        initMessageRenderer(elements.messagesContainer, elements.welcomeMessage, () => this.isAdmin());

        // Initialize conversation manager
        initConversationManager(
            {
                conversationList: elements.conversationList,
                welcomeMessage: elements.welcomeMessage,
                messageInput: elements.messageInput,
            },
            {
                onLoad: conversationId => setCurrentConversationId(conversationId),
                updateSessionProtection: () => this.updateSessionProtection(),
                autoResize: () => autoResizeInput(),
            }
        );

        // Set stream callbacks
        setStreamCallbacks({
            onConversationCreated: conversationId => {
                setCurrentConversationId(conversationId);
                loadConversations();
            },
            onStreamComplete: () => loadConversations(),
        });

        // Set up unauthorized handler for automatic logout
        api.setUnauthorizedHandler(() => this.handleSessionExpired());

        // Bind events
        this.bindEvents(elements);

        // Check authentication
        await this.checkAuth(elements.messageInput);

        // Store reference to message input for later use
        this.messageInput = elements.messageInput;
    }

    /**
     * Get all DOM elements
     * @returns {Object} DOM element references
     */
    getDOMElements() {
        return {
            messagesContainer: document.getElementById('messages-container'),
            welcomeMessage: document.getElementById('welcome-message'),
            chatForm: document.getElementById('chat-form'),
            messageInput: document.getElementById('message-input'),
            sendBtn: document.getElementById('send-btn'),
            cancelBtn: document.getElementById('cancel-btn'),
            statusIndicator: document.getElementById('status-indicator'),
            themeToggle: document.getElementById('theme-toggle'),
            userDropdown: document.getElementById('user-dropdown'),
            dropdownUserName: document.getElementById('dropdown-user-name'),
            loginBtn: document.getElementById('login-btn'),
            logoutBtn: document.getElementById('logout-btn'),
            newChatBtn: document.getElementById('new-chat-btn'),
            headerNewChatBtn: document.getElementById('header-new-chat-btn'),
            sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
            collapseSidebarBtn: document.getElementById('collapse-sidebar-btn'),
            toolsBtn: document.getElementById('tools-btn'),
            conversationList: document.getElementById('conversation-list'),
            chatSidebar: document.getElementById('chat-sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            modelSelector: document.getElementById('model-selector'),
            healthLink: document.getElementById('health-link'),
            toolExecutingEl: document.getElementById('tool-executing'),
        };
    }

    /**
     * Bind all event handlers
     * @param {Object} elements - DOM elements
     */
    bindEvents(elements) {
        elements.chatForm?.addEventListener('submit', e => this.handleSubmit(e));
        elements.messageInput?.addEventListener('keydown', e => this.handleKeyDown(e, elements.chatForm));
        elements.messageInput?.addEventListener('input', () => {
            autoResizeInput();
            this.updateSessionProtection();
        });
        elements.logoutBtn?.addEventListener('click', () => this.logout());
        elements.newChatBtn?.addEventListener('click', () => newConversation());
        elements.headerNewChatBtn?.addEventListener('click', () => newConversation());
        elements.toolsBtn?.addEventListener('click', () => this.showTools());
        elements.cancelBtn?.addEventListener('click', () => cancelCurrentRequest());
        elements.sidebarToggleBtn?.addEventListener('click', () => expandSidebar());
        elements.collapseSidebarBtn?.addEventListener('click', () => collapseSidebar());
        elements.sidebarOverlay?.addEventListener('click', () => closeSidebar());
        elements.modelSelector?.addEventListener('change', e => handleModelChange(e));
        elements.healthLink?.addEventListener('click', e => this.showHealthCheck(e));

        // Track user scroll to prevent auto-scroll during streaming
        elements.messagesContainer?.addEventListener('scroll', () => handleMessageScroll(isStreaming()));

        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => handleSidebarResize());
    }

    /**
     * Check if current user has admin role
     * @returns {boolean}
     */
    isAdmin() {
        if (!this.currentUser) return false;

        let roles = this.currentUser.roles || [];
        if (!roles.length && this.currentUser.realm_access) {
            roles = this.currentUser.realm_access.roles || [];
        }
        if (!roles.length && this.currentUser.resource_access?.account) {
            roles = this.currentUser.resource_access.account.roles || [];
        }

        return roles.includes('admin');
    }

    /**
     * Handle session expiration
     */
    handleSessionExpired() {
        if (!this.isAuthenticated) return;

        this.isAuthenticated = false;
        this.currentUser = null;

        stopDraftManager();
        stopSessionMonitoring();

        updateAuthUI(false, null, false, '');
        updateSidebarAuth(false);
    }

    /**
     * Handle before redirect - save draft
     */
    handleBeforeRedirect() {
        if (saveCurrentDraft()) {
            console.log('[ChatApp] Draft saved before redirect');
        }
    }

    /**
     * Update session protection based on current state
     */
    updateSessionProtection() {
        if (isStreaming()) {
            enableProtection('streaming');
        } else if (hasDraft()) {
            enableProtection('draft');
        } else {
            disableProtection();
        }
    }

    /**
     * Check authentication and initialize session
     * @param {HTMLTextAreaElement} messageInput - Message input element
     */
    async checkAuth(messageInput) {
        try {
            const data = await api.checkAuth();
            this.isAuthenticated = true;
            this.currentUser = data.user;

            const config = getAppConfig();
            updateAuthUI(this.isAuthenticated, this.currentUser, this.isAdmin(), config?.tools_provider_url);
            updateSidebarAuth(true);

            await loadConversations();
            await this.fetchToolCount();
            await runHealthCheck();

            // Initialize draft manager
            initDraftManager(messageInput);

            // Restore any saved draft
            const restoredDraft = restoreDraft();
            if (restoredDraft) {
                showToast('Your draft message has been restored', 'info');
                autoResizeInput();
            }

            // Start session monitoring
            await startSessionMonitoring(
                () => this.handleSessionExpired(),
                () => this.handleBeforeRedirect()
            );
        } catch (error) {
            console.error('Auth check failed:', error);
            this.isAuthenticated = false;
            updateAuthUI(false, null, false, '');
        }
    }

    /**
     * Fetch tool count for indicator
     */
    async fetchToolCount() {
        const toolsIndicator = document.getElementById('tools-btn');
        const toolsCount = toolsIndicator?.querySelector('.tools-count');
        if (!toolsCount) return;

        try {
            const tools = await api.getTools();
            this.availableTools = tools;
            toolsCount.textContent = tools.length;
            toolsIndicator.classList.toggle('has-tools', tools.length > 0);
            toolsIndicator.title = tools.length > 0 ? `${tools.length} tool${tools.length === 1 ? '' : 's'} available - Click to view` : 'No tools available';
        } catch (error) {
            console.error('Failed to fetch tool count:', error);
            toolsCount.textContent = '?';
        }
    }

    /**
     * Handle form submission
     * @param {Event} e - Submit event
     */
    async handleSubmit(e) {
        e.preventDefault();

        if (isStreaming()) {
            showToast('Please wait for the current response to complete', 'warning');
            return;
        }

        const message = getInputValue();
        if (!message || !this.isAuthenticated) return;

        // Clear input
        clearAndDisableInput();
        clearCurrentDraft();
        hideWelcomeMessage();

        // Add user message and thinking indicator
        addUserMessage(message);
        const thinkingMsg = addThinkingMessage();

        // Set streaming state
        setStreamingState(true);
        updateSendButton(true);
        enableProtection('streaming');
        resetUserScroll();

        // Send message
        await sendMessage(message, getCurrentConversationId(), getSelectedModelId(), thinkingMsg);

        // Reset state
        setStreamingState(false);
        api.clearRequestState();
        updateSendButton(false);
        this.updateSessionProtection();
        resetUserScroll();

        // Re-enable input
        enableAndFocusInput();

        // Check for pending expiration
        if (hasPendingExpiration()) {
            showToast('Session expired - please log in again', 'warning');
        }
    }

    /**
     * Handle keydown in message input
     * @param {KeyboardEvent} e - Keydown event
     * @param {HTMLFormElement} chatForm - Chat form element
     */
    handleKeyDown(e, chatForm) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm?.dispatchEvent(new Event('submit'));
        }
    }

    /**
     * Show health check modal
     * @param {Event} e - Click event
     */
    showHealthCheck(e) {
        e.preventDefault();
        showHealthModal(() => api.checkHealth());
    }

    /**
     * Show tools modal
     */
    async showTools() {
        try {
            this.availableTools = await api.getTools();
            showToolsModal(this.availableTools, async () => {
                try {
                    this.availableTools = await api.getTools(true);
                    await this.fetchToolCount();
                    return this.availableTools;
                } catch (error) {
                    console.error('Failed to refresh tools:', error);
                    showToast('Failed to refresh tools', 'error');
                    return this.availableTools;
                }
            });
        } catch (error) {
            console.error('Failed to load tools:', error);
            showToast('Failed to load tools', 'error');
        }
    }

    /**
     * Logout user
     */
    logout() {
        clearAllStoredDrafts();
        stopDraftManager();
        stopSessionMonitoring();
        api.logout();
    }
}

export default ChatApp;
