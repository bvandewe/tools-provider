/**
 * ConversationManager - Class-based conversation list manager
 *
 * Handles conversation list rendering, pinning, and CRUD operations.
 *
 * Key responsibilities:
 * - Load and render conversation list in sidebar
 * - Pin/unpin conversations with localStorage persistence
 * - Create, rename, delete conversations
 * - Session list rendering and management
 * - Track current active conversation/session
 *
 * NOTE: Conversation loading is handled by domain/conversation.js which emits
 * CONVERSATION_LOADED events. The handlers/conversation-handlers.js listens
 * to these events and connects WebSocket via the /connect endpoint.
 *
 * @module managers/ConversationManager
 */

import * as bootstrap from 'bootstrap';
import { api } from '../services/api.js';
import { showRenameModal, showDeleteModal, showShareModal, showConversationInfoModal, showToast } from '../services/modals.js';
import { escapeHtml, getPinnedConversations, savePinnedConversations, getPinnedSessions, savePinnedSessions, isMobile } from '../utils/helpers.js';
import { loadConversation } from '../domain/conversation.js';
import { eventBus, Events } from '../core/event-bus.js';

/**
 * @class ConversationManager
 * @description Manages conversation list rendering and operations
 */
export class ConversationManager {
    /**
     * Create ConversationManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {string|null} Current conversation ID */
        this._currentConversationId = null;

        /** @type {string|null} Current session ID */
        this._currentSessionId = null;

        /** @type {string|null} Current session type filter */
        this._currentSessionType = null;

        /** @type {HTMLElement|null} Conversation list container element */
        this._conversationListEl = null;

        /** @type {HTMLElement|null} Welcome message element */
        this._welcomeMessageEl = null;

        /** @type {Function|null} Clear messages function */
        this._clearMessagesFn = null;

        /** @type {Function|null} Render messages function */
        this._renderMessagesFn = null;

        /** @type {Function|null} Close sidebar function */
        this._closeSidebarFn = null;

        /** @type {Function|null} Set draft conversation function */
        this._setDraftConversationFn = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize conversation manager
     * @param {Object} elements - DOM element references
     * @param {Object} functions - Callback functions
     */
    init(elements = {}, functions = {}) {
        if (this._initialized) {
            console.warn('[ConversationManager] Already initialized');
            return;
        }

        this._conversationListEl = elements.conversationList || null;
        this._welcomeMessageEl = elements.welcomeMessage || null;

        this._clearMessagesFn = functions.clearMessages || null;
        this._renderMessagesFn = functions.renderMessages || null;
        this._closeSidebarFn = functions.closeSidebar || null;
        this._setDraftConversationFn = functions.setDraftConversation || null;

        this._initialized = true;
        console.log('[ConversationManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._currentConversationId = null;
        this._currentSessionId = null;
        this._currentSessionType = null;
        this._conversationListEl = null;
        this._welcomeMessageEl = null;
        this._clearMessagesFn = null;
        this._renderMessagesFn = null;
        this._closeSidebarFn = null;
        this._setDraftConversationFn = null;
        this._initialized = false;
        console.log('[ConversationManager] Destroyed');
    }

    // =========================================================================
    // Conversation Loading
    // =========================================================================

    /**
     * Load all conversations for sidebar display
     */
    async loadConversations() {
        try {
            const conversations = await api.getConversations();
            console.debug('[ConversationManager] Loaded conversations:', conversations?.length || 0);
            this.renderConversationList(conversations);
        } catch (error) {
            console.error('Failed to load conversations:', error);
            // Don't clear existing conversations on error
        }
    }

    /**
     * Create a new conversation
     * @param {string|null} definitionId - Optional agent definition ID for the conversation
     * @returns {Promise<string|null>} Conversation ID or null on failure
     */
    async newConversation(definitionId = null) {
        try {
            // POST returns full conversation DTO for optimistic UI
            const conversation = await api.createConversation(definitionId);
            this._currentConversationId = conversation.id;

            // Switch draft context to new conversation
            if (this._setDraftConversationFn) {
                this._setDraftConversationFn(conversation.id);
            }

            if (this._clearMessagesFn) {
                this._clearMessagesFn();
            }

            // Optimistic UI: Add the new conversation directly to the sidebar
            // This avoids race condition with async reconciliator projection
            this.addConversationToList(conversation);

            // Close sidebar on mobile
            if (isMobile() && this._closeSidebarFn) {
                this._closeSidebarFn();
            }

            return conversation.id;
        } catch (error) {
            console.error('Failed to create conversation:', error);
            showToast('Failed to create conversation', 'error');
            return null;
        }
    }

    // =========================================================================
    // Conversation Rendering
    // =========================================================================

    /**
     * Add a single conversation to the list (optimistic UI)
     * Used when creating a new conversation to avoid race condition with async projection
     * @param {Object} conv - Conversation object from POST response
     */
    addConversationToList(conv) {
        if (!this._conversationListEl) {
            console.warn('[ConversationManager] conversationListEl is null');
            return;
        }

        // Remove "No conversations yet" placeholder if present
        const placeholder = this._conversationListEl.querySelector('.text-muted');
        if (placeholder) {
            placeholder.remove();
        }

        // Check if conversation already exists (avoid duplicates)
        const existingItem = this._conversationListEl.querySelector(`[data-conversation-id="${conv.id}"]`);
        if (existingItem) {
            existingItem.classList.add('active');
            return;
        }

        // Create and insert at top (new conversations go first among unpinned)
        const pinnedIds = getPinnedConversations();
        const item = this._createConversationItem(conv, pinnedIds.has(conv.id));
        item.classList.add('active');

        // Find the first unpinned item to insert before it
        // (pinned items are at the top, new unpinned goes after them)
        const firstUnpinned = this._conversationListEl.querySelector('.conversation-item:not(.pinned)');
        if (firstUnpinned) {
            this._conversationListEl.insertBefore(item, firstUnpinned);
        } else {
            // All items are pinned or list is empty, append at end
            this._conversationListEl.appendChild(item);
        }

        // Remove active class from other items
        this._conversationListEl.querySelectorAll('.conversation-item').forEach(el => {
            if (el !== item) {
                el.classList.remove('active');
            }
        });

        console.debug('[ConversationManager] Added new conversation to list:', conv.id);
    }

    /**
     * Render conversations in the sidebar
     * @param {Array} conversations - Array of conversation objects
     */
    renderConversationList(conversations) {
        if (!this._conversationListEl) {
            console.warn('[ConversationManager] conversationListEl is null');
            return;
        }

        // Guard against null/undefined
        if (!conversations || !Array.isArray(conversations)) {
            console.warn('[ConversationManager] Invalid conversations array:', conversations);
            return;
        }

        this._conversationListEl.innerHTML = '';

        if (conversations.length === 0) {
            this._conversationListEl.innerHTML = '<p class="text-muted p-3">No conversations yet</p>';
            return;
        }

        // Get pinned conversations
        const pinnedIds = getPinnedConversations();

        // Sort conversations:
        // - Pinned first, sorted alphabetically by title
        // - Unpinned second, sorted chronologically (most recent first)
        const sortedConversations = [...conversations].sort((a, b) => {
            const aIsPinned = pinnedIds.has(a.id);
            const bIsPinned = pinnedIds.has(b.id);

            // Pinned conversations come first
            if (aIsPinned && !bIsPinned) return -1;
            if (!aIsPinned && bIsPinned) return 1;

            // Both pinned: sort alphabetically by title
            if (aIsPinned && bIsPinned) {
                const titleA = (a.title || 'New conversation').toLowerCase();
                const titleB = (b.title || 'New conversation').toLowerCase();
                return titleA.localeCompare(titleB);
            }

            // Both unpinned: sort chronologically (most recent first)
            const dateA = new Date(a.updated_at || a.created_at || 0);
            const dateB = new Date(b.updated_at || b.created_at || 0);
            return dateB - dateA;
        });

        sortedConversations.forEach(conv => {
            const item = this._createConversationItem(conv, pinnedIds.has(conv.id));
            this._conversationListEl.appendChild(item);
        });
    }

    /**
     * Create a conversation list item element
     * @private
     * @param {Object} conv - Conversation object
     * @param {boolean} isPinned - Whether conversation is pinned
     * @returns {HTMLElement} Conversation item element
     */
    _createConversationItem(conv, isPinned) {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        item.dataset.conversationId = conv.id;

        if (conv.id === this._currentConversationId) {
            item.classList.add('active');
        }
        if (isPinned) {
            item.classList.add('pinned');
        }

        // Check if conversation is completed and cannot continue
        const isCompleted = conv.status === 'completed';
        const continueAfterCompletion = conv.template_config?.continue_after_completion ?? true;
        const showCompletedIndicator = isCompleted && !continueAfterCompletion;

        // Build completion indicator HTML
        const completedIndicator = showCompletedIndicator
            ? '<i class="bi bi-check-circle-fill text-success completed-indicator" data-bs-toggle="tooltip" data-bs-placement="top" title="Completed"></i>'
            : '';

        item.innerHTML = `
            <div class="conversation-content">
                <div class="conversation-title-wrapper">
                    ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                    <i class="bi ${conv.definition_icon || 'bi-robot'} conversation-agent-icon" title="${escapeHtml(conv.definition_name || 'Agent')}"></i>
                    ${completedIndicator}
                    <p class="conversation-title">${escapeHtml(conv.title || 'New conversation')}</p>
                </div>
                <div class="conversation-meta-row">
                    <p class="conversation-meta">${conv.message_count ?? 0} message${(conv.message_count ?? 0) === 1 ? '' : 's'}</p>
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

        // Initialize Bootstrap tooltip for completed indicator
        if (showCompletedIndicator) {
            const tooltipEl = item.querySelector('.completed-indicator');
            if (tooltipEl && bootstrap?.Tooltip) {
                new bootstrap.Tooltip(tooltipEl);
            }
        }

        // Bind event handlers
        this._bindConversationItemEvents(item, conv);

        return item;
    }

    /**
     * Bind event handlers to a conversation item
     * @private
     * @param {HTMLElement} item - Conversation item element
     * @param {Object} conv - Conversation object
     */
    _bindConversationItemEvents(item, conv) {
        // Click on content loads conversation
        item.querySelector('.conversation-content').addEventListener('click', () => {
            loadConversation(conv.id);
            if (isMobile() && this._closeSidebarFn) {
                this._closeSidebarFn();
            }
        });

        // Pin/Unpin button
        item.querySelector('.btn-pin').addEventListener('click', e => {
            e.stopPropagation();
            this._togglePinConversation(conv.id);
        });

        // Share button
        item.querySelector('.btn-share').addEventListener('click', async e => {
            e.stopPropagation();
            try {
                const fullConv = await api.getConversation(conv.id);
                showShareModal(fullConv);
            } catch (error) {
                console.error('Failed to load conversation for sharing:', error);
                showToast('Failed to share conversation', 'error');
            }
        });

        // Info button
        item.querySelector('.btn-info-conv').addEventListener('click', async e => {
            e.stopPropagation();
            try {
                const fullConv = await api.getConversation(conv.id);
                showConversationInfoModal(fullConv);
            } catch (error) {
                console.error('Failed to load conversation details:', error);
                showToast('Failed to load conversation details', 'error');
            }
        });

        // Rename button
        item.querySelector('.btn-rename').addEventListener('click', e => {
            e.stopPropagation();
            showRenameModal(conv.id, conv.title || 'New conversation', (id, newTitle) => {
                this._renameConversation(id, newTitle);
            });
        });

        // Delete button
        item.querySelector('.btn-delete').addEventListener('click', e => {
            e.stopPropagation();
            showDeleteModal(conv.id, conv.title || 'New conversation', id => {
                this._deleteConversation(id);
            });
        });
    }

    // =========================================================================
    // Conversation Operations
    // =========================================================================

    /**
     * Toggle pin state for a conversation
     * @private
     * @param {string} conversationId - Conversation ID to pin/unpin
     */
    _togglePinConversation(conversationId) {
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
        this.loadConversations();
    }

    /**
     * Rename a conversation
     * @private
     * @param {string} conversationId - Conversation ID
     * @param {string} newTitle - New title
     */
    async _renameConversation(conversationId, newTitle) {
        try {
            await api.renameConversation(conversationId, newTitle);
            await this.loadConversations();
            showToast('Conversation renamed', 'success');
        } catch (error) {
            console.error('Failed to rename conversation:', error);
            showToast(error.message || 'Failed to rename conversation', 'error');
        }
    }

    /**
     * Delete a conversation
     * @private
     * @param {string} conversationId - Conversation ID
     */
    async _deleteConversation(conversationId) {
        try {
            await api.deleteConversation(conversationId);

            // If we deleted the current conversation, clear the chat
            if (conversationId === this._currentConversationId) {
                this._currentConversationId = null;
                if (this._clearMessagesFn) {
                    this._clearMessagesFn();
                }
                if (this._welcomeMessageEl) {
                    this._welcomeMessageEl.style.display = '';
                }
            }

            await this.loadConversations();
            showToast('Conversation deleted', 'success');
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            showToast(error.message || 'Failed to delete conversation', 'error');
        }
    }

    /**
     * Delete all unpinned conversations
     * @returns {Promise<{deleted: number, failed: number}>} Delete result
     */
    async deleteAllUnpinnedConversations() {
        try {
            // Get all conversations
            const conversations = await api.getConversations();
            const pinnedIds = getPinnedConversations();

            // Find unpinned conversation IDs
            const unpinnedIds = conversations.filter(c => !pinnedIds.has(c.id)).map(c => c.id);

            if (unpinnedIds.length === 0) {
                showToast('No unpinned conversations to delete', 'info');
                return { deleted: 0, failed: 0 };
            }

            // Delete all unpinned conversations
            const result = await api.deleteConversations(unpinnedIds);

            // If we deleted the current conversation, clear the chat
            if (this._currentConversationId && unpinnedIds.includes(this._currentConversationId)) {
                this._currentConversationId = null;
                if (this._clearMessagesFn) {
                    this._clearMessagesFn();
                }
                if (this._welcomeMessageEl) {
                    this._welcomeMessageEl.style.display = '';
                }
            }

            await this.loadConversations();

            const failed = result.failed_ids?.length || 0;
            if (failed > 0) {
                showToast(`Deleted ${result.deleted_count} conversations, ${failed} failed`, 'warning');
            } else {
                showToast(`Deleted ${result.deleted_count} conversations`, 'success');
            }

            return { deleted: result.deleted_count, failed };
        } catch (error) {
            console.error('Failed to delete unpinned conversations:', error);
            showToast(error.message || 'Failed to delete conversations', 'error');
            return { deleted: 0, failed: -1 };
        }
    }

    // =========================================================================
    // State Getters/Setters
    // =========================================================================

    /**
     * Get current conversation ID
     * @returns {string|null}
     */
    getCurrentConversationId() {
        return this._currentConversationId;
    }

    /**
     * Set current conversation ID
     * @param {string|null} id - Conversation ID
     */
    setCurrentConversationId(id) {
        this._currentConversationId = id;
    }

    /**
     * Set a conversation as active in the sidebar
     * Updates both the internal state and the visual highlighting
     * @param {string} conversationId - Conversation ID to mark as active
     */
    setActiveConversation(conversationId) {
        if (!this._conversationListEl) return;

        // Update internal state
        this._currentConversationId = conversationId;

        // Remove active class from all items
        this._conversationListEl.querySelectorAll('.conversation-item').forEach(el => {
            el.classList.remove('active');
        });

        // Add active class to the matching item
        const activeItem = this._conversationListEl.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
            console.debug('[ConversationManager] Set active conversation:', conversationId);
        }
    }

    // =========================================================================
    // Session List Management
    // =========================================================================

    /**
     * Load sessions for the sidebar
     * @param {string} [sessionType] - Optional filter by session type
     */
    async loadSessions(sessionType = null) {
        this._currentSessionType = sessionType;
        try {
            const sessions = await api.getSessions();
            // Filter by session type if provided
            const filteredSessions = sessionType ? sessions.filter(s => s.session_type === sessionType) : sessions;
            this._renderSessions(filteredSessions);
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    }

    /**
     * Render sessions in the sidebar
     * @private
     * @param {Array} sessions - Array of session objects
     */
    _renderSessions(sessions) {
        if (!this._conversationListEl) return;

        this._conversationListEl.innerHTML = '';

        if (!sessions || sessions.length === 0) {
            this._conversationListEl.innerHTML = '<p class="text-muted p-3">No sessions yet</p>';
            return;
        }

        // Get pinned sessions and sort - pinned first, then by update date
        const pinnedIds = getPinnedSessions();
        const sortedSessions = [...sessions].sort((a, b) => {
            const aIsPinned = pinnedIds.has(a.id);
            const bIsPinned = pinnedIds.has(b.id);
            if (aIsPinned && !bIsPinned) return -1;
            if (!aIsPinned && bIsPinned) return 1;
            // Then by date
            const aDate = new Date(a.updated_at || a.created_at);
            const bDate = new Date(b.updated_at || b.created_at);
            return bDate - aDate;
        });

        sortedSessions.forEach(session => {
            const isPinned = pinnedIds.has(session.id);
            const item = this._createSessionItem(session, isPinned);
            this._conversationListEl.appendChild(item);
        });
    }

    /**
     * Create a session list item element
     * @private
     * @param {Object} session - Session object
     * @param {boolean} isPinned - Whether session is pinned
     * @returns {HTMLElement} Session item element
     */
    _createSessionItem(session, isPinned) {
        const item = document.createElement('div');
        item.className = 'conversation-item session-item';
        item.dataset.sessionId = session.id;

        if (session.id === this._currentSessionId) {
            item.classList.add('active');
        }
        if (isPinned) {
            item.classList.add('pinned');
        }

        // Format timestamp
        const timestamp = new Date(session.updated_at || session.created_at);
        const timeStr = timestamp.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });

        // Session type icon
        const typeIcons = {
            learning: 'bi-mortarboard',
            thought: 'bi-lightbulb',
            validation: 'bi-check-circle',
        };
        const typeIcon = typeIcons[session.session_type] || 'bi-circle';

        // Session status
        const isActive = session.status === 'active';
        const statusBadge = isActive ? '<span class="badge bg-success ms-2">Active</span>' : '';

        // Title from config or default
        const title = session.config?.category_name || session.config?.topic || `${session.session_type} session`;

        item.innerHTML = `
            <div class="conversation-content">
                <div class="conversation-title-wrapper">
                    ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                    <i class="bi ${typeIcon} me-2 text-muted session-type-icon"></i>
                    <p class="conversation-title">${escapeHtml(title)}${statusBadge}</p>
                </div>
                <div class="conversation-meta-row">
                    <p class="conversation-meta">${timeStr}</p>
                    <div class="conversation-actions">
                        <button class="btn-action btn-pin ${isPinned ? 'active' : ''}" title="${isPinned ? 'Unpin' : 'Pin'}">
                            <i class="bi bi-pin${isPinned ? '-fill' : ''}"></i>
                        </button>
                        <button class="btn-action btn-delete" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Bind event handlers
        this._bindSessionItemEvents(item, session);

        return item;
    }

    /**
     * Bind event handlers to a session item
     * @private
     * @param {HTMLElement} item - Session item element
     * @param {Object} session - Session object
     */
    _bindSessionItemEvents(item, session) {
        // Click to load session
        item.addEventListener('click', e => {
            // Don't trigger on action button clicks
            if (e.target.closest('.conversation-actions')) return;
            this.loadSession(session.id);
        });

        // Pin button
        const pinBtn = item.querySelector('.btn-pin');
        pinBtn?.addEventListener('click', e => {
            e.stopPropagation();
            this._toggleSessionPin(session.id);
        });

        // Delete button
        const deleteBtn = item.querySelector('.btn-delete');
        deleteBtn?.addEventListener('click', e => {
            e.stopPropagation();
            const sessionTitle = session.config?.category_name || session.config?.topic || `${session.session_type} session`;
            showDeleteModal(session.id, sessionTitle, () => this._deleteSession(session.id));
        });
    }

    /**
     * Load a session (view its history in the chat area)
     * @param {string} sessionId - Session ID to load
     */
    async loadSession(sessionId) {
        try {
            // Get session details which includes conversation_id and items
            const session = await api.getSession(sessionId);
            this._currentSessionId = sessionId;

            // Try to load conversation messages first
            let hasMessages = false;
            if (session.conversation_id) {
                const conversation = await api.getConversation(session.conversation_id);
                if (conversation.messages && conversation.messages.length > 0) {
                    if (this._renderMessagesFn) {
                        this._renderMessagesFn(conversation.messages);
                    }
                    hasMessages = true;
                }
            }

            // If no conversation messages, try to reconstruct from session items
            if (!hasMessages && session.items && session.items.length > 0) {
                const reconstructedMessages = this._reconstructSessionMessages(session);
                if (reconstructedMessages.length > 0) {
                    if (this._renderMessagesFn) {
                        this._renderMessagesFn(reconstructedMessages);
                    }
                    hasMessages = true;
                }
            }

            // If still no messages, show a placeholder
            if (!hasMessages) {
                if (this._clearMessagesFn) {
                    this._clearMessagesFn();
                }
                const placeholder = document.createElement('div');
                placeholder.className = 'text-muted text-center p-4';
                placeholder.innerHTML = `
                    <i class="bi bi-chat-square-text fs-1 d-block mb-2"></i>
                    <p>No messages in this session yet.</p>
                    <small>Session status: ${session.status}</small>
                `;
                const container = document.getElementById('messages-container');
                container?.appendChild(placeholder);
            }

            // Mark active in list
            document.querySelectorAll('.session-item').forEach(el => {
                el.classList.toggle('active', el.dataset.sessionId === sessionId);
            });

            // Close sidebar on mobile
            if (isMobile() && this._closeSidebarFn) {
                this._closeSidebarFn();
            }

            console.log('[ConversationManager] Session loaded:', sessionId, session);
        } catch (error) {
            console.error('Failed to load session:', error);
            showToast('Failed to load session', 'error');
        }
    }

    /**
     * Reconstruct chat messages from session items
     * @private
     * @param {Object} session - Session object with items
     * @returns {Array} Array of message objects for rendering
     */
    _reconstructSessionMessages(session) {
        const messages = [];

        for (const item of session.items || []) {
            // Add agent's question/content as assistant message
            if (item.content) {
                messages.push({
                    role: 'assistant',
                    content: item.content,
                });
            }

            // Add user's response if present
            if (item.response !== undefined && item.response !== null) {
                let responseText = item.response;
                // Handle structured responses
                if (typeof item.response === 'object') {
                    responseText = item.response.value || item.response.text || JSON.stringify(item.response);
                }
                messages.push({
                    role: 'user',
                    content: String(responseText),
                });
            }
        }

        return messages;
    }

    /**
     * Toggle pin state for a session
     * @private
     * @param {string} sessionId - Session ID
     */
    _toggleSessionPin(sessionId) {
        const pinnedIds = getPinnedSessions();

        if (pinnedIds.has(sessionId)) {
            pinnedIds.delete(sessionId);
            showToast('Session unpinned', 'info');
        } else {
            pinnedIds.add(sessionId);
            showToast('Session pinned', 'success');
        }

        savePinnedSessions(pinnedIds);
        this.loadSessions(this._currentSessionType);
    }

    /**
     * Delete a session
     * @private
     * @param {string} sessionId - Session ID
     */
    async _deleteSession(sessionId) {
        try {
            await api.terminateSession(sessionId);

            // If we deleted the current session, clear the view
            if (sessionId === this._currentSessionId) {
                this._currentSessionId = null;
                if (this._clearMessagesFn) {
                    this._clearMessagesFn();
                }
                if (this._welcomeMessageEl) {
                    this._welcomeMessageEl.style.display = '';
                }
            }

            // Remove from pinned if present
            const pinnedIds = getPinnedSessions();
            if (pinnedIds.has(sessionId)) {
                pinnedIds.delete(sessionId);
                savePinnedSessions(pinnedIds);
            }

            await this.loadSessions(this._currentSessionType);
            showToast('Session deleted', 'success');
        } catch (error) {
            console.error('Failed to delete session:', error);
            showToast(error.message || 'Failed to delete session', 'error');
        }
    }

    /**
     * Get current session ID
     * @returns {string|null}
     */
    getCurrentSessionId() {
        return this._currentSessionId;
    }

    /**
     * Set current session ID
     * @param {string|null} id - Session ID
     */
    setCurrentSessionId(id) {
        this._currentSessionId = id;
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    /**
     * Get current conversation ID (getter alias)
     * @returns {string|null}
     */
    get currentConversationId() {
        return this._currentConversationId;
    }

    /**
     * Get current session ID (getter alias)
     * @returns {string|null}
     */
    get currentSessionId() {
        return this._currentSessionId;
    }
}

// Export singleton instance
export const conversationManager = new ConversationManager();
export default conversationManager;
