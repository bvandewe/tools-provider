/**
 * Conversation Manager
 * Handles conversation list rendering and pinning.
 *
 * NOTE: Conversation loading is handled by domain/conversation.js which emits
 * CONVERSATION_LOADED events. The handlers/conversation-handlers.js listens
 * to these events and connects WebSocket via the /connect endpoint.
 */

import { api } from '../services/api.js';
import { showRenameModal, showDeleteModal, showShareModal, showConversationInfoModal, showToast } from '../services/modals.js';
import { escapeHtml, getPinnedConversations, savePinnedConversations, getPinnedSessions, savePinnedSessions, isMobile } from '../utils/helpers.js';
import { clearMessages } from './message-renderer.js';
import { closeSidebar } from './sidebar-manager.js';
import { loadConversation } from '../domain/conversation.js';

// =============================================================================
// State
// =============================================================================

let currentConversationId = null;
let conversationListEl = null;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize conversation manager
 * @param {Object} elements - DOM element references
 * @param {Object} callbacks - Callback functions (unused, kept for API compatibility)
 */
export function initConversationManager(elements, callbacks) {
    conversationListEl = elements.conversationList;
}

// =============================================================================
// Conversation Loading
// =============================================================================

/**
 * Load all conversations for sidebar display
 */
export async function loadConversations() {
    try {
        const conversations = await api.getConversations();
        console.debug('[ConversationManager] Loaded conversations:', conversations?.length || 0);
        renderConversationList(conversations);
    } catch (error) {
        console.error('Failed to load conversations:', error);
        // Don't clear existing conversations on error
    }
}

/**
 * Create a new conversation
 * @param {string|null} definitionId - Optional agent definition ID for the conversation
 */
export async function newConversation(definitionId = null) {
    try {
        // POST returns full conversation DTO for optimistic UI
        const conversation = await api.createConversation(definitionId);
        currentConversationId = conversation.id;

        // Switch draft context to new conversation
        setDraftConversation(conversation.id);

        clearMessages();

        // Optimistic UI: Add the new conversation directly to the sidebar
        // This avoids race condition with async reconciliator projection
        addConversationToList(conversation);

        // Close sidebar on mobile
        if (isMobile()) {
            closeSidebar();
        }

        return conversation.id;
    } catch (error) {
        console.error('Failed to create conversation:', error);
        showToast('Failed to create conversation', 'error');
        return null;
    }
}

// =============================================================================
// Conversation Rendering
// =============================================================================

/**
 * Add a single conversation to the list (optimistic UI)
 * Used when creating a new conversation to avoid race condition with async projection
 * @param {Object} conv - Conversation object from POST response
 */
export function addConversationToList(conv) {
    if (!conversationListEl) {
        console.warn('[ConversationManager] conversationListEl is null');
        return;
    }

    // Remove "No conversations yet" placeholder if present
    const placeholder = conversationListEl.querySelector('.text-muted');
    if (placeholder) {
        placeholder.remove();
    }

    // Check if conversation already exists (avoid duplicates)
    const existingItem = conversationListEl.querySelector(`[data-conversation-id="${conv.id}"]`);
    if (existingItem) {
        existingItem.classList.add('active');
        return;
    }

    // Create and insert at top (new conversations go first among unpinned)
    const pinnedIds = getPinnedConversations();
    const item = createConversationItem(conv, pinnedIds.has(conv.id));
    item.classList.add('active');

    // Find the first unpinned item to insert before it
    // (pinned items are at the top, new unpinned goes after them)
    const firstUnpinned = conversationListEl.querySelector('.conversation-item:not(.pinned)');
    if (firstUnpinned) {
        conversationListEl.insertBefore(item, firstUnpinned);
    } else {
        // All items are pinned or list is empty, append at end
        conversationListEl.appendChild(item);
    }

    // Remove active class from other items
    conversationListEl.querySelectorAll('.conversation-item').forEach(el => {
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
export function renderConversationList(conversations) {
    if (!conversationListEl) {
        console.warn('[ConversationManager] conversationListEl is null');
        return;
    }

    // Guard against null/undefined
    if (!conversations || !Array.isArray(conversations)) {
        console.warn('[ConversationManager] Invalid conversations array:', conversations);
        return;
    }

    conversationListEl.innerHTML = '';

    if (conversations.length === 0) {
        conversationListEl.innerHTML = '<p class="text-muted p-3">No conversations yet</p>';
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
        const item = createConversationItem(conv, pinnedIds.has(conv.id));
        conversationListEl.appendChild(item);
    });
}

/**
 * Create a conversation list item element
 * @param {Object} conv - Conversation object
 * @param {boolean} isPinned - Whether conversation is pinned
 * @returns {HTMLElement} Conversation item element
 */
function createConversationItem(conv, isPinned) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.conversationId = conv.id;

    if (conv.id === currentConversationId) {
        item.classList.add('active');
    }
    if (isPinned) {
        item.classList.add('pinned');
    }

    item.innerHTML = `
        <div class="conversation-content">
            <div class="conversation-title-wrapper">
                ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                <i class="bi ${conv.definition_icon || 'bi-robot'} conversation-agent-icon" title="${escapeHtml(conv.definition_name || 'Agent')}"></i>
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

    // Bind event handlers
    bindConversationItemEvents(item, conv);

    return item;
}

/**
 * Bind event handlers to a conversation item
 * @param {HTMLElement} item - Conversation item element
 * @param {Object} conv - Conversation object
 */
function bindConversationItemEvents(item, conv) {
    // Click on content loads conversation
    item.querySelector('.conversation-content').addEventListener('click', () => {
        loadConversation(conv.id);
        if (isMobile()) {
            closeSidebar();
        }
    });

    // Pin/Unpin button
    item.querySelector('.btn-pin').addEventListener('click', e => {
        e.stopPropagation();
        togglePinConversation(conv.id);
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
            renameConversation(id, newTitle);
        });
    });

    // Delete button
    item.querySelector('.btn-delete').addEventListener('click', e => {
        e.stopPropagation();
        showDeleteModal(conv.id, conv.title || 'New conversation', id => {
            deleteConversation(id);
        });
    });
}

// =============================================================================
// Conversation Operations
// =============================================================================

/**
 * Toggle pin state for a conversation
 * @param {string} conversationId - Conversation ID to pin/unpin
 */
function togglePinConversation(conversationId) {
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
    loadConversations();
}

/**
 * Rename a conversation
 * @param {string} conversationId - Conversation ID
 * @param {string} newTitle - New title
 */
async function renameConversation(conversationId, newTitle) {
    try {
        await api.renameConversation(conversationId, newTitle);
        await loadConversations();
        showToast('Conversation renamed', 'success');
    } catch (error) {
        console.error('Failed to rename conversation:', error);
        showToast(error.message || 'Failed to rename conversation', 'error');
    }
}

/**
 * Delete a conversation
 * @param {string} conversationId - Conversation ID
 */
async function deleteConversation(conversationId) {
    try {
        await api.deleteConversation(conversationId);

        // If we deleted the current conversation, clear the chat
        if (conversationId === currentConversationId) {
            currentConversationId = null;
            clearMessages();
            if (welcomeMessageEl) {
                welcomeMessageEl.style.display = '';
            }
        }

        await loadConversations();
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
export async function deleteAllUnpinnedConversations() {
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
        if (currentConversationId && unpinnedIds.includes(currentConversationId)) {
            currentConversationId = null;
            clearMessages();
            if (welcomeMessageEl) {
                welcomeMessageEl.style.display = '';
            }
        }

        await loadConversations();

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

// =============================================================================
// State Getters/Setters
// =============================================================================

/**
 * Get current conversation ID
 * @returns {string|null}
 */
export function getCurrentConversationId() {
    return currentConversationId;
}

/**
 * Set current conversation ID
 * @param {string|null} id - Conversation ID
 */
export function setCurrentConversationId(id) {
    currentConversationId = id;
}

/**
 * Set a conversation as active in the sidebar
 * Updates both the internal state and the visual highlighting
 * @param {string} conversationId - Conversation ID to mark as active
 */
export function setActiveConversation(conversationId) {
    if (!conversationListEl) return;

    // Update internal state
    currentConversationId = conversationId;

    // Remove active class from all items
    conversationListEl.querySelectorAll('.conversation-item').forEach(el => {
        el.classList.remove('active');
    });

    // Add active class to the matching item
    const activeItem = conversationListEl.querySelector(`[data-conversation-id="${conversationId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
        console.debug('[ConversationManager] Set active conversation:', conversationId);
    }
}

// =============================================================================
// Session List Management
// =============================================================================

// Current session tracking
let currentSessionId = null;
let currentSessionType = null;

/**
 * Load sessions for the sidebar
 * @param {string} [sessionType] - Optional filter by session type
 */
export async function loadSessions(sessionType = null) {
    currentSessionType = sessionType;
    try {
        const sessions = await api.getSessions();
        // Filter by session type if provided
        const filteredSessions = sessionType ? sessions.filter(s => s.session_type === sessionType) : sessions;
        renderSessions(filteredSessions);
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

/**
 * Render sessions in the sidebar
 * @param {Array} sessions - Array of session objects
 */
function renderSessions(sessions) {
    if (!conversationListEl) return;

    conversationListEl.innerHTML = '';

    if (!sessions || sessions.length === 0) {
        conversationListEl.innerHTML = '<p class="text-muted p-3">No sessions yet</p>';
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
        const item = createSessionItem(session, isPinned);
        conversationListEl.appendChild(item);
    });
}

/**
 * Create a session list item element
 * @param {Object} session - Session object
 * @param {boolean} isPinned - Whether session is pinned
 * @returns {HTMLElement} Session item element
 */
function createSessionItem(session, isPinned) {
    const item = document.createElement('div');
    item.className = 'conversation-item session-item';
    item.dataset.sessionId = session.id;

    if (session.id === currentSessionId) {
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
    bindSessionItemEvents(item, session);

    return item;
}

/**
 * Bind event handlers to a session item
 * @param {HTMLElement} item - Session item element
 * @param {Object} session - Session object
 */
function bindSessionItemEvents(item, session) {
    // Click to load session
    item.addEventListener('click', e => {
        // Don't trigger on action button clicks
        if (e.target.closest('.conversation-actions')) return;
        loadSession(session.id);
    });

    // Pin button
    const pinBtn = item.querySelector('.btn-pin');
    pinBtn?.addEventListener('click', e => {
        e.stopPropagation();
        toggleSessionPin(session.id);
    });

    // Delete button
    const deleteBtn = item.querySelector('.btn-delete');
    deleteBtn?.addEventListener('click', e => {
        e.stopPropagation();
        const sessionTitle = session.config?.category_name || session.config?.topic || `${session.session_type} session`;
        showDeleteModal(session.id, sessionTitle, () => deleteSession(session.id));
    });
}

/**
 * Load a session (view its history in the chat area)
 * @param {string} sessionId - Session ID to load
 */
export async function loadSession(sessionId) {
    try {
        // Get session details which includes conversation_id and items
        const session = await api.getSession(sessionId);
        currentSessionId = sessionId;

        // Try to load conversation messages first
        let hasMessages = false;
        if (session.conversation_id) {
            const conversation = await api.getConversation(session.conversation_id);
            if (conversation.messages && conversation.messages.length > 0) {
                renderMessages(conversation.messages);
                hasMessages = true;
            }
        }

        // If no conversation messages, try to reconstruct from session items
        if (!hasMessages && session.items && session.items.length > 0) {
            const reconstructedMessages = reconstructSessionMessages(session);
            if (reconstructedMessages.length > 0) {
                renderMessages(reconstructedMessages);
                hasMessages = true;
            }
        }

        // If still no messages, show a placeholder
        if (!hasMessages) {
            clearMessages();
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
        if (isMobile()) {
            closeSidebar();
        }

        console.log('[ConversationManager] Session loaded:', sessionId, session);
    } catch (error) {
        console.error('Failed to load session:', error);
        showToast('Failed to load session', 'error');
    }
}

/**
 * Reconstruct chat messages from session items
 * @param {Object} session - Session object with items
 * @returns {Array} Array of message objects for rendering
 */
function reconstructSessionMessages(session) {
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
 * @param {string} sessionId - Session ID
 */
function toggleSessionPin(sessionId) {
    const pinnedIds = getPinnedSessions();

    if (pinnedIds.has(sessionId)) {
        pinnedIds.delete(sessionId);
        showToast('Session unpinned', 'info');
    } else {
        pinnedIds.add(sessionId);
        showToast('Session pinned', 'success');
    }

    savePinnedSessions(pinnedIds);
    loadSessions(currentSessionType);
}

/**
 * Delete a session
 * @param {string} sessionId - Session ID
 */
async function deleteSession(sessionId) {
    try {
        await api.terminateSession(sessionId);

        // If we deleted the current session, clear the view
        if (sessionId === currentSessionId) {
            currentSessionId = null;
            clearMessages();
            if (welcomeMessageEl) {
                welcomeMessageEl.style.display = '';
            }
        }

        // Remove from pinned if present
        const pinnedIds = getPinnedSessions();
        if (pinnedIds.has(sessionId)) {
            pinnedIds.delete(sessionId);
            savePinnedSessions(pinnedIds);
        }

        await loadSessions(currentSessionType);
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
export function getCurrentSessionId() {
    return currentSessionId;
}

/**
 * Set current session ID
 * @param {string|null} id - Session ID
 */
export function setCurrentSessionId(id) {
    currentSessionId = id;
}
