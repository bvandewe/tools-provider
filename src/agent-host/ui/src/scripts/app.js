/**
 * ChatApp - Main Application Class (Simplified Architecture)
 *
 * Orchestrates the chat interface using the simplified architecture:
 * - Conversation is the single AggregateRoot
 * - AgentDefinition defines what kind of assistant
 * - Agent is a stateless executor
 *
 * Removed: Session modes, Agent aggregates
 * Added: Definition tiles, streamlined conversation flow
 */
import { api } from './services/api.js';
import { initModals, showToolsModal, showToast, showHealthModal, showPermissionsModal, showDeleteAllUnpinnedModal } from './services/modals.js';
import { initSettings } from './services/settings.js';
import { startSessionMonitoring, stopSessionMonitoring, enableProtection, disableProtection, hasPendingExpiration } from './core/session-manager.js';
import { initDraftManager, stopDraftManager, saveCurrentDraft, restoreDraft, clearCurrentDraft, hasDraft, clearAllStoredDrafts } from './core/draft-manager.js';
import { initSidebarManager, updateAuthState as updateSidebarAuth, collapseSidebar, expandSidebar, closeSidebar, handleResize as handleSidebarResize } from './core/sidebar-manager.js';
import { loadAppConfig, handleModelChange, getAppConfig, getSelectedModelId, setSelectedModelId } from './core/config-manager.js';
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
import { initMessageRenderer, addUserMessage, addThinkingMessage, handleUserScroll as handleMessageScroll, resetUserScroll, clearMessages, getMessagesContainer } from './core/message-renderer.js';
import { sendMessage, cancelCurrentRequest, isStreaming, setStreamCallbacks } from './core/stream-handler.js';
import {
    initConversationManager,
    loadConversations,
    loadConversation,
    newConversation,
    getCurrentConversationId,
    setCurrentConversationId,
    deleteAllUnpinnedConversations,
} from './core/conversation-manager.js';
import {
    initDefinitionManager,
    loadDefinitions,
    getSelectedDefinition,
    getSelectedDefinitionId,
    renderDefinitionTiles,
    selectDefinition,
    isProactiveDefinition,
    getDefinitions,
    shouldUseWebSocket,
} from './core/definition-manager.js';
import { initAgentManager, setConversationContext, clearConversationContext, canAccessConversations, canTypeFreeText, getRestrictions } from './core/agent-manager-new.js';
import { initFileUpload, setUploadEnabled, getAttachedFiles, clearAttachedFiles, hasAttachedFiles, getAttachedFilesMessage } from './components/FileUpload.js';
import { connect as wsConnect, disconnect as wsDisconnect, startTemplate, sendMessage as wsSendMessage, isConnected as wsIsConnected, setWebSocketCallbacks } from './core/websocket-handler.js';
import { getPinnedConversations } from './utils/helpers.js';

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
                onLoad: (conversationId, definitionId) => {
                    setCurrentConversationId(conversationId);

                    // If the conversation has a definition_id, select it to update the header
                    // Use skipCallback=true to avoid triggering proactive flow for existing conversations
                    if (definitionId) {
                        selectDefinition(definitionId, true);
                        // Manually update header agent selector since we skipped the callback
                        const definition = getSelectedDefinition();
                        if (definition) {
                            this.updateHeaderAgentSelector(definition, elements);
                        }
                    }

                    // Update agent context with the conversation's definition (or fallback to selected)
                    // Use skipRestrictions=true because we're loading an existing conversation
                    const effectiveDefinitionId = definitionId || getSelectedDefinitionId();
                    setConversationContext(conversationId, effectiveDefinitionId, true);
                },
                updateSessionProtection: () => this.updateSessionProtection(),
                autoResize: () => autoResizeInput(),
            }
        );

        // Initialize definition manager
        initDefinitionManager(
            {
                definitionTiles: elements.definitionTiles,
                selectedDefinitionLabel: elements.selectedDefinitionLabel,
                selectedDefinitionIcon: elements.selectedDefinitionIcon,
            },
            {
                onDefinitionSelect: (definition, previousId) => {
                    this.handleDefinitionSelect(definition, previousId, elements);
                    // Update header agent selector
                    this.updateHeaderAgentSelector(definition, elements);
                },
                onDefinitionsLoaded: definitions => {
                    // Render tiles in welcome screen
                    if (elements.definitionTiles) {
                        renderDefinitionTiles(elements.definitionTiles);
                    }
                    // Populate header agent selector menu
                    this.populateHeaderAgentMenu(definitions, elements);
                },
            }
        );

        // Initialize simplified agent manager
        initAgentManager({
            onRestrictionsChange: restrictions => {
                this.applyRestrictions(restrictions, elements);
            },
            onModeChange: (newDefId, oldDefId) => {
                console.log(`[ChatApp] Definition changed: ${oldDefId} → ${newDefId}`);
            },
        });

        // Set stream callbacks
        setStreamCallbacks({
            onConversationCreated: conversationId => {
                setCurrentConversationId(conversationId);
                loadConversations();
            },
            onStreamComplete: () => loadConversations(),
        });

        // Initialize file upload component
        initFileUpload({
            uploadBtn: elements.uploadBtn,
            fileInput: elements.fileInput,
            attachedFilesContainer: elements.attachedFilesContainer,
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
            permissionsBtn: document.getElementById('my-permissions-btn'),
            newChatBtn: document.getElementById('new-chat-btn'),
            sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
            collapseSidebarBtn: document.getElementById('collapse-sidebar-btn'),
            toolsBtn: document.getElementById('tools-btn'),
            conversationList: document.getElementById('conversation-list'),
            chatSidebar: document.getElementById('chat-sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            modelSelector: document.getElementById('model-selector'),
            healthLink: document.getElementById('health-link'),
            toolExecutingEl: document.getElementById('tool-executing'),
            // Definition tiles container (in welcome screen)
            definitionTiles: document.getElementById('definition-tiles'),
            selectedDefinitionLabel: document.getElementById('selected-definition-label'),
            selectedDefinitionIcon: document.getElementById('selected-definition-icon'),
            // File upload elements
            uploadBtn: document.getElementById('upload-btn'),
            fileInput: document.getElementById('file-input'),
            attachedFilesContainer: document.getElementById('attached-files'),
            // Header elements
            appTitleLink: document.getElementById('app-title-link'),
            deleteAllUnpinnedBtn: document.getElementById('delete-all-unpinned-btn'),
            headerAgentSelector: document.getElementById('header-agent-selector'),
            headerAgentSelectorBtn: document.getElementById('header-agent-selector-btn'),
            headerAgentMenu: document.getElementById('header-agent-menu'),
            headerSelectedAgentIcon: document.getElementById('header-selected-agent-icon'),
            headerSelectedAgentName: document.getElementById('header-selected-agent-name'),
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
        elements.permissionsBtn?.addEventListener('click', () => this.showPermissions());
        elements.newChatBtn?.addEventListener('click', () => this.startNewConversation());
        elements.toolsBtn?.addEventListener('click', () => this.showTools());
        elements.cancelBtn?.addEventListener('click', () => cancelCurrentRequest());
        elements.sidebarToggleBtn?.addEventListener('click', () => expandSidebar());
        elements.collapseSidebarBtn?.addEventListener('click', () => collapseSidebar());
        elements.sidebarOverlay?.addEventListener('click', () => closeSidebar());
        elements.modelSelector?.addEventListener('change', e => handleModelChange(e));
        elements.healthLink?.addEventListener('click', e => this.showHealthCheck(e));

        // App title link - show welcome page
        elements.appTitleLink?.addEventListener('click', e => {
            e.preventDefault();
            showWelcomeMessage();
            const welcomeDefs = document.getElementById('welcome-definitions');
            if (welcomeDefs) {
                welcomeDefs.classList.remove('d-none');
            }
        });

        // Delete all unpinned conversations
        elements.deleteAllUnpinnedBtn?.addEventListener('click', () => this.handleDeleteAllUnpinned());

        // Track user scroll to prevent auto-scroll during streaming
        elements.messagesContainer?.addEventListener('scroll', () => handleMessageScroll(isStreaming()));

        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => handleSidebarResize());

        // Template event listeners for progress indicator
        this.setupTemplateEventListeners(elements);
    }

    /**
     * Set up event listeners for template-based conversation events
     * @param {Object} elements - DOM elements
     */
    setupTemplateEventListeners(elements) {
        // Handle template configuration received
        window.addEventListener('ax-template-config', e => {
            // The detail object contains the config fields directly (not wrapped in a config property)
            const config = e.detail;
            const conversationId = e.detail.conversationId;
            console.log('[ChatApp] Template config received:', config);

            // Store template config for later use
            this.currentTemplateConfig = config;

            // Create or update conversation header if progress indicator is enabled
            if (config.displayProgressIndicator) {
                this.createOrUpdateConversationHeader(elements.messagesContainer, {
                    title: config.title || '',
                    totalItems: config.totalItems,
                    currentItem: 0,
                    deadline: config.deadline,
                    showProgress: true,
                    allowBackward: config.allowBackwardNavigation,
                });
            }
        });

        // Handle template progress updates
        window.addEventListener('ax-template-progress', e => {
            const { currentItem, totalItems, itemTitle, enableChatInput, deadline, displayProgressIndicator, allowBackwardNavigation } = e.detail;
            console.log('[ChatApp] Template progress:', e.detail);

            // Update the conversation header
            if (displayProgressIndicator) {
                this.createOrUpdateConversationHeader(elements.messagesContainer, {
                    title: itemTitle || this.currentTemplateConfig?.name || '',
                    totalItems: totalItems,
                    currentItem: currentItem,
                    deadline: deadline,
                    showProgress: true,
                    allowBackward: allowBackwardNavigation,
                });
            }

            // Handle chat input state based on enableChatInput
            if (enableChatInput === false) {
                lockChatInput('Please respond to the widget above...');
            } else if (enableChatInput === true) {
                unlockChatInput();
            }
        });

        // Handle template completion
        window.addEventListener('ax-template-complete', e => {
            const { continueAfterCompletion, totalItems, totalScore, maxPossibleScore } = e.detail;
            console.log('[ChatApp] Template complete:', e.detail);

            // Remove the progress header on completion
            this.removeConversationHeader(elements.messagesContainer);

            // Handle chat input based on continue_after_completion
            if (continueAfterCompletion) {
                unlockChatInput();
                if (elements.messageInput) {
                    elements.messageInput.placeholder = 'Continue the conversation...';
                }
            } else {
                lockChatInput('Conversation completed');
            }

            // Clear template config
            this.currentTemplateConfig = null;
        });
    }

    /**
     * Create or update the conversation header component
     * @param {HTMLElement} container - Messages container element
     * @param {Object} options - Header options
     */
    createOrUpdateConversationHeader(container, options) {
        if (!container) return;

        let header = container.parentElement?.querySelector('ax-conversation-header');

        if (!header) {
            // Create new header
            header = document.createElement('ax-conversation-header');
            // Insert before the messages container
            container.parentElement?.insertBefore(header, container);
        }

        // Update header attributes
        if (options.title) {
            header.setAttribute('title', options.title);
        }
        if (options.totalItems !== undefined) {
            header.setAttribute('total-items', options.totalItems.toString());
        }
        if (options.currentItem !== undefined) {
            header.setAttribute('current-item', options.currentItem.toString());
        }
        if (options.deadline) {
            header.setAttribute('deadline', options.deadline);
        }
        if (options.showProgress) {
            header.setAttribute('show-progress', '');
        } else {
            header.removeAttribute('show-progress');
        }
        if (options.allowBackward) {
            header.setAttribute('allow-backward', '');
        } else {
            header.removeAttribute('allow-backward');
        }
    }

    /**
     * Remove the conversation header component
     * @param {HTMLElement} container - Messages container element
     */
    removeConversationHeader(container) {
        if (!container) return;
        const header = container.parentElement?.querySelector('ax-conversation-header');
        if (header) {
            header.remove();
        }
    }

    // =========================================================================
    // Definition Handling
    // =========================================================================

    /**
     * Handle definition selection
     * @param {Object} definition - Selected definition
     * @param {string} previousId - Previous definition ID
     * @param {Object} elements - DOM elements
     */
    handleDefinitionSelect(definition, previousId, elements) {
        console.log(`[ChatApp] Definition selected: ${definition.name} (${definition.id})`);

        // Apply definition's model override if present
        // The definition's model takes precedence when switching definitions,
        // but the user can still manually change the model afterwards
        if (definition.model) {
            const modelApplied = setSelectedModelId(definition.model, true);
            if (modelApplied) {
                console.log(`[ChatApp] Applied definition model override: ${definition.model}`);
            } else {
                console.warn(`[ChatApp] Definition model not available: ${definition.model}`);
            }
        }

        // Update UI based on definition type (has_template indicates possible proactive mode)
        const hasTemplate = definition.has_template;

        // Note: We no longer auto-start proactive conversations when selecting a definition.
        // The user must explicitly click the "+" button to start a new conversation.
        // This provides a cleaner UX where switching agents doesn't unexpectedly create conversations.

        // Update input placeholder based on definition
        if (elements.messageInput) {
            const placeholder = hasTemplate ? 'Waiting for assistant...' : `Ask ${definition.name}...`;
            elements.messageInput.placeholder = placeholder;
        }
    }

    /**
     * Start a proactive conversation where the agent speaks first
     * @param {Object} definition - Selected definition
     * @param {Object} elements - DOM elements
     */
    async startProactiveConversation(definition, elements) {
        console.log(`[ChatApp] Starting proactive conversation with ${definition.name} via WebSocket`);

        // Clear any existing messages and hide welcome message
        clearMessages();
        hideWelcomeMessage();

        // Set streaming state
        setStreamingState(true);
        updateSendButton(true);
        setUploadEnabled(false);
        enableProtection('streaming');
        resetUserScroll();

        // Set up WebSocket callbacks for template events
        setWebSocketCallbacks({
            onConnected: data => {
                console.log('[ChatApp] WebSocket connected, conversation:', data.conversation_id);
                setCurrentConversationId(data.conversation_id);
                // Load conversations to show the new one in sidebar
                loadConversations();
            },
            onComplete: data => {
                console.log('[ChatApp] Template complete');
                setStreamingState(false);
                updateSendButton(false);
                setUploadEnabled(true);
                this.updateSessionProtection();

                // Refresh conversations list to update any changes
                loadConversations();

                // Enable input for follow-up conversation
                enableAndFocusInput();
                if (elements.messageInput) {
                    elements.messageInput.placeholder = `Continue conversation with ${definition.name}...`;
                }
            },
            onError: data => {
                console.error('[ChatApp] WebSocket error:', data.message);
                setStreamingState(false);
                updateSendButton(false);
                setUploadEnabled(true);
                this.updateSessionProtection();
                showToast(data.message || 'An error occurred', 'error');
            },
            onDisconnected: event => {
                console.log('[ChatApp] WebSocket disconnected');
                // Only reset state if not a clean close
                if (event.code !== 1000) {
                    setStreamingState(false);
                    updateSendButton(false);
                    setUploadEnabled(true);
                }
            },
        });

        try {
            // Connect via WebSocket with definition ID
            const definitionId = definition.id;
            await wsConnect({ definitionId });

            // Start the template flow - server will push intro + first item
            startTemplate();

            // Update placeholder while waiting
            if (elements.messageInput) {
                elements.messageInput.placeholder = `Respond to ${definition.name}...`;
            }
        } catch (error) {
            console.error('[ChatApp] Failed to start proactive conversation:', error);
            setStreamingState(false);
            updateSendButton(false);
            setUploadEnabled(true);
            this.updateSessionProtection();
            showToast('Failed to connect to server', 'error');
        }
    }

    /**
     * Populate the header agent selector dropdown menu with available definitions
     * @param {Array} definitions - Array of definition objects
     * @param {Object} elements - DOM elements
     */
    populateHeaderAgentMenu(definitions, elements) {
        const menu = elements.headerAgentMenu;
        if (!menu || !definitions || definitions.length === 0) return;

        menu.innerHTML = '';

        definitions.forEach(def => {
            const item = document.createElement('li');
            const button = document.createElement('button');
            button.className = 'dropdown-item';
            button.type = 'button';
            button.dataset.definitionId = def.id;
            button.innerHTML = `
                <i class="bi ${def.icon || 'bi-robot'} agent-icon"></i>
                <span class="agent-name">${def.name}</span>
            `;
            button.addEventListener('click', () => {
                selectDefinition(def.id);
            });
            item.appendChild(button);
            menu.appendChild(item);
        });

        // Show the selector and new chat button
        if (elements.headerAgentSelector) {
            elements.headerAgentSelector.classList.remove('d-none');
        }
        if (elements.newChatBtn) {
            elements.newChatBtn.classList.remove('d-none');
        }
    }

    /**
     * Update header agent selector to show currently selected definition
     * @param {Object} definition - Selected definition
     * @param {Object} elements - DOM elements
     */
    updateHeaderAgentSelector(definition, elements) {
        if (!definition) return;

        // Update the icon and name
        if (elements.headerSelectedAgentIcon) {
            elements.headerSelectedAgentIcon.className = `bi ${definition.icon || 'bi-robot'}`;
        }
        if (elements.headerSelectedAgentName) {
            elements.headerSelectedAgentName.textContent = definition.name;
        }

        // Update active state in menu
        if (elements.headerAgentMenu) {
            const items = elements.headerAgentMenu.querySelectorAll('.dropdown-item');
            items.forEach(item => {
                if (item.dataset.definitionId === definition.id) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        }
    }

    /**
     * Apply UI restrictions based on definition type
     * @param {Object} restrictions - Restriction settings
     * @param {Object} elements - DOM elements
     */
    applyRestrictions(restrictions, elements) {
        // Note: We no longer hide the conversation list when canAccessConversations is false
        // The list should always be visible so users can see their conversations
        // If we need to disable interaction, we can add a visual indicator or disable clicks
        const conversationList = document.getElementById('conversation-list');
        if (conversationList) {
            // Add/remove a 'disabled' class instead of hiding completely
            conversationList.classList.toggle('interactions-disabled', !restrictions.canAccessConversations);
        }

        // Enable/disable text input
        if (elements.messageInput) {
            elements.messageInput.disabled = !restrictions.canTypeFreeText;
            if (!restrictions.canTypeFreeText) {
                elements.messageInput.placeholder = 'Respond using the widget above';
            }
        }
    }

    /**
     * Start a new conversation with the selected definition
     */
    async startNewConversation() {
        const definitionId = getSelectedDefinitionId();
        const definition = getSelectedDefinition();

        if (!definition) {
            showToast('Please select an agent type first', 'warning');
            return;
        }

        // Always clear the chat area first
        clearMessages();

        // For proactive definitions (agent_starts_first=true), use the proactive flow
        if (definition.is_proactive) {
            console.log('[ChatApp] Starting proactive conversation via + button');
            const elements = this.getDOMElements();
            await this.startProactiveConversation(definition, elements);
            return;
        }

        try {
            // Create new conversation with the selected definition
            const conversationId = await newConversation(definitionId);
            if (!conversationId) return;

            // Set context
            setConversationContext(conversationId, definitionId);

            // Hide welcome, show chat
            hideWelcomeMessage();

            // For definitions with templates (but not proactive), prepare for agent
            if (definition.has_template) {
                lockChatInput('Waiting for assistant...');
            } else {
                enableAndFocusInput();
            }
        } catch (error) {
            console.error('[ChatApp] Failed to start conversation:', error);
            showToast('Failed to start conversation', 'error');
        }
    }

    /**
     * Handle delete all unpinned conversations
     */
    async handleDeleteAllUnpinned() {
        try {
            // Get conversations to count unpinned
            const conversations = await api.getConversations();
            const pinnedIds = getPinnedConversations();
            const unpinnedCount = conversations.filter(c => !pinnedIds.has(c.id)).length;

            if (unpinnedCount === 0) {
                showToast('No unpinned conversations to delete', 'info');
                return;
            }

            // Show confirmation modal
            showDeleteAllUnpinnedModal(unpinnedCount, async () => {
                await deleteAllUnpinnedConversations();
            });
        } catch (error) {
            console.error('[ChatApp] Failed to delete unpinned conversations:', error);
            showToast('Failed to delete conversations', 'error');
        }
    }

    // =========================================================================
    // Utility Methods
    // =========================================================================

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
        setUploadEnabled(false);
        clearAttachedFiles();
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
            setUploadEnabled(true);

            // Load definitions (new) and conversations
            await loadDefinitions();
            await loadConversations();
            await this.fetchToolCount();
            await runHealthCheck();

            // Show the welcome definitions section
            const welcomeDefs = document.getElementById('welcome-definitions');
            if (welcomeDefs) {
                welcomeDefs.classList.remove('d-none');
            }

            // Update definition badge if one is already selected (from localStorage)
            const selectedDef = getSelectedDefinition();
            if (selectedDef) {
                this.updateHeaderAgentSelector(selectedDef, this.getDOMElements());
            }

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

        let message = getInputValue();
        if (!message || !this.isAuthenticated) return;

        // Prepend attached files info to message if any
        if (hasAttachedFiles()) {
            const filesMessage = getAttachedFilesMessage();
            message = filesMessage + message;
        }

        // Clear input and attached files
        clearAndDisableInput();
        clearCurrentDraft();
        clearAttachedFiles();
        hideWelcomeMessage();

        // Add user message
        addUserMessage(message);

        // Determine if we should use WebSocket for this conversation
        const definitionId = getSelectedDefinitionId();
        const conversationId = getCurrentConversationId();
        const useWebSocket = shouldUseWebSocket(definitionId);

        console.log('[ChatApp] handleSubmit - definitionId:', definitionId, 'conversationId:', conversationId);
        console.log('[ChatApp] handleSubmit - shouldUseWebSocket:', useWebSocket, 'wsIsConnected:', wsIsConnected());

        // If WebSocket should be used but isn't connected, connect now
        if (useWebSocket && !wsIsConnected()) {
            console.log('[ChatApp] Connecting WebSocket for conversation');
            try {
                // Set up WebSocket callbacks for this session
                setWebSocketCallbacks({
                    onConnected: data => {
                        console.log('[ChatApp] WebSocket reconnected for conversation:', data.conversation_id);
                        // Conversation ID should match if resuming
                        if (data.conversation_id && !conversationId) {
                            setCurrentConversationId(data.conversation_id);
                        }
                    },
                    onComplete: data => {
                        console.log('[ChatApp] Template complete');
                        setStreamingState(false);
                        updateSendButton(false);
                        setUploadEnabled(true);
                        this.updateSessionProtection();
                        loadConversations();
                        enableAndFocusInput();
                    },
                    onError: data => {
                        console.error('[ChatApp] WebSocket error:', data.message);
                        setStreamingState(false);
                        updateSendButton(false);
                        setUploadEnabled(true);
                        this.updateSessionProtection();
                        showToast(data.message || 'An error occurred', 'error');
                    },
                    onDisconnected: event => {
                        console.log('[ChatApp] WebSocket disconnected');
                        if (event.code !== 1000) {
                            setStreamingState(false);
                            updateSendButton(false);
                            setUploadEnabled(true);
                        }
                    },
                });

                // Connect with existing conversation ID to resume
                await wsConnect({
                    definitionId: definitionId,
                    conversationId: conversationId,
                });
            } catch (error) {
                console.error('[ChatApp] Failed to connect WebSocket:', error);
                showToast('Failed to connect. Trying alternative method...', 'warning');
                // Fall through to SSE fallback below
            }
        }

        // Check if we're now in a WebSocket session
        if (wsIsConnected()) {
            console.log('[ChatApp] Sending message via WebSocket');
            // Set streaming state
            setStreamingState(true);
            updateSendButton(true);
            setUploadEnabled(false);
            enableProtection('streaming');
            resetUserScroll();

            // Send via WebSocket - the handler manages thinking indicator
            wsSendMessage(message);
            return; // WebSocket callbacks will handle state reset
        }

        // Fall back to SSE for non-template conversations or if WebSocket failed
        const thinkingMsg = addThinkingMessage();

        // Set streaming state
        setStreamingState(true);
        updateSendButton(true);
        setUploadEnabled(false);
        enableProtection('streaming');
        resetUserScroll();

        // Send message with definition context
        await sendMessage(message, conversationId, getSelectedModelId(), thinkingMsg, definitionId);

        // Reset state
        setStreamingState(false);
        api.clearRequestState();
        updateSendButton(false);
        setUploadEnabled(true);
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
     * Show user permissions modal with OAuth2 scopes
     */
    showPermissions() {
        const scopes = this.currentUser?.scope || [];
        showPermissionsModal(scopes);
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
