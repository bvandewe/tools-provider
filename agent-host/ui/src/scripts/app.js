/**
 * ChatApp - Main Application Class
 * Orchestrates the chat interface with enhanced UX features
 */
import { api } from './services/api.js';
import { initModals, showRenameModal, showDeleteModal, showToolsModal, showToast, showHealthModal, showToolDetailsModal, showConversationInfoModal, showShareModal } from './services/modals.js';
import { startSessionMonitoring, stopSessionMonitoring } from './core/session-manager.js';

// Sidebar state key for localStorage
const SIDEBAR_COLLAPSED_KEY = 'agent-host:sidebar-collapsed';
const SELECTED_MODEL_KEY = 'agent-host:selected-model';
const PINNED_CONVERSATIONS_KEY = 'agent-host:pinned-conversations';
const MOBILE_BREAKPOINT = 768;

/**
 * Get pinned conversation IDs from localStorage
 * @returns {Set<string>} Set of pinned conversation IDs
 */
function getPinnedConversations() {
    try {
        const stored = localStorage.getItem(PINNED_CONVERSATIONS_KEY);
        return new Set(stored ? JSON.parse(stored) : []);
    } catch (e) {
        return new Set();
    }
}

/**
 * Save pinned conversation IDs to localStorage
 * @param {Set<string>} pinnedIds - Set of pinned conversation IDs
 */
function savePinnedConversations(pinnedIds) {
    localStorage.setItem(PINNED_CONVERSATIONS_KEY, JSON.stringify([...pinnedIds]));
}

export class ChatApp {
    constructor() {
        this.isAuthenticated = false;
        this.currentUser = null;
        this.currentConversationId = null;
        this.availableTools = null;
        this.availableModels = [];
        this.selectedModelId = null;
        this.appConfig = null;
        this.isStreaming = false;
        this.userHasScrolled = false;
        this.sidebarCollapsed = false;
        // Track streaming state per conversation for switching
        this.streamingConversationId = null;
        this.streamingReader = null;
        this.streamingThinkingElement = null;
        this.streamingContent = '';
        // Tool execution indicator
        this.toolExecutingEl = null;
    }

    async init() {
        // Get DOM elements
        this.messagesContainer = document.getElementById('messages-container');
        this.welcomeMessage = document.getElementById('welcome-message');
        this.welcomeSubtitle = document.getElementById('welcome-subtitle');
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.cancelBtn = document.getElementById('cancel-btn');
        this.statusIndicator = document.getElementById('status-indicator');
        this.themeToggle = document.getElementById('theme-toggle');
        this.userDropdown = document.getElementById('user-dropdown');
        this.dropdownUserName = document.getElementById('dropdown-user-name');
        this.loginBtn = document.getElementById('login-btn');
        this.logoutBtn = document.getElementById('logout-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.headerNewChatBtn = document.getElementById('header-new-chat-btn');
        this.sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
        this.collapseSidebarBtn = document.getElementById('collapse-sidebar-btn');
        this.toolsBtn = document.getElementById('tools-btn');
        this.conversationList = document.getElementById('conversation-list');
        this.chatSidebar = document.getElementById('chat-sidebar');
        this.sidebarOverlay = document.getElementById('sidebar-overlay');
        this.modelSelector = document.getElementById('model-selector');
        this.healthLink = document.getElementById('health-link');
        this.toolExecutingEl = document.getElementById('tool-executing');

        // Initialize modals
        initModals();

        // Load app configuration first
        await this.loadAppConfig();

        // Set up unauthorized handler for automatic logout
        api.setUnauthorizedHandler(() => this.handleSessionExpired());

        // Bind events
        this.chatForm.addEventListener('submit', e => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', e => this.handleKeyDown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());
        this.logoutBtn?.addEventListener('click', () => this.logout());
        this.newChatBtn?.addEventListener('click', () => this.newConversation());
        this.headerNewChatBtn?.addEventListener('click', () => this.newConversation());
        this.toolsBtn?.addEventListener('click', () => this.showTools());
        this.cancelBtn?.addEventListener('click', () => this.cancelCurrentRequest());
        this.sidebarToggleBtn?.addEventListener('click', () => this.expandSidebar());
        this.collapseSidebarBtn?.addEventListener('click', () => this.collapseSidebar());
        this.sidebarOverlay?.addEventListener('click', () => this.closeSidebar());
        this.modelSelector?.addEventListener('change', e => this.handleModelChange(e));
        this.healthLink?.addEventListener('click', e => this.showHealthCheck(e));

        // Track user scroll to prevent auto-scroll during streaming
        this.messagesContainer?.addEventListener('scroll', () => this.handleUserScroll());

        // Handle window resize for responsive behavior
        window.addEventListener('resize', () => this.handleResize());

        // Initialize sidebar state
        this.initSidebarState();

        // Check authentication
        await this.checkAuth();
    }

    /**
     * Load application configuration from the backend
     */
    async loadAppConfig() {
        try {
            this.appConfig = await api.getConfig();

            // Apply app name to page title, header, and welcome message
            if (this.appConfig.app_name) {
                document.title = `${this.appConfig.app_name} - AI Chat`;
                const headerAppName = document.getElementById('header-app-name');
                if (headerAppName) {
                    headerAppName.textContent = this.appConfig.app_name;
                }
                const welcomeTitle = document.getElementById('welcome-title');
                if (welcomeTitle) {
                    welcomeTitle.textContent = `Welcome to ${this.appConfig.app_name}`;
                }
            }

            // Apply welcome message
            if (this.welcomeSubtitle && this.appConfig.welcome_message) {
                this.welcomeSubtitle.textContent = this.appConfig.welcome_message;
            }

            // Load model options from config (only if model selection is allowed)
            if (this.appConfig.allow_model_selection && this.appConfig.available_models && this.appConfig.available_models.length > 0) {
                this.availableModels = this.appConfig.available_models;
                this.initModelSelector();
            }

            // Apply sidebar footer
            this.updateSidebarFooter();

            console.log('App config loaded:', this.appConfig);
        } catch (error) {
            console.error('Failed to load app config:', error);
            // Use defaults
            this.appConfig = {
                app_name: 'Agent Host',
                welcome_message: 'Your AI assistant with access to powerful tools.',
                rate_limit_requests_per_minute: 20,
                rate_limit_concurrent_requests: 1,
                app_tag: '',
                app_repo_url: '',
                available_models: [],
            };
        }
    }

    /**
     * Initialize the model selector dropdown
     */
    initModelSelector() {
        if (!this.modelSelector || !this.availableModels.length) return;

        // Restore previously selected model from localStorage
        const savedModelId = localStorage.getItem(SELECTED_MODEL_KEY);

        // Clear and populate options
        this.modelSelector.innerHTML = '';

        this.availableModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name;
            option.title = model.description || '';
            this.modelSelector.appendChild(option);
        });

        // Restore selection or use first model as default
        if (savedModelId && this.availableModels.some(m => m.id === savedModelId)) {
            this.selectedModelId = savedModelId;
            this.modelSelector.value = savedModelId;
        } else if (this.availableModels.length > 0) {
            this.selectedModelId = this.availableModels[0].id;
            this.modelSelector.value = this.selectedModelId;
        }

        // Show the model selector container
        const modelSelectorContainer = document.getElementById('model-selector-container');
        if (modelSelectorContainer) {
            modelSelectorContainer.classList.remove('d-none');
        }
    }

    /**
     * Handle model selection change
     */
    handleModelChange(e) {
        this.selectedModelId = e.target.value;
        localStorage.setItem(SELECTED_MODEL_KEY, this.selectedModelId);

        const selectedModel = this.availableModels.find(m => m.id === this.selectedModelId);
        if (selectedModel) {
            showToast(`Switched to ${selectedModel.name}`, 'info');
        }
    }

    /**
     * Show health check modal
     */
    showHealthCheck(e) {
        e.preventDefault();
        showHealthModal(() => api.checkHealth());
    }

    /**
     * Update the sidebar footer with app tag, copyright, and GitHub link
     */
    updateSidebarFooter() {
        const appTagEl = document.getElementById('app-tag');
        const copyrightYearEl = document.getElementById('copyright-year');
        const githubLinkEl = document.getElementById('github-link');

        // Set current year for copyright
        if (copyrightYearEl) {
            copyrightYearEl.textContent = new Date().getFullYear();
        }

        // Set app tag if configured
        if (appTagEl && this.appConfig.app_tag) {
            appTagEl.textContent = this.appConfig.app_tag;
        }

        // Show GitHub link if URL is configured
        if (githubLinkEl && this.appConfig.app_repo_url) {
            githubLinkEl.href = this.appConfig.app_repo_url;
            githubLinkEl.classList.remove('d-none');
        }
    }

    /**
     * Initialize sidebar collapsed state from localStorage
     */
    initSidebarState() {
        // Check if we're on mobile
        const isMobile = window.innerWidth < MOBILE_BREAKPOINT;

        if (isMobile) {
            // Always start collapsed on mobile
            this.sidebarCollapsed = true;
        } else {
            // Restore from localStorage on desktop
            const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
            this.sidebarCollapsed = stored === 'true';
        }

        this.applySidebarState();
    }

    /**
     * Apply the current sidebar collapsed state to the DOM
     */
    applySidebarState() {
        const isMobile = window.innerWidth < MOBILE_BREAKPOINT;

        if (this.chatSidebar) {
            if (isMobile) {
                // On mobile, use 'open' class (sidebar slides in from left)
                this.chatSidebar.classList.remove('collapsed');
                this.chatSidebar.classList.toggle('open', !this.sidebarCollapsed);
            } else {
                // On desktop, use 'collapsed' class (sidebar shrinks width)
                this.chatSidebar.classList.remove('open');
                this.chatSidebar.classList.toggle('collapsed', this.sidebarCollapsed);
            }
        }

        // Show/hide header buttons based on sidebar state
        if (this.sidebarToggleBtn) {
            // Show expand button when collapsed (on both mobile and desktop)
            this.sidebarToggleBtn.classList.toggle('d-none', !this.sidebarCollapsed);
        }

        if (this.headerNewChatBtn) {
            // Show new chat in header when sidebar is collapsed and user is authenticated
            const showInHeader = this.sidebarCollapsed && this.isAuthenticated;
            this.headerNewChatBtn.classList.toggle('d-none', !showInHeader);
        }
    }

    /**
     * Collapse the sidebar (hide it)
     */
    collapseSidebar() {
        this.sidebarCollapsed = true;

        // Persist state (only on desktop)
        if (window.innerWidth >= MOBILE_BREAKPOINT) {
            localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');
        }

        this.applySidebarState();
        this.sidebarOverlay?.classList.remove('active');
    }

    /**
     * Expand the sidebar (show it)
     */
    expandSidebar() {
        this.sidebarCollapsed = false;

        // Persist state (only on desktop)
        if (window.innerWidth >= MOBILE_BREAKPOINT) {
            localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');
        }

        this.applySidebarState();

        // Show overlay on mobile when sidebar is open
        const isMobile = window.innerWidth < MOBILE_BREAKPOINT;
        if (isMobile) {
            this.sidebarOverlay?.classList.add('active');
        }
    }

    /**
     * Close the sidebar (mobile only - same as collapse)
     */
    closeSidebar() {
        this.collapseSidebar();
    }

    /**
     * Handle window resize events
     */
    handleResize() {
        const isMobile = window.innerWidth < MOBILE_BREAKPOINT;

        if (isMobile) {
            // Auto-collapse on mobile when resizing down
            if (!this.sidebarCollapsed) {
                this.sidebarCollapsed = true;
                this.applySidebarState();
                this.sidebarOverlay?.classList.remove('active');
            }
        } else {
            // Remove mobile classes when going back to desktop
            this.chatSidebar?.classList.remove('open');
            this.sidebarOverlay?.classList.remove('active');
            // Reapply desktop state
            this.applySidebarState();
        }
    }

    /**
     * Handle user scroll event - track if user has manually scrolled up
     */
    handleUserScroll() {
        if (!this.messagesContainer) return;

        const { scrollTop, scrollHeight, clientHeight } = this.messagesContainer;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

        // If user scrolls up during streaming, stop auto-scroll
        if (this.isStreaming && !isAtBottom) {
            this.userHasScrolled = true;
        }

        // If user scrolls back to bottom, resume auto-scroll
        if (isAtBottom) {
            this.userHasScrolled = false;
        }
    }

    /**
     * Check if current user has admin role
     * @returns {boolean}
     */
    isAdmin() {
        if (!this.currentUser) return false;

        // Check various claim locations for roles (matching backend logic)
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
     * Handle session expiration - called by session manager or API unauthorized handler
     */
    handleSessionExpired() {
        // Prevent multiple triggers
        if (!this.isAuthenticated) return;

        this.isAuthenticated = false;
        this.currentUser = null;

        // Stop session monitoring
        stopSessionMonitoring();

        // Update UI to show logged out state
        this.updateUI();

        // Note: Session manager handles redirect to login
    }

    async checkAuth() {
        try {
            const data = await api.checkAuth();
            this.isAuthenticated = true;
            this.currentUser = data.user;
            this.updateUI();
            await this.loadConversations();
            await this.fetchToolCount();

            // Run health check after login to update health icon
            await this.runHealthCheck();

            // Start session monitoring with activity tracking, idle warning, and cross-app sync
            await startSessionMonitoring(() => this.handleSessionExpired());
        } catch (error) {
            console.error('Auth check failed:', error);
            this.isAuthenticated = false;
            this.updateUI();
        }
    }

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

    updateUI() {
        const userName = this.currentUser?.name || this.currentUser?.username || 'User';

        if (this.isAuthenticated) {
            // Show user dropdown and theme toggle
            this.userDropdown?.classList.remove('d-none');
            this.themeToggle?.classList.remove('d-none');

            // Update username in dropdown
            if (this.dropdownUserName) {
                this.dropdownUserName.textContent = userName;
            }

            this.loginBtn?.classList.add('d-none');
            if (this.messageInput) this.messageInput.disabled = false;
            this.updateSendButton(false);

            // Update login prompt - remove animation and change text
            const loginPrompt = this.welcomeMessage?.querySelector('.login-prompt');
            if (loginPrompt) {
                loginPrompt.classList.remove('login-prompt');
                loginPrompt.innerHTML = 'Type a message to start chatting.';
            }

            this.setStatus('connected', 'Connected');
        } else {
            this.userDropdown?.classList.add('d-none');
            this.themeToggle?.classList.add('d-none');
            this.loginBtn?.classList.remove('d-none');
            if (this.messageInput) this.messageInput.disabled = true;
            this.updateSendButton(true);
            this.setStatus('disconnected', 'Not authenticated');
        }
    }

    /**
     * Update send/cancel button visibility based on streaming state
     */
    updateSendButton(disabled) {
        if (this.sendBtn) {
            this.sendBtn.disabled = disabled;
            this.sendBtn.classList.toggle('d-none', this.isStreaming);
        }
        if (this.cancelBtn) {
            this.cancelBtn.classList.toggle('d-none', !this.isStreaming);
        }
    }

    setStatus(state, text) {
        if (!this.statusIndicator) return;
        this.statusIndicator.className = `status-indicator ${state}`;
        const statusText = this.statusIndicator.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = text;
        }
    }

    /**
     * Show tool executing indicator in status bar
     * @param {string} toolName - Name of the tool being executed
     */
    showToolExecuting(toolName) {
        if (!this.toolExecutingEl) return;

        const toolNameEl = this.toolExecutingEl.querySelector('.tool-name');
        if (toolNameEl) {
            toolNameEl.textContent = toolName;
        }
        this.toolExecutingEl.classList.remove('d-none');
    }

    /**
     * Hide tool executing indicator
     */
    hideToolExecuting() {
        if (!this.toolExecutingEl) return;
        this.toolExecutingEl.classList.add('d-none');
    }

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

    async loadConversations() {
        try {
            const conversations = await api.getConversations();
            this.renderConversations(conversations);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        }
    }

    renderConversations(conversations) {
        if (!this.conversationList) return;

        this.conversationList.innerHTML = '';

        if (conversations.length === 0) {
            this.conversationList.innerHTML = '<p class="text-muted p-3">No conversations yet</p>';
            return;
        }

        // Get pinned conversations and sort - pinned first, then by update date
        const pinnedIds = getPinnedConversations();
        const sortedConversations = [...conversations].sort((a, b) => {
            const aIsPinned = pinnedIds.has(a.id);
            const bIsPinned = pinnedIds.has(b.id);
            if (aIsPinned && !bIsPinned) return -1;
            if (!aIsPinned && bIsPinned) return 1;
            return 0; // Keep original order within groups
        });

        sortedConversations.forEach(conv => {
            const isPinned = pinnedIds.has(conv.id);
            const item = document.createElement('div');
            item.className = 'conversation-item';
            item.dataset.conversationId = conv.id;
            if (conv.id === this.currentConversationId) {
                item.classList.add('active');
            }
            if (isPinned) {
                item.classList.add('pinned');
            }
            item.innerHTML = `
                <div class="conversation-content">
                    <div class="conversation-title-wrapper">
                        ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                        <p class="conversation-title">${this.escapeHtml(conv.title || 'New conversation')}</p>
                    </div>
                    <div class="conversation-meta-row">
                        <p class="conversation-meta">${conv.message_count} messages</p>
                        <div class="conversation-actions">
                            <button class="btn-action btn-pin ${isPinned ? 'active' : ''}" title="${isPinned ? 'Unpin' : 'Pin'}">
                                <i class="bi bi-pin${isPinned ? '-fill' : ''}"></i>
                            </button>
                            <button class="btn-action btn-share" title="Share">
                                <i class="bi bi-share"></i>
                            </button>
                            <button class="btn-action btn-info-conv" title="Details">
                                <i class="bi bi-info-circle"></i>
                            </button>
                            <button class="btn-action btn-rename" title="Rename">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn-action btn-delete" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Click on content loads conversation
            item.querySelector('.conversation-content').addEventListener('click', () => {
                this.loadConversation(conv.id);
                // Close sidebar on mobile after selection
                if (window.innerWidth < MOBILE_BREAKPOINT) {
                    this.closeSidebar();
                }
            });

            // Pin/Unpin button
            item.querySelector('.btn-pin').addEventListener('click', e => {
                e.stopPropagation();
                this.togglePinConversation(conv.id);
            });

            // Share button - show share modal
            item.querySelector('.btn-share').addEventListener('click', async e => {
                e.stopPropagation();
                try {
                    // Fetch full conversation with messages for export
                    const fullConv = await api.getConversation(conv.id);
                    showShareModal(fullConv);
                } catch (error) {
                    console.error('Failed to load conversation for sharing:', error);
                    showToast('Failed to share conversation', 'error');
                }
            });

            // Info button - show conversation info modal
            item.querySelector('.btn-info-conv').addEventListener('click', async e => {
                e.stopPropagation();
                try {
                    // Fetch full conversation with messages to get detailed stats
                    const fullConv = await api.getConversation(conv.id);
                    showConversationInfoModal(fullConv);
                } catch (error) {
                    console.error('Failed to load conversation details:', error);
                    showToast('Failed to load conversation details', 'error');
                }
            });

            // Rename button - show modal
            item.querySelector('.btn-rename').addEventListener('click', e => {
                e.stopPropagation();
                showRenameModal(conv.id, conv.title || 'New conversation', (id, newTitle) => {
                    this.renameConversation(id, newTitle);
                });
            });

            // Delete button - show confirmation modal
            item.querySelector('.btn-delete').addEventListener('click', e => {
                e.stopPropagation();
                showDeleteModal(conv.id, conv.title || 'New conversation', id => {
                    this.deleteConversation(id);
                });
            });

            this.conversationList.appendChild(item);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Toggle pin state for a conversation
     * @param {string} conversationId - Conversation ID to pin/unpin
     */
    togglePinConversation(conversationId) {
        const pinnedIds = getPinnedConversations();
        const wasPinned = pinnedIds.has(conversationId);

        if (wasPinned) {
            pinnedIds.delete(conversationId);
            showToast('Conversation unpinned', 'success');
        } else {
            pinnedIds.add(conversationId);
            showToast('Conversation pinned', 'success');
        }

        savePinnedConversations(pinnedIds);
        this.loadConversations(); // Refresh to re-sort
    }

    async renameConversation(conversationId, newTitle) {
        try {
            await api.renameConversation(conversationId, newTitle);
            await this.loadConversations();
            showToast('Conversation renamed', 'success');
        } catch (error) {
            console.error('Failed to rename conversation:', error);
            showToast(error.message || 'Failed to rename conversation', 'error');
        }
    }

    async deleteConversation(conversationId) {
        try {
            await api.deleteConversation(conversationId);

            // If we deleted the current conversation, clear the chat
            if (conversationId === this.currentConversationId) {
                this.currentConversationId = null;
                if (this.messagesContainer) {
                    this.messagesContainer.innerHTML = '';
                }
                if (this.welcomeMessage) {
                    this.welcomeMessage.style.display = '';
                }
            }

            await this.loadConversations();
            showToast('Conversation deleted', 'success');
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            showToast(error.message || 'Failed to delete conversation', 'error');
        }
    }

    async loadConversation(conversationId) {
        try {
            // If switching to the currently streaming conversation, restore the UI
            if (this.isStreaming && conversationId === this.streamingConversationId) {
                // Just switch back to the streaming view - stream continues in background
                this.currentConversationId = conversationId;
                await this.loadConversations(); // Update sidebar selection
                return;
            }

            const conversation = await api.getConversation(conversationId);
            this.currentConversationId = conversationId;
            this.renderMessages(conversation.messages);
            await this.loadConversations(); // Update sidebar

            // If there's an active stream for this conversation, restore the thinking indicator
            if (this.isStreaming && this.streamingConversationId === conversationId && this.streamingThinkingElement) {
                this.messagesContainer?.appendChild(this.streamingThinkingElement);
                this.scrollToBottom(true);
            }
        } catch (error) {
            console.error('Failed to load conversation:', error);
            showToast('Failed to load conversation', 'error');
        }
    }

    renderMessages(messages) {
        if (!this.messagesContainer) return;

        this.messagesContainer.innerHTML = '';
        if (this.welcomeMessage) {
            this.welcomeMessage.remove();
        }

        // Pre-process messages to merge tool_results from empty-content assistant messages
        // into the next assistant message with content
        const processedMessages = this._mergeToolResultsIntoContentMessages(messages);

        processedMessages.forEach(msg => {
            if (msg.role === 'system') return; // Don't show system messages

            const messageEl = document.createElement('chat-message');
            messageEl.setAttribute('role', msg.role);
            messageEl.setAttribute('content', msg.content);

            // Add created_at timestamp if present
            if (msg.created_at) {
                messageEl.setAttribute('created-at', msg.created_at);
            }

            // Add tool calls data if present (for assistant messages)
            if (msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0) {
                messageEl.setAttribute('tool-calls', JSON.stringify(msg.tool_calls));
            }

            // Add tool results data if present (for assistant messages with executed tools)
            if (msg.role === 'assistant' && msg.tool_results && msg.tool_results.length > 0) {
                messageEl.setAttribute('tool-results', JSON.stringify(msg.tool_results));
            }

            // Listen for tool badge clicks
            messageEl.addEventListener('tool-badge-click', e => {
                showToolDetailsModal(e.detail.toolCalls, e.detail.toolResults, {
                    isAdmin: this.isAdmin(),
                    fetchSourceInfo: async toolName => {
                        return await api.getToolSourceInfo(toolName);
                    },
                });
            });

            this.messagesContainer.appendChild(messageEl);
        });

        this.scrollToBottom(true); // Force scroll when loading conversation
    }

    /**
     * Merge tool_results from empty-content assistant messages into the next assistant message with content.
     * This handles the case where tool execution creates a message with empty content but tool_results,
     * followed by another message with the actual response content.
     * @param {Array} messages - Array of message objects from the API
     * @returns {Array} - Processed messages with tool_results merged appropriately
     */
    _mergeToolResultsIntoContentMessages(messages) {
        const result = [];
        let pendingToolResults = [];
        let pendingToolCalls = [];

        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];

            // Skip system messages
            if (msg.role === 'system') {
                result.push(msg);
                continue;
            }

            // Check if this is an assistant message with tool_results but empty/no content
            if (msg.role === 'assistant' && (!msg.content || msg.content.trim() === '')) {
                // Collect tool_results and tool_calls from this empty message
                if (msg.tool_results && msg.tool_results.length > 0) {
                    pendingToolResults = pendingToolResults.concat(msg.tool_results);
                }
                if (msg.tool_calls && msg.tool_calls.length > 0) {
                    pendingToolCalls = pendingToolCalls.concat(msg.tool_calls);
                }
                // Skip adding this empty message to results
                continue;
            }

            // If this is an assistant message with content, merge any pending tool data
            if (msg.role === 'assistant' && msg.content && msg.content.trim() !== '') {
                const mergedMsg = { ...msg };

                // Merge pending tool_results
                if (pendingToolResults.length > 0) {
                    mergedMsg.tool_results = pendingToolResults.concat(msg.tool_results || []);
                    pendingToolResults = [];
                }

                // Merge pending tool_calls
                if (pendingToolCalls.length > 0) {
                    mergedMsg.tool_calls = pendingToolCalls.concat(msg.tool_calls || []);
                    pendingToolCalls = [];
                }

                result.push(mergedMsg);
            } else {
                // User message or other - just add it
                result.push(msg);
            }
        }

        // If there are still pending tool results (edge case - tool results at end with no follow-up),
        // create a message for them
        if (pendingToolResults.length > 0 || pendingToolCalls.length > 0) {
            result.push({
                role: 'assistant',
                content: '',
                tool_results: pendingToolResults,
                tool_calls: pendingToolCalls,
            });
        }

        return result;
    }

    async newConversation() {
        try {
            const data = await api.createConversation();
            this.currentConversationId = data.conversation_id;
            if (this.messagesContainer) {
                this.messagesContainer.innerHTML = '';
            }
            await this.loadConversations();

            // Close sidebar on mobile
            if (window.innerWidth < MOBILE_BREAKPOINT) {
                this.closeSidebar();
            }
        } catch (error) {
            console.error('Failed to create conversation:', error);
            showToast('Failed to create conversation', 'error');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();

        // Don't allow sending while streaming
        if (this.isStreaming) {
            showToast('Please wait for the current response to complete', 'warning');
            return;
        }

        const message = this.messageInput?.value.trim();
        if (!message || !this.isAuthenticated) return;

        // Clear input and disable
        if (this.messageInput) {
            this.messageInput.value = '';
            this.messageInput.disabled = true;
        }
        this.autoResize();

        // Hide welcome message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }

        // Add user message
        const userMsg = document.createElement('chat-message');
        userMsg.setAttribute('role', 'user');
        userMsg.setAttribute('content', message);
        this.messagesContainer?.appendChild(userMsg);
        this.scrollToBottom(true);

        // Add thinking indicator
        const thinkingMsg = document.createElement('chat-message');
        thinkingMsg.setAttribute('role', 'assistant');
        thinkingMsg.setAttribute('status', 'thinking');
        this.messagesContainer?.appendChild(thinkingMsg);
        this.scrollToBottom(true);

        // Set streaming state
        this.isStreaming = true;
        this.userHasScrolled = false;
        this.updateSendButton(true);

        // Send message via SSE
        await this.sendMessage(message, thinkingMsg);

        // Reset streaming state
        this.isStreaming = false;
        this.userHasScrolled = false;
        api.clearRequestState();
        this.updateSendButton(false);

        // Re-enable input
        if (this.messageInput) {
            this.messageInput.disabled = false;
            this.messageInput.focus();
        }
    }

    /**
     * Cancel the current streaming request
     */
    async cancelCurrentRequest() {
        if (!this.isStreaming) return;

        try {
            await api.cancelCurrentRequest();
            showToast('Request cancelled', 'info');
        } catch (error) {
            console.error('Failed to cancel request:', error);
        }
    }

    async sendMessage(message, thinkingElement) {
        this.setStatus('streaming', 'Streaming...');
        let assistantContent = '';

        // Track streaming state for conversation switching
        this.streamingConversationId = this.currentConversationId;
        this.streamingThinkingElement = thinkingElement;
        this.streamingContent = '';

        try {
            const response = await api.sendMessage(message, this.currentConversationId, this.selectedModelId);

            const reader = response.body.getReader();
            this.streamingReader = reader;
            const decoder = new TextDecoder();
            let currentEventType = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        // Capture the event type for the next data line
                        currentEventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            // Handle the event and get updated content
                            const result = this.handleStreamEvent(currentEventType, data, thinkingElement, assistantContent);

                            // Update accumulated content if returned
                            if (result && result.content !== undefined) {
                                assistantContent = result.content;
                                this.streamingContent = assistantContent;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e, line);
                        }
                    }
                }
            }

            this.setStatus('connected', 'Connected');
            this.hideToolExecuting();
            await this.loadConversations();
        } catch (error) {
            // Check if it was an abort
            if (error.name === 'AbortError') {
                thinkingElement.setAttribute('content', assistantContent || '_Response cancelled_');
                thinkingElement.setAttribute('status', 'complete');
                this.setStatus('connected', 'Cancelled');
            } else if (error.message?.includes('Rate limit')) {
                showToast(error.message, 'error');
                thinkingElement.remove();
                this.setStatus('disconnected', 'Rate limited');
            } else {
                console.error('Send message failed:', error);
                thinkingElement.setAttribute('content', 'Sorry, an error occurred. Please try again.');
                thinkingElement.setAttribute('status', 'complete');
                this.setStatus('disconnected', 'Error');
            }
        }
    }

    handleStreamEvent(eventType, data, thinkingElement, currentContent) {
        switch (eventType) {
            case 'stream_started':
                // Store request ID for potential cancellation
                if (data.request_id) {
                    api.setCurrentRequestId(data.request_id);
                }
                // Capture conversation_id and update sidebar if this is a new conversation
                if (data.conversation_id && data.conversation_id !== this.currentConversationId) {
                    this.currentConversationId = data.conversation_id;
                    this.streamingConversationId = data.conversation_id;
                    // Refresh sidebar to show the new conversation
                    this.loadConversations();
                }
                return null;

            case 'assistant_thinking':
                // Already showing thinking indicator
                return null;

            case 'content_chunk':
                // Accumulate content and update UI
                const newContent = currentContent + (data.content || '');
                thinkingElement.setAttribute('content', newContent);
                thinkingElement.setAttribute('status', 'complete');
                this.scrollToBottom();
                return { content: newContent };

            case 'tool_calls_detected':
                // Store tool calls on the thinking element for badge display
                // We no longer create inline tool-call-card components - just use the badge
                if (data.tool_calls) {
                    thinkingElement.setAttribute('tool-calls', JSON.stringify(data.tool_calls));
                }
                return null;

            case 'tool_executing':
                // Show tool executing indicator in status bar
                this.showToolExecuting(data.tool_name);
                return null;

            case 'tool_result':
                // Hide tool executing indicator
                this.hideToolExecuting();

                // Store tool result for badge display
                // Get existing tool results or initialize empty array
                let toolResults = [];
                try {
                    const existingResults = thinkingElement.getAttribute('tool-results');
                    if (existingResults) {
                        toolResults = JSON.parse(existingResults);
                    }
                } catch (e) {
                    toolResults = [];
                }
                toolResults.push({
                    call_id: data.call_id,
                    tool_name: data.tool_name,
                    success: data.success,
                    result: data.result,
                    error: data.error,
                    execution_time_ms: data.execution_time_ms,
                });
                thinkingElement.setAttribute('tool-results', JSON.stringify(toolResults));
                return null;

            case 'message_complete':
                // Update the message content - tool info is displayed as badges
                thinkingElement.setAttribute('content', data.content || currentContent);
                thinkingElement.setAttribute('status', 'complete');
                this.hideToolExecuting();
                return { content: data.content || currentContent };

            case 'message_added':
                // User message was added - nothing to do here
                return null;

            case 'stream_complete':
                // Stream finished - clear streaming state
                this.streamingConversationId = null;
                this.streamingReader = null;
                this.streamingThinkingElement = null;
                this.streamingContent = '';
                this.hideToolExecuting();
                return null;

            case 'cancelled':
                // Request was cancelled by server
                thinkingElement.setAttribute('content', currentContent || '_Response cancelled_');
                thinkingElement.setAttribute('status', 'complete');
                this.hideToolExecuting();
                return null;

            case 'error':
                // Handle enhanced error structure with error_code
                const errorMsg = data.error || 'An unknown error occurred';
                const errorCode = data.error_code;

                // Show appropriate toast based on error code
                if (errorCode === 'ollama_unavailable') {
                    showToast('AI model service is unavailable. Check the health status.', 'error');
                } else if (errorCode === 'model_not_found') {
                    showToast(`Model not found: ${errorMsg}`, 'error');
                } else if (errorCode === 'ollama_timeout') {
                    showToast('AI model request timed out. Please try again.', 'warning');
                } else if (errorCode === 'connection_error') {
                    showToast('Cannot connect to AI service. Check your connection.', 'error');
                } else if (errorCode === 'timeout') {
                    showToast('Request timed out. The AI model may be busy.', 'warning');
                } else {
                    showToast(`Error: ${errorMsg}`, 'error');
                }

                thinkingElement.setAttribute('content', `_Error: ${errorMsg}_`);
                thinkingElement.setAttribute('status', 'complete');
                return null;

            default:
                console.log('Unknown SSE event type:', eventType, data);
                return null;
        }
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.chatForm?.dispatchEvent(new Event('submit'));
        }
    }

    autoResize() {
        if (!this.messageInput) return;
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    /**
     * Scroll to bottom of messages container
     * @param {boolean} force - Force scroll even if user has scrolled up
     */
    scrollToBottom(force = false) {
        if (!this.messagesContainer) return;

        // Don't auto-scroll if user has manually scrolled up (unless forced)
        if (!force && this.userHasScrolled) return;

        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    logout() {
        // Stop session monitoring before logout
        stopSessionMonitoring();
        api.logout();
    }

    /**
     * Show tools modal with refresh capability
     */
    async showTools() {
        try {
            // Always fetch fresh when opening modal
            this.availableTools = await api.getTools();
            showToolsModal(this.availableTools, async () => {
                // Refresh callback
                try {
                    this.availableTools = await api.getTools(true); // Force refresh
                    await this.fetchToolCount(); // Update indicator
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
}

export default ChatApp;
