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
    lockChatInput,
    unlockChatInput,
} from './core/ui-manager.js';
import { initMessageRenderer, addUserMessage, addThinkingMessage, handleUserScroll as handleMessageScroll, resetUserScroll, clearMessages } from './core/message-renderer.js';
import { sendMessage, cancelCurrentRequest, isStreaming, setStreamCallbacks, connectToSessionStream, disconnectSessionStream } from './core/stream-handler.js';
import {
    initConversationManager,
    loadConversations,
    loadConversation,
    newConversation,
    getCurrentConversationId,
    setCurrentConversationId,
    loadSessions,
    loadSession,
    getCurrentSessionId,
    setCurrentSessionId,
} from './core/conversation-manager.js';
import { initSessionModeManager, switchToMode, endCurrentSession, SessionMode, isInSession, getActiveSession, getCurrentMode } from './core/session-mode-manager.js';

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
            chatForm: elements.chatForm,
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

        // Initialize session mode manager
        initSessionModeManager(
            {
                modeSelector: elements.agentSelector,
                currentModeLabel: elements.agentSelectorBtn,
                chatModeBtn: elements.chatModeBtn,
                categoryList: elements.learningCategoryList,
            },
            {
                onModeChange: (newMode, oldMode) => this.handleModeChange(newMode, oldMode, elements),
                onSessionStart: session => this.handleSessionStart(session, elements),
                onSessionEnd: (session, reason) => this.handleSessionEnd(session, reason, elements),
            }
        );

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
            // Session mode elements
            agentSelector: document.getElementById('agent-selector'),
            agentSelectorBtn: document.getElementById('agent-selector-btn'),
            chatModeBtn: document.getElementById('chat-mode-btn'),
            thoughtModeBtn: document.getElementById('thought-mode-btn'),
            learningCategoryList: document.getElementById('learning-category-list'),
            sessionIndicator: document.getElementById('session-indicator'),
            endSessionBtn: document.getElementById('end-session-btn'),
            // Session UI elements in input area
            sessionBadgeInline: document.getElementById('session-badge-inline'),
            endSessionBtnInput: document.getElementById('end-session-btn-input'),
            // Sidebar elements
            sidebarTitle: document.getElementById('sidebar-title'),
            // Sidebar mode selector elements
            sidebarModeSelector: document.getElementById('sidebar-mode-selector'),
            sidebarModeBtn: document.getElementById('sidebar-mode-btn'),
            sidebarModeIcon: document.getElementById('sidebar-mode-icon'),
            sidebarChatModeBtn: document.getElementById('sidebar-chat-mode-btn'),
            sidebarThoughtModeBtn: document.getElementById('sidebar-thought-mode-btn'),
            sidebarLearningCategoryList: document.getElementById('sidebar-learning-category-list'),
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

        // Session mode events
        elements.endSessionBtn?.addEventListener('click', () => endCurrentSession());
        elements.endSessionBtnInput?.addEventListener('click', () => endCurrentSession());

        // Track user scroll to prevent auto-scroll during streaming
        elements.messagesContainer?.addEventListener('scroll', () => handleMessageScroll(isStreaming()));

        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => handleSidebarResize());
    }

    // =========================================================================
    // Session Mode Handlers
    // =========================================================================

    /**
     * Handle mode change (chat/learning/thought)
     * @param {string} newMode - New mode
     * @param {string} oldMode - Previous mode
     * @param {Object} elements - DOM elements
     */
    handleModeChange(newMode, oldMode, elements) {
        console.log(`[ChatApp] Mode changed: ${oldMode} → ${newMode}`);

        // Update UI based on mode
        const isSessionMode = newMode !== SessionMode.CHAT;
        const isEvaluationMode = newMode === SessionMode.VALIDATION;

        // Mode selector visibility:
        // - Chat mode: visible (to select session type)
        // - Learning/Thought: visible (user can switch modes or back to chat)
        // - Evaluation: hidden (must complete evaluation first)
        elements.sidebarModeSelector?.classList.toggle('d-none', isEvaluationMode);

        // Show/hide session badge in status area
        elements.sessionBadgeInline?.classList.toggle('d-none', !isSessionMode);

        // Toggle send/end-session buttons
        if (isSessionMode) {
            elements.sendBtn?.classList.add('d-none');
            elements.endSessionBtnInput?.classList.remove('d-none');
        } else {
            elements.sendBtn?.classList.remove('d-none');
            elements.endSessionBtnInput?.classList.add('d-none');
            // Unlock chat input when switching to chat mode
            unlockChatInput();
        }

        // Update sidebar title
        if (elements.sidebarTitle) {
            elements.sidebarTitle.textContent = isSessionMode ? 'Sessions' : 'Conversations';
        }

        // Update new chat button title and visibility
        if (elements.newChatBtn) {
            elements.newChatBtn.title = isSessionMode ? 'New session' : 'New conversation';
            // Hide new session button in evaluation mode
            elements.newChatBtn.classList.toggle('d-none', isEvaluationMode);
        }

        // Update the mode selector button appearance (both header and sidebar)
        const modeConfig = {
            chat: { icon: 'bi-chat-dots', label: 'Chat' },
            learning: { icon: 'bi-mortarboard', label: 'Learning' },
            thought: { icon: 'bi-lightbulb', label: 'Thought' },
            validation: { icon: 'bi-check-circle', label: 'Validation' },
        };

        const config = modeConfig[newMode] || modeConfig.chat;

        // Update header selector (if present)
        const headerIcon = elements.agentSelectorBtn?.querySelector('.mode-icon');
        const headerLabel = elements.agentSelectorBtn?.querySelector('.mode-label');
        if (headerIcon) headerIcon.className = `bi ${config.icon} mode-icon`;
        if (headerLabel) headerLabel.textContent = config.label;

        // Update sidebar selector icon
        if (elements.sidebarModeIcon) {
            elements.sidebarModeIcon.className = `bi ${config.icon}`;
        }

        // Load sessions or conversations based on mode
        if (isSessionMode) {
            // Map mode to session type
            const sessionTypeMap = {
                learning: 'learning',
                thought: 'thought',
                validation: 'validation',
            };
            const sessionType = sessionTypeMap[newMode];
            loadSessions(sessionType);
        } else {
            loadConversations();
        }
    }

    /**
     * Handle session start
     * @param {Object} session - Session data
     * @param {Object} elements - DOM elements
     */
    handleSessionStart(session, elements) {
        console.log('[ChatApp] Session started:', session);

        // Clear messages for new session
        clearMessages();
        hideWelcomeMessage();

        // Lock chat input immediately - agent will send first message
        // Use different message for validation vs other session types
        const currentMode = getCurrentMode();
        if (currentMode === SessionMode.VALIDATION) {
            lockChatInput('Starting evaluation... Please wait for the first question.');
        } else {
            lockChatInput('Starting session... Please wait for the assistant.');
        }

        // Show session badge in status area
        elements.sessionBadgeInline?.classList.remove('d-none');

        // Show end session button in input area, hide send button
        elements.endSessionBtnInput?.classList.remove('d-none');
        elements.sendBtn?.classList.add('d-none');

        // Connect to session stream
        connectToSessionStream(session.session_id, elements.messagesContainer);
    }

    /**
     * Handle session end
     * @param {Object} session - Session that ended
     * @param {string} reason - Reason for ending
     * @param {Object} elements - DOM elements
     */
    handleSessionEnd(session, reason, elements) {
        console.log('[ChatApp] Session ended:', reason);

        // Disconnect from session stream
        disconnectSessionStream();

        // Hide session badge in status area
        elements.sessionBadgeInline?.classList.add('d-none');

        // Hide end session button (keep send button hidden - session is over)
        elements.endSessionBtnInput?.classList.add('d-none');

        // Keep input locked - user must select a new mode to continue
        // Show the mode selector so user can switch to chat or start new session
        lockChatInput('Session ended. Select a mode to continue.');
        elements.sidebarModeSelector?.classList.remove('d-none');

        // Reload sessions list to show updated status
        loadSessions(session?.session_type);

        // Show completion message
        showToast('Session ended', 'info');
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
