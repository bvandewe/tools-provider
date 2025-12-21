/**
 * ChatApp v2 - Modular Application Orchestrator
 *
 * Thin orchestrator that coordinates modules via event bus.
 * All business logic lives in domain/, protocol/, and ui/ layers.
 *
 * Architecture:
 * - 100% WebSocket-based communication (no SSE)
 * - Event-driven module coordination
 * - Clean separation of concerns
 *
 * Responsibilities:
 * - Initialize all modules on startup
 * - Wire up event bus subscriptions
 * - Bind top-level DOM events
 * - Coordinate cross-module workflows
 *
 * @module app-v2
 */

import { eventBus, Events } from './core/event-bus.js';
import { stateManager, StateKeys } from './core/state-manager.js';
import { getThinkingElement, addAssistantMessage } from './ui/renderers/message-renderer.js';

// Event handlers registry (auto-discovery pattern like backend)
import { registerHandlers, getHandlerStats } from './handlers/index.js';
import { CLIENT_CAPABILITIES } from './handlers/definition-handlers.js';

// Domain layer
import { loadAppConfig, getAppConfig, getSelectedModelId, setSelectedModelId, handleModelChange } from './domain/config.js';
import { loadDefinitions, selectDefinition, getSelectedDefinition, getSelectedDefinitionId, shouldUseWebSocket, getDefinitionIcon } from './domain/definition.js';
import { loadConversations, getCurrentConversationId, setCurrentConversationId, createConversation, deleteAllUnpinned } from './domain/conversation.js';

// Services layer
import { checkAuth, isAdmin, getCurrentUser, logout as authLogout, startSessionMonitoring, stopSessionMonitoring } from './services/auth.js';

// Protocol layer (WebSocket) - MUST be initialized before use
import { initProtocol } from './protocol/index.js';
import { connect as wsConnect, disconnect as wsDisconnect, isConnected as wsIsConnected, sendMessage as wsSendMessage, getConversationId as wsGetConversationId } from './protocol/websocket-client.js';

// UI layer
import { initChatManager, updateStreamingState, clearInput, focusInput, enableInput, disableInput, getInputValue, showWelcomeMessage, hideWelcomeMessage } from './ui/managers/chat-manager.js';
import { initSidebarManager, expandSidebar, collapseSidebar, closeSidebar } from './ui/managers/sidebar-manager.js';
import { initMessageRenderer, addUserMessage, addThinkingMessage, clearMessages, renderMessages } from './ui/renderers/message-renderer.js';
import { initWidgetRenderer, showWidget, hideWidget } from './ui/renderers/widget-renderer.js';

// Legacy conversation manager (for sidebar DOM operations)
import { initConversationManager } from './core/conversation-manager.js';

// Existing services (gradual migration)
import { api } from './services/api.js';
import { initModals, showToast, showToolsModal, showHealthModal, showPermissionsModal, showDeleteAllUnpinnedModal } from './services/modals.js';
import { initSettings } from './services/settings.js';

// Existing components (for file upload, etc.)
import { initFileUpload, setUploadEnabled, getAttachedFiles, clearAttachedFiles, hasAttachedFiles, getAttachedFilesMessage } from './components/FileUpload.js';

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

    /**
     * Initialize the application
     */
    async init() {
        // Get DOM elements
        this.elements = this.getDOMElements();

        // Initialize protocol layer FIRST (registers message handlers)
        initProtocol();

        // Initialize services
        initModals();
        initSettings(() => isAdmin());

        // Initialize UI managers
        this.initUIManagers();

        // Subscribe to events
        this.subscribeToEvents();

        // Bind DOM events
        this.bindEvents();

        // Check authentication and load data
        await this.checkAuthAndLoad();

        console.log('[ChatApp] Initialized (WebSocket mode)');
    }

    /**
     * Get all DOM elements
     * @returns {Object}
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
            sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
            collapseSidebarBtn: document.getElementById('collapse-sidebar-btn'),
            toolsBtn: document.getElementById('tools-btn'),
            conversationList: document.getElementById('conversation-list'),
            chatSidebar: document.getElementById('chat-sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            modelSelector: document.getElementById('model-selector'),
            healthLink: document.getElementById('health-link'),
            definitionTiles: document.getElementById('definition-tiles'),
            headerAgentSelector: document.getElementById('header-agent-selector'),
            headerAgentMenu: document.getElementById('header-agent-menu'),
            headerSelectedAgentIcon: document.getElementById('header-selected-agent-icon'),
            headerSelectedAgentName: document.getElementById('header-selected-agent-name'),
            // Sidebar agent selector
            sidebarAgentSelector: document.getElementById('sidebar-agent-selector'),
            sidebarAgentMenu: document.getElementById('sidebar-agent-menu'),
            sidebarSelectedAgentIcon: document.getElementById('sidebar-selected-agent-icon'),
            uploadBtn: document.getElementById('upload-btn'),
            fileInput: document.getElementById('file-input'),
            attachedFilesContainer: document.getElementById('attached-files'),
            appTitleLink: document.getElementById('app-title-link'),
            deleteAllUnpinnedBtn: document.getElementById('delete-all-unpinned-btn'),
        };
    }

    /**
     * Initialize UI manager modules
     */
    initUIManagers() {
        // Chat manager
        initChatManager({
            messagesContainer: this.elements.messagesContainer,
            welcomeMessage: this.elements.welcomeMessage,
            chatForm: this.elements.chatForm,
            messageInput: this.elements.messageInput,
            sendBtn: this.elements.sendBtn,
            cancelBtn: this.elements.cancelBtn,
            statusIndicator: this.elements.statusIndicator,
        });

        // Sidebar manager
        initSidebarManager(
            {
                chatSidebar: this.elements.chatSidebar,
                sidebarOverlay: this.elements.sidebarOverlay,
                sidebarToggleBtn: this.elements.sidebarToggleBtn,
                collapseSidebarBtn: this.elements.collapseSidebarBtn,
            },
            false
        );

        // Conversation manager (legacy - needed for sidebar DOM operations)
        initConversationManager(
            {
                conversationList: this.elements.conversationList,
                welcomeMessage: this.elements.welcomeMessage,
                messageInput: this.elements.messageInput,
            },
            {}
        );

        // Message renderer (handles chat bubbles)
        initMessageRenderer(this.elements.messagesContainer, this.elements.welcomeMessage, isAdmin);

        // Widget renderer (handles ax-* widget components)
        initWidgetRenderer(this.elements.messagesContainer);

        // File upload
        initFileUpload({
            uploadBtn: this.elements.uploadBtn,
            fileInput: this.elements.fileInput,
            attachedFilesContainer: this.elements.attachedFilesContainer,
        });
    }

    /**
     * Subscribe to event bus events.
     *
     * Uses the centralized handler registry pattern (mirrors backend's
     * application.events.websocket auto-discovery).
     *
     * Handlers are defined in scripts/handlers/ organized by domain:
     * - auth-handlers.js      : Authentication events
     * - conversation-handlers.js : Conversation lifecycle
     * - definition-handlers.js   : Agent definition events
     * - websocket-handlers.js    : WebSocket connection events
     * - message-handlers.js      : Message send/receive events
     * - widget-handlers.js       : Widget interaction events
     *
     * To add/modify/delete handlers:
     * 1. Edit the appropriate handler file in scripts/handlers/
     * 2. Export the handler in the `handlers` array
     * 3. The registry auto-discovers and registers it
     */
    subscribeToEvents() {
        // Register all handlers from the registry
        // Handlers are bound to `this` (ChatApp instance) for context
        const handlerCount = registerHandlers(this);

        // Log handler stats in development
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
        this.elements.sidebarToggleBtn?.addEventListener('click', () => expandSidebar());
        this.elements.collapseSidebarBtn?.addEventListener('click', () => collapseSidebar());
        this.elements.sidebarOverlay?.addEventListener('click', () => closeSidebar());

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
            showHealthModal(() => api.checkHealth());
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

    /**
     * Check authentication and load initial data
     */
    async checkAuthAndLoad() {
        const authResult = await checkAuth();
        const authenticated = authResult.isAuthenticated;

        if (authenticated) {
            stateManager.set(StateKeys.IS_AUTHENTICATED, true);

            // Load app config
            await loadAppConfig(this.elements.modelSelector);

            // Load definitions and conversations
            await loadDefinitions();
            await loadConversations();

            // Update UI
            this.updateAuthUI(true);

            // Initially disable input until an agent is selected
            // Upload button remains disabled, send button disabled, input shows placeholder
            disableInput('Select an agent to start chatting...');
            setUploadEnabled(false);
            if (this.elements.sendBtn) {
                this.elements.sendBtn.disabled = true;
            }

            // Start session monitoring
            startSessionMonitoring(
                () => this.handleSessionExpired(),
                () => {} // beforeRedirect callback
            );
        } else {
            this.updateAuthUI(false);
        }
    }

    /**
     * Handle form submission
     * @param {Event} e
     */
    async handleSubmit(e) {
        e.preventDefault();
        console.log('[ChatApp] handleSubmit called');

        const isStreaming = stateManager.get(StateKeys.IS_STREAMING);
        if (isStreaming) {
            showToast('Please wait for the current response', 'warning');
            return;
        }

        let message = getInputValue();
        console.log('[ChatApp] Message to send:', message);
        if (!message) return;

        // Add file attachments
        if (hasAttachedFiles()) {
            message = getAttachedFilesMessage() + message;
        }

        // Clear input and files
        clearInput();
        clearAttachedFiles();
        hideWelcomeMessage();

        // Add user message to UI
        console.log('[ChatApp] Adding user message to UI');
        addUserMessage(message);

        // Update streaming state
        updateStreamingState(true);
        setUploadEnabled(false);

        const definitionId = getSelectedDefinitionId();
        const conversationId = getCurrentConversationId();

        // Ensure WebSocket is connected
        if (!wsIsConnected()) {
            console.log('[ChatApp] WebSocket not connected, connecting...');
            try {
                await wsConnect({ definitionId, conversationId });
            } catch (error) {
                console.error('[ChatApp] Failed to connect WebSocket:', error);
                showToast('Failed to connect. Please try again.', 'error');
                updateStreamingState(false);
                setUploadEnabled(true);
                return;
            }
        }

        // Add thinking indicator
        console.log('[ChatApp] Adding thinking indicator');
        addThinkingMessage();

        // Send message via WebSocket
        wsSendMessage(message);
    }

    /**
     * Start a new conversation
     * Uses the two-phase flow: REST API to create conversation, then WebSocket connection
     */
    async startNewConversation() {
        const definition = getSelectedDefinition();
        if (!definition) {
            showToast('Please select an agent first', 'warning');
            return;
        }

        console.log('[ChatApp] Starting new conversation for definition:', definition.id);

        clearMessages();
        hideWelcomeMessage();

        // Disconnect existing WebSocket connection
        wsDisconnect();

        try {
            // Phase 1: Create conversation via REST API
            const result = await api.createConversation(definition.id, {
                clientCapabilities: CLIENT_CAPABILITIES,
            });

            console.log('[ChatApp] Conversation created:', {
                conversationId: result.conversation_id,
                wsUrl: result.ws_url,
            });

            // Store server capabilities
            if (result.server_capabilities) {
                stateManager.set(StateKeys.SERVER_CAPABILITIES, result.server_capabilities);
            }

            // Emit conversation created event (adds to sidebar)
            eventBus.emit(Events.CONVERSATION_CREATED, {
                conversationId: result.conversation_id,
                definitionId: definition.id,
                wsUrl: result.ws_url,
            });

            // Phase 2: Connect WebSocket using the ws_url
            await wsConnect({
                conversationId: result.conversation_id,
                definitionId: definition.id,
                wsUrl: result.ws_url,
            });

            focusInput();
            console.log('[ChatApp] New conversation started:', result.conversation_id);
        } catch (error) {
            console.error('[ChatApp] Failed to create conversation:', error);
            showToast('Failed to create conversation', 'error');
        }
    }

    /**
     * Reset the UI to welcome state
     * Disconnects any active conversation and shows the welcome screen
     */
    resetToWelcome() {
        console.log('[ChatApp] Resetting to welcome state');

        // Disconnect WebSocket if connected
        if (wsIsConnected()) {
            wsDisconnect();
        }

        // Clear messages and show welcome
        clearMessages();
        showWelcomeMessage();

        // Disable chat input with invitation to select agent
        disableInput('Select an agent to start chatting...');

        // Disable upload button
        setUploadEnabled(false);

        // Update connection status to disconnected
        this.updateConnectionStatus('disconnected', 'Disconnected');

        // Clear current conversation ID
        stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, null);

        // Clear selected definition - but keep the sidebar agent selector showing
        stateManager.set(StateKeys.SELECTED_DEFINITION_ID, null);

        // Reset sidebar agent icon to default
        if (this.elements.sidebarSelectedAgentIcon) {
            this.elements.sidebarSelectedAgentIcon.className = 'bi bi-robot';
        }

        // Disable new chat button since no agent is selected
        if (this.elements.newChatBtn) {
            this.elements.newChatBtn.disabled = true;
        }

        // Clear definition tile selection
        this.updateDefinitionTileSelection(null);

        console.log('[ChatApp] Reset to welcome state complete');
    }

    /**
     * Update header agent selector (legacy - kept for compatibility)
     * @param {Object} definition
     */
    updateHeaderAgentSelector(definition) {
        if (!definition) return;

        if (this.elements.headerSelectedAgentIcon) {
            this.elements.headerSelectedAgentIcon.className = `bi ${definition.icon || 'bi-robot'}`;
        }
        if (this.elements.headerSelectedAgentName) {
            this.elements.headerSelectedAgentName.textContent = definition.name;
        }
    }

    /**
     * Update sidebar agent selector icon and active state
     * @param {Object} definition - Selected definition
     */
    updateSidebarAgentSelector(definition) {
        if (!definition) return;

        const icon = getDefinitionIcon(definition);
        if (this.elements.sidebarSelectedAgentIcon) {
            this.elements.sidebarSelectedAgentIcon.className = `bi ${icon}`;
            this.elements.sidebarSelectedAgentIcon.title = definition.name;
        }

        // Update active state in sidebar agent menu
        const menu = this.elements.sidebarAgentMenu;
        if (menu) {
            menu.querySelectorAll('.sidebar-agent-item').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.definitionId === definition.id);
            });
        }
    }

    /**
     * Populate sidebar agent menu with available definitions
     * @param {Array} definitions - List of agent definitions
     */
    populateSidebarAgentMenu(definitions) {
        const menu = this.elements.sidebarAgentMenu;
        if (!menu) return;

        menu.innerHTML = '';

        // Sort definitions alphabetically by name
        const sortedDefinitions = [...definitions].sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));

        sortedDefinitions.forEach(def => {
            const icon = getDefinitionIcon(def);
            const description = def.description ? this.escapeHtml(def.description) : '';
            const li = document.createElement('li');
            li.innerHTML = `
                <button class="dropdown-item sidebar-agent-item" type="button" data-definition-id="${def.id}">
                    <span class="agent-icon"><i class="bi ${icon}"></i></span>
                    <span class="agent-info">
                        <span class="agent-name">${this.escapeHtml(def.name)}</span>
                        ${description ? `<span class="agent-description">${description}</span>` : ''}
                    </span>
                </button>
            `;

            li.querySelector('button').addEventListener('click', () => {
                selectDefinition(def.id);
            });

            menu.appendChild(li);
        });

        console.log(`[ChatApp] Populated sidebar agent menu with ${definitions.length} definitions`);
    }

    /**
     * Render definition tiles in the welcome screen
     * @param {Array} definitions - List of agent definitions
     */
    renderDefinitionTiles(definitions) {
        const container = this.elements.definitionTiles;
        if (!container) return;

        container.innerHTML = '';

        // Sort definitions alphabetically by name
        const sortedDefinitions = [...definitions].sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));

        sortedDefinitions.forEach(def => {
            const tile = document.createElement('button');
            tile.className = 'definition-tile';
            tile.dataset.definitionId = def.id;

            const icon = getDefinitionIcon(def);
            const hasTemplate = def.has_template || def.template_id;

            tile.innerHTML = `
                <div class="definition-tile-icon">
                    <i class="bi ${icon}"></i>
                    ${hasTemplate ? '<span class="proactive-badge" title="Has conversation template"><i class="bi bi-lightning-charge-fill"></i></span>' : ''}
                </div>
                <div class="definition-tile-content">
                    <h4 class="definition-tile-name">${this.escapeHtml(def.name)}</h4>
                    ${def.description ? `<p class="definition-tile-description">${this.escapeHtml(def.description)}</p>` : ''}
                </div>
            `;

            tile.addEventListener('click', () => {
                selectDefinition(def.id);
            });

            container.appendChild(tile);
        });

        // Update selection state
        const selectedId = getSelectedDefinitionId();
        if (selectedId) {
            this.updateDefinitionTileSelection(selectedId);
        }

        console.log(`[ChatApp] Rendered ${definitions.length} definition tiles`);
    }

    /**
     * Update the selected state of definition tiles
     * @param {string} selectedId - Selected definition ID
     */
    updateDefinitionTileSelection(selectedId) {
        const container = this.elements.definitionTiles;
        if (!container) return;

        const tiles = container.querySelectorAll('.definition-tile');
        tiles.forEach(tile => {
            const isSelected = tile.dataset.definitionId === selectedId;
            tile.classList.toggle('selected', isSelected);
        });
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Update auth UI
     * @param {boolean} authenticated
     */
    updateAuthUI(authenticated) {
        const user = getCurrentUser();

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
     */
    handleSessionExpired() {
        stateManager.set(StateKeys.IS_AUTHENTICATED, false);
        stopSessionMonitoring();
        this.updateAuthUI(false);
        setUploadEnabled(false);
        showToast('Session expired. Please log in again.', 'warning');
    }

    /**
     * Handle delete all unpinned
     */
    async handleDeleteAllUnpinned() {
        const pinnedIds = getPinnedConversations();
        const conversations = stateManager.get(StateKeys.CONVERSATIONS) || [];
        const unpinnedCount = conversations.filter(c => !pinnedIds.has(c.id)).length;

        if (unpinnedCount === 0) {
            showToast('No unpinned conversations to delete', 'info');
            return;
        }

        showDeleteAllUnpinnedModal(unpinnedCount, async () => {
            await deleteAllUnpinned();
            loadConversations();
        });
    }

    /**
     * Show tools modal
     */
    async showTools() {
        try {
            const tools = await api.getTools();
            showToolsModal(tools, async () => {
                return await api.getTools(true);
            });
        } catch (error) {
            showToast('Failed to load tools', 'error');
        }
    }

    /**
     * Logout user
     */
    logout() {
        stopSessionMonitoring();
        authLogout();
    }

    // =========================================================================
    // Connection & Flow Control Methods (used by handlers)
    // =========================================================================

    /**
     * Update connection status indicator
     * @param {string} status - 'connected' | 'disconnected' | 'connecting' | 'error'
     * @param {string} message - Status message to display
     */
    updateConnectionStatus(status, message) {
        const indicator = this.elements.statusIndicator;
        if (!indicator) return;

        // Update classes
        indicator.className = 'status-indicator';
        indicator.classList.add(status);

        // Update tooltip
        indicator.title = message;

        // Find or create status text span
        let statusText = indicator.querySelector('.status-text');
        if (!statusText) {
            statusText = document.createElement('span');
            statusText.className = 'status-text';
            indicator.appendChild(statusText);
        }
        statusText.textContent = message;

        console.log(`[ChatApp] Connection status: ${status} - ${message}`);
    }

    /**
     * Enable or disable chat input
     * Controls both the input field and the send/cancel button state
     * @param {boolean} enabled - Whether to enable input
     */
    enableChatInput(enabled) {
        // Update streaming state (controls send/cancel button visibility)
        updateStreamingState(!enabled);

        if (enabled) {
            // Reset placeholder to default and enable input
            enableInput('Type your message...');
            focusInput();
        } else {
            disableInput('Agent is responding...');
        }
    }

    /**
     * Get the event bus (for handlers that need to emit events)
     * @returns {Object} Event bus
     */
    get eventBus() {
        return eventBus;
    }

    /**
     * Show toast notification
     * @param {string} type - 'success' | 'error' | 'warning' | 'info'
     * @param {string} message - Toast message
     */
    showToast(type, message) {
        showToast(message, type);
    }

    // =========================================================================
    // Streaming Content Methods (used by data-handlers)
    // =========================================================================

    /**
     * Append streaming content to a message
     * Called by data.content.chunk handler
     * @param {string} messageId - Message ID
     * @param {string} content - Content chunk to append
     * @param {string} [contentType='text'] - Content type (text, markdown, code)
     */
    appendStreamingContent(messageId, content, contentType = 'text') {
        // Accumulate content for this message
        const existing = this.streamingContent.get(messageId) || '';
        const accumulated = existing + content;
        this.streamingContent.set(messageId, accumulated);

        // Update the thinking element with accumulated content
        const thinkingElement = getThinkingElement();

        console.log('[ChatApp] appendStreamingContent:', {
            messageId,
            chunkLength: content?.length || 0,
            accumulatedLength: accumulated.length,
            hasThinkingElement: !!thinkingElement,
            thinkingElementStatus: thinkingElement?.getAttribute('status'),
        });

        if (thinkingElement) {
            // IMPORTANT: Set status BEFORE content so the component knows to use
            // optimized content-only update (avoids full re-render flicker)
            const currentStatus = thinkingElement.getAttribute('status');
            if (currentStatus !== 'streaming') {
                thinkingElement.setAttribute('status', 'streaming');
            }
            thinkingElement.setAttribute('content', accumulated);
        } else {
            console.warn('[ChatApp] No thinking element found for streaming content');
        }
    }

    /**
     * Finalize a streaming message
     * Called by data.content.complete handler
     * @param {string} messageId - Message ID
     * @param {string} [finalContent] - Final content (optional, for validation)
     * @param {Object} [metadata] - Token counts, model info, etc.
     */
    finalizeStreamingMessage(messageId, finalContent, metadata) {
        // Get the accumulated content (or use finalContent if provided)
        const content = finalContent || this.streamingContent.get(messageId) || '';

        // Update the thinking element to complete
        const thinkingElement = getThinkingElement();
        if (thinkingElement) {
            thinkingElement.setAttribute('content', content);
            thinkingElement.setAttribute('status', 'complete');
        }

        // Clear accumulated content for this message
        this.streamingContent.delete(messageId);

        // Update streaming state
        stateManager.set(StateKeys.IS_STREAMING, false);
    }
}

export default ChatApp;
