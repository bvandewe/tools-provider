/**
 * ChatApp - Main Application Class
 * Orchestrates the chat interface
 */
import { api } from './services/api.js';
import { initModals, showRenameModal, showDeleteModal, showToolsModal, showToast } from './services/modals.js';

export class ChatApp {
    constructor() {
        this.isAuthenticated = false;
        this.currentUser = null;
        this.currentConversationId = null;
        this.availableTools = null;
        this.sessionCheckInterval = null;
    }

    async init() {
        // Get DOM elements
        this.messagesContainer = document.getElementById('messages-container');
        this.welcomeMessage = document.getElementById('welcome-message');
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.statusIndicator = document.getElementById('status-indicator');
        this.userInfo = document.getElementById('user-info');
        this.loginBtn = document.getElementById('login-btn');
        this.logoutBtn = document.getElementById('logout-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.toolsBtn = document.getElementById('tools-btn');
        this.conversationList = document.getElementById('conversation-list');

        // Initialize modals
        initModals();

        // Set up unauthorized handler for automatic logout
        api.setUnauthorizedHandler(() => this.handleSessionExpired());

        // Bind events
        this.chatForm.addEventListener('submit', e => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', e => this.handleKeyDown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());
        this.logoutBtn?.addEventListener('click', () => this.logout());
        this.newChatBtn?.addEventListener('click', () => this.newConversation());
        this.toolsBtn?.addEventListener('click', () => this.showTools());

        // Check authentication
        await this.checkAuth();

        // Start periodic session check (every 60 seconds)
        this.startSessionCheck();
    }

    /**
     * Handle session expiration - show message and redirect to login
     */
    handleSessionExpired() {
        // Prevent multiple triggers
        if (!this.isAuthenticated) return;

        this.isAuthenticated = false;
        this.currentUser = null;
        this.stopSessionCheck();

        // Show toast notification
        showToast('Your session has expired. Please log in again.', 'warning');

        // Update UI to show logged out state
        this.updateUI();

        // Redirect to login after a short delay
        setTimeout(() => {
            window.location.href = '/api/auth/login';
        }, 2000);
    }

    /**
     * Start periodic session validation
     */
    startSessionCheck() {
        // Check session every 60 seconds
        this.sessionCheckInterval = setInterval(async () => {
            if (this.isAuthenticated) {
                try {
                    await api.checkAuth();
                } catch (error) {
                    // Session is no longer valid
                    this.handleSessionExpired();
                }
            }
        }, 60000);
    }

    /**
     * Stop periodic session check
     */
    stopSessionCheck() {
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
            this.sessionCheckInterval = null;
        }
    }

    async checkAuth() {
        try {
            const data = await api.checkAuth();
            this.isAuthenticated = true;
            this.currentUser = data.user;
            this.updateUI();
            await this.loadConversations();
            await this.fetchToolCount();
        } catch (error) {
            console.error('Auth check failed:', error);
            this.isAuthenticated = false;
            this.updateUI();
        }
    }

    updateUI() {
        if (this.isAuthenticated) {
            this.userInfo.classList.remove('d-none');
            this.userInfo.querySelector('.user-name').textContent = this.currentUser?.name || this.currentUser?.username;
            this.loginBtn.classList.add('d-none');
            this.messageInput.disabled = false;
            this.sendBtn.disabled = false;
            this.welcomeMessage.querySelector('p.text-muted').textContent = 'Type a message to start chatting.';
            this.setStatus('connected', 'Connected');
        } else {
            this.userInfo.classList.add('d-none');
            this.loginBtn.classList.remove('d-none');
            this.messageInput.disabled = true;
            this.sendBtn.disabled = true;
            this.setStatus('disconnected', 'Not authenticated');
        }
    }

    setStatus(state, text) {
        this.statusIndicator.className = `status-indicator ${state}`;
        this.statusIndicator.querySelector('.status-text').textContent = text;
    }

    async fetchToolCount() {
        const toolsIndicator = document.getElementById('tools-indicator');
        const toolsCount = toolsIndicator?.querySelector('.tools-count');
        if (!toolsCount) return;

        try {
            const tools = await api.getTools();
            this.availableTools = tools;
            toolsCount.textContent = tools.length;
            toolsIndicator.classList.toggle('has-tools', tools.length > 0);
            toolsIndicator.title = tools.length > 0 ? `${tools.length} tool${tools.length === 1 ? '' : 's'} available` : 'No tools available';
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
        this.conversationList.innerHTML = '';

        if (conversations.length === 0) {
            this.conversationList.innerHTML = '<p class="text-muted p-3">No conversations yet</p>';
            return;
        }

        conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            item.dataset.conversationId = conv.id;
            if (conv.id === this.currentConversationId) {
                item.classList.add('active');
            }
            item.innerHTML = `
                <div class="conversation-content">
                    <p class="conversation-title">${this.escapeHtml(conv.title || 'New conversation')}</p>
                    <p class="conversation-meta">${conv.message_count} messages</p>
                </div>
                <div class="conversation-actions">
                    <button class="btn-action btn-rename" title="Rename">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn-action btn-delete" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;

            // Click on content loads conversation
            item.querySelector('.conversation-content').addEventListener('click', () => {
                this.loadConversation(conv.id);
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
                this.messagesContainer.innerHTML = '';
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
            const conversation = await api.getConversation(conversationId);
            this.currentConversationId = conversationId;
            this.renderMessages(conversation.messages);
            await this.loadConversations(); // Update sidebar
        } catch (error) {
            console.error('Failed to load conversation:', error);
            showToast('Failed to load conversation', 'error');
        }
    }

    renderMessages(messages) {
        this.messagesContainer.innerHTML = '';
        this.welcomeMessage?.remove();

        messages.forEach(msg => {
            if (msg.role === 'system') return; // Don't show system messages

            const messageEl = document.createElement('chat-message');
            messageEl.setAttribute('role', msg.role);
            messageEl.setAttribute('content', msg.content);
            this.messagesContainer.appendChild(messageEl);
        });

        this.scrollToBottom();
    }

    async newConversation() {
        try {
            const data = await api.createConversation();
            this.currentConversationId = data.conversation_id;
            this.messagesContainer.innerHTML = '';
            await this.loadConversations();
        } catch (error) {
            console.error('Failed to create conversation:', error);
            showToast('Failed to create conversation', 'error');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();

        const message = this.messageInput.value.trim();
        if (!message || !this.isAuthenticated) return;

        // Clear input and disable
        this.messageInput.value = '';
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;
        this.autoResize();

        // Hide welcome message
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }

        // Add user message
        const userMsg = document.createElement('chat-message');
        userMsg.setAttribute('role', 'user');
        userMsg.setAttribute('content', message);
        this.messagesContainer.appendChild(userMsg);
        this.scrollToBottom();

        // Add thinking indicator
        const thinkingMsg = document.createElement('chat-message');
        thinkingMsg.setAttribute('role', 'assistant');
        thinkingMsg.setAttribute('status', 'thinking');
        this.messagesContainer.appendChild(thinkingMsg);
        this.scrollToBottom();

        // Send message via SSE
        await this.sendMessage(message, thinkingMsg);

        // Re-enable input
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        this.messageInput.focus();
    }

    async sendMessage(message, thinkingElement) {
        this.setStatus('streaming', 'Streaming...');

        try {
            const response = await api.sendMessage(message, this.currentConversationId);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantContent = '';
            let currentToolCards = new Map();
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
                            const result = this.handleStreamEvent(currentEventType, data, thinkingElement, assistantContent, currentToolCards);

                            // Update accumulated content if returned
                            if (result && result.content !== undefined) {
                                assistantContent = result.content;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e, line);
                        }
                    }
                }
            }

            this.setStatus('connected', 'Connected');
            await this.loadConversations();
        } catch (error) {
            console.error('Send message failed:', error);
            thinkingElement.setAttribute('content', 'Sorry, an error occurred. Please try again.');
            thinkingElement.setAttribute('status', 'complete');
            this.setStatus('disconnected', 'Error');
        }
    }

    handleStreamEvent(eventType, data, thinkingElement, currentContent, toolCards) {
        switch (eventType) {
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
                // Show tool cards
                if (data.tool_calls) {
                    for (const tc of data.tool_calls) {
                        const card = document.createElement('tool-call-card');
                        card.setAttribute('tool-name', tc.tool_name);
                        card.setAttribute('status', 'pending');
                        this.messagesContainer.appendChild(card);
                        toolCards.set(tc.tool_name, card);
                    }
                }
                return null;

            case 'tool_executing':
                const execCard = toolCards.get(data.tool_name);
                if (execCard) {
                    execCard.setStatus('executing');
                }
                return null;

            case 'tool_result':
                const resultCard = toolCards.get(data.tool_name);
                if (resultCard) {
                    resultCard.setStatus(data.success ? 'success' : 'error');
                    resultCard.setResult(data.result || data.error);
                }
                return null;

            case 'message_complete':
                thinkingElement.setAttribute('content', data.content || currentContent);
                thinkingElement.setAttribute('status', 'complete');
                return { content: data.content || currentContent };

            case 'message_added':
                // User message was added - nothing to do here
                return null;

            case 'stream_complete':
                // Stream finished
                return null;

            case 'error':
                thinkingElement.setAttribute('content', `Error: ${data.error}`);
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
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    logout() {
        api.logout();
    }

    async showTools() {
        try {
            // Use cached tools or fetch if not available
            if (!this.availableTools) {
                this.availableTools = await api.getTools();
            }
            showToolsModal(this.availableTools);
        } catch (error) {
            console.error('Failed to load tools:', error);
            showToast('Failed to load tools', 'error');
        }
    }
}

export default ChatApp;
