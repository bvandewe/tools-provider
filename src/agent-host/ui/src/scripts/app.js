/**
 * ChatApp v2 - Modular Application Orchestrator
 *
 * Thin orchestrator that coordinates modules via event bus.
 * All business logic lives in domain/, protocol/, managers/, handlers/, and renderers/ layers.
 *
 * Architecture:
 * - 100% WebSocket-based communication (no SSE)
 * - Event-driven module coordination
 * - Clean separation of concerns
 * - Class-based singletons for services, managers, handlers, and renderers
 *
 * Responsibilities:
 * - Initialize all modules on startup
 * - Bind top-level DOM events
 * - Coordinate cross-module workflows
 *
 * @module app
 */

import { eventBus, Events } from './core/event-bus.js';
import { stateManager, StateKeys } from './core/state-manager.js';

// =============================================================================
// Class-Based Services (New)
// =============================================================================
import { apiService } from './services/ApiService.js';
import { authService } from './services/AuthService.js';
import { themeService } from './services/ThemeService.js';
import { modalService } from './services/ModalService.js';
import { settingsService } from './services/SettingsService.js';

// =============================================================================
// Class-Based Managers (New)
// =============================================================================
import { chatManager, sidebarManager, panelHeaderManager, uiManager, sessionManager, configManager, definitionManager, draftManager, agentManager, conversationManager } from './managers/index.js';

// =============================================================================
// Class-Based Renderers (New)
// =============================================================================
import { definitionRenderer, messageRenderer, widgetRenderer } from './renderers/index.js';

// =============================================================================
// Class-Based Handlers Registry (New)
// =============================================================================
import { initAllHandlers, destroyAllHandlers, getHandlerStats } from './handlers/HandlersRegistry.js';

// =============================================================================
// Domain Layer (Pure Functions - Keep as-is)
// =============================================================================
import { loadAppConfig, handleModelChange } from './domain/config.js';
import { loadDefinitions, getSelectedDefinition, getSelectedDefinitionId } from './domain/definition.js';
import { loadConversations, getCurrentConversationId, deleteAllUnpinned } from './domain/conversation.js';

// =============================================================================
// Protocol Layer - WebSocket (Keep as-is)
// =============================================================================
import { initProtocol } from './protocol/index.js';
import { connect as wsConnect, disconnect as wsDisconnect, isConnected as wsIsConnected, sendMessage as wsSendMessage } from './protocol/websocket-client.js';

// =============================================================================
// Domain Constants
// =============================================================================
import { CLIENT_CAPABILITIES } from './handlers/DefinitionHandlers.js';

// Components
import { initFileUpload, setUploadEnabled, clearAttachedFiles, hasAttachedFiles, getAttachedFilesMessage } from './components/FileUpload.js';

// Utilities
import { getPinnedConversations } from './utils/storage.js';

// =============================================================================
// ChatApp Class
// =============================================================================

export class ChatApp {
    constructor() {
        /** @type {Object|null} */
        this.elements = null;

        /** @type {Map<string, string>} Accumulated content per message ID */
        this.streamingContent = new Map();
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('[ChatApp] Initializing (v2 - Class-Based Architecture)...');

            this.elements = this.getDOMElements();

            // Initialize protocol layer FIRST (registers WebSocket message handlers)
            initProtocol();

            // Initialize class-based services
            this.initServices();

            // Initialize class-based managers
            this.initManagers();

            // Initialize class-based renderers
            this.initRenderers();

            // Initialize class-based handlers (event subscriptions)
            this.initHandlers();

            // Bind DOM events
            this.bindEvents();

            // Check authentication and load data
            await this.checkAuthAndLoad();

            console.log('[ChatApp] Initialized (v2 - WebSocket mode)');
        } catch (error) {
            console.error('[ChatApp] Initialization failed:', error);
            // Show a user-friendly error message
            modalService.showToast('Application failed to initialize. Please refresh the page.', 'error');
        }
    }

    /**
     * Get all DOM elements
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
            userDropdown: document.getElementById('user-dropdown'),
            dropdownUserName: document.getElementById('dropdown-user-name'),
            loginBtn: document.getElementById('login-btn'),
            logoutBtn: document.getElementById('logout-btn'),
            newChatBtn: document.getElementById('new-chat-btn'),
            sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
            collapseSidebarBtn: document.getElementById('collapse-sidebar-btn'),
            toolsBtn: document.getElementById('tools-btn'),
            conversationList: document.getElementById('conversation-list'),
            chatSidebar: document.getElementById('chat-sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            modelSelector: document.getElementById('model-selector'),
            healthLink: document.getElementById('health-link'),
            definitionTiles: document.getElementById('definition-tiles'),
            sidebarAgentMenu: document.getElementById('sidebar-agent-menu'),
            sidebarSelectedAgentIcon: document.getElementById('sidebar-selected-agent-icon'),
            headerSelectedAgentIcon: document.getElementById('header-selected-agent-icon'),
            headerSelectedAgentName: document.getElementById('header-selected-agent-name'),
            uploadBtn: document.getElementById('upload-btn'),
            fileInput: document.getElementById('file-input'),
            attachedFilesContainer: document.getElementById('attached-files'),
            appTitleLink: document.getElementById('app-title-link'),
            deleteAllUnpinnedBtn: document.getElementById('delete-all-unpinned-btn'),
        };
    }

    /**
     * Initialize class-based services
     */
    initServices() {
        // API Service (no explicit init needed, ready to use)
        apiService.setUnauthorizedHandler(() => this.handleSessionExpired());

        // Modal Service
        modalService.init();

        // Settings Service
        settingsService.init(() => authService.isAdmin());

        console.log('[ChatApp] Services initialized');
    }

    /**
     * Initialize class-based managers
     */
    initManagers() {
        // Chat Manager
        chatManager.init({
            messagesContainer: this.elements.messagesContainer,
            welcomeMessage: this.elements.welcomeMessage,
            chatForm: this.elements.chatForm,
            messageInput: this.elements.messageInput,
            sendBtn: this.elements.sendBtn,
            cancelBtn: this.elements.cancelBtn,
            statusIndicator: this.elements.statusIndicator,
        });

        // Sidebar Manager
        sidebarManager.init({
            chatSidebar: this.elements.chatSidebar,
            sidebarOverlay: this.elements.sidebarOverlay,
            sidebarToggleBtn: this.elements.sidebarToggleBtn,
            collapseSidebarBtn: this.elements.collapseSidebarBtn,
            sidebarAgentMenu: this.elements.sidebarAgentMenu,
            sidebarSelectedAgentIcon: this.elements.sidebarSelectedAgentIcon,
            headerSelectedAgentIcon: this.elements.headerSelectedAgentIcon,
            headerSelectedAgentName: this.elements.headerSelectedAgentName,
        });

        // Panel Header Manager
        panelHeaderManager.init(this.elements.messagesContainer);

        // Conversation Manager
        conversationManager.init({
            conversationList: this.elements.conversationList,
            welcomeMessage: this.elements.welcomeMessage,
            messageInput: this.elements.messageInput,
        });

        // UI Manager
        uiManager.init();

        // Config Manager
        configManager.init();

        // Definition Manager
        definitionManager.init();

        // Session Manager
        sessionManager.init();

        // Draft Manager
        draftManager.init();

        // Agent Manager
        agentManager.init();

        // File Upload (component, not manager)
        initFileUpload({
            uploadBtn: this.elements.uploadBtn,
            fileInput: this.elements.fileInput,
            attachedFilesContainer: this.elements.attachedFilesContainer,
        });

        console.log('[ChatApp] Managers initialized');
    }

    /**
     * Initialize class-based renderers
     */
    initRenderers() {
        // Message Renderer
        messageRenderer.init(this.elements.messagesContainer, this.elements.welcomeMessage, () => authService.isAdmin());

        // Widget Renderer
        widgetRenderer.init(this.elements.messagesContainer);

        // Definition Renderer
        definitionRenderer.init(this.elements.definitionTiles);

        console.log('[ChatApp] Renderers initialized');
    }

    /**
     * Initialize class-based handlers (event subscriptions)
     */
    initHandlers() {
        const count = initAllHandlers();
        const stats = getHandlerStats();
        console.log('[ChatApp] Handler stats:', stats);
    }

    /**
     * Bind DOM event handlers
     */
    bindEvents() {
        // Form submission
        this.elements.chatForm?.addEventListener('submit', e => this.handleSubmit(e));

        // Enter key handling
        this.elements.messageInput?.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.elements.chatForm?.dispatchEvent(new Event('submit'));
            }
        });

        // Sidebar controls
        this.elements.sidebarToggleBtn?.addEventListener('click', () => sidebarManager.expand());
        this.elements.collapseSidebarBtn?.addEventListener('click', () => sidebarManager.collapse());
        this.elements.sidebarOverlay?.addEventListener('click', () => sidebarManager.close());

        // New chat
        this.elements.newChatBtn?.addEventListener('click', () => this.startNewConversation());

        // Model selector
        this.elements.modelSelector?.addEventListener('change', e => handleModelChange(e));

        // Tools button
        this.elements.toolsBtn?.addEventListener('click', () => this.showTools());

        // Logout
        this.elements.logoutBtn?.addEventListener('click', () => this.logout());

        // Health check
        this.elements.healthLink?.addEventListener('click', e => {
            e.preventDefault();
            modalService.showHealthModal(() => apiService.checkHealth());
        });

        // App title - reset to welcome state
        this.elements.appTitleLink?.addEventListener('click', e => {
            e.preventDefault();
            this.resetToWelcome();
        });

        // Delete all unpinned
        this.elements.deleteAllUnpinnedBtn?.addEventListener('click', () => this.handleDeleteAllUnpinned());

        // Window resize
        window.addEventListener('resize', () => {
            eventBus.emit(Events.UI_RESIZE);
        });
    }

    // =========================================================================
    // Authentication & Loading
    // =========================================================================

    /**
     * Check authentication and load initial data
     */
    async checkAuthAndLoad() {
        console.log('[ChatApp] Checking authentication...');

        const authResult = await authService.checkAuth();
        const authenticated = authResult.isAuthenticated;

        console.log('[ChatApp] Auth result:', { authenticated, user: authResult.user?.username || authResult.user?.email });

        if (authenticated) {
            stateManager.set(StateKeys.IS_AUTHENTICATED, true);

            console.log('[ChatApp] Loading app config...');
            await loadAppConfig(this.elements.modelSelector);

            console.log('[ChatApp] Loading definitions...');
            await loadDefinitions();

            console.log('[ChatApp] Loading conversations...');
            await loadConversations();

            console.log('[ChatApp] Updating auth UI (authenticated=true)...');
            this.updateAuthUI(true);

            // Initially disable input until an agent is selected
            chatManager.disableInput('Select an agent to start chatting...');
            setUploadEnabled(false);
            if (this.elements.sendBtn) {
                this.elements.sendBtn.disabled = true;
            }

            authService.startSessionMonitoring(
                () => this.handleSessionExpired(),
                () => {}
            );

            console.log('[ChatApp] Authentication complete, user logged in');
        } else {
            console.log('[ChatApp] User not authenticated, showing login UI');
            this.updateAuthUI(false);
        }
    }

    /**
     * Update auth UI elements
     */
    updateAuthUI(authenticated) {
        const user = authService.getCurrentUser();

        if (this.elements.userDropdown) {
            this.elements.userDropdown.classList.toggle('d-none', !authenticated);
        }
        if (this.elements.loginBtn) {
            this.elements.loginBtn.classList.toggle('d-none', authenticated);
        }
        if (this.elements.dropdownUserName && user) {
            this.elements.dropdownUserName.textContent = user.name || user.email || 'User';
        }

        // Update login prompt visibility
        const loginPrompt = this.elements.welcomeMessage?.querySelector('.login-prompt');
        if (loginPrompt) {
            loginPrompt.classList.toggle('d-none', authenticated);
        }

        // Show definition tiles when authenticated
        const welcomeDefinitions = this.elements.welcomeMessage?.querySelector('.welcome-definitions');
        if (welcomeDefinitions) {
            welcomeDefinitions.classList.toggle('d-none', !authenticated);
        }
    }

    /**
     * Handle session expiration
     * Updates local state and emits AUTH_SESSION_EXPIRED event.
     * AuthHandlers listens for this event and handles:
     * - Showing toast notification
     * - Disconnecting WebSocket
     * - Redirecting to login page
     */
    handleSessionExpired() {
        console.log('[ChatApp] Session expired, updating state and emitting event');

        stateManager.set(StateKeys.IS_AUTHENTICATED, false);
        stateManager.set(StateKeys.CURRENT_USER, null);
        stateManager.set(StateKeys.IS_ADMIN, false);

        authService.stopSessionMonitoring();
        this.updateAuthUI(false);
        setUploadEnabled(false);

        // Emit event for AuthHandlers to disconnect WebSocket and redirect
        eventBus.emit(Events.AUTH_SESSION_EXPIRED);
    }

    // =========================================================================
    // Form Handling
    // =========================================================================

    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();

        const isStreaming = stateManager.get(StateKeys.IS_STREAMING);
        if (isStreaming) {
            modalService.showToast('Please wait for the current response', 'warning');
            return;
        }

        let message = chatManager.getInputValue();
        if (!message) return;

        // Add file attachments
        if (hasAttachedFiles()) {
            message = getAttachedFilesMessage() + message;
        }

        // Clear input and files
        chatManager.clearInput();
        clearAttachedFiles();
        chatManager.hideWelcomeMessage();

        // Add user message to UI
        messageRenderer.addUserMessage(message);

        // Update streaming state
        chatManager.updateStreamingState(true);
        setUploadEnabled(false);

        const definitionId = getSelectedDefinitionId();
        const conversationId = getCurrentConversationId();

        // Ensure WebSocket is connected
        if (!wsIsConnected()) {
            try {
                await wsConnect({ definitionId, conversationId });
            } catch (error) {
                console.error('[ChatApp] Failed to connect WebSocket:', error);
                modalService.showToast('Failed to connect. Please try again.', 'error');
                chatManager.updateStreamingState(false);
                setUploadEnabled(true);
                return;
            }
        }

        // Add thinking indicator and send message
        messageRenderer.addThinkingMessage();
        wsSendMessage(message);
    }

    // =========================================================================
    // Conversation Management
    // =========================================================================

    /**
     * Start a new conversation
     */
    async startNewConversation() {
        const definition = getSelectedDefinition();
        if (!definition) {
            modalService.showToast('Please select an agent first', 'warning');
            return;
        }

        console.log('[ChatApp] Starting new conversation for definition:', definition.id);

        messageRenderer.clearMessages();
        chatManager.hideWelcomeMessage();
        wsDisconnect();

        try {
            const result = await apiService.createConversation(definition.id, {
                clientCapabilities: CLIENT_CAPABILITIES,
            });

            if (result.server_capabilities) {
                stateManager.set(StateKeys.SERVER_CAPABILITIES, result.server_capabilities);
            }

            eventBus.emit(Events.CONVERSATION_CREATED, {
                conversationId: result.conversation_id,
                definitionId: definition.id,
                wsUrl: result.ws_url,
            });

            await wsConnect({
                conversationId: result.conversation_id,
                definitionId: definition.id,
                wsUrl: result.ws_url,
            });

            chatManager.focusInput();
        } catch (error) {
            console.error('[ChatApp] Failed to create conversation:', error);
            modalService.showToast('Failed to create conversation', 'error');
        }
    }

    /**
     * Reset the UI to welcome state
     */
    resetToWelcome() {
        console.log('[ChatApp] Resetting to welcome state');

        if (wsIsConnected()) {
            wsDisconnect();
        }

        messageRenderer.clearMessages();
        chatManager.showWelcomeMessage();

        // Show the definition tiles in welcome message (if authenticated)
        const isAuthenticated = stateManager.get(StateKeys.IS_AUTHENTICATED);
        const welcomeDefinitions = this.elements.welcomeMessage?.querySelector('.welcome-definitions');
        if (welcomeDefinitions && isAuthenticated) {
            welcomeDefinitions.classList.remove('d-none');
        }

        // Remove conversation header
        panelHeaderManager.removeHeader();

        // Disable chat input
        chatManager.disableInput('Select an agent to start chatting...');
        setUploadEnabled(false);

        // Update connection status
        chatManager.updateConnectionStatus('disconnected', 'Disconnected');

        // Clear state
        stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, null);
        conversationManager.setActiveConversation(null);
        stateManager.set(StateKeys.SELECTED_DEFINITION_ID, null);

        // Reset UI elements
        sidebarManager.resetAgentSelector();

        if (this.elements.newChatBtn) {
            this.elements.newChatBtn.disabled = true;
        }

        definitionRenderer.updateTileSelection(null);
    }

    // =========================================================================
    // Actions
    // =========================================================================

    /**
     * Handle delete all unpinned
     */
    async handleDeleteAllUnpinned() {
        const pinnedIds = getPinnedConversations();
        const conversations = stateManager.get(StateKeys.CONVERSATIONS) || [];
        const unpinnedCount = conversations.filter(c => !pinnedIds.has(c.id)).length;

        if (unpinnedCount === 0) {
            modalService.showToast('No unpinned conversations to delete', 'info');
            return;
        }

        modalService.showDeleteAllUnpinnedModal(unpinnedCount, async () => {
            await deleteAllUnpinned();
            loadConversations();
        });
    }

    /**
     * Show tools modal
     */
    async showTools() {
        try {
            const tools = await apiService.getTools();
            modalService.showToolsModal(tools, async () => await apiService.getTools(true));
        } catch (error) {
            modalService.showToast('Failed to load tools', 'error');
        }
    }

    /**
     * Logout user
     */
    logout() {
        authService.stopSessionMonitoring();
        authService.logout();
    }

    // =========================================================================
    // Handler Delegates (called by event handlers)
    // These bridge the gap between legacy handlers and new managers
    // =========================================================================

    // --- Definition handlers ---
    renderDefinitionTiles(definitions) {
        definitionRenderer.renderTiles(definitions);
    }

    populateSidebarAgentMenu(definitions) {
        sidebarManager.populateAgentMenu(definitions);
    }

    updateSidebarAgentSelector(definition) {
        sidebarManager.updateAgentSelector(definition);
    }

    updateDefinitionTileSelection(definitionId) {
        definitionRenderer.updateTileSelection(definitionId);
    }

    // --- Panel header handlers ---
    updateProgress(current, total, label) {
        panelHeaderManager.updateProgress(current, total, label);
    }

    updatePanelTitle(text, visible) {
        panelHeaderManager.updateTitle(text, visible);
    }

    updatePanelScore(current, max, label, visible) {
        panelHeaderManager.updateScore(current, max, label, visible);
    }

    // --- Connection status ---
    updateConnectionStatus(status, message) {
        chatManager.updateConnectionStatus(status, message);
    }

    // --- Chat input ---
    enableChatInput(enabled) {
        chatManager.updateStreamingState(!enabled);
        if (enabled) {
            chatManager.enableInput('Type your message...');
            chatManager.focusInput();
        } else {
            chatManager.disableInput('Agent is responding...');
        }
    }

    hideAllChatInputButtons(placeholder) {
        chatManager.hideAllInputButtons(placeholder);
    }

    showAllChatInputButtons() {
        chatManager.showAllInputButtons();
    }

    // --- Streaming content ---
    // NOTE: This method is now deprecated - streaming is handled by MessageRenderer._handleMessageStreaming
    appendStreamingContent(messageId, content, contentType = 'text') {
        const existing = this.streamingContent.get(messageId) || '';
        const accumulated = existing + content;
        this.streamingContent.set(messageId, accumulated);

        let thinkingElement = messageRenderer.getThinkingElement();
        if (!thinkingElement) {
            messageRenderer.addThinkingMessage();
            thinkingElement = messageRenderer.getThinkingElement();
        }

        if (thinkingElement) {
            if (thinkingElement.getAttribute('status') !== 'streaming') {
                thinkingElement.setAttribute('status', 'streaming');
            }
            thinkingElement.setAttribute('content', accumulated);
        }
    }

    finalizeStreamingMessage(messageId, finalContent, metadata) {
        const content = finalContent || this.streamingContent.get(messageId) || '';
        const thinkingElement = messageRenderer.getThinkingElement();
        if (thinkingElement) {
            thinkingElement.setAttribute('content', content);
            thinkingElement.setAttribute('status', 'complete');
        }
        this.streamingContent.delete(messageId);
        stateManager.set(StateKeys.IS_STREAMING, false);
    }

    // --- Toast ---
    showToast(type, message) {
        modalService.showToast(message, type);
    }

    // --- Event bus access ---
    get eventBus() {
        return eventBus;
    }
}

export default ChatApp;
